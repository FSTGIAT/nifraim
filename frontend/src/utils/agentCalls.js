// Nifra Agent ↔ Nifra Calls. The agent's tools (backend services/agent/tools_calls.py)
// send `proposal` {kind: record_call | stop_call}; the chat surfaces hand it here.
// Recording itself is the calls store (same recorder as the Calls widget). When a call
// the agent started comes back summarised, `notify(message)` posts it into the chat.
import { watch } from 'vue'
import { useCallsStore, CALL_TERMINAL, isNoSpeech } from '../stores/calls'
import { getUserFlag } from './userFlags'

export const isCallProposal = (p) => p && (p.kind === 'record_call' || p.kind === 'stop_call')

// The customer must know the call is recorded — the studio asks once per agent
// (calls_consent_ack). Until then the chat card asks the same question first.
export const callsConsentGiven = () => getUserFlag('calls_consent_ack') === '1'

let following = null   // stop watcher for the call the agent is following

/** Follow ONE call until it is summarised, then notify once. */
export function followCall(callId, notify) {
  const store = useCallsStore()
  following?.()
  store.pollCall(callId)
  following = watch(
    () => store.calls.find((c) => c.id === callId)?.status,
    async (status) => {
      if (!status || !CALL_TERMINAL.has(status)) return
      following?.(); following = null
      let c = store.calls.find((x) => x.id === callId)
      try { c = await store.fetchCall(callId) } catch (_) { /* keep the list version */ }
      if (status === 'failed') { notify({ text: `הסיכום של השיחה לא הצליח${c?.error ? ' — ' + c.error : ''}.`, callId, failed: true }); return }
      if (isNoSpeech(c)) { notify({ text: 'בהקלטה לא זוהה דיבור — לא נוצר סיכום. נסו להקליט שוב קרוב יותר למיקרופון.', callId, failed: true }); return }
      const ins = c.insights || {}
      const lines = [`הסיכום של השיחה מוכן${c.title ? ` — «${c.title}»` : ''}.`]
      if (ins.tldr || c.summary) lines.push(ins.tldr || c.summary)
      if (ins.follow_up) lines.push(`הצעד הבא: ${ins.follow_up}`)
      notify({ text: lines.join('\n'), callId, ready: true })
    },
    { immediate: true },
  )
}

/** Run an agent call instruction. Returns a short state for the card. */
export async function runCallProposal(p, notify) {
  const store = useCallsStore()
  if (store.enabled === null) await store.fetchStatus()
  if (!store.enabled) return { state: 'unavailable' }
  if (p.kind === 'record_call') {
    if (store.recState === 'recording') return { state: 'recording' }
    if (!callsConsentGiven()) return { state: 'consent' }
    const ok = await store.startRecording()
    return { state: ok ? 'recording' : 'error', error: store.error }
  }
  if (p.kind === 'stop_call') return stopAndFollow(notify)
  return { state: 'idle' }
}

export async function stopAndFollow(notify) {
  const store = useCallsStore()
  if (store.recState !== 'recording') return { state: 'not_recording' }
  const c = await store.stopAndUpload()
  if (!c) return { state: 'error', error: store.error }
  if (c.status === 'done' || c.status === 'failed') { followCall(c.id, notify); return { state: 'processing', callId: c.id } }
  followCall(c.id, notify)
  return { state: 'processing', callId: c.id }
}
