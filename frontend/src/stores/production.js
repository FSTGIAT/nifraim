import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useProductionStore = defineStore('production', () => {
  const currentFile = ref(null)
  const loading = ref(false)
  const uploading = ref(false)
  const error = ref(null)

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
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה במחיקת קובץ פרודוקציה'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    currentFile, loading, uploading, error,
    fetchCurrent, uploadProduction, removeCurrent,
  }
})
