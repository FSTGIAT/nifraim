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
              <div ref="mountEl" class="mc-mount" aria-hidden="true"></div>

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
const loading = computed(() => insightsStore.monthlyLoading)
const error = computed(() => insightsStore.monthlyError)
const months = computed(() => insightsStore.monthly?.months || [])
const hasAnyMonths = computed(() => months.value.length > 0)

function fmt(v) {
  if (v == null) return '—'
  return '₪' + Math.round(v).toLocaleString('he-IL')
}

// One chip per month telling the user at a glance whether each input exists.
// Three states keep the table readable when a month has only commission OR
// only production (e.g. February has נפרעים but no production tagged for it).
function statusChipClass(m) {
  if (m.production_uploaded && m.commission_uploaded) return 'mc-chip--ok'
  if (!m.production_uploaded && !m.commission_uploaded) return 'mc-chip--missing'
  return 'mc-chip--partial'
}
function statusChipLabel(m) {
  if (m.production_uploaded && m.commission_uploaded) return 'הכל הועלה'
  if (!m.production_uploaded && !m.commission_uploaded) return 'אין נתונים'
  if (m.production_uploaded) return 'חסר נפרעים'
  return 'חסרה פרודוקציה'
}

function close() {
  emit('update:open', false)
}

// ── Remotion mounting — same chunk-split + stale-root pattern as AiVizPanel
let reactStack = null
let reactRoot = null
let currentMountEl = null

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
  }
  return reactStack
}

async function renderPlayer() {
  if (!mountEl.value || !months.value.length) return
  try {
    const stack = await ensureReactStack()
    if (!mountEl.value) return
    if (reactRoot && currentMountEl !== mountEl.value) {
      try { reactRoot.unmount() } catch { /* ignore */ }
      reactRoot = null
    }
    if (!reactRoot) {
      reactRoot = stack.createRoot(mountEl.value)
      currentMountEl = mountEl.value
    }
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const restFrames = prefersReducedMotion ? 0 : 108000  // ~1h tail so final frame persists
    const totalFrames = (prefersReducedMotion ? 1 : stack.durationFrames) + restFrames

    // months are returned newest-first by API; the Remotion composition
    // arranges them right-to-left so the newest sits on the right (Hebrew
    // reading order). Reverse here so the chronological array reads
    // "oldest → newest" left-to-right in LTR but renders RTL in the card.
    const payload = { months: [...months.value].reverse() }

    const element = stack.createElement(stack.Player, {
      key: `monthly-commission-${months.value.length}-${months.value[0]?.period_month}`,
      component: stack.Comp,
      inputProps: payload,
      durationInFrames: totalFrames,
      fps: stack.fps,
      compositionWidth: 760,
      compositionHeight: 440,
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
    })
    reactRoot.render(element)
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
  max-width: 820px;
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
  background: linear-gradient(135deg, #FFF8F0 0%, #FFFFFF 100%);
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
