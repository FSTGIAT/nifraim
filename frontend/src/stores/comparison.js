import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'

// One comparison, not one per category.
//
// This store used to hold `results.gemel_hishtalmut` and `results.insurance`
// side by side with an `activeCategory` selecting between them, so the tab
// could only ever render half the agent's picture and they had to toggle to
// see the rest. Worse, the two halves double-counted: measured on live data,
// the same portfolio produced 802 customer rows across the two categories for
// 624 actual customers, and 64 clients were reported unpaid in one category
// while being paid in the other.
//
// The backend now returns a single merged comparison covering every company
// and both categories, scoped by company coverage instead. See
// services/comparison_service.compute_comparison.
export const useComparisonStore = defineStore('comparison', () => {
  const result = ref(null)
  const lastComputedAt = ref(null)

  const uploading = ref(false)
  const error = ref(null)
  const filterStatus = ref('')
  const searchQuery = ref('')

  // Ephemeral single-file drill — a comparison of ONE commission file the
  // user clicked, shown temporarily WITHOUT being persisted server-side and
  // WITHOUT overwriting `result` — so the merged all-companies "full
  // picture" always stays the default the dashboard falls back to.
  const singleFileView = ref(null) // { result, uploadId, filename }

  const hasResult = computed(() => !!result.value)

  function clearSingleFileView() {
    singleFileView.value = null
  }

  function resetResult() {
    result.value = null
    lastComputedAt.value = null
    clearSingleFileView()
  }

  async function uploadAndCompare(productionFile, commissionFile, prodPassword, commPassword) {
    uploading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('production_file', productionFile)
      formData.append('commission_file', commissionFile)
      if (prodPassword) formData.append('production_password', prodPassword)
      if (commPassword) formData.append('commission_password', commPassword)

      const res = await api.post('/comparison/dual-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      result.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהעלאת הקבצים'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function compareExisting(productionUploadId, commissionUploadId, { persist = false, filename = '' } = {}) {
    uploading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('production_upload_id', productionUploadId)
      formData.append('commission_upload_id', commissionUploadId)
      formData.append('persist', persist ? 'true' : 'false')
      const res = await api.post('/comparison/compute', formData)
      if (persist) {
        result.value = res.data
      } else {
        singleFileView.value = {
          result: res.data,
          uploadId: commissionUploadId,
          filename: filename || res.data?.commission_company_source || '',
        }
      }
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בחישוב ההשוואה'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function compareWithProduction(commissionFiles, commPassword, onProgress) {
    uploading.value = true
    error.value = null
    try {
      const formData = new FormData()
      // Support single file or array of files
      const files = Array.isArray(commissionFiles) ? commissionFiles : [commissionFiles]
      for (const file of files) {
        formData.append('commission_files', file)
      }
      if (commPassword) formData.append('commission_password', commPassword)

      const res = await api.post('/comparison/compare-with-production', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: onProgress,
      })
      result.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהשוואה מול פרודוקציה'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function autoCompare(productionUploadId, commissionUploadId) {
    uploading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('production_upload_id', productionUploadId)
      formData.append('commission_upload_id', commissionUploadId)
      // Navigation drill — ephemeral, never clobbers the merged picture.
      formData.append('persist', 'false')
      const res = await api.post('/comparison/compute', formData)
      singleFileView.value = {
        result: res.data,
        uploadId: commissionUploadId,
        filename: res.data?.commission_company_source || '',
      }
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בחישוב ההשוואה'
      throw e
    } finally {
      uploading.value = false
    }
  }

  const fetchingLatest = ref(false)

  async function fetchLatest() {
    fetchingLatest.value = true
    try {
      const res = await api.get('/comparison/latest')
      const payload = res.data?.result || null
      if (payload) {
        result.value = payload
        lastComputedAt.value = res.data?.computed_at || null
      }
      return payload
    } catch (e) {
      // Don't surface — empty state is fine. Quietly log to error for debug.
      console.warn('fetchLatest failed', e)
      return null
    } finally {
      fetchingLatest.value = false
    }
  }

  // Cross-company reconciliation overview, feeds the "סיכום לפי חברה"
  // table at the top of the Comparison tab.
  const companySummary = ref(null)
  const fetchingSummary = ref(false)

  async function fetchCompanySummary() {
    fetchingSummary.value = true
    try {
      const res = await api.get('/comparison/company-summary')
      companySummary.value = res.data || null
      return companySummary.value
    } catch (e) {
      console.warn('fetchCompanySummary failed', e)
      return null
    } finally {
      fetchingSummary.value = false
    }
  }

  // Recompute + persist the merged all-companies comparison on the server,
  // then rehydrate it and the cross-company overview.
  async function refreshMerged() {
    try {
      const res = await api.post('/comparison/refresh')
      await fetchLatest()
      fetchCompanySummary()
      return res.data?.persisted || []
    } catch (e) {
      console.warn('refreshMerged failed', e)
      return []
    }
  }

  function reset() {
    resetResult()
    error.value = null
    filterStatus.value = ''
    searchQuery.value = ''
  }

  return {
    result, hasResult,
    uploading, error, filterStatus, searchQuery,
    lastComputedAt, fetchingLatest,
    companySummary, fetchingSummary, fetchCompanySummary,
    singleFileView, clearSingleFileView, refreshMerged,
    resetResult,
    uploadAndCompare, compareExisting, compareWithProduction, autoCompare,
    fetchLatest, reset,
  }
})
