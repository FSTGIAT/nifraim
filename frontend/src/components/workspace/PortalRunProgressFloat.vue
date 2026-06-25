<template>
  <Teleport to="body">
    <Transition name="prf">
      <div v-if="run" class="prf-shell" :class="shellClass">
        <!-- Animated gradient bar across the top (always running while active) -->
        <div class="prf-topbar">
          <div class="prf-topbar-fill" :style="{ width: progressPct + '%' }"></div>
          <div v-if="isActive" class="prf-shimmer"></div>
        </div>

        <div class="prf-body">
          <!-- Header row: portal label + elapsed time + close (when terminal) -->
          <div class="prf-head">
            <div class="prf-portal">
              <div class="prf-portal-dot" :style="brandDotStyle"></div>
              <div class="prf-portal-text">
                <div class="prf-portal-name">{{ portalLabel }}</div>
                <div class="prf-portal-sub">{{ statusLine }}</div>
              </div>
            </div>
            <div class="prf-meta">
              <span class="prf-elapsed ltr-number">{{ elapsedLabel }}</span>
              <button
                v-if="isTerminal"
                class="prf-close"
                @click="dismiss"
                aria-label="סגור"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Stage rail: four stages with connector lines -->
          <ol class="prf-stages">
            <li
              v-for="(s, i) in STAGES"
              :key="s.key"
              class="prf-stage"
              :class="stageClass(s.key)"
            >
              <span class="prf-stage-marker">
                <svg
                  v-if="stageStatus(s.key) === 'done'"
                  width="10" height="10" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"
                ><polyline points="20 6 9 17 4 12"/></svg>
                <span v-else-if="stageStatus(s.key) === 'active'" class="prf-stage-pulse"></span>
                <svg
                  v-else-if="stageStatus(s.key) === 'failed'"
                  width="10" height="10" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"
                ><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </span>
              <span class="prf-stage-label">{{ s.label }}</span>
              <span
                v-if="i < STAGES.length - 1"
                class="prf-stage-line"
                :class="{ 'prf-stage-line--done': stageStatus(s.key) === 'done' }"
              ></span>
            </li>
          </ol>

          <!-- "Don't close" reassurance — only while actively running -->
          <div v-if="isActive" class="prf-reassure">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>הריצה ממשיכה ברקע — אפשר לעבור ללשונית אחרת. עד 3 דקות.</span>
          </div>

          <!-- Terminal banners -->
          <div v-else-if="run.status === 'success'" class="prf-banner prf-banner--ok">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span>הסתיים בהצלחה — הדוח נוסף להעלאות.</span>
          </div>
          <div v-else-if="isTerminal" class="prf-banner prf-banner--err">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span class="prf-banner-text">
              {{ run.status === 'timeout' ? 'פסק זמן' : 'נכשל' }}<span v-if="run.error_message">: {{ run.error_message }}</span>
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { brandFor } from '../../utils/companyBrand.js'

const store = usePortalAutomationStore()

const STAGES = [
  { key: 'login',    label: 'כניסה' },
  { key: 'otp',      label: 'קוד SMS' },
  { key: 'download', label: 'הורדה' },
  { key: 'parse',    label: 'עיבוד' },
]

const ACTIVE = new Set(['pending', 'running', 'awaiting_otp', 'downloading', 'parsing'])
const TERMINAL = new Set(['success', 'failed', 'timeout'])

// Local override so the user can dismiss a terminal-state card.
const dismissedRunId = ref(null)

const run = computed(() => {
  const r = store.activeRun
  if (!r) return null
  if (dismissedRunId.value === r.id) return null
  return r
})

const isActive = computed(() => run.value && ACTIVE.has(run.value.status))
const isTerminal = computed(() => run.value && TERMINAL.has(run.value.status))

// Cred + brand for the portal name/colour
const cred = computed(() => {
  if (!run.value) return null
  return store.credentials.find((c) => c.id === run.value.credential_id) || null
})
const portalLabel = computed(() => {
  if (!cred.value) return 'אוטומציית פורטל'
  const kind = cred.value.portal_kind
  const fromStore = store.portalKinds.find((k) => k.id === kind)?.label
  return fromStore || brandFor(kind).label || kind
})
const brandDotStyle = computed(() => {
  if (!cred.value) return { background: 'linear-gradient(135deg, #F57C00, #FF9800)' }
  const b = brandFor(cred.value.portal_kind)
  const c = b?.color || '#F57C00'
  return { background: `linear-gradient(135deg, ${c}, ${shade(c, -15)})` }
})

// Status line under the company name
const statusLine = computed(() => {
  if (!run.value) return ''
  switch (run.value.status) {
    case 'pending':      return 'מתחבר לפורטל…'
    case 'running':      return 'מתחבר ומאמת…'
    case 'awaiting_otp': return 'ממתין לקוד SMS מהטלפון שלך'
    case 'downloading':  return 'מוריד דוח מהפורטל…'
    case 'parsing':      return 'מעבד ושומר…'
    case 'success':      return 'הסתיים בהצלחה'
    case 'failed':       return 'הריצה נכשלה'
    case 'timeout':      return 'הריצה פסקה בזמן'
    default:             return run.value.status
  }
})

// Stage status (idle | active | done | failed)
function stageStatus(name) {
  const r = run.value
  if (!r) return 'idle'
  if (r.status === 'success') return 'done'
  const order = STAGES.map((s) => s.key)
  const idx = order.indexOf(name)
  const cur = order.indexOf(r.stage)
  if (cur === -1) {
    // No stage yet (pending) — first item is "incoming"
    return idx === 0 ? 'active' : 'idle'
  }
  if (idx < cur) return 'done'
  if (idx === cur) {
    if (r.status === 'failed' || r.status === 'timeout') return 'failed'
    return 'active'
  }
  return 'idle'
}
function stageClass(name) {
  return `prf-stage--${stageStatus(name)}`
}

// Time-based progress bar (caps at 95% while running so it never looks "done"
// prematurely — finishes 100% only on actual success). 180s = backend hard timeout.
const HARD_TIMEOUT_MS = 180 * 1000
const elapsedMs = ref(0)
let elapsedTimer = null

function tickElapsed() {
  if (!run.value) { elapsedMs.value = 0; return }
  const started = new Date(run.value.started_at).getTime()
  elapsedMs.value = Math.max(0, Date.now() - started)
}

watch(
  () => run.value?.id,
  (id) => {
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null }
    if (id) {
      tickElapsed()
      elapsedTimer = setInterval(tickElapsed, 250)
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => { if (elapsedTimer) clearInterval(elapsedTimer) })

const progressPct = computed(() => {
  if (!run.value) return 0
  if (run.value.status === 'success') return 100
  if (run.value.status === 'failed' || run.value.status === 'timeout') {
    // Freeze where we were so the failure context is preserved.
    return Math.min(95, (elapsedMs.value / HARD_TIMEOUT_MS) * 100)
  }
  // Active: time-based with a slight ease so it doesn't feel linear
  const t = Math.min(1, elapsedMs.value / HARD_TIMEOUT_MS)
  const eased = 1 - Math.pow(1 - t, 1.4)
  return Math.min(95, eased * 100)
})

const elapsedLabel = computed(() => {
  const s = Math.floor(elapsedMs.value / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${String(r).padStart(2, '0')}`
})

const shellClass = computed(() => ({
  'prf-shell--ok':   run.value?.status === 'success',
  'prf-shell--err':  run.value?.status === 'failed' || run.value?.status === 'timeout',
  'prf-shell--otp':  run.value?.status === 'awaiting_otp',
}))

// Auto-dismiss success after 5s so the float doesn't linger forever
watch(
  () => run.value?.status,
  (s) => {
    if (s === 'success') {
      const id = run.value?.id
      setTimeout(() => {
        if (run.value?.id === id) dismissedRunId.value = id
      }, 5000)
    }
  },
)

function dismiss() {
  if (run.value?.id) dismissedRunId.value = run.value.id
}

// Tiny helper to darken a hex (or fallback to original on parse fail)
function shade(hex, pct) {
  try {
    let c = hex.replace('#', '')
    if (c.length === 3) c = c.split('').map((x) => x + x).join('')
    const num = parseInt(c, 16)
    let r = (num >> 16) + Math.round((255 * pct) / 100)
    let g = ((num >> 8) & 0xff) + Math.round((255 * pct) / 100)
    let b = (num & 0xff) + Math.round((255 * pct) / 100)
    r = Math.max(0, Math.min(255, r))
    g = Math.max(0, Math.min(255, g))
    b = Math.max(0, Math.min(255, b))
    return '#' + ((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)
  } catch { return hex }
}
</script>

<style scoped>
.prf-shell {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: min(440px, calc(100vw - 32px));
  z-index: 2000;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
  border-radius: 16px;
  border: 1px solid rgba(245, 124, 0, 0.16);
  box-shadow:
    0 20px 50px -8px rgba(45, 37, 34, 0.20),
    0 8px 16px -4px rgba(45, 37, 34, 0.10),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  overflow: hidden;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.prf-shell--otp {
  border-color: rgba(245, 124, 0, 0.45);
  box-shadow:
    0 20px 50px -8px rgba(245, 124, 0, 0.30),
    0 0 0 4px rgba(245, 124, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}
.prf-shell--ok {
  border-color: rgba(46, 132, 74, 0.40);
  box-shadow:
    0 20px 50px -8px rgba(46, 132, 74, 0.25),
    0 0 0 4px rgba(46, 132, 74, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}
.prf-shell--err {
  border-color: rgba(194, 57, 52, 0.40);
  box-shadow:
    0 20px 50px -8px rgba(194, 57, 52, 0.25),
    0 0 0 4px rgba(194, 57, 52, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

/* Top animated progress bar */
.prf-topbar {
  position: relative;
  height: 3px;
  background: rgba(45, 37, 34, 0.06);
  overflow: hidden;
}
.prf-topbar-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(90deg, #F57C00, #FF9800, #FFB74D);
  border-radius: 0 2px 2px 0;
  transition: width 0.4s cubic-bezier(0.34, 1.2, 0.64, 1);
}
.prf-shell--ok .prf-topbar-fill {
  background: linear-gradient(90deg, #1B5E20, #2E844A, #2E844A);
}
.prf-shell--err .prf-topbar-fill {
  background: linear-gradient(90deg, #C23934, #EA001E, #C23934);
}
.prf-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.55) 50%,
    transparent 100%
  );
  animation: prf-shimmer 1.8s linear infinite;
  pointer-events: none;
}
@keyframes prf-shimmer {
  from { transform: translateX(-100%); }
  to   { transform: translateX(100%); }
}

.prf-body {
  padding: 14px 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── Header ── */
.prf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.prf-portal {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.prf-portal-dot {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow:
    0 4px 10px rgba(245, 124, 0, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
  position: relative;
}
.prf-portal-dot::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 2px solid currentColor;
  opacity: 0;
  animation: prf-halo 2.4s ease-in-out infinite;
  color: rgba(245, 124, 0, 0.4);
  pointer-events: none;
}
.prf-shell--ok .prf-portal-dot::after { animation: none; opacity: 0; }
.prf-shell--err .prf-portal-dot::after { animation: none; opacity: 0; }
@keyframes prf-halo {
  0%   { transform: scale(0.95); opacity: 0; }
  40%  { opacity: 0.75; }
  100% { transform: scale(1.45); opacity: 0; }
}

.prf-portal-text { display: flex; flex-direction: column; min-width: 0; }
.prf-portal-name {
  font-size: 14.5px;
  font-weight: 700;
  color: #2D2522;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.prf-portal-sub {
  font-size: 12px;
  color: rgba(45, 37, 34, 0.65);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.prf-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.prf-elapsed {
  font-size: 11.5px;
  font-weight: 700;
  color: rgba(45, 37, 34, 0.55);
  letter-spacing: 0.02em;
  background: rgba(45, 37, 34, 0.05);
  padding: 3px 8px;
  border-radius: 999px;
  font-variant-numeric: tabular-nums;
}
.prf-close {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border: 0;
  background: rgba(45, 37, 34, 0.05);
  color: rgba(45, 37, 34, 0.55);
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.prf-close:hover {
  background: rgba(45, 37, 34, 0.10);
  color: #2D2522;
}

/* ── Stages rail ── */
.prf-stages {
  display: flex;
  align-items: center;
  margin: 0;
  padding: 4px 2px 2px;
  list-style: none;
  gap: 0;
}
.prf-stage {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  position: relative;
}
.prf-stage-marker {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(45, 37, 34, 0.08);
  color: rgba(45, 37, 34, 0.4);
  flex-shrink: 0;
  transition: background 0.25s, color 0.25s, transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.prf-stage-label {
  font-size: 11.5px;
  font-weight: 600;
  color: rgba(45, 37, 34, 0.55);
  white-space: nowrap;
  transition: color 0.25s;
}
.prf-stage-line {
  flex: 1;
  height: 2px;
  background: rgba(45, 37, 34, 0.10);
  margin: 0 6px;
  border-radius: 2px;
  transition: background 0.4s ease;
  min-width: 10px;
}
.prf-stage-line--done {
  background: linear-gradient(90deg, #2E844A, #2E844A);
}

.prf-stage--done .prf-stage-marker {
  background: linear-gradient(135deg, #1B5E20, #2E844A);
  color: #fff;
  transform: scale(1.05);
}
.prf-stage--done .prf-stage-label { color: #1B5E20; }

.prf-stage--active .prf-stage-marker {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  transform: scale(1.10);
  box-shadow: 0 0 0 4px rgba(245, 124, 0, 0.18);
}
.prf-stage--active .prf-stage-label {
  color: #E65100;
  font-weight: 700;
}
.prf-stage-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  animation: prf-stage-pulse 1.1s ease-in-out infinite;
}
@keyframes prf-stage-pulse {
  0%, 100% { transform: scale(1);   opacity: 1; }
  50%      { transform: scale(0.35); opacity: 0.6; }
}

.prf-stage--failed .prf-stage-marker {
  background: linear-gradient(135deg, #C23934, #EA001E);
  color: #fff;
}
.prf-stage--failed .prf-stage-label { color: #C23934; }

/* ── Reassurance + banners ── */
.prf-reassure {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.07), rgba(255, 152, 0, 0.04));
  border: 1px dashed rgba(245, 124, 0, 0.30);
  border-radius: 10px;
  font-size: 12px;
  color: #E65100;
  font-weight: 600;
  line-height: 1.4;
}
.prf-reassure svg { flex-shrink: 0; opacity: 0.85; }

.prf-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 12.5px;
  font-weight: 600;
}
.prf-banner--ok {
  background: linear-gradient(135deg, rgba(46, 132, 74, 0.10), rgba(52, 211, 153, 0.06));
  color: #1B5E20;
  border: 1px solid rgba(46, 132, 74, 0.24);
}
.prf-banner--err {
  background: linear-gradient(135deg, rgba(194, 57, 52, 0.08), rgba(248, 113, 113, 0.04));
  color: #C23934;
  border: 1px solid rgba(194, 57, 52, 0.24);
  align-items: flex-start;
}
.prf-banner-text {
  flex: 1;
  font-weight: 500;
  line-height: 1.45;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.prf-banner svg { flex-shrink: 0; }

/* ── Enter/leave ── */
.prf-enter-active {
  transition:
    transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1),
    opacity 0.30s ease;
}
.prf-leave-active {
  transition:
    transform 0.30s cubic-bezier(0.4, 0, 0.7, 0),
    opacity 0.25s ease;
}
.prf-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(36px) scale(0.95);
}
.prf-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px) scale(0.95);
}
</style>
