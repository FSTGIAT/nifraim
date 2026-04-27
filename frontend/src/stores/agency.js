import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'

export const useAgencyStore = defineStore('agency', () => {
  const agency = ref(null)
  const overview = ref(null)
  const agents = ref([])
  const reconciliation = ref(null)
  const bonus = ref(null)
  const trends = ref(null)
  const missing = ref(null)
  const invites = ref([])
  const knowledge = ref(null)

  const loading = ref({ overview: false, agents: false, reconciliation: false, bonus: false, invites: false, knowledge: false, trends: false })
  const error = ref(null)

  async function fetchSelf() {
    const res = await api.get('/agency/me')
    agency.value = res.data
  }

  async function fetchOverview() {
    loading.value.overview = true
    try { overview.value = (await api.get('/agency/overview')).data }
    finally { loading.value.overview = false }
  }

  async function fetchAgents() {
    loading.value.agents = true
    try { agents.value = (await api.get('/agency/agents')).data }
    finally { loading.value.agents = false }
  }

  async function fetchReconciliation() {
    loading.value.reconciliation = true
    try { reconciliation.value = (await api.get('/agency/reconciliation')).data }
    finally { loading.value.reconciliation = false }
  }

  async function fetchBonus(year) {
    loading.value.bonus = true
    try { bonus.value = (await api.get('/agency/bonus', { params: year ? { year } : {} })).data }
    finally { loading.value.bonus = false }
  }

  async function fetchTrends() {
    loading.value.trends = true
    try { trends.value = (await api.get('/agency/trends')).data }
    finally { loading.value.trends = false }
  }

  async function fetchMissing() {
    missing.value = (await api.get('/agency/missing-commission')).data
  }

  async function fetchAgentDetail(agentId) {
    const res = await api.get(`/agency/agents/${agentId}/detail`)
    return res.data
  }

  // ── Tab overviews (mirror the regular agent's workspace tabs) ──
  const production = ref(null)
  const comparison = ref(null)
  const rates = ref(null)
  const emails = ref(null)
  const recruits = ref(null)

  async function fetchProduction() { production.value = (await api.get('/agency/production')).data }
  async function fetchComparison() { comparison.value = (await api.get('/agency/comparison')).data }
  async function fetchCommissionRates() { rates.value = (await api.get('/agency/commission-rates')).data }
  async function fetchCompanyEmails() { emails.value = (await api.get('/agency/company-emails')).data }
  async function fetchRecruits() { recruits.value = (await api.get('/agency/recruits')).data }

  async function fetchInvites() {
    loading.value.invites = true
    try { invites.value = (await api.get('/agency/invites')).data }
    finally { loading.value.invites = false }
  }

  async function createInvite(email, role = 'agent') {
    const res = await api.post('/agency/invites', { email, role })
    invites.value = [res.data, ...invites.value]
    return res.data
  }

  async function revokeInvite(id) {
    await api.delete(`/agency/invites/${id}`)
    invites.value = invites.value.map((i) => (i.id === id ? { ...i, revoked_at: new Date().toISOString() } : i))
  }

  async function fetchKnowledge() {
    loading.value.knowledge = true
    try { knowledge.value = (await api.get('/ai/knowledge', { params: { scope: 'agency' } })).data }
    finally { loading.value.knowledge = false }
  }

  async function impersonate(agentId) {
    const res = await api.post(`/agency/impersonate/${agentId}`)
    return res.data
  }

  const hasData = computed(() => overview.value && overview.value.agent_count > 0)

  return {
    agency, overview, agents, reconciliation, bonus, trends, missing, invites, knowledge,
    loading, error, hasData,
    fetchSelf, fetchOverview, fetchAgents, fetchReconciliation, fetchBonus, fetchTrends, fetchMissing,
    fetchAgentDetail, fetchInvites, createInvite, revokeInvite, fetchKnowledge, impersonate,
    production, comparison, rates, emails, recruits,
    fetchProduction, fetchComparison, fetchCommissionRates, fetchCompanyEmails, fetchRecruits,
  }
})
