import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useRecruitsStore = defineStore('recruits', () => {
  const recruits = ref([])
  const loading = ref(false)
  const comparing = ref(false)
  const comparisonResult = ref(null)
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

  function resetComparison() {
    comparisonResult.value = null
  }

  return {
    recruits, loading, comparing, comparisonResult, error,
    fetchRecruits, createRecruit, createBulk, updateRecruit, deleteRecruit,
    compareRecruits, resetComparison,
  }
})
