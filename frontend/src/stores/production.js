import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useProductionStore = defineStore('production', () => {
  const currentFile = ref(null)
  const loading = ref(false)
  const uploading = ref(false)
  const justUploaded = ref(false)
  const error = ref(null)

  // Analytics
  const analytics = ref(null)
  const analyticsLoading = ref(false)

  // History & comparison
  const history = ref([])
  const comparisonResult = ref(null)
  const comparing = ref(false)

  async function fetchCurrent() {
    loading.value = true
    error.value = null
    try {
      const res = await api.get('/production/current')
      currentFile.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בטעינת קובץ פרודוקציה'
    } finally {
      loading.value = false
    }
  }

  async function uploadProduction(file, password, onProgress) {
    uploading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (password) formData.append('password', password)

      const res = await api.post('/production/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: onProgress,
      })
      currentFile.value = res.data
      justUploaded.value = true
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהעלאת קובץ פרודוקציה'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function removeCurrent() {
    loading.value = true
    error.value = null
    try {
      await api.delete('/production/current')
      currentFile.value = null
      analytics.value = null
      history.value = []
      comparisonResult.value = null
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה במחיקת קובץ פרודוקציה'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchAnalytics() {
    analyticsLoading.value = true
    try {
      const res = await api.get('/production/analytics')
      analytics.value = res.data
    } catch (e) {
      // silent
    } finally {
      analyticsLoading.value = false
    }
  }

  async function fetchHistory() {
    try {
      const res = await api.get('/production/history')
      history.value = res.data
    } catch (e) {
      // silent
    }
  }

  async function compareProductions(currentId, previousId) {
    comparing.value = true
    error.value = null
    try {
      const res = await api.post('/production/compare', {
        current_upload_id: currentId,
        previous_upload_id: previousId,
      })
      comparisonResult.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהשוואת קבצים'
      throw e
    } finally {
      comparing.value = false
    }
  }

  function resetComparison() {
    comparisonResult.value = null
  }

  return {
    currentFile, loading, uploading, justUploaded, error,
    analytics, analyticsLoading,
    history, comparisonResult, comparing,
    fetchCurrent, uploadProduction, removeCurrent,
    fetchAnalytics, fetchHistory, compareProductions, resetComparison,
  }
})
