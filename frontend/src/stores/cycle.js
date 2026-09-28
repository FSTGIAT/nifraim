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
