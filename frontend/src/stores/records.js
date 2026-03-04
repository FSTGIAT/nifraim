import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import api from '../api/client.js'

export const useRecordsStore = defineStore('records', () => {
  const records = ref([])
  const summary = ref({
    paid_match: 0,
    paid_mismatch: 0,
    unpaid: 0,
    cancelled: 0,
    no_data: 0,
    matched: 0,
    missing_from_report: 0,
    extra_in_report: 0,
    total: 0,
    total_expected: 0,
    total_actual: 0,
    total_difference: 0,
  })
  const pagination = reactive({
    page: 1,
    perPage: 50,
    total: 0,
    pages: 1,
  })
  const filters = reactive({
    search: '',
    company: '',
    status: '',
    product: '',
    uploadId: '',
    sortBy: 'last_name',
    sortDir: 'asc',
  })
  const loading = ref(false)

  async function fetchRecords() {
    loading.value = true
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.perPage,
        sort_by: filters.sortBy,
        sort_dir: filters.sortDir,
      }
      if (filters.search) params.search = filters.search
      if (filters.company) params.company = filters.company
      if (filters.status) params.status = filters.status
      if (filters.product) params.product = filters.product
      if (filters.uploadId) params.upload_id = filters.uploadId

      const res = await api.get('/records', { params })
      records.value = res.data.items
      pagination.total = res.data.total
      pagination.pages = res.data.pages
    } finally {
      loading.value = false
    }
  }

  async function fetchSummary() {
    const params = {}
    if (filters.uploadId) params.upload_id = filters.uploadId
    const res = await api.get('/records/summary', { params })
    summary.value = res.data
  }

  async function fetchClientRecords(idNumber) {
    const res = await api.get(`/records/client/${idNumber}`)
    return res.data
  }

  function setPage(p) {
    pagination.page = p
    fetchRecords()
  }

  function setSort(col) {
    if (filters.sortBy === col) {
      filters.sortDir = filters.sortDir === 'asc' ? 'desc' : 'asc'
    } else {
      filters.sortBy = col
      filters.sortDir = 'asc'
    }
    pagination.page = 1
    fetchRecords()
  }

  function applyFilters() {
    pagination.page = 1
    fetchRecords()
    fetchSummary()
  }

  function resetFilters() {
    filters.search = ''
    filters.company = ''
    filters.status = ''
    filters.product = ''
    filters.uploadId = ''
    filters.sortBy = 'last_name'
    filters.sortDir = 'asc'
    applyFilters()
  }

  return {
    records,
    summary,
    pagination,
    filters,
    loading,
    fetchRecords,
    fetchSummary,
    fetchClientRecords,
    setPage,
    setSort,
    applyFilters,
    resetFilters,
  }
})
