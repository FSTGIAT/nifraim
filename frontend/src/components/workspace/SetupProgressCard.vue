<template>
  <Transition name="spc-pop">
    <div v-if="visible" class="spc" :class="{ 'spc--celebrating': celebrating }" dir="rtl">
      <!-- Remotion: meshing gears in the next step's colour, in the empty band
           between the texts and the CTA. Decorative; skipped on reduced motion
           and on narrow cards where that band doesn't exist. -->
      <span v-if="!celebrating && !reducedMotion" ref="gearsEl" class="spc-gears" aria-hidden="true"></span>

      <span v-if="celebrating" class="spc-confetti-wrap" aria-hidden="true">
        <span v-for="n in 10" :key="n" class="spc-confetti" :style="confettiStyle(n)"></span>
      </span>

      <!-- progress ring -->
      <div class="spc-ring-wrap">
        <svg class="spc-ring" viewBox="0 0 44 44">
          <circle class="spc-ring-track" cx="22" cy="22" r="19"/>
          <circle class="spc-ring-fill" cx="22" cy="22" r="19" :style="{ strokeDashoffset: ringOffset, stroke: celebrating ? undefined : nextAccent.accent }"/>
        </svg>
        <Transition name="spc-check" mode="out-in">
          <svg v-if="celebrating" key="check" class="spc-ring-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
          <span v-else key="count" class="spc-ring-label ltr-number">{{ completedCount }}/{{ steps.length }}</span>
        </Transition>
      </div>

      <div class="spc-texts">
        <h3 class="spc-title">{{ celebrating ? 'הכל מוכן! המערכת עובדת בשבילכם' : 'הפעלת האוטומציה' }}</h3>
        <p v-if="!celebrating" class="spc-next">
          <span>הצעד הבא:</span>
          <span class="spc-next-chip" :style="{ background: nextAccent.soft, color: nextAccent.deep }">
            <span class="spc-next-dot" :style="{ background: nextAccent.accent }"></span>{{ nextStepTitle }}
          </span>
        </p>
      </div>

      <button v-if="!celebrating" class="spc-cta" :style="{ '--spc-cta': nextAccent.deep, '--spc-cta-glow': nextAccent.accent + '40' }" @click="onContinue">
        המשך הגדרה
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
      </button>

      <!-- In the flex row (last = far left in RTL), never absolutely positioned:
           floating it in the corner put it on top of the CTA. -->
      <button v-if="!celebrating" class="spc-close" aria-label="סגור" title="הסתר (אפשר לחזור מהפעמון)" @click="onClose">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useSetupPipeline, SETUP_ACCENTS } from '../../composables/useSetupPipeline.js'
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

const nextAccent = computed(() => SETUP_ACCENTS[firstIncompleteId.value] || SETUP_ACCENTS.run)

const CIRC = 2 * Math.PI * 19
const ringOffset = computed(() => {
  const frac = completedCount.value / steps.value.length
  return String(CIRC * (1 - frac))
})

// ── Gear background (Remotion via a React island, like BigAddButton) ──
const gearsEl = ref(null)
const reducedMotion =
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
let gearsRoot = null
let gearsMods = null

async function mountGears() {
  if (!gearsEl.value || gearsRoot) return
  try {
    const [rdClient, react, player, comp] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/SetupGears'),
    ])
    if (!gearsEl.value) return
    gearsMods = { react, player, comp }
    gearsRoot = rdClient.createRoot(gearsEl.value)
    paintGears()
  } catch (e) {
    console.error('[SetupProgressCard] gears failed', e) // decorative — card works without it
  }
}

function paintGears() {
  if (!gearsRoot || !gearsMods) return
  const { react, player, comp } = gearsMods
  gearsRoot.render(
    react.createElement(player.Player, {
      component: comp.SetupGears,
      inputProps: { color: nextAccent.value.accent },
      durationInFrames: comp.SETUP_GEARS_FRAMES,
      fps: 30,
      compositionWidth: comp.SETUP_GEARS_W,
      compositionHeight: comp.SETUP_GEARS_H,
      autoPlay: true,
      loop: true,
      controls: false,
      clickToPlay: false,
      doubleClickToFullscreen: false,
      showPosterWhenUnplayed: false,
      acknowledgeRemotionLicense: true,
      style: { width: '100%', height: '100%', backgroundColor: 'transparent' },
    }),
  )
}

function unmountGears() {
  if (gearsRoot) {
    try { gearsRoot.unmount() } catch { /* ignore */ }
    gearsRoot = null
  }
}

watch(() => nextAccent.value.accent, paintGears)
watch(celebrating, (c) => { if (c) unmountGears() })
onBeforeUnmount(unmountGears)

function onContinue() {
  openSetup(firstIncompleteId.value)
}

function onClose() {
  setup.closeCard()
  dismissed.value = true
}

function confettiStyle(n) {
  const colors = [...Object.values(SETUP_ACCENTS).map((a) => a.accent), '#2E844A']
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
  if (setup.isClosed()) { dismissed.value = true; setup.pinReminder(); return }
  if (!reducedMotion) nextTick(mountGears)
})
</script>

<style scoped>
.spc {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  /* Same width, radius and border as the home cards grid below
     (4 × 210px + 3 × 14px gaps = 882px; WorkspaceTabs breakpoints). */
  box-sizing: border-box;
  width: calc(100% - 48px);
  max-width: 882px;
  margin: 24px auto -12px;
  padding: 12px 14px 12px 12px;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  font-family: 'Heebo', sans-serif;
  overflow: hidden;
  z-index: 2;
}
/* Content sits above the gear layer. */
.spc > :not(.spc-gears):not(.spc-confetti-wrap) { position: relative; z-index: 1; }
.spc-gears {
  position: absolute;
  /* The empty band: past the ✕ + CTA (≈190px from the left edge in RTL). */
  left: 196px;
  top: 50%;
  width: 260px;
  height: 100px;
  margin-top: -35px; /* top gear clears the edge; the big one runs off the bottom */
  direction: ltr; /* Player mount must not inherit RTL — see remotion_rtl_player */
  pointer-events: none;
  z-index: 0;
}
.spc--celebrating { border-color: rgba(46, 132, 74, 0.3); background: var(--green-light, #EBF7EE); }

.spc-close {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm, 8px);
  background: transparent;
  color: var(--text-muted, #706E6B);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.spc-close:hover { background: var(--bg, #F3F3F3); color: var(--text, #181818); }
.spc-close:focus-visible, .spc-cta:focus-visible { outline: 2px solid var(--text); outline-offset: 2px; }

.spc-ring-wrap { position: relative; flex-shrink: 0; width: 48px; height: 48px; }
.spc-ring { width: 100%; height: 100%; transform: rotate(-90deg); }
.spc-ring-track { fill: none; stroke: var(--bg, #F3F3F3); stroke-width: 4.5; }
.spc-ring-fill {
  fill: none;
  stroke: var(--tab-automation);
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
.spc-next {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 13px;
  color: var(--text-muted, #706E6B);
  white-space: nowrap;
  min-width: 0;
}
.spc-next-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
}
.spc-next-dot { flex-shrink: 0; width: 6px; height: 6px; border-radius: 50%; }

.spc-cta {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border: none;
  border-radius: 10px;
  /* The next step's own ink (same hue as the chip and the wizard step it
     opens) — never orange. `deep`, not `accent`: white on the sky/teal
     accents fails 4.5:1. */
  background: var(--spc-cta, #0A6664);
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 3px 10px var(--spc-cta-glow, rgba(14, 140, 138, 0.25));
  transition: transform 0.15s, background 0.15s, box-shadow 0.15s;
}
.spc-cta:hover { filter: brightness(0.9); transform: translateY(-1px); }
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

/* Track the cards grid's breakpoints (WorkspaceTabs.vue) so the card never
   outgrows the row of cards it sits above. */
@media (max-width: 960px) {
  .spc { max-width: 628px; } /* 3 × 200px + 2 × 14px */
  .spc-gears { display: none; } /* no free band between texts and CTA */
}
@media (max-width: 700px) {
  .spc { width: calc(100% - 32px); max-width: 460px; margin-top: 16px; flex-wrap: wrap; gap: 12px; }
  .spc-texts { flex-basis: calc(100% - 108px); }
  .spc-cta { flex: 1; justify-content: center; order: 3; }
  .spc-close { order: 2; }
}
/* Phone widths: the fixed notification bell drops to top: 8px (44px tall) and
   would sit on the progress ring — start the card below it. */
@media (max-width: 560px) {
  .spc { margin-top: 64px; }
}

@media (prefers-reduced-motion: reduce) {
  .spc-pop-enter-active, .spc-pop-leave-active { transition: none; }
  .spc-confetti { animation: none; }
  .spc-ring-fill { transition: none; }
}
</style>
