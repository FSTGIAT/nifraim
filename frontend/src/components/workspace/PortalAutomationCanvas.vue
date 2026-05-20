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
          <path d="M0 0 L10 5 L0 10 z" fill="var(--primary, #F57C00)" />
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
        stroke="var(--primary, #F57C00)"
        stroke-width="2.5"
        fill="none"
        stroke-dasharray="7 5"
        stroke-linecap="round"
        marker-end="url(#drag-trail-arrow)"
        class="drag-trail-line"
      />
      <!-- start anchor dot -->
      <circle :cx="dragTrail.start.x" :cy="dragTrail.start.y" r="6" fill="var(--primary, #F57C00)" stroke="#fff" stroke-width="2" />
      <!-- snap pulse on the target -->
      <circle
        v-if="dragSnapZone"
        :cx="dragTrail.end.x"
        :cy="dragTrail.end.y"
        r="14"
        fill="none"
        stroke="var(--primary, #F57C00)"
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
            <span class="chip-brand" :style="{ background: brandFor(cred.portal_kind).color }" aria-hidden="true">
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
        <button class="btn-add" type="button" @click="$emit('add')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14" /><path d="M12 5v14" />
          </svg>
          <span>הוסף פורטל</span>
        </button>
      </header>

      <!-- ── Empty state — Remotion intro showcase ───────────── -->
      <div v-if="!credentials.length" class="empty-state">
        <div ref="introMountEl" class="empty-intro" aria-hidden="true">
          <div v-if="introError" class="intro-fallback">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect width="18" height="18" x="3" y="4" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />
            </svg>
          </div>
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
              :is-running="isRunning(cred.id)"
              :portal-label="portalLabel(cred.portal_kind)"
              :active-run="activeRun"
              :draggable="true"
              @run="$emit('run', cred.id)"
              @edit="$emit('edit', cred)"
              @delete="$emit('delete', cred.id)"
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import PortalCard from './PortalCard.vue'
import { brandFor } from '../../utils/companyBrand.js'

const props = defineProps({
  credentials: { type: Array, required: true },
  portalLabel: { type: Function, required: true },
  activeRun: { type: Object, default: null },
  activeRunId: { type: String, default: null },
})

const emit = defineEmits(['run', 'edit', 'delete', 'schedule', 'unschedule', 'add'])

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

// ─── Remotion intro (empty-state showcase) ───────────────
const introMountEl = ref(null)
const introError = ref(false)
let reactStack = null
let reactRoot = null
let currentMountEl = null
let renderCounter = 0

function prefersReducedMotion() {
  return typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

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
    AutomationIntro: remotion.AutomationIntro,
    AUTOMATION_INTRO_DURATION: remotion.AUTOMATION_INTRO_DURATION,
  }
  return reactStack
}

async function renderIntro() {
  if (!introMountEl.value) return
  if (prefersReducedMotion()) return  // respect user preference — fallback icon stays
  try {
    const stack = await ensureReactStack()
    if (!introMountEl.value) return
    if (reactRoot && currentMountEl !== introMountEl.value) {
      try { reactRoot.unmount() } catch { /* ignore */ }
      reactRoot = null
    }
    if (!reactRoot) {
      reactRoot = stack.createRoot(introMountEl.value)
      currentMountEl = introMountEl.value
    }
    renderCounter += 1
    const el = stack.createElement(stack.Player, {
      key: `automation-intro-${renderCounter}`,
      component: stack.AutomationIntro,
      durationInFrames: stack.AUTOMATION_INTRO_DURATION,
      fps: 30,
      compositionWidth: 1080,
      compositionHeight: 600,
      autoPlay: true,
      loop: true,
      controls: false,
      clickToPlay: false,
      doubleClickToFullscreen: false,
      showPosterWhenUnplayed: false,
      showPosterWhenPaused: false,
      showPosterWhenEnded: false,
      showPosterWhenBuffering: false,
      acknowledgeRemotionLicense: true,
      style: { width: '100%', height: '100%' },
    })
    reactRoot.render(el)
  } catch (e) {
    console.warn('[PortalAutomationCanvas] intro render failed', e)
    introError.value = true
  }
}

function teardownIntro() {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentMountEl = null
  }
}

// Mount intro when entering empty state; tear down when leaving.
watch(
  () => props.credentials.length,
  (n) => {
    if (n === 0) {
      nextTick(renderIntro)
    } else {
      teardownIntro()
    }
  },
)

onMounted(() => {
  if (!props.credentials.length) nextTick(renderIntro)
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  if (leavePaneTimeout) clearTimeout(leavePaneTimeout)
  if (leaveZoneTimeout) clearTimeout(leaveZoneTimeout)
  document.removeEventListener('dragover', onDocDragOver)
  window.removeEventListener('resize', onResize)
  teardownIntro()
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
  flex: 0 0 240px;     /* sized to give the zone cards real presence  */
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;           /* breathing room between schedule cards       */
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
  border-radius: 14px;
  padding: 14px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease, background 0.2s ease;
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

/* Cadence palette */
.zone--daily   { --cadence: #C2410C; --cadence-bg: rgba(194, 65, 12, 0.04);  --cadence-strong: rgba(194, 65, 12, 0.10); }
.zone--weekly  { --cadence: #0E7490; --cadence-bg: rgba(14, 116, 144, 0.04); --cadence-strong: rgba(14, 116, 144, 0.10); }
.zone--monthly { --cadence: #4338CA; --cadence-bg: rgba(67, 56, 202, 0.04);  --cadence-strong: rgba(67, 56, 202, 0.10); }

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
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: color-mix(in srgb, var(--cadence) 10%, transparent);
  color: var(--cadence);
  border: 1px solid color-mix(in srgb, var(--cadence) 18%, transparent);
  flex-shrink: 0;
}
.zone-icon svg { width: 18px; height: 18px; }
.zone-meta { display: flex; flex-direction: column; flex: 1; min-width: 0; gap: 2px; }
.zone-title { font-size: 15px; font-weight: 800; color: var(--text); line-height: 1.15; letter-spacing: -0.1px; }
.zone-sub { font-size: 11.5px; color: var(--text-muted); line-height: 1.2; }
.zone-count {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.5px;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.zone-count[data-count="0"] { opacity: 0.55; }

.zone-empty {
  position: relative;
  flex: 1;                /* fill the rest of the zone so it feels substantial */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-muted);
  border-radius: 10px;
  border: 1.5px dashed color-mix(in srgb, var(--cadence) 22%, transparent);
  background: color-mix(in srgb, var(--cadence) 3%, transparent);
  min-height: 100px;
  padding: 14px 12px;
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
  background: color-mix(in srgb, var(--primary, #F57C00) 12%, transparent);
  color: var(--primary-deep, #C2410C);
  border-color: color-mix(in srgb, var(--primary, #F57C00) 28%, transparent);
}
.chip-run:disabled { opacity: 0.5; cursor: not-allowed; }
.chip-x:hover { background: rgba(239, 68, 68, 0.16); color: #b91c1c; }
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
  border-color: var(--primary, #F57C00);
  box-shadow: 0 0 0 4px rgba(245, 124, 0, 0.10), 0 14px 32px rgba(0,0,0,0.06);
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.04) 0%, transparent 50%), var(--card-bg, #fff);
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
  background: linear-gradient(135deg, #F57C00, #FF9800);
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
  box-shadow: 0 5px 12px rgba(245, 124, 0, 0.28);
  transition: transform 0.16s ease, box-shadow 0.16s ease;
  flex-shrink: 0;
}
.btn-add:hover {
  transform: translateY(-1px);
  box-shadow: 0 9px 20px rgba(245, 124, 0, 0.38);
}
.btn-add--cta { height: 40px; padding: 10px 18px; font-size: 13.5px; }

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

/* Empty state */
.empty-state {
  flex: 1;
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 22px;
  align-items: center;
  min-height: 440px;
}
@media (max-width: 720px) {
  .empty-state { grid-template-columns: 1fr; }
}
.empty-intro {
  position: relative;
  width: 100%;
  aspect-ratio: 9 / 5;
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(135deg, #FFF8F0 0%, #FFFBF4 100%);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 4px 14px rgba(26, 20, 16, 0.04);
}
.intro-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--text-muted);
  opacity: 0.4;
}
.empty-copy {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px;
}
.empty-copy h3 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.3px;
  line-height: 1.15;
}
.empty-copy p {
  margin: 0;
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.6;
  max-width: 38ch;
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
  background: rgba(16, 185, 129, 0.10);
  color: #047857;
  border: 1px solid rgba(16, 185, 129, 0.22);
}
.allscheduled-msg { font-size: 13.5px; max-width: 36ch; margin: 0; line-height: 1.5; }

@keyframes spin { to { transform: rotate(360deg); } }
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
</style>
