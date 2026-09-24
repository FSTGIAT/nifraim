import { defineStore, acceptHMRUpdate } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

// The AI mail agent ("דואר" tab). Server-side state is the truth: the tab
// re-reads it; nothing here is persisted in the browser.
export const useMailAgentStore = defineStore('mailAgent', () => {
  const summary = ref(null)
  const items = ref([])
  const filter = ref('open')
  const selected = ref(null)        // full item (body + draft)
  const senders = ref([])
  const suggestions = ref([])
  const loading = ref(false)
  const polling = ref(false)
  const busy = ref('')              // which action is running on the selected item
  const error = ref('')
  // Writing-style profile (the first-run workshop). `profileState` is the
  // whole GET /profile payload; `workshopOpen` shows the workshop in place of
  // the inbox inside the Mail Agent modal.
  const profileState = ref(null)
  const workshopOpen = ref(false)
  const styleJustDone = ref(false)   // one-shot: the inbox plays the pencil "landing"

  function detail(e, fallback) {
    const d = e?.response?.data?.detail
    return typeof d === 'string' ? d : fallback
  }

  async function fetchSummary() {
    summary.value = (await api.get('/mail-agent/summary')).data
  }

  async function fetchItems() {
    loading.value = true
    try {
      items.value = (await api.get('/mail-agent/items', { params: { status: filter.value } })).data
    } finally {
      loading.value = false
    }
  }

  async function refreshAll() {
    await Promise.all([fetchSummary(), fetchItems()])
  }

  async function openItem(id) {
    error.value = ''
    selected.value = (await api.get(`/mail-agent/items/${id}`)).data
  }

  function _replaceItem(full) {
    selected.value = full
    const i = items.value.findIndex((x) => x.id === full.id)
    if (i >= 0) items.value[i] = { ...items.value[i], ...full }
  }

  async function run(action, fn) {
    busy.value = action
    error.value = ''
    try {
      return await fn()
    } catch (e) {
      error.value = detail(e, 'הפעולה נכשלה')
      return null
    } finally {
      busy.value = ''
    }
  }

  const regenerate = (id) => run('draft', async () => {
    _replaceItem((await api.post(`/mail-agent/items/${id}/draft`)).data)
  })

  const saveDraft = (id, subject, body) => run('save', async () => {
    _replaceItem((await api.put(`/mail-agent/items/${id}/draft`, { subject, body })).data)
  })

  const send = (id, subject, body) => run('send', async () => {
    _replaceItem((await api.post(`/mail-agent/items/${id}/send`, { subject, body })).data)
    await fetchSummary()
    return true
  })

  const dismiss = (id, done = false) => run(done ? 'done' : 'dismiss', async () => {
    await api.post(`/mail-agent/items/${id}/dismiss`, null, { params: { done } })
    items.value = items.value.filter((x) => x.id !== id || filter.value === 'all')
    if (selected.value?.id === id) selected.value = null
    await fetchSummary()
  })

  const importFile = (id, filename) => run('import', async () => {
    const { data } = await api.post(`/mail-agent/items/${id}/import`, null, { params: { filename } })
    await openItem(id)
    return data
  })

  async function pollNow() {
    polling.value = true
    error.value = ''
    try {
      const { data } = await api.post('/mail-agent/poll-now')
      await refreshAll()
      return data.new
    } catch (e) {
      error.value = detail(e, 'הבדיקה נכשלה')
      return null
    } finally {
      polling.value = false
    }
  }

  async function fetchSenders() {
    senders.value = (await api.get('/mail-agent/senders')).data
  }

  async function fetchSuggestions() {
    suggestions.value = (await api.get('/mail-agent/senders/suggestions')).data
  }

  async function addSender(payload) {
    error.value = ''
    try {
      const { data } = await api.post('/mail-agent/senders', payload)
      if (!senders.value.some((s) => s.id === data.id)) senders.value.push(data)
      suggestions.value = suggestions.value.filter((s) => s.address !== data.address)
      await fetchSummary()
      return true
    } catch (e) {
      error.value = detail(e, 'ההוספה נכשלה')
      return false
    }
  }

  async function removeSender(id) {
    await api.delete(`/mail-agent/senders/${id}`)
    senders.value = senders.value.filter((s) => s.id !== id)
    await Promise.all([fetchSummary(), fetchSuggestions()])
  }

  async function fetchProfile() {
    profileState.value = (await api.get('/mail-agent/profile')).data
    return profileState.value
  }

  // PUT is partial: only the fields passed change. Throws with a readable detail.
  async function saveProfile(patch) {
    try {
      profileState.value = (await api.put('/mail-agent/profile', patch)).data
      return profileState.value
    } catch (e) {
      throw new Error(detail(e, 'השמירה נכשלה'))
    }
  }

  async function learnStyle() {
    try {
      const { data } = await api.post('/mail-agent/profile/learn', null, { timeout: 120000 })
      await fetchProfile()
      return data
    } catch (e) {
      throw new Error(detail(e, 'הלמידה נכשלה'))
    }
  }

  async function previewStyle(profile, kind) {
    try {
      return (await api.post('/mail-agent/profile/preview', { ...profile, kind }, { timeout: 120000 })).data
    } catch (e) {
      throw new Error(detail(e, 'לא הצלחנו לכתוב דוגמה'))
    }
  }

  return {
    profileState, workshopOpen, styleJustDone, fetchProfile, saveProfile, learnStyle, previewStyle,
    summary, items, filter, selected, senders, suggestions, loading, polling, busy, error,
    fetchSummary, fetchItems, refreshAll, openItem, regenerate, saveDraft, send, dismiss,
    importFile, pollNow, fetchSenders, fetchSuggestions, addSender, removeSender,
  }
})

// Dev only: without this, an edit to this file hot-swaps the components but
// keeps the OLD store instance — new actions show up as "is not a function".
if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useMailAgentStore, import.meta.hot))
