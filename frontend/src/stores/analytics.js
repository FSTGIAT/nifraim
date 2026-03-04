import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useAnalyticsStore = defineStore('analytics', () => {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchAnalytics(uploadId = null) {
    loading.value = true
    error.value = null
    try {
      const params = {}
      if (uploadId) params.upload_id = uploadId
      const res = await api.get('/records/analytics', { params })
      data.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בטעינת נתוני ניתוח'
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, fetchAnalytics }
})
