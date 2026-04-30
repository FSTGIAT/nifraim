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

  async function listRuns(credentialId, limit = 10) {
    const params = { limit }
    if (credentialId) params.credential_id = credentialId
    const res = await api.get('/portal-automation/runs', { params })
    runs.value = res.data
    return res.data
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
    loading,
    error,
    fetchPortalKinds,
    fetchCredentials,
    createCredential,
    updateCredential,
    deleteCredential,
    listRuns,
    fetchRun,
    runNow,
    submitOtp,
    reset,
  }
})
