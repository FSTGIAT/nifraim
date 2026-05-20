// Workspace insights store — backs the radial-orbital launcher's two modals:
//   1. MonthlyCommissionModal — 3 months × (expected, actual, gap)
//   2. YieldRecommendationsModal — production × mygemel.net tracks
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useInsightsStore = defineStore('insights', () => {
  // ── Monthly commission ──────────────────────────────────────────────
  const monthly = ref(null)              // { months: [...] }
  const monthlyLoading = ref(false)
  const monthlyError = ref(null)

  // ── Yield recommendations ───────────────────────────────────────────
  const recommendations = ref([])
  const recommendationsTotalGain = ref(0)
  const recommendationsGeneratedAt = ref(null)
  const recommendationsLoading = ref(false)
  const recommendationsError = ref(null)
  const generating = ref(false)

  async function fetchMonthlyCommission(months = 3) {
    monthlyLoading.value = true
    monthlyError.value = null
    try {
      const res = await api.get('/insights/monthly-commission', { params: { months } })
      monthly.value = res.data
    } catch (e) {
      monthlyError.value = e.response?.data?.detail || 'שגיאה בטעינת נתוני העמלות'
      monthly.value = null
    } finally {
      monthlyLoading.value = false
    }
  }

  async function fetchRecommendations() {
    recommendationsLoading.value = true
    recommendationsError.value = null
    try {
      const res = await api.get('/yield-recommendations')
      recommendations.value = res.data.items || []
      recommendationsTotalGain.value = res.data.total_potential_annual_gain || 0
      recommendationsGeneratedAt.value = res.data.generated_at || null
    } catch (e) {
      recommendationsError.value = e.response?.data?.detail || 'שגיאה בטעינת המלצות'
      recommendations.value = []
    } finally {
      recommendationsLoading.value = false
    }
  }

  async function generateRecommendations() {
    generating.value = true
    recommendationsError.value = null
    try {
      await api.post('/yield-recommendations/generate')
      await fetchRecommendations()
    } catch (e) {
      recommendationsError.value = e.response?.data?.detail || 'שגיאה בחישוב המלצות'
      throw e
    } finally {
      generating.value = false
    }
  }

  // Builds an authenticated blob download for the Excel report. Anchor-with-
  // `download` would lose the Bearer token, so we fetch via axios and create
  // a temporary blob URL.
  async function downloadRecommendationsExcel() {
    const res = await api.get('/yield-recommendations/export.xlsx', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'yield_recommendations.xlsx'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => window.URL.revokeObjectURL(url), 0)
  }

  return {
    monthly, monthlyLoading, monthlyError, fetchMonthlyCommission,
    recommendations, recommendationsTotalGain, recommendationsGeneratedAt,
    recommendationsLoading, recommendationsError, generating,
    fetchRecommendations, generateRecommendations, downloadRecommendationsExcel,
  }
})
