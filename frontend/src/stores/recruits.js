import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useRecruitsStore = defineStore('recruits', () => {
  const recruits = ref([])
  const loading = ref(false)
  const comparing = ref(false)
  const comparisonResult = ref(null)
  const comparisonMode = ref('production') // tracks which comparison is active
  const comparingCommission = ref(false)
  const commissionComparisonResult = ref(null)
  const uploading = ref(false)
  const error = ref(null)

  async function fetchRecruits() {
    loading.value = true
    error.value = null
    try {
      const res = await api.get('/recruits')
      recruits.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בטעינת מגויסים'
    } finally {
      loading.value = false
    }
  }

  async function createRecruit(data) {
    error.value = null
    try {
      const res = await api.post('/recruits', data)
      recruits.value.unshift(res.data)
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה ביצירת מגויס'
      throw e
    }
  }

  async function createBulk(items) {
    error.value = null
    try {
      const res = await api.post('/recruits/bulk', items)
      recruits.value.unshift(...res.data)
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה ביצירת מגויסים'
      throw e
    }
  }

  async function uploadRecruits(file, password) {
    uploading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (password) formData.append('password', password)
      const res = await api.post('/recruits/upload', formData)
      // Re-fetch full list after bulk upload
      await fetchRecruits()
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהעלאת קובץ'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function updateRecruit(id, data) {
    error.value = null
    try {
      const res = await api.put(`/recruits/${id}`, data)
      const idx = recruits.value.findIndex(r => r.id === id)
      if (idx !== -1) recruits.value[idx] = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בעדכון מגויס'
      throw e
    }
  }

  async function deleteRecruit(id) {
    error.value = null
    try {
      await api.delete(`/recruits/${id}`)
      recruits.value = recruits.value.filter(r => r.id !== id)
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה במחיקת מגויס'
      throw e
    }
  }

  async function compareRecruits() {
    comparing.value = true
    error.value = null
    comparisonResult.value = null
    comparisonMode.value = 'production'
    try {
      const res = await api.post('/recruits/compare')
      comparisonResult.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהשוואת מגויסים'
      throw e
    } finally {
      comparing.value = false
    }
  }

  const commissionFilterCompany = ref(null)

  async function compareRecruitsCommission(company = null) {
    comparingCommission.value = true
    error.value = null
    commissionComparisonResult.value = null
    comparisonMode.value = 'commission'
    commissionFilterCompany.value = company
    try {
      const params = company ? { company } : {}
      const res = await api.post('/recruits/compare-commission', null, { params })
      commissionComparisonResult.value = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'שגיאה בהשוואת מגויסים מול נפרעים'
      throw e
    } finally {
      comparingCommission.value = false
    }
  }

  function resetComparison() {
    comparisonResult.value = null
  }

  function resetCommissionComparison() {
    commissionComparisonResult.value = null
  }

  return {
    recruits, loading, comparing, comparisonResult, comparisonMode,
    comparingCommission, commissionComparisonResult, commissionFilterCompany,
    uploading, error,
    fetchRecruits, createRecruit, createBulk, uploadRecruits,
    updateRecruit, deleteRecruit,
    compareRecruits, resetComparison,
    compareRecruitsCommission, resetCommissionComparison,
  }
})
