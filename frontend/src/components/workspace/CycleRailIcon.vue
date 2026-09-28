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
      <svg class="cri-clock" viewBox="0 0 48 48" aria-hidden="true">
        <g class="cri-shake">
          <!-- sound lines (only while ringing) -->
          <g class="cri-sound" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M5 10 q-2 4 0 8" /><path d="M2 8 q-3 6 0 12" />
            <path d="M43 10 q2 4 0 8" /><path d="M46 8 q3 6 0 12" />
          </g>
          <!-- bells + hammer -->
          <g class="cri-bell cri-bell--l"><path d="M9 13 a8 8 0 0 1 11 -6 z" fill="currentColor" /></g>
          <g class="cri-bell cri-bell--r"><path d="M39 13 a8 8 0 0 0 -11 -6 z" fill="currentColor" /></g>
          <path d="M24 6 v4" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
          <circle cx="24" cy="5" r="2" fill="currentColor" />
          <!-- legs -->
          <path d="M14 40 l-3 4 M34 40 l3 4" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
          <!-- body -->
          <circle cx="24" cy="26" r="15" fill="#fff" stroke="currentColor" stroke-width="3" />
          <!-- hour ticks -->
          <g stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity="0.55">
            <path d="M24 14.5 v2" /><path d="M35.5 26 h-2" /><path d="M24 37.5 v-2" /><path d="M12.5 26 h2" />
          </g>
          <!-- hands: hour + minute fixed at ~10:10 (friendly), second ticks -->
          <path d="M24 26 L19 22" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
          <path d="M24 26 L30 19" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
          <g class="cri-sec"><path d="M24 28 V16" stroke="#EA001E" stroke-width="1.4" stroke-linecap="round" /></g>
          <circle cx="24" cy="26" r="1.9" fill="currentColor" />
        </g>
      </svg>
      <span class="cri-badge ltr-number">{{ days }}</span>
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
import { useCycleStore } from '../../stores/cycle.js'
import CycleHomeTimer from './CycleHomeTimer.vue'

const emit = defineEmits(['select'])
const cycle = useCycleStore()
const st = computed(() => cycle.status)
const open = ref(false)

const now = ref(Date.now())
let timer = null
function onKey(e) { if (e.key === 'Escape') open.value = false }
onMounted(() => {
  timer = setInterval(() => { now.value = Date.now() }, 60000)
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
  return st.value?.locked ? 'locked' : 'ok'
})
const label = computed(() => {
  if (st.value?.worker_waiting) return 'המחזור החודשי ממתין למחשב'
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
  width: 46px; height: 46px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle, #E5E5E5);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.cri-btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-md, 0 6px 18px rgba(0, 0, 0, 0.1)); }
.cri-btn:focus-visible { outline: 2px solid var(--primary, #181818); outline-offset: 2px; }
.cri-btn--locked { color: var(--tab-production, #2F73C4); }
.cri-btn--ok { color: #0A6664; }
.cri-btn--wait { color: var(--amber, #8A6300); }
.cri-clock { width: 34px; height: 34px; overflow: visible; }
.cri-badge {
  position: absolute; bottom: -4px; inset-inline-end: -6px;
  min-width: 22px; height: 20px; padding: 0 6px; border-radius: 999px;
  display: inline-flex; align-items: center; justify-content: center;
  background: currentColor; box-shadow: 0 0 0 2px #fff;
  font-family: 'Heebo', sans-serif; font-size: 11.5px; font-weight: 900; line-height: 1;
}
/* background = the tone (currentColor); the digits are white */
.cri-badge { -webkit-text-fill-color: #fff; }

/* second hand: 60 discrete ticks per minute */
.cri-sec { transform-origin: 24px 26px; animation: criTick 60s steps(60) infinite; }
@keyframes criTick { to { transform: rotate(360deg); } }

/* every 7s: a short ring — the clock shakes, bells vibrate, sound lines flash */
.cri-shake { transform-origin: 24px 40px; animation: criShake 7s ease-in-out infinite; }
@keyframes criShake {
  0%, 84%, 100% { transform: rotate(0); }
  86% { transform: rotate(-9deg); } 88% { transform: rotate(9deg); }
  90% { transform: rotate(-7deg); } 92% { transform: rotate(7deg); }
  94% { transform: rotate(-4deg); } 96% { transform: rotate(3deg); }
}
.cri-bell { animation: criBell 7s ease-in-out infinite; }
.cri-bell--l { transform-origin: 14px 12px; }
.cri-bell--r { transform-origin: 34px 12px; animation-delay: 0.05s; }
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
@media (prefers-reduced-motion: reduce) { .cri-sec, .cri-shake, .cri-bell, .cri-sound { animation: none; } }
</style>
