import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'
import { useAuthStore } from './auth.js'

// Cadence. The presence beat always runs (it also refreshes the unread badge,
// so the collapsed pill stays live for free); the message poll only runs while
// the dock is open.
const PRESENCE_MS = 20000
const POLL_OPEN_MS = 4000
const BACKOFF_CAP_MS = 60000

export const useMessengerStore = defineStore('messenger', () => {
  const auth = useAuthStore()

  const contacts = ref([])
  const onlineFriends = ref([])       // anyone with the app open — not just my contacts
  const searchResults = ref([])
  const searchQuery = ref('')
  const searching = ref(false)

  const openContact = ref(null)       // the ContactOut we're chatting with
  const messages = ref([])            // messages of the open thread, ascending by seq
  const loadingThread = ref(false)
  const hasMore = ref(false)

  const dockOpen = ref(false)
  const totalUnread = ref(0)
  const error = ref('')

  const cursor = ref(0)               // max seq of any INCOMING message seen
  const seenIds = new Set()           // dedupe key: server message id
  const failCount = ref(0)

  let presenceTimer = null
  let pollTimer = null
  let searchDebounce = null

  const myId = computed(() => auth.user?.id || null)
  const showingSearch = computed(() => searchQuery.value.trim().length >= 2)
  const listedContacts = computed(() => (showingSearch.value ? searchResults.value : contacts.value))

  // ---------------------------------------------------------------- API calls

  async function fetchContacts () {
    const { data } = await api.get('/messenger/contacts')
    contacts.value = data
  }

  async function fetchOnline () {
    const { data } = await api.get('/messenger/online')
    onlineFriends.value = data
  }

  /** Pick the seed for my generated avatar. */
  async function changeAvatar (seed) {
    const { data } = await api.patch('/auth/me/avatar', { avatar_seed: seed })
    if (auth.user) auth.user.avatar_seed = data.avatar_seed
    // Everyone's copy of me is stale now; refresh the lists that render faces.
    await Promise.all([fetchContacts().catch(() => {}), fetchOnline().catch(() => {})])
    return data.avatar_seed
  }

  /**
   * Rename my handle. The server owns uniqueness (409) — the regex here is only
   * to spare the round-trip on obviously bad input.
   */
  async function changeUsername (raw) {
    const handle = (raw || '').trim().replace(/^@/, '').toLowerCase()
    if (!/^[a-z0-9_]{3,32}$/.test(handle)) {
      throw new Error('שם משתמש יכול להכיל רק אותיות אנגליות קטנות, ספרות וקו תחתון (3–32 תווים)')
    }
    try {
      const { data } = await api.patch('/auth/me/username', { username: handle })
      if (auth.user) auth.user.username = data.username   // re-seeds my avatar
      return data.username
    } catch (e) {
      throw new Error(
        e.response?.status === 409
          ? 'שם המשתמש תפוס'
          : e.response?.data?.detail || 'שמירת שם המשתמש נכשלה',
      )
    }
  }

  async function runSearch (q) {
    const term = (q || '').trim()
    if (term.length < 2) {
      searchResults.value = []
      return
    }
    searching.value = true
    try {
      const { data } = await api.get('/messenger/search', { params: { q: term } })
      searchResults.value = data
    } finally {
      searching.value = false
    }
  }

  function setSearch (q) {
    searchQuery.value = q
    clearTimeout(searchDebounce)
    searchDebounce = setTimeout(() => runSearch(q), 250)
  }

  function clearSearch () {
    searchQuery.value = ''
    searchResults.value = []
    clearTimeout(searchDebounce)
  }

  async function openThread (contact) {
    openContact.value = contact
    messages.value = []
    hasMore.value = false
    loadingThread.value = true
    try {
      const { data } = await api.get(`/messenger/threads/${contact.id}/messages`)
      messages.value = data.messages
      hasMore.value = data.has_more
      data.messages.forEach((m) => seenIds.add(m.id))
      // Any incoming message already in history is, by definition, seen.
      const maxIncoming = data.messages
        .filter((m) => m.recipient_id === myId.value)
        .reduce((mx, m) => Math.max(mx, m.seq), 0)
      if (maxIncoming > cursor.value) cursor.value = maxIncoming
      await markRead(contact.id)
    } finally {
      loadingThread.value = false
    }
  }

  async function loadOlder () {
    if (!openContact.value || !hasMore.value || !messages.value.length) return
    const oldest = messages.value[0].seq
    const { data } = await api.get(`/messenger/threads/${openContact.value.id}/messages`, {
      params: { before: oldest },
    })
    const fresh = data.messages.filter((m) => !seenIds.has(m.id))
    fresh.forEach((m) => seenIds.add(m.id))
    messages.value = [...fresh, ...messages.value]
    hasMore.value = data.has_more
  }

  function closeThread () {
    openContact.value = null
    messages.value = []
  }

  /**
   * Delete a conversation for me. The server keeps the other person's copy —
   * this only stamps my side's cleared_at.
   */
  async function deleteThread (contactId) {
    const { data } = await api.delete(`/messenger/threads/${contactId}`)
    contacts.value = contacts.value.filter((c) => c.id !== contactId)
    if (openContact.value?.id === contactId) closeThread()
    if (typeof data?.total_unread === 'number') totalUnread.value = data.total_unread
  }

  async function markRead (contactId) {
    try {
      await api.post(`/messenger/threads/${contactId}/read`)
    } catch { /* non-critical */ }
    const c = contacts.value.find((x) => x.id === contactId)
    if (c) {
      totalUnread.value = Math.max(0, totalUnread.value - (c.unread || 0))
      c.unread = 0
    }
  }

  /**
   * Optimistic send. The bubble appears immediately with a temporary id; when
   * the server acks we swap in the real row (id/seq/created_at). On failure the
   * bubble stays and is flagged, so the user's text is never silently lost.
   */
  async function sendMessage (text) {
    const body = (text || '').trim()
    const contact = openContact.value
    if (!body || !contact) return

    const clientId = (crypto.randomUUID?.() || `c${Date.now()}${Math.random()}`)
    const optimistic = {
      id: clientId,
      client_id: clientId,
      seq: Number.MAX_SAFE_INTEGER,   // sorts last until reconciled
      sender_id: myId.value,
      recipient_id: contact.id,
      body,
      created_at: new Date().toISOString(),
      pending: true,
      failed: false,
    }
    messages.value.push(optimistic)

    try {
      const { data } = await api.post(`/messenger/threads/${contact.id}/messages`, {
        body,
        client_id: clientId,
      })
      const i = messages.value.findIndex((m) => m.client_id === clientId)
      if (i !== -1) messages.value[i] = { ...data, pending: false, failed: false }
      seenIds.add(data.id)
      bumpContactPreview(contact.id, body, true)
      error.value = ''
    } catch (e) {
      const i = messages.value.findIndex((m) => m.client_id === clientId)
      if (i !== -1) messages.value[i] = { ...optimistic, pending: false, failed: true }
      error.value = e.response?.status === 429
        ? 'האטו — נשלחו יותר מדי הודעות'
        : 'שליחת ההודעה נכשלה'
    }
  }

  async function retry (msg) {
    messages.value = messages.value.filter((m) => m.id !== msg.id)
    await sendMessage(msg.body)
  }

  function bumpContactPreview (contactId, body, fromMe) {
    const c = contacts.value.find((x) => x.id === contactId)
    if (c) {
      c.last_message_preview = body.slice(0, 140)
      c.last_message_at = new Date().toISOString()
      c.last_message_from_me = fromMe
    } else if (openContact.value?.id === contactId) {
      // First message to someone found via search — promote them into contacts.
      contacts.value.unshift({
        ...openContact.value,
        unread: 0,
        last_message_preview: body.slice(0, 140),
        last_message_at: new Date().toISOString(),
        last_message_from_me: fromMe,
      })
    }
  }

  // ------------------------------------------------------------ polling loops

  function backoff (base) {
    return Math.min(base * 2 ** failCount.value, BACKOFF_CAP_MS)
  }

  async function pollOnce () {
    const { data } = await api.get('/messenger/poll', { params: { since: cursor.value } })
    cursor.value = data.cursor
    totalUnread.value = data.total_unread

    let arrivedInOpenThread = false
    for (const m of data.messages) {
      if (seenIds.has(m.id)) continue      // dedupe by server id
      seenIds.add(m.id)

      // Per-message, not a loop-wide flag: a message from contact X landing in
      // the open thread must not suppress the unread bump for contact Y.
      const inOpenThread = openContact.value && m.sender_id === openContact.value.id
      if (inOpenThread) {
        messages.value.push(m)
        arrivedInOpenThread = true
      }

      const c = contacts.value.find((x) => x.id === m.sender_id)
      if (c) {
        c.last_message_preview = m.body.slice(0, 140)
        c.last_message_at = m.created_at
        c.last_message_from_me = false
        if (!inOpenThread) c.unread = (c.unread || 0) + 1
      } else {
        await fetchContacts()   // a brand-new conversation started by someone else
      }
    }

    // Reading a message as it lands means it must not stay unread.
    if (arrivedInOpenThread) await markRead(openContact.value.id)

    // Keep the presence rail fresh, but only while it is actually on screen.
    if (!openContact.value) await fetchOnline().catch(() => {})
  }

  async function heartbeatOnce () {
    const { data } = await api.post('/messenger/presence/heartbeat')
    totalUnread.value = data.total_unread
    // Also refresh who's around: the collapsed pill shows their faces when you
    // have no unread, so this must stay current even with the dock closed.
    await fetchOnline().catch(() => {})
  }

  function schedulePresence () {
    clearTimeout(presenceTimer)
    if (document.hidden) return
    presenceTimer = setTimeout(async () => {
      try {
        await heartbeatOnce()
        failCount.value = 0
      } catch { failCount.value++ }
      schedulePresence()
    }, backoff(PRESENCE_MS))
  }

  function schedulePoll () {
    clearTimeout(pollTimer)
    if (document.hidden || !dockOpen.value) return
    pollTimer = setTimeout(async () => {
      try {
        await pollOnce()
        failCount.value = 0
      } catch { failCount.value++ }
      schedulePoll()
    }, backoff(POLL_OPEN_MS))
  }

  function onVisibility () {
    if (document.hidden) {
      clearTimeout(presenceTimer)
      clearTimeout(pollTimer)
      return
    }
    // Back on screen: catch up immediately, then resume both cadences.
    failCount.value = 0
    heartbeatOnce().catch(() => {})
    if (dockOpen.value) pollOnce().catch(() => {})
    schedulePresence()
    schedulePoll()
  }

  /** Mounted once, app-wide (WorkspaceView). Keeps the badge alive with the dock closed. */
  function startPresence () {
    document.addEventListener('visibilitychange', onVisibility)
    heartbeatOnce().catch(() => {})
    schedulePresence()
  }

  function stopPresence () {
    document.removeEventListener('visibilitychange', onVisibility)
    clearTimeout(presenceTimer)
    clearTimeout(pollTimer)
    clearTimeout(searchDebounce)
  }

  async function openDock () {
    dockOpen.value = true
    try {
      await Promise.all([fetchContacts(), fetchOnline()])
      await pollOnce()
    } catch { /* the loop will retry */ }
    schedulePoll()
  }

  function closeDock () {
    dockOpen.value = false
    clearTimeout(pollTimer)
    closeThread()
    clearSearch()
  }

  return {
    contacts, onlineFriends, searchResults, searchQuery, searching, showingSearch, listedContacts,
    openContact, messages, loadingThread, hasMore,
    dockOpen, totalUnread, error, myId,
    fetchContacts, fetchOnline, changeUsername, changeAvatar, setSearch, clearSearch,
    openThread, closeThread, loadOlder, sendMessage, retry, markRead, deleteThread,
    startPresence, stopPresence, openDock, closeDock,
  }
})
