<template>
  <Transition name="spc-pop">
    <div v-if="visible" class="spc" :class="{ 'spc--celebrating': celebrating }" dir="rtl">
      <button v-if="!celebrating" class="spc-close" aria-label="סגור" @click="onClose">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>

      <span v-if="celebrating" class="spc-confetti-wrap" aria-hidden="true">
        <span v-for="n in 10" :key="n" class="spc-confetti" :style="confettiStyle(n)"></span>
      </span>

      <!-- progress ring -->
      <div class="spc-ring-wrap">
        <svg class="spc-ring" viewBox="0 0 44 44">
          <circle class="spc-ring-track" cx="22" cy="22" r="19"/>
          <circle class="spc-ring-fill" cx="22" cy="22" r="19" :style="{ strokeDashoffset: ringOffset, stroke: celebrating ? undefined : nextAccent }"/>
        </svg>
        <Transition name="spc-check" mode="out-in">
          <svg v-if="celebrating" key="check" class="spc-ring-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
          <span v-else key="count" class="spc-ring-label ltr-number">{{ completedCount }}/{{ steps.length }}</span>
        </Transition>
      </div>

      <div class="spc-texts">
        <h3 class="spc-title">{{ celebrating ? 'הכל מוכן! המערכת עובדת בשבילכם' : 'הפעלת האוטומציה' }}</h3>
        <p v-if="!celebrating" class="spc-next">
          הצעד הבא: <strong :style="{ color: nextAccent }">{{ nextStepTitle }}</strong>
        </p>
      </div>

      <button v-if="!celebrating" class="spc-cta" @click="onContinue">
        המשך הגדרה
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
      </button>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useSetupPipeline } from '../../composables/useSetupPipeline.js'
import { openSetup } from '../../utils/setupState.js'

const setup = useSetupPipeline()
const { steps, completedCount, allDone, firstIncompleteId } = setup

const dismissed = ref(false)
const celebrating = ref(false)
let celebrated = false

const visible = computed(() => !dismissed.value)
const nextStepTitle = computed(
  () => steps.value.find((s) => s.id === firstIncompleteId.value)?.title || '',
)

// Pastel accent per step — same map as SetupPipelineModal
const ACCENTS = { worker: '#E8930C', phone: '#4E9DD0', portal: '#8E6FD6', run: '#1FA88C' }
const nextAccent = computed(() => ACCENTS[firstIncompleteId.value] || '#E8930C')

const CIRC = 2 * Math.PI * 19
const ringOffset = computed(() => {
  const frac = completedCount.value / steps.value.length
  return String(CIRC * (1 - frac))
})

function onContinue() {
  openSetup(firstIncompleteId.value)
}

function onClose() {
  setup.closeCard()
  dismissed.value = true
}

function confettiStyle(n) {
  const colors = ['#F57C00', '#FFB74D', '#2E844A', '#E65100', '#FFCC80']
  return {
    left: `${(n * 83) % 100}%`,
    background: colors[n % colors.length],
    animationDelay: `${(n % 5) * 0.14}s`,
  }
}

// Celebrate once when everything completes while the card is visible, then go away.
watch(allDone, (done) => {
  if (!done || celebrated) return
  celebrated = true
  if (!visible.value) { setup.markCompleted(); return }
  celebrating.value = true
  setTimeout(() => {
    setup.markCompleted()
    dismissed.value = true
  }, 2600)
})

onMounted(async () => {
  setup.migrateFlags()
  if (setup.isCompleted()) { dismissed.value = true; return }
  await setup.bootstrap()
  if (allDone.value) {
    // Returning power user — everything already set up. No card, no fanfare.
    celebrated = true
    setup.markCompleted()
    dismissed.value = true
    return
  }
  if (setup.isClosed()) { dismissed.value = true; setup.pinReminder() }
})
</script>

<style scoped>
.spc {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  max-width: 640px;
  margin: 0 auto 18px;
  padding: 14px 18px;
  background: #fff;
  border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: var(--radius-lg, 16px);
  box-shadow: var(--shadow-sm, 0 2px 6px rgba(24, 24, 24, 0.06));
  font-family: 'Heebo', sans-serif;
  overflow: hidden;
  z-index: 2;
}
.spc--celebrating { border-color: rgba(46, 132, 74, 0.3); background: #F6FBF7; }

.spc-close {
  position: absolute;
  top: 10px;
  left: 10px;
  display: inline-flex;
  padding: 5px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text-tertiary, #706E6B);
  cursor: pointer;
}
.spc-close:hover { background: #F3F3F3; }

.spc-ring-wrap { position: relative; flex-shrink: 0; width: 48px; height: 48px; }
.spc-ring { width: 100%; height: 100%; transform: rotate(-90deg); }
.spc-ring-track { fill: none; stroke: #F0EDE8; stroke-width: 4.5; }
.spc-ring-fill {
  fill: none;
  stroke: var(--primary, #F57C00);
  stroke-width: 4.5;
  stroke-linecap: round;
  stroke-dasharray: 119.4; /* 2π·19 */
  transition: stroke-dashoffset 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}
.spc--celebrating .spc-ring-fill { stroke: var(--accent-emerald, #2E844A); }
.spc-ring-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12.5px;
  font-weight: 800;
  color: var(--text, #181818);
}
.spc-ring-check {
  position: absolute;
  inset: 12px;
  color: var(--accent-emerald, #2E844A);
}
.spc-check-enter-active { transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s; }
.spc-check-enter-from { transform: scale(0.3); opacity: 0; }
.spc-check-leave-active { transition: opacity 0.15s; }
.spc-check-leave-to { opacity: 0; }

.spc-texts { flex: 1; min-width: 0; }
.spc-title { margin: 0 0 2px; font-size: 15px; font-weight: 800; color: var(--text, #181818); }
.spc-next { margin: 0; font-size: 13px; color: var(--text-tertiary, #706E6B); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.spc-next strong { color: var(--primary-deep, #E65100); font-weight: 700; }

.spc-cta {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border: none;
  border-radius: 10px;
  background: var(--primary, #F57C00);
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 3px 10px rgba(245, 124, 0, 0.28);
  transition: transform 0.15s, background 0.15s, box-shadow 0.15s;
}
.spc-cta:hover { background: var(--primary-deep, #E65100); transform: translateY(-1px); }
.spc-cta:active { transform: translateY(0); }

.spc-confetti-wrap { position: absolute; inset: 0; pointer-events: none; }
.spc-confetti {
  position: absolute;
  top: -8px;
  width: 6px;
  height: 10px;
  border-radius: 2px;
  animation: spc-confetti-fall 1.8s linear infinite;
}
@keyframes spc-confetti-fall {
  from { transform: translateY(-12px) rotate(0deg); opacity: 1; }
  to { transform: translateY(110px) rotate(320deg); opacity: 0.15; }
}

.spc-pop-enter-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.spc-pop-leave-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.spc-pop-enter-from, .spc-pop-leave-to { opacity: 0; transform: translateY(-8px); }

@media (prefers-reduced-motion: reduce) {
  .spc-pop-enter-active, .spc-pop-leave-active { transition: none; }
  .spc-confetti { animation: none; }
  .spc-ring-fill { transition: none; }
}
</style>
