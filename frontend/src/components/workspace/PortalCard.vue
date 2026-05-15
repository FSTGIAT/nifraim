<template>
  <div
    class="cred-card"
    :class="[
      `cred-card--${badgeKind}`,
      `cred-card--cadence-${cred.schedule_kind || 'manual'}`,
      { disabled: !isImplemented, scheduled: isScheduled, running: isRunning },
    ]"
    :draggable="draggable"
    @dragstart="$emit('dragstart', $event)"
  >
    <!-- Active-run scanning beam (only animates while running) -->
    <span v-if="isRunning" class="scan-beam" aria-hidden="true"></span>

    <header class="cc-head">
      <span
        class="brand-badge"
        :style="{ background: brand.color }"
        :title="brand.label"
        aria-hidden="true"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path :d="brand.iconPath"/>
        </svg>
      </span>
      <div class="cc-title-block">
        <span class="cc-name">{{ portalLabel }}</span>
        <span class="cc-user">{{ cred.username }}</span>
      </div>
      <span v-if="!isImplemented" class="meta-pill meta-pill--coming">בקרוב</span>
      <span v-else-if="isScheduled" class="sched-chip" :title="`תזמון: ${scheduleLabel}`">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
        </svg>
        {{ scheduleLabel }}
      </span>
      <span class="cc-grip" aria-hidden="true" title="גרור לשינוי תזמון">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="9" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="18" r="1"/>
          <circle cx="15" cy="6" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="18" r="1"/>
        </svg>
      </span>
    </header>

    <!-- Last-run row: status dot + label + relative time -->
    <div class="cc-status-row">
      <span class="status-line" :class="`status-line--${badgeKind}`">
        <span class="sl-dot"></span>
        <span class="sl-label">{{ badgeLabel }}</span>
        <span v-if="cred.last_run_at" class="sl-time">{{ relativeHebrew(cred.last_run_at) }}</span>
      </span>
    </div>

    <div v-if="cred.last_error" class="last-error" :title="cred.last_error">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>{{ cred.last_error.slice(0, 80) }}</span>
    </div>

    <!-- Twilio sync status -->
    <div class="cc-meta">
      <span v-if="isSynced" class="meta-pill meta-pill--ok">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        טלפון מסונכרן
      </span>
      <button
        v-else-if="twilioNumber"
        class="meta-pill meta-pill--cta"
        :disabled="isRunning"
        @click="$emit('sync')"
        :title="`עדכן את הטלפון בפורטל ל-${twilioNumber.phone_number}`"
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect width="14" height="20" x="5" y="2" rx="2"/><path d="M12 18h.01"/>
        </svg>
        סנכרן טלפון
      </button>
      <span v-else class="meta-pill meta-pill--muted">דורש מספר Twilio</span>
    </div>

    <!-- Live progress -->
    <div v-if="activeRun?.credential_id === cred.id" class="cc-progress">
      <PortalRunProgress :runId="activeRun.id" />
    </div>

    <!-- Actions -->
    <footer class="cc-actions">
      <button
        class="btn-run"
        :disabled="isRunning || !isImplemented"
        @click="$emit('run')"
      >
        <span v-if="isRunning" class="btn-spinner" aria-hidden="true"></span>
        <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true">
          <polygon points="6 4 20 12 6 20" />
        </svg>
        <span>{{ isRunning ? 'רץ…' : 'הרץ עכשיו' }}</span>
      </button>
      <button class="btn-icon" title="עריכה" @click="$emit('edit')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
        </svg>
      </button>
      <button class="btn-icon btn-icon--danger" title="מחיקה" @click="$emit('delete')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          <line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
        </svg>
      </button>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PortalRunProgress from './PortalRunProgress.vue'
import { relativeHebrew } from '../../utils/relativeTime.js'
import { brandFor } from '../../utils/companyBrand.js'

const props = defineProps({
  cred: { type: Object, required: true },
  portalLabel: { type: String, required: true },
  isImplemented: { type: Boolean, default: true },
  isRunning: { type: Boolean, default: false },
  isSynced: { type: Boolean, default: false },
  twilioNumber: { type: Object, default: null },
  activeRun: { type: Object, default: null },
  draggable: { type: Boolean, default: false },
})
defineEmits(['run', 'edit', 'delete', 'sync', 'dragstart'])

const SCHEDULE_LABELS = { daily: 'יומי', weekly: 'שבועי', monthly: 'חודשי' }
const STATUS_LABELS = {
  success: 'הצליח',
  failed: 'נכשל',
  timeout: 'פסק זמן',
  none: 'טרם הופעל',
}

const brand = computed(() => brandFor(props.cred.portal_kind))
const isScheduled = computed(() => props.cred.schedule_kind && props.cred.schedule_kind !== 'manual')
const scheduleLabel = computed(() => SCHEDULE_LABELS[props.cred.schedule_kind] || '')

const badgeKind = computed(() => {
  const s = props.cred.last_run_status
  if (!s) return 'none'
  if (s === 'success') return 'success'
  if (['failed', 'timeout'].includes(s)) return 'failed'
  return 'running'
})
const badgeLabel = computed(() => STATUS_LABELS[props.cred.last_run_status] || STATUS_LABELS[badgeKind.value])
</script>

<style scoped>
.cred-card {
  position: relative;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: transform 0.18s var(--transition, ease), border-color 0.18s, box-shadow 0.18s;
  cursor: grab;
  overflow: hidden;
}
.cred-card:hover {
  transform: translateY(-1px);
  border-color: var(--text-muted);
  box-shadow: 0 8px 20px rgba(17, 12, 6, 0.06);
}
.cred-card:active { cursor: grabbing; }
.cred-card.disabled { opacity: 0.6; cursor: not-allowed; }

/* Cadence stripe — 3px left edge, color-coded by schedule_kind. The
   "manual" stripe is invisible so unscheduled cards stay neutral. */
.cred-card--cadence-manual  { --cadence-color: transparent; }
.cred-card--cadence-daily   { --cadence-color: #c2410c; }
.cred-card--cadence-weekly  { --cadence-color: #0e7490; }
.cred-card--cadence-monthly { --cadence-color: #4338ca; }
.cred-card.scheduled::before {
  content: '';
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  width: 3px;
  background: var(--cadence-color);
}

/* Status accents — subtle border & top-edge tint by run state */
.cred-card--success { border-color: rgba(16, 185, 129, 0.28); }
.cred-card--failed  { border-color: rgba(239, 68, 68, 0.28); }
.cred-card--running { border-color: rgba(59, 130, 246, 0.32); }

/* Scanning beam during active run — single sweep across the top edge */
.scan-beam {
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: linear-gradient(90deg, transparent 0%, var(--primary, #F57C00) 50%, transparent 100%);
  background-size: 50% 100%;
  background-repeat: no-repeat;
  animation: scanSweep 1.5s linear infinite;
  pointer-events: none;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
}
@keyframes scanSweep {
  0%   { background-position: -50% 0; }
  100% { background-position: 150% 0; }
}

/* ───── Header ───── */
.cc-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-badge {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12), inset 0 -1px 0 rgba(0, 0, 0, 0.18);
}
.cc-title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.cc-name {
  font-size: 14.5px;
  font-weight: 800;
  letter-spacing: -0.1px;
  color: var(--text);
  line-height: 1.2;
}
.cc-user {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11.5px;
  color: var(--text-muted);
  letter-spacing: 0.3px;
  line-height: 1.2;
}
.cc-grip {
  display: inline-flex;
  color: var(--text-muted);
  cursor: grab;
  user-select: none;
  opacity: 0.55;
  flex-shrink: 0;
}
.cred-card:hover .cc-grip { opacity: 1; }

.sched-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--cadence-color, var(--text-muted));
  background: rgba(0, 0, 0, 0.025);
  border: 1px solid rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
}

/* ───── Status line ───── */
.cc-status-row { display: flex; align-items: center; gap: 8px; }
.status-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.sl-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  display: inline-block;
}
.sl-label { font-weight: 700; }
.sl-time {
  color: var(--text-muted);
  font-weight: 500;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11px;
}
.status-line--success { color: #047857; }
.status-line--failed  { color: #b91c1c; }
.status-line--running { color: #1d4ed8; }
.status-line--none    { color: var(--text-muted); }
.status-line--running .sl-dot {
  position: relative;
  box-shadow: 0 0 0 0 currentColor;
  animation: statusPulse 1.4s infinite cubic-bezier(0.4, 0, 0.6, 1);
}
@keyframes statusPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.5); }
  50%      { box-shadow: 0 0 0 5px rgba(59, 130, 246, 0); }
}

.last-error {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11.5px;
  color: #b91c1c;
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.18);
  border-radius: 6px;
  padding: 5px 8px;
  line-height: 1.4;
}
.last-error svg { flex-shrink: 0; margin-top: 1px; }
.last-error span {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* ───── Twilio meta pill ───── */
.cc-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.2px;
  padding: 3px 8px;
  border-radius: 5px;
  border: 1px solid var(--border-subtle);
  background: var(--bg);
  color: var(--text-muted);
  font-family: inherit;
}
.meta-pill--ok { background: rgba(16, 185, 129, 0.10); color: #047857; border-color: rgba(16, 185, 129, 0.22); }
.meta-pill--cta {
  background: var(--card-bg);
  color: var(--primary-deep, #c2410c);
  border-color: rgba(245, 124, 0, 0.32);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.meta-pill--cta:hover:not(:disabled) {
  background: rgba(245, 124, 0, 0.08);
  border-color: var(--primary, #F57C00);
}
.meta-pill--cta:disabled { opacity: 0.55; cursor: not-allowed; }
.meta-pill--muted { font-style: normal; }
.meta-pill--coming {
  background: var(--text-muted);
  color: var(--card-bg, #fff);
  border-color: transparent;
}

.cc-progress {
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-subtle);
}

/* ───── Actions ───── */
.cc-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: auto;
  padding-top: 6px;
  border-top: 1px solid var(--border-subtle);
}
.btn-run {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-family: inherit;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.1px;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(245, 124, 0, 0.28);
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
}
.btn-run:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(245, 124, 0, 0.4);
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
  border-radius: 8px;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.btn-icon:hover { background: var(--bg); color: var(--text); border-color: var(--text-muted); }
.btn-icon--danger:hover {
  color: #b91c1c;
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.06);
}
</style>
