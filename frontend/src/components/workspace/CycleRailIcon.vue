<template>
  <!-- Monthly cycle, minimised: an animated alarm clock + days-left badge in
       the top-right corner (tabs / smaller screens — on a roomy home the big
       CycleEmotionClock is shown instead). Click → the full widget. -->
  <div v-if="st" class="cri">
    <button
      type="button"
      class="cri-btn"
      :class="'cri-btn--' + tone"
      :aria-label="label"
      :title="label"
      :aria-expanded="open"
      @click="open = !open"
    >
      <!-- Animated alarm clock: ticking second hand, and every few seconds it
           shakes and rings (bells + sound lines). Days left ride on a badge. -->
      <!-- A mini CycleEmotionClock: same line-drawn bells, hammer, double-ring
           dial, hour ticks, dashed halo and seconds dot, days in the dial. -->
      <svg class="cri-clock" viewBox="0 0 56 60" aria-hidden="true">
        <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <circle class="cri-halo" cx="28" cy="33" r="25" stroke-width="0.9" stroke-dasharray="1.4 4" opacity="0.5" />
          <g class="cri-shake">
            <g class="cri-sound" stroke-width="1.4">
              <path d="M6 13 q-2.5 4 0 8" /><path d="M50 13 q2.5 4 0 8" />
            </g>
            <g class="cri-bell cri-bell--l" stroke-width="1.6"><path d="M10 17 a8 8 0 0 1 11 -6.5 z" /></g>
            <g class="cri-bell cri-bell--r" stroke-width="1.6"><path d="M46 17 a8 8 0 0 0 -11 -6.5 z" /></g>
            <path d="M28 8 v4.5" stroke-width="1.6" /><circle cx="28" cy="6.4" r="1.7" stroke-width="1.5" />
            <path d="M18.5 50 l-3.2 4.2 M37.5 50 l3.2 4.2" stroke-width="1.8" />
            <circle cx="28" cy="33" r="18" stroke-width="2" fill="var(--card-bg, #fff)" />
            <circle cx="28" cy="33" r="15.4" stroke-width="0.8" opacity="0.35" />
            <line v-for="i in 12" :key="i"
                  :x1="28 + 14.4 * Math.cos(i * 30 * Math.PI / 180)" :y1="33 + 14.4 * Math.sin(i * 30 * Math.PI / 180)"
                  :x2="28 + (i % 3 === 0 ? 11.6 : 12.8) * Math.cos(i * 30 * Math.PI / 180)" :y2="33 + (i % 3 === 0 ? 11.6 : 12.8) * Math.sin(i * 30 * Math.PI / 180)"
                  :stroke-width="i % 3 === 0 ? 1.3 : 0.8" :opacity="i % 3 === 0 ? 0.85 : 0.4" />
            <g class="cri-sec"><circle cx="28" cy="18.6" r="1.4" fill="currentColor" stroke="none" /></g>
            <text x="28" y="37.4" text-anchor="middle" font-family="Heebo, sans-serif" font-size="12.5" font-weight="800"
                  fill="currentColor" stroke="none" style="font-variant-numeric: tabular-nums">{{ days }}</text>
          </g>
        </g>
      </svg>
    </button>

    <Teleport to="body">
      <Transition name="cri-pop">
        <div v-if="open" class="cri-overlay" @click.self="open = false">
          <div class="cri-pop" role="dialog" aria-modal="true" aria-label="המחזור החודשי">
            <CycleHomeTimer embedded @select="onSelect" />
            <button type="button" class="cri-close" aria-label="סגור" @click="open = false">
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
import { useCycleStore, cycleNow } from '../../stores/cycle.js'
import CycleHomeTimer from './CycleHomeTimer.vue'

const emit = defineEmits(['select'])
const cycle = useCycleStore()
const st = computed(() => cycle.status)
const open = ref(false)

const now = ref(cycleNow())
let timer = null
function onKey(e) { if (e.key === 'Escape') open.value = false }
onMounted(() => {
  timer = setInterval(() => { now.value = cycleNow() }, 60000)
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('keydown', onKey)
})

const target = computed(() => new Date(st.value?.locked ? st.value.first_cycle_at : st.value?.next_cycle_at))
const days = computed(() => Math.max(0, Math.floor((target.value - now.value) / 86400000)))
const tone = computed(() => {
  if (st.value?.worker_waiting) return 'wait'
  return st.value?.locked || st.value?.needs_production_upload ? 'locked' : 'ok'
})
const label = computed(() => {
  if (st.value?.worker_waiting) return 'המחזור החודשי ממתין למחשב'
  if (st.value?.needs_production_upload) return `הנפרעים של ${st.value.current_period_label} כאן — העלו את הפרודוקציה`
  return st.value?.locked
    ? `לשונית הפרודוקציה נפתחת בעוד ${days.value} ימים`
    : `המחזור הבא בעוד ${days.value} ימים`
})

function onSelect(tab) {
  open.value = false
  emit('select', tab)
}
</script>

<style scoped>
.cri-btn {
  position: relative;
  width: 54px; height: 58px; border-radius: 16px; padding: 0;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: none;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.cri-btn:hover { transform: translateY(-1px) scale(1.05); }
.cri-btn:focus-visible { outline: 2px solid var(--primary, #181818); outline-offset: 2px; }
.cri-btn--locked { color: var(--tab-production, #2F73C4); }
.cri-btn--ok { color: #0A6664; }
.cri-btn--wait { color: var(--amber, #8A6300); }
.cri-clock { width: 50px; height: 54px; overflow: visible; filter: drop-shadow(0 3px 6px rgba(24, 24, 24, 0.12)); }
/* second hand: 60 discrete ticks per minute */
.cri-halo { transform-origin: 28px 33px; animation: criHalo 40s linear infinite; }
@keyframes criHalo { to { transform: rotate(360deg); } }
.cri-sec { transform-origin: 28px 33px; animation: criTick 60s steps(60) infinite; }
@keyframes criTick { to { transform: rotate(360deg); } }

/* every 7s: a short ring — the clock shakes, bells vibrate, sound lines flash */
.cri-shake { transform-origin: 28px 50px; animation: criShake 7s ease-in-out infinite; }
@keyframes criShake {
  0%, 84%, 100% { transform: rotate(0); }
  86% { transform: rotate(-9deg); } 88% { transform: rotate(9deg); }
  90% { transform: rotate(-7deg); } 92% { transform: rotate(7deg); }
  94% { transform: rotate(-4deg); } 96% { transform: rotate(3deg); }
}
.cri-bell { animation: criBell 7s ease-in-out infinite; }
.cri-bell--l { transform-origin: 15px 14px; }
.cri-bell--r { transform-origin: 41px 14px; animation-delay: 0.05s; }
@keyframes criBell {
  0%, 84%, 100% { transform: translateY(0); }
  86%, 90%, 94% { transform: translateY(-1.5px); }
  88%, 92%, 96% { transform: translateY(0.5px); }
}
.cri-sound { opacity: 0; animation: criSound 7s ease-in-out infinite; }
@keyframes criSound {
  0%, 84%, 100% { opacity: 0; }
  87%, 95% { opacity: 0.8; }
}
.cri-btn:hover .cri-shake { animation-duration: 1.4s; }
.cri-btn:hover .cri-bell, .cri-btn:hover .cri-sound { animation-duration: 1.4s; }

.cri-overlay { position: fixed; inset: 0; z-index: 1010; background: rgba(24, 24, 24, 0.18); }
.cri-pop {
  position: fixed;
  top: 36px;
  inset-inline-start: 80px; /* RTL: just left of the right rail */
  width: min(760px, calc(100vw - 100px));
}
.cri-close {
  position: absolute; top: 10px; inset-inline-end: 10px;
  width: 32px; height: 32px; border: none; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; color: var(--text-secondary, #706E6B); cursor: pointer; z-index: 3;
}
.cri-close:hover { background: var(--bg, #F3F3F3); color: var(--text-primary, #181818); }
@media (max-width: 720px) {
  .cri-pop { inset-inline-start: 12px; width: calc(100vw - 24px); top: 64px; }
}

.cri-pop-enter-active, .cri-pop-leave-active { transition: opacity 0.2s ease; }
.cri-pop-enter-active .cri-pop, .cri-pop-leave-active .cri-pop { transition: transform 0.22s ease, opacity 0.22s ease; }
.cri-pop-enter-from, .cri-pop-leave-to { opacity: 0; }
.cri-pop-enter-from .cri-pop, .cri-pop-leave-to .cri-pop { transform: translateY(-8px) scale(0.98); opacity: 0; }
@media (prefers-reduced-motion: reduce) { .cri-sec, .cri-shake, .cri-bell, .cri-sound, .cri-halo { animation: none; } }
</style>
