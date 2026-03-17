import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useVolumeStore = defineStore('volume', () => {
  const comparisonResult = ref(null)
  const bonusResult = ref(null)
  const bonusPayments = ref([])
  const loading = ref(false)
  const bonusLoading = ref(false)
  const error = ref(null)
  const volumeFile = ref(null) // keep reference to file for bonus calc

  async function uploadAndCompare(file, password) {
    loading.value = true
    error.value = null
    comparisonResult.value = null
    bonusResult.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (password) formData.append('password', password)

      const res = await api.post('/volume/upload-compare', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      comparisonResult.value = res.data
      volumeFile.value = file
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהעלאת דוח היקפים'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function calculateBonus() {
    if (!volumeFile.value) return
    bonusLoading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', volumeFile.value)

      const res = await api.post('/volume/calculate-bonus', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      bonusResult.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בחישוב עמלות היקף'
      throw e
    } finally {
      bonusLoading.value = false
    }
  }

  async function fetchBonusPayments() {
    try {
      const res = await api.get('/volume/bonus-payments')
      bonusPayments.value = res.data
    } catch (e) {
      // silent — non-critical
    }
  }

  async function upsertBonusPayment(data) {
    try {
      const res = await api.post('/volume/bonus-payments', data)
      // Update local state
      const idx = bonusPayments.value.findIndex(
        p => p.company_name === data.company_name && p.year === data.year
      )
      if (idx >= 0) {
        bonusPayments.value[idx] = res.data
      } else {
        bonusPayments.value.push(res.data)
      }
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בעדכון סטטוס תשלום'
    }
  }

  function reset() {
    comparisonResult.value = null
    bonusResult.value = null
    volumeFile.value = null
    error.value = null
  }

  return {
    comparisonResult, bonusResult, bonusPayments, loading, bonusLoading, error, volumeFile,
    uploadAndCompare, calculateBonus, fetchBonusPayments, upsertBonusPayment, reset,
  }
})
