import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'

// The collection agent ("סוכן גבייה") — services/collection_agent.py.
// One case per insurer with unpaid commission; drafts are sent only on the
// agent's click. `brief` is the whole state the UI needs.
export const useCollectionAgentStore = defineStore('collectionAgent', () => {
  const brief = ref(null)
  const loading = ref(false)
  const busyId = ref(null)
  const error = ref('')

  const cases = computed(() => brief.value?.cases || [])
  const openCount = computed(() => brief.value?.open_count || 0)
  const visible = computed(() => cases.value.length > 0)

  async function run(fn, id = null) {
    busyId.value = id
    error.value = ''
    try {
      const res = await fn()
      brief.value = res.data
      return true
    } catch (e) {
      const d = e?.response?.data?.detail
      error.value = d === 'not_connected' || d === 'cannot_send'
        ? 'כדי לשלוח, חברו את Nifraim Mail Agent (Gmail) בהגדרות'
        : d === 'missing contact email' ? 'חסר מייל של איש קשר'
        : 'השליחה לא הצליחה — נסו שוב'
      return false
    } finally {
      busyId.value = null
    }
  }

  // Build/refresh the drafts from the latest comparison (cheap, idempotent).
  async function load() {
    loading.value = true
    try { await run(() => api.post('/collection-agent/refresh')) } finally { loading.value = false }
  }
  const edit = (id, patch) => run(() => api.patch(`/collection-agent/cases/${id}`, patch), id)
  const send = (id) => run(() => api.post(`/collection-agent/cases/${id}/send`), id)
  const remind = (id) => run(() => api.post(`/collection-agent/cases/${id}/remind`), id)
  const resolve = (id) => run(() => api.post(`/collection-agent/cases/${id}/resolve`), id)

  return { brief, loading, busyId, error, cases, openCount, visible, load, edit, send, remind, resolve }
})
