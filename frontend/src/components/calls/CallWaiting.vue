<template>
  <div class="cwt" :class="{ 'cwt--failed': failed }">
    <!-- While the summary is on its way — the same calm language as the
         result: the orb small and thinking, who is working on it, elapsed
         time and a rough ETA, then neutral skeletons in the result's shape. -->
    <div class="cwt-head">
      <CallsOrb :size="64" :state="failed ? 'idle' : 'processing'" />
      <div class="cwt-copy">
        <h2 class="cwt-stage">{{ stageText }}</h2>
        <p v-if="failed" class="cwt-err">{{ call.error || 'משהו השתבש. נסו להקליט שוב.' }}</p>
        <p v-else class="cwt-meta">
          <template v-if="etaLabel"><span class="ltr-number">{{ elapsedLabel }}</span> עברו · {{ etaLabel }}</template>
          <template v-else>נעדכן כשהסיכום מוכן — אפשר להמשיך לעבוד</template>
        </p>
      </div>
    </div>
    <ol v-if="!failed" class="cwt-steps" aria-label="שלבי העיבוד">
      <li v-for="(st, i) in STEPS" :key="st.key" :class="{ 'is-done': i < idx, 'is-now': i === idx }">
        <span class="cwt-bar"></span><span class="cwt-label">{{ st.label }}</span>
      </li>
    </ol>

    <div v-if="!failed" class="cwt-skel" aria-hidden="true">
      <div class="sk" style="width: 62%; height: 26px"></div>
      <div class="sk" style="width: 90%; height: 14px"></div>
      <div class="sk sk-timeline"></div>
      <div class="cwt-cols">
        <div class="cwt-col">
          <div class="sk" style="height: 64px"></div>
          <div v-for="n in 3" :key="n" class="sk" style="height: 14px" :style="{ width: 70 + n * 8 + '%' }"></div>
        </div>
        <div class="cwt-col">
          <div v-for="n in 5" :key="n" class="sk" style="height: 12px" :style="{ width: 60 + ((n * 13) % 35) + '%' }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import CallsOrb from './CallsOrb.vue'

const props = defineProps({ call: { type: Object, required: true } })

const STEPS = [
  { key: 'uploaded', label: 'הועלה' },
  { key: 'queued', label: 'בתור' },
  { key: 'transcribing', label: 'תמלול' },
  { key: 'summarizing', label: 'סיכום' },
]
const IDX = { uploaded: 0, queued: 1, transcribing: 2, summarizing: 3 }
const failed = computed(() => props.call.status === 'failed')
const idx = computed(() => IDX[props.call.status] ?? 2)
const STAGE = {
  uploaded: 'מעלים…',
  queued: 'ממתינה בתור',
  transcribing: 'ivrit.ai מתמלל את השיחה',
  summarizing: 'Claude כותב סיכום',
}
const stageText = computed(() => (failed.value ? 'לא הצלחנו לסכם את השיחה' : STAGE[props.call.status] || 'בעיבוד…'))

const now = ref(Date.now())
let tick = null
onMounted(() => { tick = setInterval(() => { now.value = Date.now() }, 1000) })
onBeforeUnmount(() => clearInterval(tick))
const startMs = computed(() => {
  const t = new Date(props.call.created_at || Date.now()).getTime()
  return Number.isNaN(t) ? Date.now() : t
})
const elapsed = computed(() => Math.max(0, Math.floor((now.value - startMs.value) / 1000)))
const elapsedLabel = computed(() => `${String(Math.floor(elapsed.value / 60)).padStart(2, '0')}:${String(elapsed.value % 60).padStart(2, '0')}`)
// rough ETA: transcription ≈ 1× the call, plus queue + summary headroom
const etaLabel = computed(() => {
  // waiting in the queue behind other agents' calls — no honest ETA until it starts
  if (props.call.status !== 'transcribing' && props.call.status !== 'summarizing') return ''
  const dur = Number(props.call.duration_s) || 0
  if (!dur) return ''
  const left = Math.round(dur + 25 - elapsed.value)
  if (left <= 5) return 'עוד רגע'
  if (left < 60) return `בערך עוד ${left} שנ׳`
  return `בערך עוד ${Math.ceil(left / 60)} דק׳`
})
</script>

<style scoped>
.cwt { display: flex; flex-direction: column; gap: 20px; max-width: 1080px; margin: 0 auto; }
.cwt-head { display: flex; align-items: center; gap: 16px; }
.cwt-copy { display: flex; flex-direction: column; gap: 4px; }
.cwt-stage { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: var(--text); }
.cwt-meta { margin: 0; font-size: 14px; color: var(--text-muted); }
.cwt-err { margin: 0; font-size: 14.5px; color: var(--red); }
.cwt-steps { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.cwt-steps li { display: flex; flex-direction: column; gap: 6px; }
.cwt-bar { height: 3px; border-radius: 3px; background: var(--border-subtle); position: relative; overflow: hidden; }
.is-done .cwt-bar { background: var(--text); }
.is-now .cwt-bar::after { content: ''; position: absolute; inset-block: 0; width: 35%; background: #A63A86; border-radius: 3px; animation: cwtRun 1.6s ease-in-out infinite; }
@keyframes cwtRun { from { inset-inline-start: -35%; } to { inset-inline-start: 100%; } }
.cwt-label { font-size: 12.5px; color: var(--text-muted); }
.is-done .cwt-label, .is-now .cwt-label { color: var(--text); font-weight: 600; }

.cwt-skel { display: flex; flex-direction: column; gap: 14px; padding-top: 8px; border-top: 1px solid var(--border-subtle); }
.sk { position: relative; overflow: hidden; border-radius: 8px; background: #F0EFED; }
.sk::after { content: ''; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.7), transparent); transform: translateX(100%); animation: skSweep 1.8s ease-in-out infinite; }
@keyframes skSweep { to { transform: translateX(-100%); } }
.sk-timeline { height: 72px; border-radius: 12px; }
.cwt-cols { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px; }
.cwt-col { display: flex; flex-direction: column; gap: 10px; }
@media (max-width: 760px) { .cwt-cols { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .sk::after, .is-now .cwt-bar::after { animation: none; } }
</style>
