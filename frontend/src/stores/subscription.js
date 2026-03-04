import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useSubscriptionStore = defineStore('subscription', () => {
  const status = ref(null) // { is_active, plan, expires_at, status }
  const loading = ref(false)

  async function fetchStatus() {
    loading.value = true
    try {
      const res = await api.get('/subscription/status')
      status.value = res.data
      return res.data
    } catch {
      status.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  function reset() {
    status.value = null
  }

  return { status, loading, fetchStatus, reset }
})
