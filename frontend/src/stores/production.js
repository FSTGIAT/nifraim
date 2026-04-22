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
      // Verify the active production is actually gone before clearing local state.
      const res = await api.get('/production/current')
      if (res.data) {
        error.value = 'המחיקה נכשלה — קובץ הפרודוקציה עדיין קיים'
        currentFile.value = res.data
        throw new Error(error.value)
      }
      currentFile.value = null
      analytics.value = null
      comparisonResult.value = null
      // Refresh history so the deleted file drops off the comparison picker.
      await fetchHistory()
    } catch (e) {
      if (!error.value) {
        error.value = e.response?.data?.detail || 'שגיאה במחיקת קובץ פרודוקציה'
      }
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

  // Parse "YYYYMM" from a production filename (Hebrew month + 2/4-digit year).
  // Returns null if the filename doesn't carry a recognisable month.
  function monthOrdinalFromFilename(filename) {
    if (!filename) return null
    const HEBREW_MONTHS = {
      'ינואר': 1, 'פברואר': 2, 'מרץ': 3, 'מרס': 3, 'אפריל': 4,
      'מאי': 5, 'יוני': 6, 'יולי': 7, 'אוגוסט': 8,
      'ספטמבר': 9, 'אוקטובר': 10, 'נובמבר': 11, 'דצמבר': 12,
    }
    const name = filename.replace(/\.(xlsx?|xls)$/i, '')
    let month = null
    for (const [he, num] of Object.entries(HEBREW_MONTHS)) {
      if (name.includes(he)) { month = num; break }
    }
    if (!month) return null
    const yearMatch = name.match(/\b(20)?(\d{2})\b/)
    const year = yearMatch
      ? (yearMatch[1] ? parseInt(yearMatch[1] + yearMatch[2]) : 2000 + parseInt(yearMatch[2]))
      : new Date().getFullYear()
    return year * 100 + month
  }

  function _filenameForId(id) {
    if (currentFile.value?.id === id) return currentFile.value.filename
    return history.value.find(f => f.id === id)?.filename || ''
  }

  async function compareProductions(currentId, previousId) {
    comparing.value = true
    error.value = null
    try {
      // Always diff newer-month → older-month regardless of upload order.
      // If the caller-supplied "previous" file actually represents a later month,
      // swap the two IDs so backend semantics (new = current - previous) match the user's mental model.
      const currOrd = monthOrdinalFromFilename(_filenameForId(currentId))
      const prevOrd = monthOrdinalFromFilename(_filenameForId(previousId))
      if (currOrd != null && prevOrd != null && prevOrd > currOrd) {
        ;[currentId, previousId] = [previousId, currentId]
      }
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
