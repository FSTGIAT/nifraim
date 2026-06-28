<template>
  <article
    class="pcard"
    :class="[`pcard--${badgeKind}`, { running: isRunning }]"
    :style="cardVars"
  >
    <!-- Active-run scanning beam -->
    <span v-if="isRunning" class="pcard__beam" aria-hidden="true"></span>
    <!-- Pastel brand accent line -->
    <span class="pcard__accent" aria-hidden="true"></span>

    <!-- ─── HEAD: brand tile + identity + status ─────────────── -->
    <header class="pcard__head">
      <span class="pcard__tile" :title="brand.label" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path :d="brand.iconPath" />
        </svg>
      </span>
      <div class="pcard__id">
        <span class="pcard__name">{{ portalLabel }}</span>
        <span class="pcard__user ltr-number">{{ cred.username }}</span>
      </div>
      <span class="pcard__status" :class="`pcard__status--${badgeKind}`">
        <span class="pcard__status-dot" aria-hidden="true"></span>
        <span>{{ statusText }}</span>
      </span>
    </header>

    <!-- ─── META: run history + last run ────────────────────── -->
    <div class="pcard__meta" :aria-label="runStripAriaLabel">
      <span class="pcard__dots" role="img">
        <span
          v-for="(s, i) in displayedHistory"
          :key="i"
          class="pcard__dot"
          :class="[`pcard__dot--${dotClass(s)}`, { 'pcard__dot--pulse': i === 0 && isRunning }]"
          :title="dotTitle(s)"
        ></span>
      </span>
      <span v-if="cred.last_run_at" class="pcard__when">{{ relativeHebrew(cred.last_run_at) }}</span>
      <button
        v-if="cred.last_error"
        class="pcard__errpill"
        type="button"
        :title="cred.last_error"
        aria-label="הצג פרטי שגיאה"
        @click="$emit('view-error', cred.last_error)"
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <span>פרטים</span>
      </button>
    </div>

    <!-- Live progress -->
    <div v-if="activeRun?.credential_id === cred.id" class="pcard__progress">
      <PortalRunProgress :runId="activeRun.id" />
    </div>

    <!-- ─── ACTIONS ─────────────────────────────────────────── -->
    <footer class="pcard__actions">
      <button
        class="pcard__run"
        type="button"
        :disabled="isRunning"
        :title="isRunning ? 'רץ…' : 'הרצה עכשיו'"
        :aria-label="isRunning ? 'רץ' : 'הרצה עכשיו'"
        @click="$emit('run')"
      >
        <span v-if="isRunning" class="pcard__spinner" aria-hidden="true"></span>
        <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <polygon points="6 4 20 12 6 20" />
        </svg>
      </button>
      <button class="pcard__ic" type="button" title="עריכה" aria-label="עריכה" @click="$emit('edit')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
        </svg>
      </button>
      <button class="pcard__ic pcard__ic--danger" type="button" title="מחיקה" aria-label="מחיקה" @click="$emit('delete')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          <line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" />
        </svg>
      </button>
    </footer>
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
  // Distinct on-palette wash color assigned by the parent (de-duped per company).
  washColor: { type: String, default: '' },
})
defineEmits(['run', 'edit', 'delete', 'view-error'])

const STATUS_LABELS = {
  success: 'הצליח',
  failed: 'נכשל',
  timeout: 'פסק זמן',
  none: 'טרם הופעל',
}
const STATUS_PILL = {
  running: 'פעיל כעת',
  success: 'תקין',
  failed: 'שגיאה',
  none: 'ממתין',
}
const HISTORY_SLOTS = 7

const brand = computed(() => brandFor(props.cred.portal_kind))

const badgeKind = computed(() => {
  const s = props.cred.last_run_status
  if (props.isRunning) return 'running'
  if (!s) return 'none'
  if (s === 'success') return 'success'
  if (['failed', 'timeout'].includes(s)) return 'failed'
  return 'running'
})
const statusText = computed(() => STATUS_PILL[badgeKind.value] || STATUS_PILL.none)

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

// Soft pastel SaaS look: the brand color only tints the icon tile + accent line,
// expressed as low-alpha rgba so every company reads as a calm pastel card.
function hexToRgb(hex) {
  const clean = (hex || '#706E6B').replace('#', '')
  const full = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean
  const n = parseInt(full, 16)
  return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff]
}
const cardVars = computed(() => {
  const base = props.washColor || nearestChartColor(brand.value.color)
  const [r, g, b] = hexToRgb(base)
  return {
    '--brand': base,
    '--brand-soft': `rgba(${r}, ${g}, ${b}, 0.13)`,
    '--brand-soft2': `rgba(${r}, ${g}, ${b}, 0.07)`,
    '--brand-line': `rgba(${r}, ${g}, ${b}, 0.55)`,
  }
})
</script>

<style scoped>
.pcard {
  position: relative;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 16px 14px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(26, 20, 16, 0.03), 0 4px 14px rgba(26, 20, 16, 0.05);
  transition: transform 0.18s var(--transition, ease), border-color 0.18s, box-shadow 0.18s;
}
.pcard:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--brand) 35%, var(--border-subtle));
  box-shadow: 0 16px 32px rgba(17, 12, 6, 0.10), 0 4px 10px rgba(17, 12, 6, 0.04);
}

/* Pastel brand accent line along the top edge */
.pcard__accent {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--brand-line), color-mix(in srgb, var(--brand) 20%, transparent));
  opacity: 0.9;
}

/* Status ring tones */
.pcard--success { border-color: color-mix(in srgb, var(--green) 35%, var(--border-subtle)); }
.pcard--failed  { border-color: color-mix(in srgb, var(--red) 38%, var(--border-subtle)); }
.pcard--running { border-color: rgba(31, 168, 140, 0.5); box-shadow: 0 0 0 3px rgba(31, 168, 140, 0.12), 0 10px 26px rgba(17, 12, 6, 0.08); }

/* Scanning beam while running */
.pcard__beam {
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: linear-gradient(90deg, transparent 0%, #1FA88C 50%, transparent 100%);
  background-size: 50% 100%;
  background-repeat: no-repeat;
  animation: pcScan 1.5s linear infinite;
  pointer-events: none;
  z-index: 3;
}
@keyframes pcScan {
  0%   { background-position: -50% 0; }
  100% { background-position: 150% 0; }
}

/* ───── HEAD ───── */
.pcard__head {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
}
.pcard__tile {
  width: 46px;
  height: 46px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: var(--brand);
  background: var(--brand-soft);
  border: 1px solid var(--brand-soft);
  flex-shrink: 0;
}
.pcard__id { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.pcard__name {
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.2px;
  line-height: 1.15;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pcard__user {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11.5px;
  letter-spacing: 0.3px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Status pill — pastel */
.pcard__status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px 4px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1px;
  white-space: nowrap;
  flex-shrink: 0;
  border: 1px solid transparent;
}
.pcard__status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.pcard__status--success { background: rgba(46, 132, 74, 0.12); color: var(--green-deep); border-color: rgba(46, 132, 74, 0.24); }
.pcard__status--failed  { background: rgba(234, 0, 30, 0.10); color: var(--red-deep); border-color: rgba(234, 0, 30, 0.24); }
.pcard__status--running { background: rgba(31, 168, 140, 0.13); color: #178f78; border-color: rgba(31, 168, 140, 0.30); }
.pcard__status--none    { background: rgba(112, 110, 107, 0.12); color: var(--text-muted); border-color: rgba(112, 110, 107, 0.22); }
.pcard__status--running .pcard__status-dot {
  box-shadow: 0 0 0 0 rgba(31, 168, 140, 0.5);
  animation: pcDot 1.6s ease-out infinite;
}
@keyframes pcDot {
  0%   { box-shadow: 0 0 0 0 rgba(31, 168, 140, 0.5); }
  70%  { box-shadow: 0 0 0 6px rgba(31, 168, 140, 0); }
  100% { box-shadow: 0 0 0 0 rgba(31, 168, 140, 0); }
}

/* ───── META ───── */
.pcard__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 11px;
  border-radius: 11px;
  background: var(--brand-soft2);
  border: 1px solid color-mix(in srgb, var(--brand) 10%, transparent);
}
.pcard__dots { display: inline-flex; align-items: center; gap: 4px; flex-shrink: 0; }
.pcard__dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.10);
  display: inline-block;
}
.pcard__dot--success { background: var(--green); }
.pcard__dot--failed  { background: var(--red); }
.pcard__dot--timeout { background: var(--amber); }
.pcard__dot--running { background: #1FA88C; }
.pcard__dot--empty   { background: rgba(0, 0, 0, 0.10); }
.pcard__dot--pulse { animation: pcDotPulse 1.4s infinite cubic-bezier(0.4, 0, 0.6, 1); }
@keyframes pcDotPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(31, 168, 140, 0.5); }
  50%      { box-shadow: 0 0 0 5px rgba(31, 168, 140, 0); }
}
.pcard__when {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
  margin-inline-start: auto;
  white-space: nowrap;
}
.pcard__errpill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-inline-start: auto;
  background: rgba(234, 0, 30, 0.10);
  color: var(--red);
  border: 1px solid rgba(234, 0, 30, 0.26);
  border-radius: 999px;
  padding: 2px 9px 2px 7px;
  font-size: 10.5px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.pcard__errpill:hover { background: rgba(234, 0, 30, 0.18); border-color: rgba(234, 0, 30, 0.5); transform: translateY(-1px); }

.pcard__progress {
  padding-top: 10px;
  border-top: 1px dashed var(--border-subtle);
}

/* ───── ACTIONS ───── */
.pcard__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: auto;
}
.pcard__run {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  padding: 0;
  border: none;
  border-radius: 11px;
  background: linear-gradient(135deg, #5BB4DE, #1FA88C);  /* pastel sky → teal */
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  box-shadow: 0 5px 13px rgba(31, 168, 140, 0.26);
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease, opacity 0.15s ease;
}
.pcard__run:hover:not(:disabled) {
  transform: translateY(-1px);
  filter: brightness(1.04);
  box-shadow: 0 10px 22px rgba(31, 168, 140, 0.36);
}
.pcard__run:disabled { opacity: 0.6; cursor: not-allowed; box-shadow: none; }
.pcard__run svg { transform: translateX(1px); }
.pcard__run:focus-visible { outline: 2px solid #1FA88C; outline-offset: 2px; }

.pcard__spinner {
  width: 13px; height: 13px;
  border: 1.6px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: pcSpin 0.8s linear infinite;
}
@keyframes pcSpin { to { transform: rotate(360deg); } }

.pcard__ic {
  width: 38px; height: 38px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  border: 1px solid var(--border-subtle);
  background: var(--bg);
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s, border-color 0.15s, transform 0.15s;
}
.pcard__ic:hover { background: var(--card-bg); color: var(--text); border-color: var(--text-muted); transform: translateY(-1px); }
.pcard__ic--danger:hover {
  color: var(--red-deep);
  border-color: rgba(234, 0, 30, 0.4);
  background: rgba(234, 0, 30, 0.06);
}

@media (prefers-reduced-motion: reduce) {
  .pcard__beam,
  .pcard__dot--pulse,
  .pcard__status--running .pcard__status-dot,
  .pcard__spinner {
    animation: none;
  }
  .pcard, .pcard:hover { transform: none; }
}
</style>
