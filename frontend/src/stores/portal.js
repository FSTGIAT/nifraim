import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'
import portalApi from '../api/portalClient.js'

export const usePortalStore = defineStore('portal', () => {
  // ─── Agent-side state ───
  const links = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Filter / sort / pagination
  const searchQuery = ref('')
  const statusFilter = ref('all') // 'all' | 'active' | 'expired' | 'revoked'
  const sortBy = ref('created_at') // 'created_at' | 'customer_name' | 'last_accessed_at' | 'status'
  const sortDir = ref('desc')
  const currentPage = ref(1)
  const pageSize = 20

  // ─── Customer-side state ───
  const dashboardData = ref(null)
  const customerName = ref('')
  const authenticated = ref(false)
  const history = ref([])

  // ─── Derived status per link ───
  function linkStatus(link) {
    if (!link.is_active) return 'revoked'
    if (link.expires_at && new Date(link.expires_at) < new Date()) return 'expired'
    return 'active'
  }

  // ─── Computed pipeline ───
  const enrichedLinks = computed(() =>
    links.value.map(l => ({ ...l, _status: linkStatus(l) }))
  )

  const statusCounts = computed(() => {
    const counts = { all: enrichedLinks.value.length, active: 0, expired: 0, revoked: 0 }
    for (const l of enrichedLinks.value) counts[l._status]++
    return counts
  })

  const filteredLinks = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    const status = statusFilter.value
    const normalizeId = (v) => String(v || '').replace(/^0+/, '')
    return enrichedLinks.value.filter(l => {
      if (status !== 'all' && l._status !== status) return false
      if (!q) return true
      const name = (l.customer_name || '').toLowerCase()
      const email = (l.customer_email || '').toLowerCase()
      const id = String(l.customer_id_number || '')
      return name.includes(q) ||
        email.includes(q) ||
        id.includes(q) ||
        normalizeId(id).includes(normalizeId(q))
    })
  })

  const sortedLinks = computed(() => {
    const dir = sortDir.value === 'asc' ? 1 : -1
    const by = sortBy.value
    const copy = [...filteredLinks.value]
    copy.sort((a, b) => {
      let av, bv
      if (by === 'status') { av = a._status; bv = b._status }
      else if (by === 'customer_name') { av = (a.customer_name || '').toLowerCase(); bv = (b.customer_name || '').toLowerCase() }
      else { av = a[by] || ''; bv = b[by] || '' }
      if (av < bv) return -1 * dir
      if (av > bv) return 1 * dir
      return 0
    })
    return copy
  })

  const totalPages = computed(() =>
    Math.max(1, Math.ceil(sortedLinks.value.length / pageSize))
  )

  const paginatedLinks = computed(() => {
    const start = (currentPage.value - 1) * pageSize
    return sortedLinks.value.slice(start, start + pageSize)
  })

  function setSearch(q) {
    searchQuery.value = q
    currentPage.value = 1
  }

  function setStatusFilter(s) {
    statusFilter.value = s
    currentPage.value = 1
  }

  function setSort(column) {
    if (sortBy.value === column) {
      sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortBy.value = column
      sortDir.value = column === 'customer_name' ? 'asc' : 'desc'
    }
  }

  function setPage(p) {
    currentPage.value = Math.min(totalPages.value, Math.max(1, p))
  }

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
    // state
    links, loading, error,
    searchQuery, statusFilter, sortBy, sortDir, currentPage, pageSize,
    dashboardData, customerName, authenticated, history,
    // computed
    enrichedLinks, statusCounts, filteredLinks, sortedLinks, paginatedLinks, totalPages,
    // control
    setSearch, setStatusFilter, setSort, setPage, linkStatus,
    // agent
    fetchLinks, generateLink, revokeLink, sendEmail, getCustomerInfo,
    // customer
    accessPortal, fetchDashboard, fetchHistory, logout,
  }
})
