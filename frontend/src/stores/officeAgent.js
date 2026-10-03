import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'
import { streamAgent, stripMarkdown } from '../utils/agentStream.js'
import { isCallProposal, runCallProposal } from '../utils/agentCalls.js'
import { getUserFlag, setUserFlag } from '../utils/userFlags.js'

// The office agent ("סוכן המשרד") — services/office_agent.py. One brief that
// speaks for the Mail Agent + the collection agent; every action goes through
// their existing endpoints (sending is always the agent's click).
export const useOfficeAgentStore = defineStore('officeAgent', () => {
  const brief = ref(null)
  const loading = ref(false)
  const busy = ref('')
  const error = ref('')
  const thread = ref([]) // [{role:'user'|'agent', text}] — the short Q&A
  const narration = ref(null) // {greeting, lines:[{text, ref}]} — what the agent writes on open
  const narrating = ref(false)

  const cards = computed(() => brief.value?.cards || [])
  const todoCount = computed(() => (brief.value?.todo_count || 0) + (brief.value && !brief.value.mailbox?.mailbox_connected ? 1 : 0))
  // always there once loaded — a new agent's first job is "connect mail"
  const visible = computed(() => !!brief.value)
  const needsMail = computed(() => !!brief.value && !brief.value.mailbox?.mailbox_connected)

  async function load() {
    loading.value = true
    try {
      brief.value = (await api.get('/office-agent')).data
      checkCallPops()
    } catch { /* keep the last brief */ } finally { loading.value = false }
  }

  // ── a call summary is ready → the agent opens by itself, once per call ──
  // `popRequest` is the call card to open on; WorkspaceView opens the panel
  // (when no other overlay — the calls studio — is up) and the panel expands
  // that card's line. Popped ids are remembered per user.
  const popRequest = ref(null)
  const attention = ref(0) // bumped on each pop → the orb's attention pulse
  function poppedSet() {
    try { return new Set(JSON.parse(getUserFlag('agent_call_popped') || '[]')) } catch { return new Set() }
  }
  function checkCallPops() {
    if (popRequest.value) return
    const popped = poppedSet()
    const card = (brief.value?.cards || []).find((c) => c.kind === 'call' && !popped.has(c.id))
    if (card) popRequest.value = card.id
  }
  function markPopped(cardId) {
    const s = poppedSet()
    s.add(cardId)
    setUserFlag('agent_call_popped', JSON.stringify([...s].slice(-200)))
    attention.value++
  }
  function clearPop() { popRequest.value = null }

  // The agent's written brief (≤5 lines). Also refreshes the cards behind it.
  async function narrate() {
    narrating.value = true
    try {
      const { data } = await api.get('/office-agent/narrate')
      narration.value = { greeting: data.greeting, lines: data.lines || [] }
      brief.value = { ...(brief.value || {}), cards: data.cards, mailbox: data.mailbox, todo_count: data.todo_count }
      checkCallPops()
    } catch {
      if (!narration.value) narration.value = { greeting: 'שלום', lines: [{ text: 'לא הצלחתי לטעון את התדריך כרגע — נסו שוב בעוד רגע.', ref: null }] }
    } finally {
      narrating.value = false
    }
  }

  function message(e) {
    const d = e?.response?.data?.detail
    if (d === 'not_connected') return 'חברו את המייל כדי לשלוח'
    // connected, but only for reading (Microsoft / forwarding) — sending needs Gmail with an app password
    if (d === 'cannot_send') return 'המייל המחובר משמש לקריאה בלבד — כדי לשלוח, חברו Gmail עם סיסמת אפליקציה'
    if (d === 'bad_email') return 'המייל לא תקין'
    if (d === 'missing_text') return 'חסר נושא או תוכן למייל'
    if (e?.response?.status === 502) return 'השליחה נכשלה — נסו שוב בעוד רגע'
    if (d === 'missing contact email') return 'חסר מייל של איש קשר'
    return typeof d === 'string' ? d : 'הפעולה לא הצליחה — נסו שוב'
  }

  async function act(card, action, payload = {}) {
    busy.value = card.id + ':' + action
    error.value = ''
    errorCode.value = ''
    try {
      const ref_ = card.ref
      if (action === 'send_reply') await api.post(`/mail-agent/items/${ref_}/send`, { subject: payload.subject ?? card.draft_subject ?? '', body: payload.body ?? card.draft_body ?? '' })
      else if (action === 'make_draft') await api.post(`/mail-agent/items/${ref_}/draft`)
      else if (action === 'import') await api.post(`/mail-agent/items/${ref_}/import`)
      else if (action === 'done') await api.post(`/mail-agent/items/${ref_}/dismiss`, null, { params: { done: true } })
      else if (action === 'set_email') await api.patch(`/collection-agent/cases/${ref_}`, { to_email: payload.email })
      else if (action === 'save_case_body') await api.patch(`/collection-agent/cases/${ref_}`, { body: payload.body })
      else if (action === 'send_case') await api.post(`/collection-agent/cases/${ref_}/send`)
      else if (action === 'remind') await api.post(`/collection-agent/cases/${ref_}/remind`)
      else if (action === 'resolve') await api.post(`/collection-agent/cases/${ref_}/resolve`)
      else if (action === 'send_followup') await api.post(`/calls/${ref_}/followup/send`, {
        to_email: payload.to_email, to_name: payload.to_name || '', subject: payload.subject, body: payload.body,
      })
      else if (action === 'dismiss_followup') await api.post(`/calls/${ref_}/followup/dismiss`)
      await load()
      return true
    } catch (e) {
      error.value = message(e)
      errorCode.value = e?.response?.data?.detail || ''
      return false
    } finally {
      busy.value = ''
    }
  }
  const errorCode = ref('')

  // the @ search in the ask box
  async function searchContacts(q) {
    try { return (await api.get('/office-agent/contacts', { params: { q } })).data || [] } catch { return [] }
  }

  // Nifra AI v2: streamed from /api/ai/agent (tools + fast lane). The answer is
  // pushed once complete (AiStreamingText types it); meanwhile `askStatus`
  // shows which tool runs ("בודק עמלות שלא שולמו…").
  const askStatus = ref('')
  async function ask(question, mentions = []) {
    const q = (question || '').trim()
    if (!q) return
    const history = thread.value.slice(-8).map((m) => ({ role: m.role, text: m.text }))
    thread.value.push({ role: 'user', text: q })
    busy.value = 'ask'
    askStatus.value = ''
    let text = ''
    let proposal = null
    const vizs = []
    try {
      await streamAgent({ question: q, history, mentions, surface: 'panel' }, (ev) => {
        if (ev.status) askStatus.value = ev.status
        if (ev.text) text += ev.text
        if (ev.viz) vizs.push(ev.viz)
        if (ev.proposal) proposal = { ...ev.proposal, status: 'open' }
      })
      const msg = { role: 'agent', text: stripMarkdown(text).trim() || 'אין לי תשובה כרגע.', proposal, vizs, call: null }
      if (isCallProposal(proposal)) {
        msg.proposal = null
        msg.call = { state: 'pending' }
        thread.value.push(msg)
        const live = thread.value[thread.value.length - 1]       // the reactive copy
        runCallProposal(proposal, notifyCall).then((r) => { Object.assign(live.call, r) })
      } else {
        thread.value.push(msg)
      }
    } catch {
      thread.value.push({ role: 'agent', text: 'לא הצלחתי לענות כרגע — נסו שוב בעוד רגע.' })
    } finally {
      busy.value = ''
      askStatus.value = ''
    }
  }

  // A call the agent recorded came back summarised → say so in the thread.
  function notifyCall({ text, callId, ready }) {
    thread.value.push({ role: 'agent', text, call: ready ? { state: 'done', callId } : null })
  }

  // The agent approved a prepared email / meeting — send it from their mailbox.
  async function approve(msg) {
    const p = msg.proposal
    busy.value = 'act'
    error.value = ''
    try {
      const { kind, status, ...data } = p
      await api.post('/office-agent/act', { kind, data })
      p.status = 'sent'
      return true
    } catch (e) {
      const d = e?.response?.data?.detail
      error.value = d === 'bad_email' ? 'כתובת המייל לא תקינה'
        : d === 'bad_start' ? 'המועד לא תקין'
        : d === 'bad_code' ? 'קוד בקשה לא תקין'
        : e?.response?.status === 503 ? 'המסלקה כבויה בסביבה הזו'
        : e?.response?.status === 403 ? 'השיוך למסלקה עוד לא אושר'
        : message(e)
      return false
    } finally {
      busy.value = ''
    }
  }

  return { popRequest, attention, markPopped, clearPop, checkCallPops, errorCode, notifyCall, askStatus, searchContacts, approve, brief, loading, busy, error, thread, narration, narrating, cards, todoCount, visible, needsMail, load, narrate, act, ask }
})
