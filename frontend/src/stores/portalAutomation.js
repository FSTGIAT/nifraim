import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

const TERMINAL_STATUSES = new Set(['success', 'failed', 'timeout'])

export const usePortalAutomationStore = defineStore('portalAutomation', () => {
  const credentials = ref([])
  const portalKinds = ref([])
  const runs = ref([])
  const activeRunId = ref(null)
  const activeRun = ref(null)
  const twilioNumber = ref(null)   // null when no Twilio number is provisioned
  const phoneForward = ref({ token: null, url: null })
  const otpInbox = ref([])
  const loading = ref(false)
  const error = ref(null)
  // Local worker liveness (the agent's Israeli machine that runs the automation)
  const workerStatus = ref({ online: false, last_seen: null, hostname: null, current_job: null, update_pending: false })

  let pollHandle = null

  async function fetchWorkerStatus() {
    try {
      const res = await api.get('/portal-automation/worker/status')
      workerStatus.value = res.data
    } catch (_) {
      workerStatus.value = { online: false, last_seen: null, hostname: null, current_job: null, update_pending: false }
    }
    return workerStatus.value
  }

  // "עדכן עובד" button — ask the local worker to git-pull + restart itself (no git
  // or console needed). The worker reads the flag on its next heartbeat (≤15s).
  async function requestWorkerUpdate() {
    const res = await api.post('/portal-automation/worker/request-update')
    return res.data
  }

  async function fetchPortalKinds() {
    const res = await api.get('/portal-automation/portal-kinds')
    portalKinds.value = res.data
  }

  async function fetchCredentials() {
    loading.value = true
    error.value = null
    try {
      const res = await api.get('/portal-automation/credentials')
      credentials.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בטעינת אישורים'
    } finally {
      loading.value = false
    }
  }

  async function createCredential(payload) {
    error.value = null
    try {
      const res = await api.post('/portal-automation/credentials', payload)
      credentials.value.push(res.data)
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה ביצירת אישור'
      throw e
    }
  }

  async function updateCredential(id, payload) {
    error.value = null
    try {
      const res = await api.put(`/portal-automation/credentials/${id}`, payload)
      const idx = credentials.value.findIndex((c) => c.id === id)
      if (idx >= 0) credentials.value[idx] = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בעדכון'
      throw e
    }
  }

  async function deleteCredential(id) {
    await api.delete(`/portal-automation/credentials/${id}`)
    credentials.value = credentials.value.filter((c) => c.id !== id)
  }

  async function updateSchedule(id, scheduleKind) {
    error.value = null
    // Optimistic update so the drag feels instantaneous.
    const before = credentials.value.find((c) => c.id === id)?.schedule_kind
    const idx = credentials.value.findIndex((c) => c.id === id)
    if (idx >= 0) credentials.value[idx] = { ...credentials.value[idx], schedule_kind: scheduleKind }
    try {
      const res = await api.patch(`/portal-automation/credentials/${id}/schedule`, { schedule_kind: scheduleKind })
      if (idx >= 0) credentials.value[idx] = res.data
      return res.data
    } catch (e) {
      // Roll back on failure
      if (idx >= 0 && before !== undefined) {
        credentials.value[idx] = { ...credentials.value[idx], schedule_kind: before }
      }
      error.value = e.response?.data?.detail || 'שגיאה בעדכון התזמון'
      throw e
    }
  }

  async function listRuns(credentialId, limit = 10) {
    const params = { limit }
    if (credentialId) params.credential_id = credentialId
    const res = await api.get('/portal-automation/runs', { params })
    runs.value = res.data
    return res.data
  }

  /** If a run is still in-flight on the server (pending/running/awaiting_otp/
   *  downloading/parsing), hydrate it into the store + start polling so the
   *  UI reflects the live state on page reload. */
  const ACTIVE = new Set(['pending', 'running', 'awaiting_otp', 'downloading', 'parsing'])
  async function hydrateActiveRun() {
    try {
      const recent = await listRuns(null, 5)
      const live = recent.find((r) => ACTIVE.has(r.status))
      if (live && !activeRunId.value) {
        activeRunId.value = live.id
        activeRun.value = live
        _startPolling(live.id)
      }
      return live || null
    } catch {
      return null
    }
  }

  function _stopPolling() {
    if (pollHandle) {
      clearInterval(pollHandle)
      pollHandle = null
    }
  }

  async function fetchRun(runId) {
    const res = await api.get(`/portal-automation/runs/${runId}`)
    activeRun.value = res.data
    return res.data
  }

  function _startPolling(runId) {
    _stopPolling()
    let polls = 0
    // ~10 min at 1.5s. A real run can outlast a short window: harel_savings
    // alone is ~2 min, and the CONSOLIDATED Harel (one login → מוצרי צבירה גמל
    // + מגוון + נפרעים) or a slow Migdal/Phoenix export runs several minutes.
    // If the poller stops while the run is still going, activeRunId clears and
    // the card falls back to the credential's PREVIOUS last_run_status — which
    // flashes a stale שגיאה even though the run then succeeds. Give it real room.
    const maxPolls = 400

    pollHandle = setInterval(async () => {
      polls += 1
      try {
        const data = await fetchRun(runId)
        // Only give up early on a TRUE terminal status. On the safety cap, do a
        // final authoritative re-fetch so we don't surface a mid-run stale state.
        if (TERMINAL_STATUSES.has(data.status) || polls >= maxPolls) {
          _stopPolling()
          activeRunId.value = null
          // Refresh credential list so last_run_status pill updates
          await fetchCredentials()
          // Race-proof the pill: fetchCredentials() can fire microseconds before the
          // runner commits the credential's last_run_status (runner.py finally-block),
          // re-surfacing a stale שגיאה even though the run SUCCEEDED (observed on
          // menora נפרעים). The just-finished run's own terminal status is
          // authoritative for that credential — apply it after the refetch so it wins.
          if (TERMINAL_STATUSES.has(data.status) && data.credential_id) {
            const idx = credentials.value.findIndex(
              (c) => String(c.id) === String(data.credential_id),
            )
            if (idx >= 0) {
              credentials.value[idx] = {
                ...credentials.value[idx],
                last_run_status: data.status,
                last_error:
                  data.status === 'success'
                    ? null
                    : credentials.value[idx].last_error || data.error_message || null,
              }
            }
          }
        }
      } catch (e) {
        _stopPolling()
        activeRunId.value = null
      }
    }, 1500)
  }

  async function runNow(credentialId) {
    error.value = null
    try {
      const res = await api.post(`/portal-automation/credentials/${credentialId}/run`)
      activeRunId.value = res.data.run_id
      activeRun.value = {
        id: res.data.run_id,
        credential_id: credentialId,
        status: 'pending',
        stage: null,
      }
      _startPolling(res.data.run_id)
      return res.data.run_id
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהפעלת ריצה'
      throw e
    }
  }

  // ── "Run all portals" batch ────────────────────────────────────────────
  const activeBatchId = ref(null)
  const activeBatch = ref(null)          // PortalRunBatchOut (status, runs[], ...)
  const batchJustFinished = ref(null)    // set to the finished batch for one tick
  const latestBatch = ref(null)          // most recent batch (any status) or null — drives activation checklist step 4
  const batchToastSeenId = ref(null)     // batch id the global toast already announced (survives component remounts)
  let batchPollHandle = null
  const BATCH_TERMINAL = new Set(['success', 'partial', 'failed'])
  const BATCH_MAX_AGE_MS = 2 * 60 * 60 * 1000 // don't re-adopt batches older than 2h — likely orphaned by a dead worker

  function _stopBatchPolling() {
    if (batchPollHandle) {
      clearInterval(batchPollHandle)
      batchPollHandle = null
    }
  }

  async function fetchLatestBatch() {
    try {
      const res = await api.get('/portal-automation/batches/latest')
      latestBatch.value = res.data || null
    } catch {
      latestBatch.value = null
    }
    return latestBatch.value
  }

  async function fetchBatch(batchId) {
    const res = await api.get(`/portal-automation/batches/${batchId}`)
    activeBatch.value = res.data
    // Mirror the currently-running child into activeRun so PortalOtpModal
    // (bound to activeRun) targets the right run during a sequential batch.
    const cur = res.data.current_run_id
    if (cur) {
      const child = (res.data.runs || []).find((r) => r.id === cur)
      if (child) {
        activeRun.value = child
        activeRunId.value = child.id
      }
    }
    return res.data
  }

  function _startBatchPolling(batchId) {
    _stopBatchPolling()
    let polls = 0
    let consecutiveFailures = 0
    const maxPolls = 2400 // generous — a full batch can take many minutes
    const maxConsecutiveFailures = 40 // ~1 min of solid errors before giving up
    batchPollHandle = setInterval(async () => {
      polls += 1
      try {
        const data = await fetchBatch(batchId)
        consecutiveFailures = 0
        if (BATCH_TERMINAL.has(data.status)) {
          _stopBatchPolling()
          activeRun.value = null
          activeRunId.value = null
          activeBatchId.value = null
          latestBatch.value = data
          await fetchCredentials()
          // Refresh every consumer store BEFORE announcing completion, so
          // anything reacting to batchJustFinished already sees fresh data.
          await _refreshAfterBatch(data)
          // A newer batch may have started while we were refreshing — never
          // announce a stale completion over it.
          if (!activeBatchId.value || activeBatchId.value === batchId) {
            batchJustFinished.value = data
          }
        } else if (polls >= maxPolls) {
          // Poll budget exhausted while the batch is still non-terminal —
          // release the UI (button, progress strip) but do NOT announce a
          // completion that didn't happen.
          _stopBatchPolling()
          activeRun.value = null
          activeRunId.value = null
          activeBatchId.value = null
          activeBatch.value = null
        }
      } catch (e) {
        // Transient fetch errors (redeploy blip, laptop sleep/resume) must not
        // kill the poll that owns all post-batch refresh. Give up only after a
        // sustained outage, and clear state so the UI can recover in-session.
        consecutiveFailures += 1
        if (consecutiveFailures >= maxConsecutiveFailures) {
          _stopBatchPolling()
          activeRun.value = null
          activeRunId.value = null
          activeBatchId.value = null
          activeBatch.value = null
        }
      }
    }, 1500)
  }

  // Post-batch side effects live HERE (not in a component) so they run even
  // if the user navigated away from the automation tab mid-batch. Stores are
  // imported lazily inside the function to avoid circular imports.
  async function _refreshAfterBatch(_batchData) {
    try {
      const [{ useComparisonStore }, { useProductionStore }, { useUploadsStore }] =
        await Promise.all([
          import('./comparison.js'),
          import('./production.js'),
          import('./uploads.js'),
        ])
      const comparisonStore = useComparisonStore()
      const productionStore = useProductionStore()
      const uploadsStore = useUploadsStore()
      // Tolerate individual failures — a partial refresh is still better
      // than a stale screen.
      await Promise.allSettled([
        comparisonStore.fetchLatest('gemel_hishtalmut'),
        comparisonStore.fetchLatest('insurance'),
        comparisonStore.fetchCompanySummary(),
        productionStore.refreshAll(),
        uploadsStore.fetchUploads(),
      ])
    } catch (e) {
      console.warn('post-batch refresh failed', e)
    }
  }

  /** Resume a run-all batch that's still in-flight on the server — the batch
   *  analogue of hydrateActiveRun, so a page reload mid-batch keeps polling
   *  and the post-batch refresh still fires. */
  async function hydrateBatch() {
    const latest = await fetchLatestBatch()
    if (latest && !BATCH_TERMINAL.has(latest.status)) {
      // Skip batches that are non-terminal only because a worker died mid-run
      // (the orphan reaper runs on the next POST /batches/run, not on reads) —
      // adopting one would lock the run-all button for the whole poll budget.
      // started_at is naive UTC from the backend — anchor it before parsing
      const rawStart = latest.started_at
        ? (/[zZ]|[+-]\d\d:?\d\d$/.test(latest.started_at) ? latest.started_at : latest.started_at + 'Z')
        : null
      const startedAt = rawStart ? new Date(rawStart).getTime() : 0
      const tooOld = startedAt && Date.now() - startedAt > BATCH_MAX_AGE_MS
      const alreadyPolling = activeBatchId.value === latest.id && batchPollHandle
      if (!tooOld && !alreadyPolling) {
        activeBatchId.value = latest.id
        activeBatch.value = latest
        _startBatchPolling(latest.id)
      }
    }
    return latest
  }

  async function runAllPortals() {
    error.value = null
    try {
      const res = await api.post('/portal-automation/batches/run')
      activeBatchId.value = res.data.batch_id
      activeBatch.value = { id: res.data.batch_id, status: 'pending', runs: [] }
      _startBatchPolling(res.data.batch_id)
      return res.data.batch_id
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהפעלת הורדה אוטומטית'
      throw e
    }
  }

  async function submitOtp(runId, otp) {
    await api.post(`/portal-automation/runs/${runId}/submit-otp`, { otp })
  }

  async function cancelRun(runId) {
    if (!runId) return
    try {
      await api.post(`/portal-automation/runs/${runId}/cancel`)
    } catch (e) {
      console.warn('cancelRun failed', e)
    } finally {
      _stopPolling()
      activeRunId.value = null
      activeRun.value = null
    }
  }

  async function fetchTwilioNumber() {
    const res = await api.get('/portal-automation/twilio-numbers/me')
    twilioNumber.value = res.data || null
    return twilioNumber.value
  }

  async function fetchOtpInbox(limit = 20) {
    const res = await api.get('/portal-automation/otp-inbox', { params: { limit } })
    otpInbox.value = res.data
    return res.data
  }

  async function provisionTwilio() {
    error.value = null
    try {
      const res = await api.post('/portal-automation/twilio-numbers/provision')
      twilioNumber.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה ברכישת מספר Twilio'
      throw e
    }
  }

  async function releaseTwilio() {
    error.value = null
    await api.delete('/portal-automation/twilio-numbers/me')
    twilioNumber.value = null
  }

  async function fetchPhoneForward() {
    const res = await api.get('/portal-automation/phone-forward/me')
    phoneForward.value = res.data || { token: null, url: null }
    return phoneForward.value
  }

  async function regeneratePhoneForwardToken() {
    error.value = null
    try {
      const res = await api.post('/portal-automation/phone-forward/token/regenerate')
      phoneForward.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה ביצירת מפתח'
      throw e
    }
  }

  async function testPhoneForward(message) {
    const res = await api.post('/portal-automation/phone-forward/test', { message })
    return res.data
  }

  async function syncContactPhone(credentialId) {
    error.value = null
    try {
      const res = await api.post(`/portal-automation/credentials/${credentialId}/sync-contact-phone`)
      activeRunId.value = res.data.run_id
      activeRun.value = {
        id: res.data.run_id,
        credential_id: credentialId,
        kind: 'phone_change',
        status: 'pending',
        stage: null,
      }
      _startPolling(res.data.run_id)
      return res.data.run_id
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בעדכון מספר טלפון בפורטל'
      throw e
    }
  }

  // keepBatch: soft reset for tab unmount — stops single-run polling/UI state
  // but leaves an in-flight batch (pending/running) polling in the background
  // so its completion still refreshes the app. Terminal batches are cleared.
  function reset({ keepBatch = false } = {}) {
    _stopPolling()
    activeRunId.value = null
    activeRun.value = null
    const batchLive =
      keepBatch && activeBatch.value && !BATCH_TERMINAL.has(activeBatch.value.status)
    if (!batchLive) {
      _stopBatchPolling()
      activeBatchId.value = null
      activeBatch.value = null
    }
  }

  return {
    credentials,
    portalKinds,
    runs,
    activeRunId,
    activeRun,
    activeBatchId,
    activeBatch,
    batchJustFinished,
    batchToastSeenId,
    latestBatch,
    fetchLatestBatch,
    hydrateBatch,
    runAllPortals,
    fetchBatch,
    twilioNumber,
    phoneForward,
    otpInbox,
    loading,
    error,
    workerStatus,
    fetchWorkerStatus,
    requestWorkerUpdate,
    fetchPortalKinds,
    fetchCredentials,
    createCredential,
    updateCredential,
    deleteCredential,
    updateSchedule,
    listRuns,
    hydrateActiveRun,
    fetchRun,
    runNow,
    submitOtp,
    cancelRun,
    fetchTwilioNumber,
    fetchOtpInbox,
    provisionTwilio,
    releaseTwilio,
    fetchPhoneForward,
    regeneratePhoneForwardToken,
    testPhoneForward,
    syncContactPhone,
    reset,
  }
})
