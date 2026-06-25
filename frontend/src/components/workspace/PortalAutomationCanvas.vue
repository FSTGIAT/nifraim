<template>
  <!-- Drag trail overlay — fullscreen SVG that follows the cursor while dragging -->
  <Teleport to="body">
    <svg
      v-if="dragTrail"
      class="drag-trail"
      :width="vw"
      :height="vh"
      :viewBox="`0 0 ${vw} ${vh}`"
      aria-hidden="true"
    >
      <defs>
        <marker id="drag-trail-arrow" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--primary)" />
        </marker>
        <filter id="drag-trail-glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="4" />
        </filter>
      </defs>
      <!-- glow halo -->
      <path :d="dragTrail.path" stroke="rgba(245, 124, 0, 0.40)" stroke-width="10" fill="none" filter="url(#drag-trail-glow)" />
      <!-- main dashed line -->
      <path
        :d="dragTrail.path"
        stroke="var(--primary)"
        stroke-width="2.5"
        fill="none"
        stroke-dasharray="7 5"
        stroke-linecap="round"
        marker-end="url(#drag-trail-arrow)"
        class="drag-trail-line"
      />
      <!-- start anchor dot -->
      <circle :cx="dragTrail.start.x" :cy="dragTrail.start.y" r="6" fill="var(--primary)" stroke="#fff" stroke-width="2" />
      <!-- snap pulse on the target -->
      <circle
        v-if="dragSnapZone"
        :cx="dragTrail.end.x"
        :cy="dragTrail.end.y"
        r="14"
        fill="none"
        stroke="var(--primary)"
        stroke-width="2"
        class="drag-trail-snap"
      />
    </svg>
  </Teleport>

  <div class="canvas" :class="{ 'is-empty': !credentials.length, 'is-dragging': !!draggingId }">
    <!-- LEFT RAIL: vertical schedule zones ────────────────────── -->
    <aside class="rail" aria-label="תזמון אוטומטי">
      <header class="rail-head">
        <span class="rail-title">תזמון</span>
        <span class="rail-eyebrow">SCHEDULES</span>
      </header>

      <div
        v-for="z in zones"
        :key="z.kind"
        class="zone"
        :class="[`zone--${z.kind}`, { 'is-over': dragOverZone === z.kind, 'is-pulsing': landingZone === z.kind }]"
        @dragover.prevent="onZoneDragOver(z.kind, $event)"
        @dragleave="onZoneDragLeave(z.kind)"
        @drop.prevent="onZoneDrop(z.kind, $event)"
      >
        <div class="zone-grid" aria-hidden="true"></div>
        <div class="zone-ripple" aria-hidden="true"></div>

        <header class="zone-head">
          <span class="zone-icon" aria-hidden="true">
            <svg v-if="z.kind === 'daily'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
            </svg>
            <svg v-else-if="z.kind === 'weekly'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect width="18" height="18" x="3" y="4" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />
            </svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect width="18" height="18" x="3" y="4" rx="2" /><path d="M16 2v4M8 2v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
            </svg>
          </span>
          <div class="zone-meta">
            <span class="zone-title">{{ z.label }}</span>
            <span class="zone-sub">{{ z.sub }}</span>
          </div>
          <span class="zone-count" :data-count="cardsByKind[z.kind].length">
            <span class="ltr-number">{{ cardsByKind[z.kind].length.toString().padStart(2, '0') }}</span>
          </span>
        </header>

        <div v-if="cardsByKind[z.kind].length === 0" class="zone-empty">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14" /><path d="M12 5v14" />
          </svg>
          <span>גרור פורטל לכאן</span>
        </div>

        <TransitionGroup v-else name="chip" tag="div" class="zone-chips">
          <div
            v-for="cred in cardsByKind[z.kind]"
            :key="cred.id"
            class="chip"
            :class="{ 'is-dragging': draggingId === cred.id, 'is-running': isRunning(cred.id) }"
            draggable="true"
            @dragstart="onDragStart(cred.id, $event)"
            @dragend="onDragEnd"
            :title="`${portalLabel(cred.portal_kind)} · ${cred.username}`"
          >
            <span class="chip-grip" aria-hidden="true">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="9" cy="6" r="0.7" fill="currentColor" /><circle cx="9" cy="12" r="0.7" fill="currentColor" /><circle cx="9" cy="18" r="0.7" fill="currentColor" />
                <circle cx="15" cy="6" r="0.7" fill="currentColor" /><circle cx="15" cy="12" r="0.7" fill="currentColor" /><circle cx="15" cy="18" r="0.7" fill="currentColor" />
              </svg>
            </span>
            <span class="chip-brand" :style="{ background: credColor(cred.portal_kind) }" aria-hidden="true">
              {{ brandInitial(cred.portal_kind) }}
            </span>
            <span class="chip-name">{{ portalLabel(cred.portal_kind) }}</span>
            <span class="chip-user">{{ cred.username }}</span>
            <button
              class="chip-run"
              type="button"
              :disabled="isRunning(cred.id) || anyRunning"
              :aria-label="`הרץ עכשיו: ${portalLabel(cred.portal_kind)}`"
              @click.stop="$emit('run', cred.id)"
            >
              <span v-if="isRunning(cred.id)" class="chip-spinner" aria-hidden="true"></span>
              <svg v-else width="10" height="10" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <polygon points="6 4 20 12 6 20" />
              </svg>
            </button>
            <button class="chip-x" type="button" :aria-label="`הסר תזמון מ${portalLabel(cred.portal_kind)}`" @click.stop="$emit('unschedule', cred.id)">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 6 6 18" /><path d="m6 6 12 12" />
              </svg>
            </button>
          </div>
        </TransitionGroup>
      </div>
    </aside>

    <!-- RIGHT PANE: card library + intro ───────────────────────── -->
    <section
      class="pane"
      :class="{ 'is-over': dragOverPane }"
      @dragover.prevent="onPaneDragOver"
      @dragleave="onPaneDragLeave"
      @drop.prevent="onPaneDrop"
    >
      <header class="pane-head">
        <div class="pane-titles">
          <span class="pane-title">פורטלים</span>
          <span class="pane-sub">{{ paneSub }}</span>
        </div>
        <button v-if="credentials.length" class="btn-add" type="button" @click="$emit('add')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14" /><path d="M12 5v14" />
          </svg>
          <span>הוסף פורטל</span>
        </button>
      </header>

      <!-- ── Empty state — clean, single CTA ─────────────────── -->
      <div v-if="!credentials.length" class="empty-state">
        <div class="empty-art" aria-hidden="true">
          <span class="empty-art-ring"></span>
          <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <div class="empty-copy">
          <h3>חבר פורטל ראשון</h3>
          <p>הוסף פרטי התחברות לפורטל של חברת ביטוח, גרור לאחד התזמונים, והדוחות יורידו את עצמם.</p>
          <button class="btn-add btn-add--cta" type="button" @click="$emit('add')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M5 12h14" /><path d="M12 5v14" />
            </svg>
            <span>הוסף פורטל</span>
          </button>
        </div>
      </div>

      <!-- ── Unscheduled cards grid ──────────────────────────── -->
      <div v-else-if="unscheduled.length" class="pane-body">
        <TransitionGroup name="card-flip" tag="div" class="cards-grid">
          <div
            v-for="cred in unscheduled"
            :key="cred.id"
            class="card-slot"
            :class="{ 'is-source': draggingId === cred.id }"
          >
            <PortalCard
              :cred="cred"
              :wash-color="credColor(cred.portal_kind)"
              :is-running="isRunning(cred.id)"
              :portal-label="portalLabel(cred.portal_kind)"
              :active-run="activeRun"
              :draggable="true"
              @run="$emit('run', cred.id)"
              @edit="$emit('edit', cred)"
              @delete="$emit('delete', cred.id)"
              @view-error="(msg) => $emit('view-error', { cred, message: msg })"
              @dragstart="onDragStart(cred.id, $event)"
              @dragend="onDragEnd"
            />
          </div>
        </TransitionGroup>
      </div>

      <!-- ── All scheduled, none unscheduled ─────────────────── -->
      <div v-else class="pane-allscheduled">
        <div class="allscheduled-art" aria-hidden="true">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        </div>
        <p class="allscheduled-msg">כל הפורטלים מתוזמנים. גרור פורטל החוצה כדי לערוך תזמון.</p>
        <button class="btn-add" type="button" @click="$emit('add')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14" /><path d="M12 5v14" />
          </svg>
          <span>הוסף עוד פורטל</span>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import PortalCard from './PortalCard.vue'
import { brandFor } from '../../utils/companyBrand.js'
import { nearestChartColor, assignNearestDistinct } from '../../utils/chartPalette.js'

const props = defineProps({
  credentials: { type: Array, required: true },
  portalLabel: { type: Function, required: true },
  activeRun: { type: Object, default: null },
  activeRunId: { type: String, default: null },
})

const emit = defineEmits(['run', 'edit', 'delete', 'schedule', 'unschedule', 'add', 'view-error'])

const zones = [
  { kind: 'daily',   label: 'יומי',   sub: 'כל יום · 09:00' },
  { kind: 'weekly',  label: 'שבועי',  sub: 'כל יום ראשון' },
  { kind: 'monthly', label: 'חודשי',  sub: 'בתחילת כל חודש' },
]

const cardsByKind = computed(() => {
  const out = { daily: [], weekly: [], monthly: [] }
  for (const c of props.credentials || []) {
    if (out[c.schedule_kind]) out[c.schedule_kind].push(c)
  }
  return out
})

// Distinct on-palette color per company (nearest-to-brand, de-duplicated so
// several red insurers don't collapse to the same red). Shared by cards + chips.
const colorByKind = computed(() => {
  const seen = []
  for (const c of props.credentials || []) {
    if (!seen.some((s) => s.key === c.portal_kind)) {
      seen.push({ key: c.portal_kind, brand: brandFor(c.portal_kind).color })
    }
  }
  return assignNearestDistinct(seen)
})
function credColor(kind) {
  return colorByKind.value.get(kind) || nearestChartColor(brandFor(kind).color)
}

const unscheduled = computed(() =>
  (props.credentials || []).filter((c) => !c.schedule_kind || c.schedule_kind === 'manual'),
)

const paneSub = computed(() => {
  if (!props.credentials.length) return 'עוד אין פורטלים מחוברים'
  const total = props.credentials.length
  const scheduled = total - unscheduled.value.length
  if (scheduled === 0) return `${total} פורטל${total === 1 ? '' : 'ים'} · גרור שמאלה לתזמן`
  return `${scheduled}/${total} מתוזמנים · גרור שמאלה להוסיף`
})

// ─── Drag state ──────────────────────────────────────────
const draggingId = ref(null)
const dragOverZone = ref(null)
const dragOverPane = ref(false)
const landingZone = ref(null)
let leavePaneTimeout = null
let leaveZoneTimeout = null

// Drag-trail overlay state (cursor-following SVG line)
const dragSourcePos = ref(null)   // { x, y } center of the source card at drag start
const dragCursorPos = ref(null)   // { x, y } current cursor position during drag
const dragSnapZone = ref(null)    // { x, y } snap target when hovering a zone
const vw = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)
const vh = ref(typeof window !== 'undefined' ? window.innerHeight : 800)

function onResize() {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
}

const dragTrail = computed(() => {
  if (!draggingId.value || !dragSourcePos.value || !dragCursorPos.value) return null
  const start = dragSourcePos.value
  const end = dragSnapZone.value || dragCursorPos.value
  // Quadratic bezier — control point bowed upward proportional to horizontal distance.
  const dx = end.x - start.x
  const mx = (start.x + end.x) / 2
  const my = Math.min(start.y, end.y) - Math.max(60, Math.abs(dx) * 0.28)
  return {
    start,
    end,
    path: `M ${start.x} ${start.y} Q ${mx} ${my} ${end.x} ${end.y}`,
  }
})

function onDocDragOver(e) {
  if (!draggingId.value) return
  dragCursorPos.value = { x: e.clientX, y: e.clientY }
}

function isRunning(credId) {
  return props.activeRunId && props.activeRun?.credential_id === credId
}
const anyRunning = computed(() => !!props.activeRunId)

function brandInitial(kind) {
  const lbl = props.portalLabel(kind) || kind
  return (lbl[0] || '').toUpperCase()
}

function onDragStart(credId, event) {
  draggingId.value = credId
  if (event?.dataTransfer) {
    event.dataTransfer.setData('text/plain', credId)
    event.dataTransfer.effectAllowed = 'move'
  }
  // Capture the source-card center so the trail line anchors there.
  const cardEl = event?.currentTarget?.closest?.('.card-slot, .chip') || event?.currentTarget
  if (cardEl?.getBoundingClientRect) {
    const r = cardEl.getBoundingClientRect()
    dragSourcePos.value = { x: r.left + r.width / 2, y: r.top + r.height / 2 }
    dragCursorPos.value = { x: r.left + r.width / 2, y: r.top + r.height / 2 }
  }
  document.addEventListener('dragover', onDocDragOver)
}
function onDragEnd() {
  draggingId.value = null
  dragOverZone.value = null
  dragOverPane.value = false
  dragSourcePos.value = null
  dragCursorPos.value = null
  dragSnapZone.value = null
  document.removeEventListener('dragover', onDocDragOver)
}

function onZoneDragOver(kind, event) {
  if (leaveZoneTimeout) { clearTimeout(leaveZoneTimeout); leaveZoneTimeout = null }
  dragOverZone.value = kind
  // Snap the trail's end-point to the zone's visual center.
  const zoneEl = event?.currentTarget
  if (zoneEl?.getBoundingClientRect) {
    const r = zoneEl.getBoundingClientRect()
    dragSnapZone.value = { x: r.left + r.width / 2, y: r.top + r.height / 2 }
  }
}
function onZoneDragLeave(kind) {
  if (leaveZoneTimeout) clearTimeout(leaveZoneTimeout)
  leaveZoneTimeout = setTimeout(() => {
    if (dragOverZone.value === kind) {
      dragOverZone.value = null
      dragSnapZone.value = null
    }
  }, 40)
}
async function onZoneDrop(kind, event) {
  dragOverZone.value = null
  const credId = event?.dataTransfer?.getData('text/plain') || draggingId.value
  if (!credId) return
  const cred = (props.credentials || []).find((c) => c.id === credId)
  if (!cred || cred.schedule_kind === kind) {
    draggingId.value = null
    return
  }
  // Fire the success ripple on the target zone.
  landingZone.value = kind
  setTimeout(() => { if (landingZone.value === kind) landingZone.value = null }, 620)
  emit('schedule', { id: credId, schedule_kind: kind })
  draggingId.value = null
}

function onPaneDragOver() {
  if (leavePaneTimeout) { clearTimeout(leavePaneTimeout); leavePaneTimeout = null }
  // Only highlight when the source card is currently scheduled — pane is the unschedule target.
  if (!draggingId.value) { dragOverPane.value = true; return }
  const cred = (props.credentials || []).find((c) => c.id === draggingId.value)
  if (cred && cred.schedule_kind && cred.schedule_kind !== 'manual') dragOverPane.value = true
}
function onPaneDragLeave() {
  if (leavePaneTimeout) clearTimeout(leavePaneTimeout)
  leavePaneTimeout = setTimeout(() => { dragOverPane.value = false }, 40)
}
function onPaneDrop(event) {
  dragOverPane.value = false
  const credId = event?.dataTransfer?.getData('text/plain') || draggingId.value
  if (!credId) return
  const cred = (props.credentials || []).find((c) => c.id === credId)
  if (!cred || !cred.schedule_kind || cred.schedule_kind === 'manual') {
    draggingId.value = null
    return
  }
  emit('unschedule', credId)
  draggingId.value = null
}

onMounted(() => {
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  if (leavePaneTimeout) clearTimeout(leavePaneTimeout)
  if (leaveZoneTimeout) clearTimeout(leaveZoneTimeout)
  document.removeEventListener('dragover', onDocDragOver)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.canvas {
  /* Flexbox is more forgiving than grid for "two items side by side".
   * In RTL with flex-direction: row, the FIRST child sits on the visual-right
   * — we want pane on the visual-right, so pane uses `order: 1` and rail
   * uses `order: 2` regardless of DOM order. */
  display: flex;
  align-items: flex-start;
  flex-wrap: nowrap;
  column-gap: clamp(16px, 2.5vw, 40px);
  row-gap: 18px;
  min-height: 520px;
}
/* Only stack on phone-sized portrait windows. Everything wider stays side-by-side. */
@media (max-width: 480px) {
  .canvas {
    flex-wrap: wrap;
    column-gap: 0;
  }
}

/* ─── LEFT RAIL ─────────────────────────────────────────────── */
.rail {
  /* In RTL flex row: higher order = visual-left, so rail is order 2 */
  order: 2;
  flex: 0 0 212px;     /* compact schedule rail                       */
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;           /* tighter — three zones fit without scrolling */
  position: sticky;
  top: 80px;
  align-self: flex-start;
}
@media (max-width: 480px) {
  .rail { flex-basis: auto; width: 100%; position: static; order: 0; }
}
.rail-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 4px 4px;
}
.rail-title {
  font-size: 13px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.2px;
}
.rail-eyebrow {
  font-size: 10px;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: 1px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}

/* Zone shell — sized to match a portal card's footprint so rail and pane
 * read as peer columns (not a tiny sidebar next to big cards).             */
.zone {
  position: relative;
  background: var(--card-bg, #fff);
  border: 1.5px solid var(--border-subtle);
  border-radius: 12px;
  padding: 12px 12px 11px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-height: 128px;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease, background 0.2s ease;
}
/* Monday-style colored group ribbon */
.zone::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--cadence);
  z-index: 1;
  border-top-left-radius: 14px;
  border-top-right-radius: 14px;
}
.zone-grid {
  position: absolute;
  inset: 0;
  opacity: 0.45;
  background-image:
    linear-gradient(to right, rgba(0,0,0,0.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(0,0,0,0.025) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
  mask-image: radial-gradient(ellipse at top right, #000 30%, transparent 80%);
}
.zone-ripple {
  position: absolute;
  inset: 0;
  pointer-events: none;
  display: grid;
  place-items: center;
}
.zone-ripple::after {
  content: '';
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--cadence);
  opacity: 0;
  transform: scale(0.4);
}
.zone.is-pulsing .zone-ripple::after {
  animation: ripple-out 600ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
@keyframes ripple-out {
  0%   { opacity: 0.55; transform: scale(0.4); }
  100% { opacity: 0;    transform: scale(8); }
}

/* Cadence palette — Salesforce Lightning (orange / green / violet, distinct) */
.zone--daily   { --cadence: var(--cadence-daily);   --cadence-bg: color-mix(in srgb, var(--cadence) 10%, transparent);  --cadence-strong: color-mix(in srgb, var(--cadence) 22%, transparent); }
.zone--weekly  { --cadence: var(--cadence-weekly);  --cadence-bg: color-mix(in srgb, var(--cadence) 10%, transparent);  --cadence-strong: color-mix(in srgb, var(--cadence) 22%, transparent); }
.zone--monthly { --cadence: var(--cadence-monthly); --cadence-bg: color-mix(in srgb, var(--cadence) 10%, transparent);  --cadence-strong: color-mix(in srgb, var(--cadence) 22%, transparent); }

.zone {
  background:
    linear-gradient(135deg, var(--cadence-bg) 0%, transparent 60%),
    var(--card-bg, #fff);
}
.zone.is-over {
  border-color: var(--cadence);
  background:
    linear-gradient(135deg, var(--cadence-strong) 0%, transparent 70%),
    var(--card-bg, #fff);
  box-shadow:
    0 0 0 4px color-mix(in srgb, var(--cadence) 12%, transparent),
    0 14px 32px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}

.zone-head {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
}
.zone-icon {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: var(--cadence);
  color: #fff;
  border: 1px solid color-mix(in srgb, var(--cadence) 80%, #000 10%);
  box-shadow: 0 3px 8px color-mix(in srgb, var(--cadence) 38%, transparent),
              inset 0 1px 0 rgba(255, 255, 255, 0.25);
  flex-shrink: 0;
}
.zone-icon svg { width: 15px; height: 15px; }
.zone-meta { display: flex; flex-direction: column; flex: 1; min-width: 0; gap: 1px; }
.zone-title { font-size: 13.5px; font-weight: 800; color: var(--text); line-height: 1.15; letter-spacing: -0.1px; }
.zone-sub { font-size: 10.5px; color: var(--text-muted); line-height: 1.2; }
.zone-count {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.5px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--cadence);
  border: none;
  box-shadow: 0 2px 6px color-mix(in srgb, var(--cadence) 35%, transparent);
  flex-shrink: 0;
}
.zone-count[data-count="0"] {
  opacity: 0.4;
  background: var(--text-muted);
  box-shadow: none;
}

.zone-empty {
  position: relative;
  flex: 1;                /* fill the rest of the zone so it feels substantial */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-muted);
  border-radius: 9px;
  border: 1.5px dashed color-mix(in srgb, var(--cadence) 22%, transparent);
  background: color-mix(in srgb, var(--cadence) 3%, transparent);
  min-height: 56px;
  padding: 8px 10px;
  text-align: center;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
.zone-empty svg { opacity: 0.7; }
.zone.is-over .zone-empty {
  color: var(--cadence);
  border-color: var(--cadence);
  background: color-mix(in srgb, var(--cadence) 5%, transparent);
}

.zone-chips {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* Scheduled chip */
.chip {
  display: grid;
  grid-template-columns: auto auto 1fr auto auto auto;
  align-items: center;
  gap: 8px;
  padding: 6px 6px 6px 8px;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle);
  border-inline-start: 3px solid var(--cadence);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text);
  cursor: grab;
  transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.18s ease, border-color 0.18s ease;
  position: relative;
}
.chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.08);
  border-color: var(--cadence);
}
.chip:active { cursor: grabbing; }
.chip.is-dragging {
  opacity: 0.45;
  transform: rotate(-2deg) scale(0.98);
  cursor: grabbing;
}
.chip-grip { color: var(--text-muted); display: inline-flex; opacity: 0.55; }
.chip:hover .chip-grip { opacity: 1; }
.chip-brand {
  width: 22px; height: 22px;
  border-radius: 6px;
  display: grid; place-items: center;
  color: #fff;
  font-weight: 800;
  font-size: 11px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15), inset 0 -1px 0 rgba(0,0,0,0.16);
  flex-shrink: 0;
}
.chip-name { font-weight: 800; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-user {
  color: var(--text-muted);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 10.5px;
  letter-spacing: 0.3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chip-run, .chip-x {
  width: 22px; height: 22px;
  display: grid; place-items: center;
  border-radius: 5px;
  border: 1px solid transparent;
  background: rgba(0,0,0,0.04);
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.chip-run:hover:not(:disabled) {
  background: rgba(31, 168, 140, 0.12);
  color: #1A7F69;
  border-color: rgba(31, 168, 140, 0.30);
}
.chip-run:disabled { opacity: 0.5; cursor: not-allowed; }
.chip-x:hover { background: rgba(234, 0, 30, 0.16); color: var(--red-deep); }
.chip-spinner {
  width: 9px; height: 9px;
  border: 1.5px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.chip.is-running { border-color: var(--cadence); box-shadow: 0 0 0 2px color-mix(in srgb, var(--cadence) 20%, transparent); }

/* Chip transitions (TransitionGroup) */
.chip-enter-active, .chip-leave-active, .chip-move {
  transition: all 0.32s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.chip-enter-from { opacity: 0; transform: translateX(20px) scale(0.96); }
.chip-leave-to   { opacity: 0; transform: translateX(20px) scale(0.96); position: absolute; }
.chip-leave-active { position: absolute; }

/* ─── RIGHT PANE ───────────────────────────────────────────── */
.pane {
  /* In RTL flex row: lower order = visual-right, so pane is order 1 */
  order: 1;
  flex: 1 1 0;      /* take all remaining space */
  min-width: 0;     /* allow shrinking below content's intrinsic min */
  max-width: 880px;
  margin-inline: auto;  /* center within available flex space when room allows */
  position: relative;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 18px 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 520px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}
@media (max-width: 480px) {
  .pane { max-width: none; margin-inline: 0; flex-basis: auto; width: 100%; order: 0; }
}
.pane.is-over {
  border-color: #1FA88C;
  box-shadow: 0 0 0 4px rgba(31, 168, 140, 0.12), 0 14px 32px rgba(0,0,0,0.06);
  background: linear-gradient(135deg, rgba(143, 217, 198, 0.10) 0%, transparent 50%), var(--card-bg, #fff);
}

.pane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--border-subtle);
}
.pane-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pane-title { font-size: 14px; font-weight: 800; color: var(--text); letter-spacing: -0.2px; }
.pane-sub { font-size: 11.5px; color: var(--text-muted); }

.btn-add {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #4E9DD0, #1FA88C);  /* pastel sky → teal, no orange */
  color: #fff;
  border: none;
  border-radius: 9px;
  padding: 8px 14px;
  height: 34px;
  font-family: inherit;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.1px;
  cursor: pointer;
  box-shadow: 0 5px 12px rgba(31, 168, 140, 0.26);
  transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease;
  flex-shrink: 0;
}
.btn-add:hover {
  transform: translateY(-1px);
  filter: brightness(1.04);
  box-shadow: 0 9px 20px rgba(31, 168, 140, 0.34);
}
.btn-add:focus-visible { outline: 2px solid #1FA88C; outline-offset: 2px; }
.btn-add--cta { height: 44px; padding: 12px 22px; font-size: 14px; border-radius: 11px; }

/* Cards grid */
.pane-body { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  position: relative;
}
.card-slot { transition: opacity 0.28s ease; }
.card-slot.is-source {
  opacity: 0.35;
  filter: grayscale(0.3);
}

/* FLIP move/enter/leave for the cards grid */
.card-flip-enter-active, .card-flip-leave-active, .card-flip-move {
  transition: all 0.36s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.card-flip-enter-from { opacity: 0; transform: scale(0.92) translateY(8px); }
.card-flip-leave-to   { opacity: 0; transform: scale(0.92) translateX(40px); position: absolute; }
.card-flip-leave-active { position: absolute; }

/* Empty state — single, centered, calm (no fake-UI animation) */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 20px;
  min-height: 440px;
  padding: 24px;
}
.empty-art {
  position: relative;
  width: 104px;
  height: 104px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #1FA88C;
  background:
    radial-gradient(circle at 30% 25%, rgba(78, 157, 208, 0.16), transparent 60%),
    rgba(143, 217, 198, 0.18);
  border: 1px solid rgba(31, 168, 140, 0.22);
}
.empty-art-ring {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  border: 1.5px dashed rgba(31, 168, 140, 0.3);
}
.empty-copy {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.empty-copy h3 {
  margin: 0;
  font-size: 23px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.3px;
  line-height: 1.15;
}
.empty-copy p {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
  max-width: 42ch;
}

/* All scheduled */
.pane-allscheduled {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 24px;
  text-align: center;
  color: var(--text-muted);
}
.allscheduled-art {
  width: 84px;
  height: 84px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(46, 132, 74, 0.10);
  color: var(--green-deep);
  border: 1px solid rgba(46, 132, 74, 0.22);
}
.allscheduled-msg { font-size: 13.5px; max-width: 36ch; margin: 0; line-height: 1.5; }

@keyframes spin { to { transform: rotate(360deg); } }

/* ─── Staggered entrance — schedule zones + credential cards ───── */
@keyframes auto-rise {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.zone,
.card-slot {
  animation: auto-rise 300ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
/* Zones follow .rail-head, so the first zone is the 2nd child of .rail */
.zone:nth-child(2) { animation-delay: 40ms; }
.zone:nth-child(3) { animation-delay: 80ms; }
.zone:nth-child(4) { animation-delay: 120ms; }
.card-slot:nth-child(1) { animation-delay: 40ms; }
.card-slot:nth-child(2) { animation-delay: 80ms; }
.card-slot:nth-child(3) { animation-delay: 120ms; }
.card-slot:nth-child(4) { animation-delay: 160ms; }
.card-slot:nth-child(5) { animation-delay: 200ms; }
.card-slot:nth-child(6) { animation-delay: 240ms; }
.card-slot:nth-child(7) { animation-delay: 280ms; }
.card-slot:nth-child(8) { animation-delay: 320ms; }

@media (prefers-reduced-motion: reduce) {
  .zone,
  .card-slot {
    animation: none;
    transform: none;
  }
  .zone.is-pulsing .zone-ripple::after,
  .chip-spinner {
    animation: none;
  }
}
</style>

<!-- Trail overlay is Teleported to <body>, so scoped styles can't reach it. -->
<style>
.drag-trail {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 9999;
}
.drag-trail-line {
  animation: drag-trail-dashflow 0.7s linear infinite;
}
@keyframes drag-trail-dashflow {
  to { stroke-dashoffset: -24; }  /* dash-array 7+5 → -24 = 2 cycles */
}
.drag-trail-snap {
  transform-box: fill-box;
  transform-origin: center;
  animation: drag-trail-snap-pulse 1.1s ease-out infinite;
}
@keyframes drag-trail-snap-pulse {
  0%   { opacity: 0.9; transform: scale(1);   }
  70%  { opacity: 0;   transform: scale(2.2); }
  100% { opacity: 0;   transform: scale(2.2); }
}
@media (prefers-reduced-motion: reduce) {
  .drag-trail-line,
  .drag-trail-snap {
    animation: none;
  }
}
</style>
