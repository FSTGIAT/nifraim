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

  function selectCategory(cat) {
    activeCategory.value = cat
  }

  function clearCategory() {
    activeCategory.value = null
  }

  function hasResultFor(cat) {
    return !!results[cat]
  }

  function resetCategory(cat) {
    if (cat) {
      results[cat] = null
    }
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

  async function compareExisting(productionUploadId, commissionUploadId) {
    uploading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('production_upload_id', productionUploadId)
      formData.append('commission_upload_id', commissionUploadId)
      if (activeCategory.value) formData.append('category', activeCategory.value)
      const res = await api.post('/comparison/compute', formData)
      if (activeCategory.value) {
        results[activeCategory.value] = res.data
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

  function reset() {
    activeCategory.value = null
    results.gemel_hishtalmut = null
    results.insurance = null
    error.value = null
    filterStatus.value = ''
    searchQuery.value = ''
  }

  return {
    activeCategory, results, result,
    uploading, error, filterStatus, searchQuery,
    selectCategory, clearCategory, hasResultFor, resetCategory,
    uploadAndCompare, compareExisting, compareWithProduction, reset,
  }
})
