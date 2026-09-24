import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useSubscriptionStore = defineStore('subscription', () => {
  const status = ref(null) // { is_active, plan, expires_at, status, next_charge_at, last4_digits, card_brand, is_recurring }
  const loading = ref(false)
  // True when the last status call FAILED (server down, 5xx, network) — as
  // opposed to the server answering `is_active: false`. The router must not
  // read "couldn't ask" as "subscription expired": that sent paying agents to
  // the renew page on every deploy/restart window.
  const fetchFailed = ref(false)

  async function fetchStatus() {
    loading.value = true
    try {
      const res = await api.get('/subscription/status')
      status.value = res.data
      fetchFailed.value = false
      return res.data
    } catch {
      status.value = null
      fetchFailed.value = true
      return null
    } finally {
      loading.value = false
    }
  }

  async function cancelSubscription() {
    try {
      const res = await api.post('/subscription/cancel')
      await fetchStatus()
      return res.data
    } catch (e) {
      throw new Error(e.response?.data?.detail || 'שגיאה בביטול המנוי')
    }
  }

  async function renewSubscription() {
    try {
      const res = await api.post('/subscription/renew')
      return res.data // { payment_url, user_id }
    } catch (e) {
      throw new Error(e.response?.data?.detail || 'שגיאה בחידוש המנוי')
    }
  }

  function reset() {
    status.value = null
    fetchFailed.value = false
  }

  return { status, loading, fetchFailed, fetchStatus, cancelSubscription, renewSubscription, reset }
})
