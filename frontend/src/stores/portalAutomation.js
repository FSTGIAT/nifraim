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

  let pollHandle = null

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
    const maxPolls = 80 // ~120s at 1.5s intervals

    pollHandle = setInterval(async () => {
      polls += 1
      try {
        const data = await fetchRun(runId)
        if (TERMINAL_STATUSES.has(data.status) || polls >= maxPolls) {
          _stopPolling()
          activeRunId.value = null
          // Refresh credential list so last_run_status pill updates
          await fetchCredentials()
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

  function reset() {
    _stopPolling()
    activeRunId.value = null
    activeRun.value = null
  }

  return {
    credentials,
    portalKinds,
    runs,
    activeRunId,
    activeRun,
    twilioNumber,
    phoneForward,
    otpInbox,
    loading,
    error,
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
