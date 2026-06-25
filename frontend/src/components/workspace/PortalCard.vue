<template>
  <article
    class="cred-card"
    :class="[
      `cred-card--${badgeKind}`,
      `cred-card--cadence-${cred.schedule_kind || 'manual'}`,
      { scheduled: isScheduled, running: isRunning },
    ]"
    :draggable="draggable"
    @dragstart="$emit('dragstart', $event)"
  >
    <!-- Active-run scanning beam -->
    <span v-if="isRunning" class="scan-beam" aria-hidden="true"></span>

    <!-- ─── WASH HEADER ──────────────────────────────────────── -->
    <header class="wash" :style="washStyle">
      <span class="wash-glow" aria-hidden="true"></span>
      <span class="wash-overlay" aria-hidden="true"></span>

      <span class="wash-art" :title="brand.label" aria-hidden="true">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round">
          <path :d="brand.iconPath" />
        </svg>
      </span>

      <div class="wash-titles">
        <span class="wash-name">{{ portalLabel }}</span>
        <span class="wash-user">{{ cred.username }}</span>
      </div>

      <span class="wash-grip" aria-hidden="true" title="גרור לשינוי תזמון">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <circle cx="9" cy="6" r="1.2" /><circle cx="9" cy="12" r="1.2" /><circle cx="9" cy="18" r="1.2" />
          <circle cx="15" cy="6" r="1.2" /><circle cx="15" cy="12" r="1.2" /><circle cx="15" cy="18" r="1.2" />
        </svg>
      </span>

      <!-- Schedule chip — overlays the wash bottom-end corner when scheduled -->
      <span v-if="isScheduled" class="sched-corner" :title="`תזמון: ${scheduleLabel}`">
        <svg v-if="cred.schedule_kind === 'daily'" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
        <svg v-else-if="cred.schedule_kind === 'weekly'" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect width="18" height="18" x="3" y="4" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
        <svg v-else width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect width="18" height="18" x="3" y="4" rx="2" /><path d="M16 2v4M8 2v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
        </svg>
        <span>{{ scheduleLabel }}</span>
      </span>
    </header>

    <!-- ─── BODY ─────────────────────────────────────────────── -->
    <div class="body">
      <!-- Run-history strip -->
      <div class="run-strip" :class="`run-strip--${badgeKind}`" :aria-label="runStripAriaLabel">
        <span class="rs-dots" role="img">
          <span
            v-for="(s, i) in displayedHistory"
            :key="i"
            class="rs-dot"
            :class="[`rs-dot--${dotClass(s)}`, { 'rs-dot--pulse': i === 0 && isRunning }]"
            :title="dotTitle(s)"
          ></span>
        </span>
        <span class="rs-meta">
          <span class="rs-label">{{ badgeLabel }}</span>
          <span v-if="cred.last_run_at" class="rs-time">· {{ relativeHebrew(cred.last_run_at) }}</span>
        </span>
        <button
          v-if="cred.last_error"
          class="rs-error-pill"
          type="button"
          :title="cred.last_error"
          aria-label="הצג פרטי שגיאה"
          @click.stop="$emit('view-error', cred.last_error)"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>פרטים</span>
        </button>
      </div>

      <!-- Live progress -->
      <div v-if="activeRun?.credential_id === cred.id" class="cc-progress">
        <PortalRunProgress :runId="activeRun.id" />
      </div>

      <!-- Actions -->
      <footer class="actions">
        <button
          class="btn-run"
          :disabled="isRunning"
          :aria-label="isRunning ? 'רץ' : 'הרץ עכשיו'"
          :title="isRunning ? 'רץ…' : 'הרץ עכשיו'"
          @click="$emit('run')"
        >
          <span v-if="isRunning" class="btn-spinner" aria-hidden="true"></span>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true">
            <polygon points="6 4 20 12 6 20" />
          </svg>
        </button>
        <div class="actions-secondary">
          <button class="btn-icon" type="button" title="עריכה" aria-label="עריכה" @click="$emit('edit')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
            </svg>
          </button>
          <button class="btn-icon btn-icon--danger" type="button" title="מחיקה" aria-label="מחיקה" @click="$emit('delete')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              <line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" />
            </svg>
          </button>
        </div>
      </footer>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import PortalRunProgress from './PortalRunProgress.vue'
import { relativeHebrew } from '../../utils/relativeTime.js'
import { brandFor } from '../../utils/companyBrand.js'
import { nearestChartColor } from '../../utils/chartPalette.js'

const props = defineProps({
  cred: { type: Object, required: true },
  portalLabel: { type: String, required: true },
  isRunning: { type: Boolean, default: false },
  activeRun: { type: Object, default: null },
  draggable: { type: Boolean, default: false },
  // Distinct on-palette wash color assigned by the parent (de-duped per company).
  washColor: { type: String, default: '' },
})
defineEmits(['run', 'edit', 'delete', 'dragstart', 'view-error'])

const SCHEDULE_LABELS = { daily: 'יומי', weekly: 'שבועי', monthly: 'חודשי' }
const STATUS_LABELS = {
  success: 'הצליח',
  failed: 'נכשל',
  timeout: 'פסק זמן',
  none: 'טרם הופעל',
}
const HISTORY_SLOTS = 7

const brand = computed(() => brandFor(props.cred.portal_kind))
const isScheduled = computed(() => props.cred.schedule_kind && props.cred.schedule_kind !== 'manual')
const scheduleLabel = computed(() => SCHEDULE_LABELS[props.cred.schedule_kind] || '')

const badgeKind = computed(() => {
  const s = props.cred.last_run_status
  if (props.isRunning) return 'running'
  if (!s) return 'none'
  if (s === 'success') return 'success'
  if (['failed', 'timeout'].includes(s)) return 'failed'
  return 'running'
})
const badgeLabel = computed(() => STATUS_LABELS[props.cred.last_run_status] || STATUS_LABELS[badgeKind.value])

// Pad recent history (most-recent first) to a fixed 7 slots so the strip width is stable.
const displayedHistory = computed(() => {
  const raw = Array.isArray(props.cred.recent_run_statuses) ? props.cred.recent_run_statuses.slice(0, HISTORY_SLOTS) : []
  const padded = raw.slice()
  while (padded.length < HISTORY_SLOTS) padded.push(null)
  return padded
})

function dotClass(s) {
  if (!s) return 'empty'
  if (s === 'success') return 'success'
  if (s === 'failed') return 'failed'
  if (s === 'timeout') return 'timeout'
  return 'running'  // pending / running / awaiting_otp / downloading / parsing
}
function dotTitle(s) {
  if (!s) return 'לא הופעל'
  return STATUS_LABELS[s] || s
}
const runStripAriaLabel = computed(() => {
  const counts = displayedHistory.value.reduce((acc, s) => {
    const k = dotClass(s); acc[k] = (acc[k] || 0) + 1; return acc
  }, {})
  return `היסטוריה: ${counts.success || 0} הצלחות, ${(counts.failed || 0) + (counts.timeout || 0)} כישלונות`
})

// Card wash uses the bright-bold palette, picking the palette color CLOSEST to
// the company's brand color (see nearestChartColor) — so the board is on-palette
// but each company keeps a recognizable hue (Phoenix→palette-blue, Harel→red…).

// Brand wash gradient — darken the brand color by ~22% for the gradient bottom.
function hexShift(hex, factor) {
  const clean = (hex || '#706E6B').replace('#', '')
  const n = parseInt(clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean, 16)
  const r = Math.max(0, Math.min(255, Math.floor(((n >> 16) & 0xff) * factor)))
  const g = Math.max(0, Math.min(255, Math.floor(((n >> 8) & 0xff) * factor)))
  const b = Math.max(0, Math.min(255, Math.floor((n & 0xff) * factor)))
  return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')
}
const washStyle = computed(() => {
  const base = props.washColor || nearestChartColor(brand.value.color)
  const deep = hexShift(base, 0.82)
  return {
    background: `linear-gradient(135deg, ${base} 0%, ${deep} 100%)`,
    '--brand-base': base,
    '--brand-deep': deep,
  }
})
</script>

<style scoped>
.cred-card {
  position: relative;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  transition: transform 0.18s var(--transition, ease), border-color 0.18s, box-shadow 0.18s;
  cursor: grab;
  overflow: hidden;
  box-shadow: 0 1px 0 rgba(26, 20, 16, 0.02), 0 2px 6px rgba(26, 20, 16, 0.04);
}
.cred-card:hover {
  transform: translateY(-2px);
  border-color: var(--text-muted);
  box-shadow: 0 14px 28px rgba(17, 12, 6, 0.10), 0 4px 8px rgba(17, 12, 6, 0.04);
}
.cred-card:active { cursor: grabbing; }

.cred-card--cadence-manual  { --cadence-color: transparent; }
.cred-card--cadence-daily   { --cadence-color: var(--cadence-daily); }
.cred-card--cadence-weekly  { --cadence-color: var(--cadence-weekly); }
.cred-card--cadence-monthly { --cadence-color: var(--cadence-monthly); }

/* Status accents — outer ring tone (Salesforce Lightning palette) */
.cred-card--success { border-color: rgba(46, 132, 74, 0.55); }
.cred-card--failed  { border-color: rgba(234, 0, 30, 0.55); }
.cred-card--running { border-color: rgba(31, 168, 140, 0.55); box-shadow: 0 0 0 3px rgba(31, 168, 140, 0.14), 0 8px 24px rgba(17, 12, 6, 0.10); }

/* Scanning beam */
.scan-beam {
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: linear-gradient(90deg, transparent 0%, var(--primary) 50%, transparent 100%);
  background-size: 50% 100%;
  background-repeat: no-repeat;
  animation: scanSweep 1.5s linear infinite;
  pointer-events: none;
  z-index: 4;
  border-top-left-radius: 14px;
  border-top-right-radius: 14px;
}
@keyframes scanSweep {
  0%   { background-position: -50% 0; }
  100% { background-position: 150% 0; }
}

/* ───── WASH HEADER ───── */
.wash {
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 14px 14px 16px;
  color: #fff;
  min-height: 84px;
  overflow: hidden;
}
.wash-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(120% 80% at 100% 0%, rgba(255, 255, 255, 0.18) 0%, transparent 55%),
    rgba(0, 0, 0, 0.10);
  pointer-events: none;
}
.wash-glow {
  position: absolute;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,0.32) 0%, transparent 65%);
  top: -60px;
  inset-inline-end: -40px;
  pointer-events: none;
  filter: blur(4px);
}
.wash-art {
  position: relative;
  z-index: 1;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.20),
    0 4px 10px rgba(0, 0, 0, 0.18);
  flex-shrink: 0;
}
.wash-art svg { filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3)); }

.wash-titles {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.wash-name {
  font-size: 17px;
  font-weight: 800;
  letter-spacing: -0.2px;
  line-height: 1.15;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.32);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wash-user {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11.5px;
  letter-spacing: 0.3px;
  line-height: 1.2;
  color: rgba(255, 255, 255, 0.86);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wash-grip {
  position: relative;
  z-index: 1;
  display: inline-flex;
  color: rgba(255, 255, 255, 0.78);
  cursor: grab;
  user-select: none;
  opacity: 0.7;
  flex-shrink: 0;
  transition: opacity 0.15s;
}
.cred-card:hover .wash-grip { opacity: 1; }

.sched-corner {
  position: absolute;
  z-index: 2;
  bottom: 8px;
  inset-inline-end: 10px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  font-weight: 800;
  padding: 3px 8px 3px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--cadence-color, var(--primary-deep));
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
  letter-spacing: 0.2px;
  backdrop-filter: blur(4px);
}

/* ───── BODY ───── */
.body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px 12px;
}

/* Run-history strip */
.run-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 9px;
}
.rs-dots {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.rs-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.08);
  display: inline-block;
  position: relative;
  transition: transform 0.2s ease;
}
.rs-dot--success { background: var(--green); box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05); }
.rs-dot--failed  { background: var(--red); box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05); }
.rs-dot--timeout { background: var(--amber); box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05); }
.rs-dot--running { background: var(--primary); box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05); }
.rs-dot--empty   { background: rgba(0, 0, 0, 0.08); }
.rs-dot--pulse {
  animation: dotPulse 1.4s infinite cubic-bezier(0.4, 0, 0.6, 1);
}
@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 124, 0, 0.55); }
  50%      { box-shadow: 0 0 0 6px rgba(245, 124, 0, 0); }
}

.rs-meta {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  min-width: 0;
  margin-inline-start: auto;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.rs-label {
  font-size: 11.5px;
  font-weight: 800;
  letter-spacing: 0.1px;
}
.run-strip--success .rs-label { color: var(--green); }
.run-strip--failed  .rs-label { color: var(--red); }
.run-strip--running .rs-label { color: var(--primary); }
.run-strip--none    .rs-label { color: var(--text-muted); }
.rs-time {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 10.5px;
  color: var(--text-muted);
  font-weight: 600;
}

/* Inline error pill — opens popup with full message */
.rs-error-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-inline-start: 6px;
  background: rgba(234, 0, 30, 0.12);
  color: var(--red);
  border: 1px solid rgba(234, 0, 30, 0.30);
  border-radius: 999px;
  padding: 2px 9px 2px 7px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.2px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.rs-error-pill:hover {
  background: rgba(234, 0, 30, 0.20);
  border-color: rgba(234, 0, 30, 0.55);
  transform: translateY(-1px);
}

.cc-progress {
  margin-top: 2px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-subtle);
}

/* ───── Actions ───── */
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}
.actions-secondary {
  display: flex;
  gap: 6px;
}
.btn-run {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #27bd9f, #178f78);
  color: #fff;
  border: none;
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(31, 168, 140, 0.30);
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
  flex-shrink: 0;
}
/* Play triangle is visually-left-biased; nudge it 2px so it reads centered in the circle */
.btn-run svg { transform: translateX(1.5px); }
.btn-run:hover:not(:disabled) {
  transform: translateY(-1px) scale(1.04);
  box-shadow: 0 10px 22px rgba(31, 168, 140, 0.42);
}
.btn-run:disabled {
  background: var(--text-muted);
  cursor: not-allowed;
  opacity: 0.55;
  box-shadow: none;
}

.btn-spinner {
  width: 12px;
  height: 12px;
  border: 1.5px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.btn-icon {
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 9px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.btn-icon:hover { background: var(--bg); color: var(--text); border-color: var(--text-muted); }
.btn-icon--danger:hover {
  color: var(--red-deep);
  border-color: rgba(234, 0, 30, 0.4);
  background: rgba(234, 0, 30, 0.06);
}

/* Respect reduced-motion for all decorative animations */
@media (prefers-reduced-motion: reduce) {
  .scan-beam,
  .rs-dot--pulse,
  .btn-spinner {
    animation: none;
  }
  .cred-card,
  .cred-card:hover {
    transform: none;
  }
}
</style>
