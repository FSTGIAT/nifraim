import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'
import { usePortalAutomationStore } from './portalAutomation.js'

// Monthly cycle (מחזור) — mirrors GET /api/cycle/status, the server's single
// truth for: the Production tab lock, the manual-production window, the
// automation tab's "next cycle" card, and the cycle notification modal.
// Never derive any of it client-side (backend/app/services/cycle_service.py).

const HE_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']

export function monthName(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${HE_MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

export function shortDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getDate()}.${d.getMonth() + 1}`
}

// Countdowns run on the SERVER's clock: an agent PC whose clock is off (or a
// local simulation's CYCLE_NOW_OVERRIDE) must not show a wrong countdown.
let _skewMs = 0
export function cycleNow() { return Date.now() + _skewMs }
export function cycleSkewMs() { return _skewMs }

export const useCycleStore = defineStore('cycle', () => {
  const status = ref(null)
  const loaded = ref(false)
  const notifications = ref([])
  let pollTimer = null

  const locked = computed(() => !!status.value?.locked)
  const manualUploadOpen = computed(() => !!status.value?.manual_upload_open)
  const workerWaiting = computed(() => !!status.value?.worker_waiting)
  const cycleRunning = computed(() => ['pending', 'running'].includes(status.value?.cycle_batch_status))

  async function fetchStatus() {
    try {
      const prev = status.value?.cycle_batch_status
      const res = await api.get('/cycle/status')
      if (res.data?.server_now) _skewMs = Date.parse(res.data.server_now) - Date.now()
      status.value = res.data
      // The worker just claimed this month's cycle batch → hand it to the
      // live progress widget (it deliberately ignores pending batches).
      if (prev === 'pending' && res.data?.cycle_batch_status === 'running') {
        usePortalAutomationStore().hydrateBatch()
      }
    } catch (_) {
      // Fail OPEN for display (the server still enforces every gate).
    } finally {
      loaded.value = true
    }
    _syncPolling()
    return status.value
  }

  // While the month's cycle batch is queued/running, keep the cards live.
  function _syncPolling() {
    const want = cycleRunning.value
    if (want && !pollTimer) {
      pollTimer = setInterval(fetchStatus, 30000)
    } else if (!want && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function fetchNotifications() {
    try {
      const res = await api.get('/cycle/notifications')
      notifications.value = res.data || []
    } catch (_) {
      notifications.value = []
    }
    return notifications.value
  }

  async function markSeen(id) {
    notifications.value = notifications.value.filter((n) => n.id !== id)
    try {
      await api.post(`/cycle/notifications/${id}/seen`)
    } catch (_) { /* shown again next load — harmless */ }
  }

  function reset() {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = null
    status.value = null
    loaded.value = false
    notifications.value = []
  }

  return {
    status, loaded, notifications,
    locked, manualUploadOpen, workerWaiting, cycleRunning,
    fetchStatus, fetchNotifications, markSeen, reset,
  }
})

// ── מסלקה timeline wording, shared by every surface (server fields only) ──
// The rule: a שיוך form submitted by the 26th → the מסלקה production arrives on
// the 15th of the next month; from the 27th on → the 15th of the month after.
export const MASLAKA_RULE = 'טופס שיוך שמוגש עד ה-26 בחודש — הפרודוקציה מהמסלקה מגיעה ב-15 בחודש הבא. מה-27 ואילך — ב-15 בחודש שאחריו.'

export function signupLine(st) {
  return st?.signup_at ? `נרשמתם ב-${shortDate(st.signup_at)}` : ''
}

/** { title, sub, tone } describing where the agent stands with the מסלקה. */
export function maslakaLine(st) {
  if (!st) return null
  const s = st.maslaka_status
  if (s === 'approved') {
    return {
      tone: 'ok',
      title: `פרודוקציה מהמסלקה ב-${shortDate(st.maslaka_first_auto)}`,
      sub: [st.maslaka_submitted_at && `הוגש ב-${shortDate(st.maslaka_submitted_at)}`, st.maslaka_approved_at && `אושר ב-${shortDate(st.maslaka_approved_at)}`].filter(Boolean).join(' · '),
    }
  }
  if (s === 'submitted') {
    return {
      tone: 'wait',
      title: `פרודוקציה מהמסלקה ב-${shortDate(st.maslaka_first_auto)}`,
      sub: `הוגש ב-${shortDate(st.maslaka_submitted_at)} · ממתין לאישור המסלקה`,
    }
  }
  return {
    tone: 'todo',
    title: `הגישו את טופס השיוך עד ${shortDate(st.maslaka_deadline)}`,
    sub: `והפרודוקציה מהמסלקה תגיע ב-${shortDate(st.maslaka_if_submitted_now)}`,
  }
}
