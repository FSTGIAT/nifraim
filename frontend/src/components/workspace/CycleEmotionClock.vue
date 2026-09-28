<template>
  <!-- Workspace home, right side: the monthly cycle as a line-drawn alarm
       clock. A live countdown in the dial (days · hh:mm:ss, seconds on the
       right), a seconds dot on the tick ring, a slowly turning dashed halo, an
       arc that fills as the month runs to the 21st, and a subtle ring every
       12s. Mood is motion only: calm (waiting), brisk (download running),
       paused + amber (computer off). Click → the full cycle widget. -->
  <div v-if="st" class="ec" :class="['ec--' + mood, 'ec--' + tone]">
    <button ref="btnEl" type="button" class="ec-btn" :aria-label="aria" :title="aria" :aria-expanded="open" @click="toggle">
      <svg class="ec-svg" viewBox="0 0 220 240" aria-hidden="true">
        <g class="ec-draw" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <!-- decoration: slow dashed halo + the month's progress arc -->
          <circle class="ec-halo" cx="110" cy="128" r="100" stroke-width="1.2" stroke-dasharray="2 9" opacity="0.45" />
          <circle cx="110" cy="128" r="90" stroke-width="1" opacity="0.14" />
          <circle cx="110" cy="128" r="90" stroke-width="2.6" :stroke-dasharray="`${ARC * frac} ${ARC}`" transform="rotate(-90 110 128)" />
          <circle :cx="tip.x" :cy="tip.y" r="4" fill="currentColor" stroke="none" />

          <g class="ec-shake">
            <!-- sound arcs (ring) -->
            <g class="ec-waves" stroke-width="2">
              <path d="M30 52 q-8 12 0 24" /><path d="M20 46 q-12 18 0 36" />
              <path d="M190 52 q8 12 0 24" /><path d="M200 46 q12 18 0 36" />
            </g>
            <!-- bells -->
            <g class="ec-bell ec-bell--l" stroke-width="2.4"><path d="M44 62 a28 28 0 0 1 38 -22 z" /><path d="M58 56 l-6 -6" /></g>
            <g class="ec-bell ec-bell--r" stroke-width="2.4"><path d="M176 62 a28 28 0 0 0 -38 -22 z" /><path d="M162 56 l6 -6" /></g>
            <g class="ec-hammer" stroke-width="2.4"><path d="M110 34 v16" /><circle cx="110" cy="29" r="5" /></g>
            <!-- legs -->
            <path d="M72 196 l-12 16 M148 196 l12 16" stroke-width="2.6" />
            <!-- body: double outline -->
            <circle cx="110" cy="128" r="72" stroke-width="2.8" fill="var(--card-bg, #fff)" />
            <circle cx="110" cy="128" r="64" stroke-width="1" opacity="0.35" />
            <!-- minute + hour ticks -->
            <line v-for="i in 60" :key="'m' + i"
                  :x1="110 + 60 * Math.cos(i * 6 * Math.PI / 180)" :y1="128 + 60 * Math.sin(i * 6 * Math.PI / 180)"
                  :x2="110 + (i % 5 === 0 ? 51 : 56) * Math.cos(i * 6 * Math.PI / 180)" :y2="128 + (i % 5 === 0 ? 51 : 56) * Math.sin(i * 6 * Math.PI / 180)"
                  :stroke-width="i % 5 === 0 ? 2.2 : 0.9" :opacity="i % 5 === 0 ? 0.9 : 0.35" />
            <!-- seconds: a dot running round the tick ring -->
            <g class="ec-sec" :style="{ '--sec0': secDeg + 'deg' }"><circle cx="110" cy="68" r="3.4" fill="currentColor" stroke="none" /></g>
            <!-- the countdown, in the middle of the dial: days on top, then
                 hh:mm:ss read like a clock — hours LEFT, seconds RIGHT. -->
            <g stroke="none" fill="currentColor" font-family="Heebo, sans-serif" text-anchor="middle">
              <text x="110" y="122" font-size="38" font-weight="800" style="font-variant-numeric: tabular-nums">{{ left.d }}</text>
              <text x="110" y="138" font-size="11" font-weight="700" fill="#181818" opacity="0.55">ימים</text>
              <text x="80" y="162" font-size="15" font-weight="800" style="font-variant-numeric: tabular-nums">{{ left.h }}</text>
              <text x="125" y="161" font-size="13" font-weight="700" opacity="0.35">:</text>
              <text x="110" y="162" font-size="15" font-weight="800" style="font-variant-numeric: tabular-nums">{{ left.m }}</text>
              <text x="95" y="161" font-size="13" font-weight="700" opacity="0.35">:</text>
              <text x="140" y="162" font-size="15" font-weight="800" style="font-variant-numeric: tabular-nums">{{ left.s }}</text>
            </g>
          </g>
        </g>
      </svg>
    </button>

    <!-- what the clock is counting to -->
    <div class="ec-card">
      <span class="ec-what">{{ what }}</span>
    </div>

    <Teleport to="body">
      <Transition name="ec-pop">
        <div v-if="open" class="ec-overlay" @click.self="open = false">
          <div class="ec-pop" :style="popStyle" role="dialog" aria-modal="true" aria-label="המחזור החודשי">
            <CycleHomeTimer embedded @select="onSelect" />
            <button type="button" class="ec-close" aria-label="סגור" @click="open = false">
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useCycleStore, shortDate } from '../../stores/cycle.js'
import CycleHomeTimer from './CycleHomeTimer.vue'

const emit = defineEmits(['select'])
const cycle = useCycleStore()
const st = computed(() => cycle.status)
const open = ref(false)
const btnEl = ref(null)
const popStyle = ref(null)

const now = ref(Date.now())
let timer = null
// The dial shows a live countdown; the seconds dot starts at the current second.
const left = computed(() => {
  const ms = Math.max(0, target.value - now.value)
  const t = Math.floor(ms / 1000)
  const p2 = (n) => String(n).padStart(2, '0')
  return { d: Math.floor(t / 86400), h: p2(Math.floor((t % 86400) / 3600)), m: p2(Math.floor((t % 3600) / 60)), s: p2(t % 60) }
})
const secDeg = ref(new Date().getSeconds() * 6)
// Month progress arc around the dial (previous cycle → target).
const ARC = 2 * Math.PI * 90
const frac = computed(() => {
  const t = target.value
  const start = new Date(t.getFullYear(), t.getMonth() - 1, t.getDate(), t.getHours())
  return Math.max(0.03, Math.min(1, 1 - (t - now.value) / (t - start)))
})
const tip = computed(() => {
  const a = -Math.PI / 2 + frac.value * 2 * Math.PI
  return { x: 110 + 90 * Math.cos(a), y: 128 + 90 * Math.sin(a) }
})
function onKey(e) { if (e.key === 'Escape') open.value = false }
onMounted(() => {
  timer = setInterval(() => { now.value = Date.now() }, 1000)
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('keydown', onKey)
})

const target = computed(() => new Date(st.value?.locked ? st.value.first_cycle_at : st.value?.next_cycle_at))
const days = computed(() => Math.max(0, Math.floor((target.value - now.value) / 86400000)))
const mood = computed(() => {
  if (st.value?.worker_waiting) return 'sleepy'
  if (st.value?.cycle_batch_status === 'running') return 'excited'
  return 'happy'
})
const tone = computed(() => (st.value?.worker_waiting ? 'wait' : st.value?.locked ? 'locked' : 'ok'))
const what = computed(() => {
  const s = st.value
  if (!s) return ''
  if (s.worker_waiting) return 'ממתין שהמחשב יתעורר'
  if (s.cycle_batch_status === 'running') return 'הנפרעים יורדים עכשיו'
  return s.locked ? `עד שהפרודוקציה נפתחת · ${shortDate(s.first_cycle_at)}` : `עד המחזור הבא · ${shortDate(s.next_cycle_at)}`
})
const aria = computed(() => `המחזור החודשי — עוד ${days.value} ימים. לחיצה לפרטים`)

// Open the widget to the LEFT of the clock (it sits on the right edge).
function toggle() {
  if (!open.value && btnEl.value) {
    const r = btnEl.value.getBoundingClientRect()
    const h = 330
    const top = Math.max(16, Math.min(r.top + r.height / 2 - h / 2, window.innerHeight - h - 16))
    const right = window.innerWidth - r.left + 20
    popStyle.value = { top: `${top}px`, right: `${right}px`, width: `min(760px, calc(100vw - ${right + 24}px))` }
  }
  open.value = !open.value
}
function onSelect(tab) {
  open.value = false
  emit('select', tab)
}
</script>

<style scoped>
.ec { display: flex; flex-direction: column; align-items: center; gap: 6px; font-family: 'Heebo', sans-serif; }
.ec--locked { color: var(--tab-production, #2F73C4); }
.ec--ok { color: #0E8C8A; }
.ec--wait { color: #8A6300; }

.ec-btn {
  width: 168px; padding: 0; border: none; background: none; cursor: pointer;
  color: inherit; border-radius: 24px;
  transition: transform 0.2s ease;
}
.ec-btn:hover { transform: scale(1.04); }
.ec-btn:focus-visible { outline: 2px solid var(--primary, #181818); outline-offset: 6px; }
.ec-svg { width: 100%; height: auto; overflow: visible; display: block; }

.ec-card {
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 7px 14px; border-radius: 14px;
  background: var(--card-bg, #fff); border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
}
.ec-what { font-size: 12.5px; font-weight: 700; color: var(--text-secondary, #706E6B); white-space: nowrap; }

/* ── draws itself in once ── */
.ec-draw { animation: ecIn 1.4s cubic-bezier(0.32, 0.72, 0, 1) both; }
@keyframes ecIn { from { opacity: 0; transform: translateY(8px) scale(0.96); } to { opacity: 1; transform: none; } }

/* ── idle: halo turns, second hand ticks ── */
.ec-halo { transform-origin: 110px 128px; animation: ecHalo 80s linear infinite; }
@keyframes ecHalo { to { transform: rotate(360deg); } }
.ec-sec { transform-origin: 110px 128px; animation: ecTick 60s steps(60) infinite; }
@keyframes ecTick { from { transform: rotate(var(--sec0)); } to { transform: rotate(calc(var(--sec0) + 360deg)); } }

/* ── a subtle ring, every 12s ── */
.ec-shake { transform-origin: 110px 200px; animation: ecShake 12s ease-in-out infinite; }
@keyframes ecShake {
  0%, 86%, 100% { transform: rotate(0); }
  87.5% { transform: rotate(-4deg); } 89% { transform: rotate(4deg); }
  90.5% { transform: rotate(-3deg); } 92% { transform: rotate(2deg); } 93.5% { transform: rotate(-1deg); }
}
.ec-bell { animation: ecBell 12s ease-in-out infinite; }
.ec-bell--l { transform-origin: 63px 50px; }
.ec-bell--r { transform-origin: 157px 50px; }
@keyframes ecBell {
  0%, 86%, 95%, 100% { transform: rotate(0); }
  87.5%, 90.5%, 93.5% { transform: rotate(-5deg); }
  89%, 92% { transform: rotate(5deg); }
}
.ec-hammer { transform-origin: 110px 50px; animation: ecHammer 12s linear infinite; }
@keyframes ecHammer {
  0%, 86%, 95%, 100% { transform: rotate(0); }
  87%, 89%, 91%, 93% { transform: rotate(-16deg); }
  88%, 90%, 92%, 94% { transform: rotate(16deg); }
}
.ec-waves { opacity: 0; animation: ecWaves 12s ease-in-out infinite; }
@keyframes ecWaves { 0%, 86%, 96%, 100% { opacity: 0; } 88%, 93% { opacity: 0.6; } }

/* ── moods (motion only, no faces) ── */
.ec--excited .ec-sec { animation-duration: 6s; }   /* the download is running */
.ec--excited .ec-halo { animation-duration: 20s; }
.ec--sleepy .ec-sec, .ec--sleepy .ec-shake, .ec--sleepy .ec-bell,
.ec--sleepy .ec-hammer, .ec--sleepy .ec-waves { animation: none; }  /* computer off: paused */

/* hover: ring now */
.ec-btn:hover .ec-shake, .ec-btn:hover .ec-bell, .ec-btn:hover .ec-hammer, .ec-btn:hover .ec-waves { animation-duration: 2s; }

@media (prefers-reduced-motion: reduce) {
  .ec * { animation: none !important; }
}

/* ── popover ── */
.ec-overlay { position: fixed; inset: 0; z-index: 1010; background: rgba(24, 24, 24, 0.18); }
.ec-pop { position: fixed; }
.ec-close {
  position: absolute; top: 10px; inset-inline-end: 10px;
  width: 32px; height: 32px; border: none; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; color: var(--text-secondary, #706E6B); cursor: pointer; z-index: 3;
}
.ec-close:hover { background: var(--bg, #F3F3F3); color: var(--text-primary, #181818); }
.ec-pop-enter-active, .ec-pop-leave-active { transition: opacity 0.2s ease; }
.ec-pop-enter-active .ec-pop, .ec-pop-leave-active .ec-pop { transition: transform 0.22s ease, opacity 0.22s ease; }
.ec-pop-enter-from, .ec-pop-leave-to { opacity: 0; }
.ec-pop-enter-from .ec-pop, .ec-pop-leave-to .ec-pop { transform: translateX(10px) scale(0.98); opacity: 0; }
</style>
