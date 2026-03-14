import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'
import portalApi from '../api/portalClient.js'

export const usePortalStore = defineStore('portal', () => {
  // Agent-side state
  const links = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Customer-side state
  const dashboardData = ref(null)
  const customerName = ref('')
  const authenticated = ref(false)
  const history = ref([])

  // ─── Agent-side methods ───

  async function fetchLinks() {
    loading.value = true
    error.value = null
    try {
      const res = await api.get('/portal/links')
      links.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בטעינת קישורים'
    } finally {
      loading.value = false
    }
  }

  async function generateLink(data) {
    error.value = null
    try {
      const res = await api.post('/portal/generate', data)
      links.value.unshift(res.data)
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה ביצירת קישור'
      throw e
    }
  }

  async function revokeLink(token) {
    error.value = null
    try {
      await api.delete(`/portal/${token}`)
      const idx = links.value.findIndex(l => l.token === token)
      if (idx !== -1) links.value[idx].is_active = false
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בביטול קישור'
      throw e
    }
  }

  async function sendEmail(token) {
    error.value = null
    try {
      await api.post(`/portal/${token}/send-email`)
      return true
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בשליחת אימייל'
      throw e
    }
  }

  async function getCustomerInfo(idNumber) {
    try {
      const res = await api.get(`/portal/customer-info/${idNumber}`)
      return res.data
    } catch {
      return { name: '', email: '' }
    }
  }

  // ─── Customer-side methods ───

  async function accessPortal(token, password) {
    error.value = null
    try {
      const res = await portalApi.post(`/${token}/access`, { password })
      sessionStorage.setItem('portal_token', res.data.session_token)
      customerName.value = res.data.customer_name
      authenticated.value = true
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'סיסמה שגויה או קישור לא פעיל'
      throw e
    }
  }

  async function fetchDashboard(token) {
    loading.value = true
    error.value = null
    try {
      const res = await portalApi.get(`/${token}/dashboard`)
      dashboardData.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בטעינת הנתונים'
      authenticated.value = false
      sessionStorage.removeItem('portal_token')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory(token) {
    try {
      const res = await portalApi.get(`/${token}/history`)
      history.value = res.data.snapshots || []
    } catch {
      history.value = []
    }
  }

  function logout() {
    sessionStorage.removeItem('portal_token')
    authenticated.value = false
    dashboardData.value = null
    customerName.value = ''
    history.value = []
  }

  return {
    links, loading, error,
    dashboardData, customerName, authenticated, history,
    fetchLinks, generateLink, revokeLink, sendEmail, getCustomerInfo,
    accessPortal, fetchDashboard, fetchHistory, logout,
  }
})
