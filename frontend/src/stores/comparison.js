import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import api from '../api/client.js'

export const useComparisonStore = defineStore('comparison', () => {
  const activeCategory = ref(null)  // 'gemel_hishtalmut' | 'insurance' | null
  const results = reactive({ gemel_hishtalmut: null, insurance: null })
  const result = computed(() => activeCategory.value ? results[activeCategory.value] : null)

  const uploading = ref(false)
  const error = ref(null)
  const filterStatus = ref('')
  const searchQuery = ref('')

  // Ephemeral single-file drill — a comparison of ONE commission file the
  // user clicked, shown temporarily WITHOUT being persisted server-side and
  // WITHOUT overwriting results[] — so the merged all-companies "full
  // picture" always stays the default the dashboard falls back to.
  const singleFileView = ref(null) // { result, uploadId, filename, category }

  function clearSingleFileView() {
    singleFileView.value = null
  }

  function selectCategory(cat) {
    if (activeCategory.value !== cat) clearSingleFileView()
    activeCategory.value = cat
  }

  function clearCategory() {
    activeCategory.value = null
    clearSingleFileView()
  }

  function hasResultFor(cat) {
    return !!results[cat]
  }

  function resetCategory(cat) {
    if (cat) {
      results[cat] = null
    }
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
      // Store in active category if set
      if (activeCategory.value) {
        results[activeCategory.value] = res.data
      }
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
      if (activeCategory.value) formData.append('category', activeCategory.value)
      formData.append('persist', persist ? 'true' : 'false')
      const res = await api.post('/comparison/compute', formData)
      if (persist) {
        if (activeCategory.value) {
          results[activeCategory.value] = res.data
        }
      } else {
        singleFileView.value = {
          result: res.data,
          uploadId: commissionUploadId,
          filename: filename || res.data?.commission_company_source || '',
          category: activeCategory.value,
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
      if (activeCategory.value) formData.append('category', activeCategory.value)

      const res = await api.post('/comparison/compare-with-production', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: onProgress,
      })
      if (activeCategory.value) {
        results[activeCategory.value] = res.data
      }
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
      const cat = res.data.commission_category || 'gemel_hishtalmut'
      activeCategory.value = cat
      singleFileView.value = {
        result: res.data,
        uploadId: commissionUploadId,
        filename: res.data?.commission_company_source || '',
        category: cat,
      }
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בחישוב ההשוואה'
      throw e
    } finally {
      uploading.value = false
    }
  }

  // Per-category timestamp of when the persisted comparison was computed
  const lastComputedAt = reactive({ gemel_hishtalmut: null, insurance: null })
  const fetchingLatest = ref(false)

  async function fetchLatest(category) {
    if (!category) return null
    fetchingLatest.value = true
    try {
      const res = await api.get('/comparison/latest', { params: { category } })
      const payload = res.data?.result || null
      if (payload) {
        results[category] = payload
        lastComputedAt[category] = res.data?.computed_at || null
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

  // Cross-company reconciliation overview (both categories), feeds the
  // "סיכום לפי חברה" table at the top of the Comparison tab.
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
  // then rehydrate the active category and the cross-company overview.
  async function refreshMerged() {
    try {
      const res = await api.post('/comparison/refresh')
      if (activeCategory.value) await fetchLatest(activeCategory.value)
      fetchCompanySummary()
      return res.data?.persisted || []
    } catch (e) {
      console.warn('refreshMerged failed', e)
      return []
    }
  }

  function reset() {
    activeCategory.value = null
    results.gemel_hishtalmut = null
    results.insurance = null
    error.value = null
    filterStatus.value = ''
    searchQuery.value = ''
    clearSingleFileView()
  }

  return {
    activeCategory, results, result,
    uploading, error, filterStatus, searchQuery,
    lastComputedAt, fetchingLatest,
    companySummary, fetchingSummary, fetchCompanySummary,
    singleFileView, clearSingleFileView, refreshMerged,
    selectCategory, clearCategory, hasResultFor, resetCategory,
    uploadAndCompare, compareExisting, compareWithProduction, autoCompare,
    fetchLatest, reset,
  }
})
