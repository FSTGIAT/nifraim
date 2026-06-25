<template>
  <Teleport to="body">
    <Transition name="mc-modal">
      <div
        v-if="open"
        class="mc-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="השוואת עמלות 3 חודשים אחרונים"
        @click.self="close"
      >
        <div class="mc-card">
          <header class="mc-head">
            <div class="mc-head-left">
              <span class="mc-badge" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="20" x2="12" y2="10"/>
                  <line x1="18" y1="20" x2="18" y2="4"/>
                  <line x1="6" y1="20" x2="6" y2="16"/>
                </svg>
              </span>
              <div class="mc-titles">
                <span class="mc-title">השוואת עמלות — 3 חודשים אחרונים</span>
                <span class="mc-sub">צפוי לפי פרודוקציה × עמלות מוסכמות • בפועל לפי קבצי נפרעים</span>
              </div>
            </div>
            <button class="mc-icon-btn" type="button" title="סגור" @click="close">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </header>

          <div class="mc-body">
            <div v-if="loading" class="mc-state">
              <div class="mc-loader"></div>
              <span>טוען נתונים…</span>
            </div>
            <div v-else-if="error" class="mc-state mc-state--error">{{ error }}</div>
            <template v-else>
              <div class="mc-viz-row">
                <div ref="mountEl" class="mc-mount mc-mount--bars" aria-hidden="true"></div>
                <div ref="mountElCircle" class="mc-mount mc-mount--circle" aria-hidden="true"></div>
              </div>

              <!-- Textual summary table — gives the same numbers the Remotion
                   animation shows, in a format the user can scroll/copy. -->
              <div class="mc-table-wrap">
                <table class="mc-table">
                  <thead>
                    <tr>
                      <th>חודש</th>
                      <th>סטטוס</th>
                      <th>צפוי</th>
                      <th>בפועל</th>
                      <th>פער</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="m in months" :key="m.period_month">
                      <td>{{ m.label }}</td>
                      <td>
                        <span class="mc-chip" :class="statusChipClass(m)">
                          {{ statusChipLabel(m) }}
                        </span>
                      </td>
                      <td>
                        <span v-if="m.expected_total != null" class="ltr-number">{{ fmt(m.expected_total) }}</span>
                        <span v-else class="mc-muted">—</span>
                      </td>
                      <td>
                        <span v-if="m.actual_total != null" class="ltr-number">{{ fmt(m.actual_total) }}</span>
                        <span v-else class="mc-muted">—</span>
                      </td>
                      <td>
                        <span
                          v-if="m.gap_total != null"
                          class="ltr-number"
                          :class="m.gap_total > 0 ? 'mc-gap-positive' : 'mc-gap-zero'"
                        >
                          {{ fmt(m.gap_total) }}
                        </span>
                        <span v-else class="mc-muted">—</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useInsightsStore } from '../../stores/insights.js'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open'])

const insightsStore = useInsightsStore()

const mountEl = ref(null)
const mountElCircle = ref(null)
const loading = computed(() => insightsStore.monthlyLoading)
const error = computed(() => insightsStore.monthlyError)
const months = computed(() => insightsStore.monthly?.months || [])
const hasAnyMonths = computed(() => months.value.length > 0)

function fmt(v) {
  if (v == null) return '—'
  return '₪' + Math.round(v).toLocaleString('he-IL')
}

// One chip per month telling the user at a glance the upload state. Note
// "הכל הועלה" must mean every recurring נפרעים company filed — not merely that
// one commission file exists — otherwise it contradicts the missing-files ring
// (e.g. April had a file from הפניקס but מור/מנורה were still missing).
function statusChipClass(m) {
  if (!m.production_uploaded && !m.commission_uploaded) return 'mc-chip--missing'
  if (!m.commission_uploaded) return 'mc-chip--partial'
  if ((m.missing_count || 0) > 0) return 'mc-chip--partial'
  return 'mc-chip--ok'
}
function statusChipLabel(m) {
  if (!m.production_uploaded && !m.commission_uploaded) return 'אין נתונים'
  if (!m.production_uploaded) return 'חסרה פרודוקציה'
  if (!m.commission_uploaded) return 'חסר נפרעים'
  const miss = m.missing_count || 0
  if (miss === 1) return 'חסר דיווח אחד'
  if (miss > 1) return `חסרים ${miss} דיווחים`
  return 'הכל הועלה'
}

function close() {
  emit('update:open', false)
}

// ── Remotion mounting — same chunk-split + stale-root pattern as AiVizPanel.
// Two players side by side: bars (expected vs actual) + circle (missing files).
let reactStack = null
let reactRoot = null            // bars
let currentMountEl = null
let reactRootCircle = null      // missing-files ring
let currentMountElCircle = null

async function ensureReactStack() {
  if (reactStack) return reactStack
  const [rdClient, react, player, remotion] = await Promise.all([
    import('react-dom/client'),
    import('react'),
    import('@remotion/player'),
    import('../../remotion'),
  ])
  reactStack = {
    createRoot: rdClient.createRoot,
    createElement: react.createElement,
    Player: player.Player,
    Comp: remotion.MonthlyCommissionComposition,
    durationFrames: remotion.MONTHLY_COMMISSION_DURATION_FRAMES,
    fps: remotion.MONTHLY_COMMISSION_FPS,
    CircleComp: remotion.MissingFilesComposition,
    circleDuration: remotion.MISSING_FILES_DURATION_FRAMES,
    circleFps: remotion.MISSING_FILES_FPS,
  }
  return reactStack
}

function commonPlayerProps(prefersReducedMotion) {
  const restFrames = prefersReducedMotion ? 0 : 108000  // ~1h still-tail
  return {
    autoPlay: true,
    loop: false,
    controls: false,
    clickToPlay: false,
    doubleClickToFullscreen: false,
    showPosterWhenUnplayed: false,
    showPosterWhenPaused: false,
    showPosterWhenEnded: false,
    showPosterWhenBuffering: false,
    acknowledgeRemotionLicense: true,
    style: { width: '100%', borderRadius: 12, overflow: 'hidden' },
    _restFrames: restFrames,
  }
}

async function renderPlayer() {
  if (!mountEl.value || !months.value.length) return
  try {
    const stack = await ensureReactStack()
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const base = commonPlayerProps(prefersReducedMotion)
    const periodKey = months.value[0]?.period_month

    // ── Bars (expected vs actual). API is newest-first; reverse so the
    // composition renders oldest→newest left-to-right (RTL card → newest right).
    if (mountEl.value) {
      if (reactRoot && currentMountEl !== mountEl.value) {
        try { reactRoot.unmount() } catch { /* ignore */ }
        reactRoot = null
      }
      if (!reactRoot) {
        reactRoot = stack.createRoot(mountEl.value)
        currentMountEl = mountEl.value
      }
      const totalFrames = (prefersReducedMotion ? 1 : stack.durationFrames) + base._restFrames
      reactRoot.render(stack.createElement(stack.Player, {
        ...base,
        key: `mc-bars-${months.value.length}-${periodKey}`,
        component: stack.Comp,
        inputProps: { months: [...months.value].reverse() },
        durationInFrames: totalFrames,
        fps: stack.fps,
        compositionWidth: 760,
        compositionHeight: 440,
      }))
    }

    // ── Circle (missing נפרעים files). Newest month at the top of the stack.
    if (mountElCircle.value) {
      if (reactRootCircle && currentMountElCircle !== mountElCircle.value) {
        try { reactRootCircle.unmount() } catch { /* ignore */ }
        reactRootCircle = null
      }
      if (!reactRootCircle) {
        reactRootCircle = stack.createRoot(mountElCircle.value)
        currentMountElCircle = mountElCircle.value
      }
      const circleFrames = (prefersReducedMotion ? 1 : stack.circleDuration) + base._restFrames
      const ringCount = Math.max(1, months.value.length)
      reactRootCircle.render(stack.createElement(stack.Player, {
        ...base,
        key: `mc-circle-${months.value.length}-${periodKey}`,
        component: stack.CircleComp,
        inputProps: { months: months.value },
        durationInFrames: circleFrames,
        fps: stack.circleFps,
        compositionWidth: 480,
        compositionHeight: Math.min(560, 180 + ringCount * 180),
      }))
    }
  } catch (e) {
    console.error('[MonthlyCommissionModal] render failed', e)
  }
}

watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    if (!insightsStore.monthly) {
      await insightsStore.fetchMonthlyCommission(3)
    }
    await nextTick()
    if (hasAnyMonths.value) renderPlayer()
  }
})

watch(months, async () => {
  if (props.open && hasAnyMonths.value) {
    await nextTick()
    renderPlayer()
  }
})

onBeforeUnmount(() => {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentMountEl = null
  }
  if (reactRootCircle) {
    try { reactRootCircle.unmount() } catch { /* ignore */ }
    reactRootCircle = null
    currentMountElCircle = null
  }
})
</script>

<style scoped>
.mc-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(17, 12, 6, 0.45);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.mc-card {
  width: 100%;
  max-width: 1320px;
  max-height: 94vh;
  background: var(--bg-surface, #fff);
  border-radius: var(--radius-lg, 16px);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.mc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border, #DDDBDA);
  background: linear-gradient(135deg, #FFF3E0 0%, #FFFFFF 100%);
}
.mc-head-left { display: flex; align-items: center; gap: 12px; }
.mc-badge {
  width: 32px; height: 32px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #F57C00 0%, #FFA040 100%);
  box-shadow: 0 4px 10px rgba(245, 124, 0, 0.3);
}
.mc-titles { display: flex; flex-direction: column; }
.mc-title { font-size: 15px; font-weight: 700; color: var(--text, #181818); }
.mc-sub { font-size: 12px; color: var(--text-muted, #706E6B); margin-top: 2px; }
.mc-icon-btn {
  width: 32px; height: 32px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted, #706E6B);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.18s ease, color 0.18s ease;
}
.mc-icon-btn:hover { background: var(--primary-light, #FFF3E0); color: var(--primary, #F57C00); }

.mc-body {
  padding: 18px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mc-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; padding: 36px 12px;
  color: var(--text-muted, #706E6B);
  font-size: 14px;
}
.mc-state--error { color: var(--red, #EA001E); }
.mc-state--empty strong { color: var(--text, #181818); font-size: 15px; }

.mc-loader {
  width: 28px; height: 28px;
  border: 2.5px solid var(--primary-light, #FFF3E0);
  border-top-color: var(--primary, #F57C00);
  border-radius: 50%;
  animation: mc-spin 0.9s linear infinite;
}
@keyframes mc-spin { to { transform: rotate(360deg); } }

.mc-mount { width: 100%; }
/* Two players side by side: bars (wider) + missing-files circle. Stacks on
   narrow screens. */
.mc-viz-row {
  display: flex;
  gap: 16px;
  align-items: stretch;
}
.mc-mount--bars { flex: 2 1 0; min-width: 0; }
.mc-mount--circle { flex: 1 1 0; min-width: 0; }
@media (max-width: 880px) {
  .mc-viz-row { flex-direction: column; }
}

.mc-table-wrap {
  border: 1px solid var(--border, #DDDBDA);
  border-radius: var(--radius-md, 12px);
  overflow: hidden;
}
.mc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.mc-table th, .mc-table td {
  padding: 10px 12px;
  text-align: right;
  border-bottom: 1px solid var(--border-subtle, #E5E5E5);
}
.mc-table th {
  background: var(--primary-light, #FFF3E0);
  font-weight: 700;
  color: var(--primary-deep, #E65100);
  text-align: right;
}
.mc-table tbody tr:last-child td { border-bottom: none; }
.mc-chip {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.mc-chip--ok { background: rgba(46, 132, 74, 0.12); color: var(--green, #2E844A); }
.mc-chip--partial { background: rgba(245, 124, 0, 0.12); color: var(--primary-deep, #E65100); }
.mc-chip--missing { background: rgba(112, 110, 107, 0.12); color: var(--text-muted, #706E6B); }
.mc-gap-positive { color: var(--red, #EA001E); font-weight: 700; }
.mc-gap-zero { color: var(--green, #2E844A); font-weight: 600; }
.mc-muted { color: var(--text-muted, #706E6B); }

.mc-modal-enter-active, .mc-modal-leave-active {
  transition: opacity 0.2s ease;
}
.mc-modal-enter-from, .mc-modal-leave-to { opacity: 0; }
</style>
