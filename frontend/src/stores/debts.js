import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'

export const useDebtsStore = defineStore('debts', () => {
  const debts = ref([])
  const summary = ref(null)
  const loading = ref(false)
  const error = ref('')

  // Filters
  const statusFilter = ref('open')
  const companyFilter = ref('')
  const searchQuery = ref('')

  const filteredDebts = computed(() => {
    let list = debts.value
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      list = list.filter(d =>
        d.customer_name.toLowerCase().includes(q) ||
        d.customer_id_number.includes(q) ||
        d.company_name.toLowerCase().includes(q)
      )
    }
    if (companyFilter.value) {
      list = list.filter(d => d.company_name === companyFilter.value)
    }
    return list
  })

  // Group debts by company
  const groupedByCompany = computed(() => {
    const groups = {}
    for (const d of filteredDebts.value) {
      if (!groups[d.company_name]) {
        groups[d.company_name] = { company: d.company_name, category: d.category, debts: [], total: 0, count: 0 }
      }
      groups[d.company_name].debts.push(d)
      groups[d.company_name].total += d.expected_amount
      groups[d.company_name].count++
    }
    return Object.values(groups).sort((a, b) => b.total - a.total)
  })

  async function fetchDebts() {
    loading.value = true
    error.value = ''
    try {
      const params = {}
      if (statusFilter.value) params.status = statusFilter.value
      const res = await api.get('/debts', { params })
      debts.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בטעינת חובות'
    } finally {
      loading.value = false
    }
  }

  async function fetchSummary() {
    try {
      const res = await api.get('/debts/summary')
      summary.value = res.data
    } catch (e) {
      // silent
    }
  }

  async function updateStatus(debtId, status) {
    try {
      await api.patch(`/debts/${debtId}/status`, { status })
      // Update local state
      const idx = debts.value.findIndex(d => d.id === debtId)
      if (idx >= 0) {
        if (status !== statusFilter.value && statusFilter.value) {
          debts.value.splice(idx, 1)
        } else {
          debts.value[idx].status = status
        }
      }
      await fetchSummary()
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בעדכון סטטוס'
    }
  }

  async function bulkUpdateStatus(ids, status) {
    try {
      await api.patch('/debts/bulk-status', { ids, status })
      await fetchDebts()
      await fetchSummary()
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בעדכון סטטוס'
    }
  }

  async function sendEmail(companyName) {
    try {
      const res = await api.post('/debts/send-email', { company_name: companyName })
      return res.data
    } catch (e) {
      throw e.response?.data?.detail || 'שגיאה בשליחת אימייל'
    }
  }

  function exportExcel() {
    const params = statusFilter.value ? `?status=${statusFilter.value}` : ''
    const token = localStorage.getItem('token')
    window.open(`/api/debts/export/excel${params}`, '_blank')
  }

  return {
    debts, summary, loading, error,
    statusFilter, companyFilter, searchQuery,
    filteredDebts, groupedByCompany,
    fetchDebts, fetchSummary, updateStatus, bulkUpdateStatus, sendEmail, exportExcel,
  }
})
