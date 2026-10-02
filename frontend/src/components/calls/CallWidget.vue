<template>
  <div v-if="store.enabled" class="cw" :class="['cw--' + size, 'cw--' + phase]">
    <!-- Nifra Calls — the home-hub launcher, in the Nifra Agent family (glass
         ring, glow, breathing) but brighter. It mirrors what is happening
         (recording swells with the mic, processing thinks, a badge counts
         unseen summaries); a click opens the full-screen calls studio, where
         recording and reading happen. -->
    <button
      ref="ringEl"
      type="button"
      class="cw-ring"
      :title="title"
      :aria-label="title"
      @click="openStudio"
    >
      <CallsOrb :size="size === 'big' ? 118 : 54" :state="orbState" :level="store.micLevel" :still="studioOpen" />
      <svg v-if="phase === 'uploading'" class="cw-arc" viewBox="0 0 100 100" aria-hidden="true">
        <circle class="cw-arc-track" cx="50" cy="50" r="47" pathLength="100" />
        <circle class="cw-arc-done" cx="50" cy="50" r="47" pathLength="100" :style="{ strokeDasharray: arcPct + ' 100' }" />
        <circle class="cw-arc-run" cx="50" cy="50" r="47" pathLength="100" />
      </svg>
      <b v-if="unseen && phase === 'idle'" class="cw-badge ltr-number">{{ unseen }}</b>
      <span v-if="phase === 'recording'" class="cw-rec" aria-hidden="true"></span>
    </button>

    <button v-if="size === 'big' || phase !== 'idle'" type="button" class="cw-cap"
            :class="{ 'cw-cap--live': phase === 'recording' }" @click="openStudio">
      <template v-if="phase === 'recording'">
        <span class="cw-dot" aria-hidden="true"></span>
        <span>מקליט <span class="ltr-number">{{ timeLabel }}</span></span>
      </template>
      <template v-else-if="phase === 'uploading'">שולח <span class="ltr-number">{{ Math.round(store.uploadProgress * 100) }}%</span></template>
      <template v-else-if="phase === 'processing'">ממתין לסיכום</template>
      <template v-else-if="unseen">סיכום מוכן</template>
      <template v-else><span dir="ltr">Nifra <b>Calls</b></span></template>
    </button>

    <CallsStudio v-model:open="studioOpen" @seen="markAllSeen" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useCallsStore, CALL_TERMINAL, isNoSpeech } from '../../stores/calls'
import { getUserFlag, setUserFlag } from '../../utils/userFlags'
import CallsOrb from './CallsOrb.vue'
import CallsStudio from './CallsStudio.vue'

const props = defineProps({
  size: { type: String, default: 'big' }, // big (home) | small (corner)
  popSide: { type: String, default: 'left' }, // kept for the mount points; the studio owns popovers now
})
const store = useCallsStore()
const ringEl = ref(null)
const studioOpen = ref(false)


const inFlight = computed(() => store.calls.some((c) => !CALL_TERMINAL.has(c.status)) || (store.current && !CALL_TERMINAL.has(store.current.status)))
const phase = computed(() => {
  if (store.recState === 'recording') return 'recording'
  if (store.recState === 'requesting' || store.recState === 'uploading') return 'uploading'
  if (inFlight.value) return 'processing'
  return 'idle'
})
// the arc only tracks the upload; after that the call waits in a shared queue (minutes, with many agents)
const arcPct = computed(() => Math.max(3, Math.round(store.uploadProgress * 100)))
const timeLabel = computed(() => {
  const s = store.elapsed
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})

// unseen summaries (per user)
function readSeen() {
  try { return new Set(JSON.parse(getUserFlag('calls_seen') || '[]')) } catch (_) { return new Set() }
}
const seen = ref(readSeen())
const unseen = computed(() => store.calls.filter((c) => c.status === 'done' && !isNoSpeech(c) && !seen.value.has(c.id)).length)
function markAllSeen() {
  const ids = store.calls.filter((c) => c.status === 'done').map((c) => c.id)
  seen.value = new Set([...seen.value, ...ids])
  setUserFlag('calls_seen', JSON.stringify([...seen.value].slice(-300)))
}
watch(() => store.calls.map((c) => c.id + c.status).join(), () => { if (studioOpen.value) markAllSeen() })

const orbState = computed(() => {
  if (phase.value === 'recording') return 'recording'
  if (phase.value === 'uploading') return 'processing'
  return unseen.value ? 'done' : 'idle'
})
const title = computed(() => {
  if (phase.value === 'recording') return `מקליט ${timeLabel.value}`
  if (phase.value === 'processing') return 'שיחה ממתינה לסיכום'
  if (unseen.value) return `${unseen.value} סיכומי שיחה מחכים לכם`
  return 'Nifra Calls — הקלטת שיחה'
})

function openStudio() {
  studioOpen.value = true
  markAllSeen()
}

onMounted(async () => {
  await store.hydrate()
  if (getUserFlag('calls_seen') === null) markAllSeen() // first visit: old calls aren't "new"
})
</script>

<style scoped>
.cw { position: relative; display: inline-flex; flex-direction: column; align-items: center; gap: 8px; font-family: 'Heebo', sans-serif; }
.cw-ring {
  position: relative; display: grid; place-items: center; padding: 0; border: none; background: none; border-radius: 50%; cursor: pointer;
  transition: transform 0.25s ease;
}
.cw-ring:hover { transform: scale(1.05); }
.cw-ring:focus-visible { outline: 2px solid var(--tab-calls); outline-offset: 8px; }

.cw-arc { position: absolute; inset: -7px; width: calc(100% + 14px); height: calc(100% + 14px); transform: rotate(-90deg); pointer-events: none; overflow: visible; }
.cw-arc circle { fill: none; stroke-linecap: round; }
.cw-arc-track { stroke: rgba(217, 106, 181, 0.2); stroke-width: 3; }
.cw-arc-done { stroke: #A63A86; stroke-width: 3.4; transition: stroke-dasharray 0.9s cubic-bezier(0.32, 0.72, 0, 1); }
.cw-arc-run { stroke: #D96AB5; stroke-width: 3.4; stroke-dasharray: 9 91; animation: cwRun 1.6s linear infinite; }
@keyframes cwRun { from { stroke-dashoffset: 0; } to { stroke-dashoffset: -100; } }

.cw-badge {
  position: absolute; top: 4px; inset-inline-end: 4px; min-width: 22px; height: 22px; padding: 0 6px; border-radius: 999px;
  display: grid; place-items: center; font-size: 12px; font-weight: 900; color: #fff; background: #181818; box-shadow: 0 0 0 2px #fff;
}
.cw--small .cw-badge { top: -4px; inset-inline-end: -4px; min-width: 18px; height: 18px; font-size: 10.5px; }
.cw-rec { position: absolute; top: 8px; inset-inline-start: 10px; width: 10px; height: 10px; border-radius: 50%; background: var(--red); box-shadow: 0 0 0 2px #fff; animation: cwBlink 1.2s ease-in-out infinite; }
.cw--small .cw-rec { top: -2px; inset-inline-start: -2px; width: 9px; height: 9px; }

.cw-cap {
  display: inline-flex; align-items: center; gap: 6px; padding: 5px 13px; border: none; border-radius: 999px; cursor: pointer;
  background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(8px); box-shadow: 0 2px 10px rgba(24, 24, 24, 0.08);
  font: inherit; font-size: 13px; font-weight: 800; letter-spacing: -0.01em; color: #181818; white-space: nowrap;
}
.cw-cap b { color: #C2378F; font-weight: 900; }
.cw-cap:hover { background: #fff; }
.cw-cap--live { color: var(--tab-calls-ink); }
.cw--small .cw-cap { font-size: 11px; padding: 3px 9px; }
.cw-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--red); animation: cwBlink 1.2s ease-in-out infinite; }
@keyframes cwBlink { 50% { opacity: 0.25; } }
@media (prefers-reduced-motion: reduce) { .cw-arc-run, .cw-rec, .cw-dot { animation: none; } .cw-arc-done { transition: none; } }
</style>
