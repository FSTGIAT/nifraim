<template>
  <!-- The agent's live call card in the chat: consent (once) → recording with a timer and
       stop → "waiting for the summary" → open it. Reads the calls store, so it mirrors the
       Calls widget exactly. -->
  <div class="acc" :class="'acc--' + view">
    <template v-if="view === 'consent'">
      <label class="acc-consent"><input v-model="tick" type="checkbox" /> הלקוח יודע שהשיחה מוקלטת</label>
      <button type="button" class="acc-go" :disabled="!tick" @click="consentAndStart">התחלת הקלטה</button>
    </template>
    <template v-else-if="view === 'recording'">
      <span class="acc-dot" aria-hidden="true"></span>
      <span class="acc-label">מקליט <b class="ltr-number">{{ timeLabel }}</b></span>
      <button type="button" class="acc-go" @click="stop">עצירה ושליחה לסיכום</button>
      <button type="button" class="acc-ghost" @click="cancel">ביטול</button>
    </template>
    <template v-else-if="view === 'uploading'">
      <span class="acc-spin" aria-hidden="true"></span>
      <span class="acc-label">שולח <b class="ltr-number">{{ Math.round(store.uploadProgress * 100) }}%</b></span>
    </template>
    <template v-else-if="view === 'processing'">
      <span class="acc-spin" aria-hidden="true"></span>
      <span class="acc-label">מתמלל ומסכם — אעדכן כאן כשהסיכום מוכן</span>
    </template>
    <template v-else-if="view === 'ready'">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>
      <span class="acc-label">{{ readyCall?.title || 'הסיכום מוכן' }}</span>
      <button type="button" class="acc-go" @click="open">פתיחת הסיכום</button>
    </template>
    <span v-else-if="view === 'summarized'" class="acc-label acc-muted">סוכם ✓ · הסיכום למטה</span>
    <span v-else-if="view === 'unavailable'" class="acc-label">שירות השיחות לא פעיל בחשבון הזה.</span>
    <span v-else-if="view === 'error'" class="acc-label acc-err">{{ store.error || 'ההקלטה לא התחילה.' }}</span>
    <span v-else class="acc-label">ההקלטה הסתיימה.</span>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { setUserFlag } from '../../utils/userFlags'
import { useCallsStore, CALL_TERMINAL } from '../../stores/calls'
import { stopAndFollow } from '../../utils/agentCalls'

// msg.call = { state, callId? } — owned by the chat store; `notify` posts the summary message
const props = defineProps({ call: { type: Object, required: true }, notify: { type: Function, required: true } })
const store = useCallsStore()
const tick = ref(false)

const tracked = computed(() => (props.call.callId ? store.calls.find((c) => c.id === props.call.callId) : null))
const readyCall = computed(() => (tracked.value?.status === 'done' ? tracked.value : null))
const view = computed(() => {
  const s = props.call.state
  if (s === 'consent' || s === 'unavailable' || s === 'error') return s
  if (s === 'recording') {
    if (store.recState === 'recording') return 'recording'
    if (store.recState === 'uploading' || store.recState === 'requesting') return 'uploading'
  }
  if (tracked.value) {
    if (!CALL_TERMINAL.has(tracked.value.status)) return 'processing'
    // only the agent's "summary is ready" message carries the open button; earlier cards collapse
    if (tracked.value.status === 'done') return props.call.state === 'done' ? 'ready' : 'summarized'
    return 'done'
  }
  return props.call.callId ? 'processing' : 'done'
})
const timeLabel = computed(() => `${String(Math.floor(store.elapsed / 60)).padStart(2, '0')}:${String(store.elapsed % 60).padStart(2, '0')}`)

// stopped elsewhere (the Calls widget / studio): follow whatever it uploaded
watch(() => [store.recState, store.current?.id], ([rec, id]) => {
  if (props.call.state === 'recording' && rec === 'idle' && id && !props.call.callId) adopt(id)
})

function adopt(id) {
  props.call.callId = id
  import('../../utils/agentCalls').then(({ followCall }) => followCall(id, props.notify))
}
async function consentAndStart() {
  setUserFlag('calls_consent_ack', '1')
  const ok = await store.startRecording()
  props.call.state = ok ? 'recording' : 'error'
}
async function stop() {
  const r = await stopAndFollow(props.notify)
  if (r.callId) props.call.callId = r.callId
  if (r.state === 'error') props.call.state = 'error'
}
async function cancel() {
  await store.cancelRecording()
  props.call.state = 'cancelled'
}
function open() {
  if (props.call.callId) store.openCall(props.call.callId).catch(() => {})
  store.requestStudio(props.call.callId)
}
</script>

<style scoped>
.acc {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 8px; padding: 10px 12px;
  border: 1px solid var(--border-subtle); border-radius: 12px; background: #fff;
  font-size: 13.5px; color: var(--text);
}
.acc--recording { border-color: color-mix(in srgb, var(--red) 35%, transparent); }
.acc-label b { font-weight: 800; font-variant-numeric: tabular-nums; }
.acc-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--red); animation: accBlink 1.2s ease-in-out infinite; }
@keyframes accBlink { 50% { opacity: 0.25; } }
.acc-spin { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--border); border-top-color: var(--text); animation: accSpin 0.9s linear infinite; }
@keyframes accSpin { to { transform: rotate(360deg); } }
.acc-go {
  margin-inline-start: auto; padding: 6px 12px; border: none; border-radius: 10px; cursor: pointer;
  background: var(--primary, #181818); color: #fff; font: inherit; font-size: 13px; font-weight: 700;
}
.acc-go:disabled { opacity: 0.4; cursor: default; }
.acc-ghost { padding: 6px 10px; border: none; border-radius: 10px; background: transparent; color: var(--text-muted); font: inherit; font-size: 13px; cursor: pointer; }
.acc-consent { display: inline-flex; align-items: center; gap: 6px; }
.acc-err { color: var(--red); }
.acc--summarized { padding: 4px 0; border: none; background: transparent; }
.acc-muted { color: var(--text-muted); font-size: 12.5px; }
@media (prefers-reduced-motion: reduce) { .acc-dot, .acc-spin { animation: none; } }
</style>
