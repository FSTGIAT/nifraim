<template>
  <div class="zones-row" role="region" aria-label="תזמון אוטומטי">
    <div
      v-for="z in zones"
      :key="z.kind"
      class="zone"
      :class="[`zone--${z.kind}`, { 'is-over': dragOver === z.kind, 'is-empty': cardsByKind[z.kind].length === 0 }]"
      @dragover.prevent="onDragOver(z.kind)"
      @dragleave="onDragLeave(z.kind)"
      @drop.prevent="onDrop($event, z.kind)"
    >
      <div class="zone-grid" aria-hidden="true"></div>
      <header class="zone-head">
        <span class="zone-icon" aria-hidden="true">
          <!-- daily: sunrise; weekly: calendar; monthly: calendar-range -->
          <svg v-if="z.kind === 'daily'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2v8"/><path d="m4.93 10.93 1.41 1.41"/><path d="M2 18h2"/><path d="M20 18h2"/><path d="m19.07 10.93-1.41 1.41"/><path d="M22 22H2"/><path d="m8 6 4-4 4 4"/><path d="M16 18a4 4 0 0 0-8 0"/>
          </svg>
          <svg v-else-if="z.kind === 'weekly'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/><path d="M12 14v4"/><path d="M10 16h4"/>
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
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M5 12h14"/><path d="M12 5v14"/>
        </svg>
        <span>גרור פורטל לכאן</span>
      </div>

      <div v-else class="zone-cards">
        <div
          v-for="cred in cardsByKind[z.kind]"
          :key="cred.id"
          class="zone-card"
          draggable="true"
          @dragstart="onDragStart($event, cred.id)"
          :title="`${portalLabel(cred.portal_kind)} · ${cred.username}`"
        >
          <span class="zc-grip" aria-hidden="true">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="9" cy="6" r="0.5" fill="currentColor"/><circle cx="9" cy="12" r="0.5" fill="currentColor"/><circle cx="9" cy="18" r="0.5" fill="currentColor"/>
              <circle cx="15" cy="6" r="0.5" fill="currentColor"/><circle cx="15" cy="12" r="0.5" fill="currentColor"/><circle cx="15" cy="18" r="0.5" fill="currentColor"/>
            </svg>
          </span>
          <span class="zc-name">{{ portalLabel(cred.portal_kind) }}</span>
          <span class="zc-user">{{ cred.username }}</span>
          <button
            class="zc-x"
            type="button"
            :aria-label="`הסר תזמון מ${portalLabel(cred.portal_kind)}`"
            @click="$emit('remove', cred.id)"
          >
            <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="zone-corner" aria-hidden="true">
        <span class="zone-corner-tl"></span><span class="zone-corner-tr"></span>
        <span class="zone-corner-bl"></span><span class="zone-corner-br"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  credentials: { type: Array, required: true },
  portalLabel: { type: Function, required: true },
})
const emit = defineEmits(['drop', 'remove'])

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

const dragOver = ref(null)

function onDragStart(e, credId) {
  e.dataTransfer.setData('text/plain', credId)
  e.dataTransfer.effectAllowed = 'move'
}
function onDragOver(kind) { dragOver.value = kind }
function onDragLeave(kind) { if (dragOver.value === kind) dragOver.value = null }
function onDrop(e, kind) {
  dragOver.value = null
  const credId = e.dataTransfer.getData('text/plain')
  if (!credId) return
  const cred = (props.credentials || []).find((c) => c.id === credId)
  if (!cred || cred.schedule_kind === kind) return
  emit('drop', { id: credId, schedule_kind: kind })
}
</script>

<style scoped>
.zones-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 720px) {
  .zones-row { grid-template-columns: 1fr; }
}

/* ───── Zone shell ───── */
.zone {
  position: relative;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 14px 14px 12px;
  min-height: 132px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.12s, background 0.18s;
}

/* Subtle hairline grid background, like a control panel */
.zone-grid {
  position: absolute;
  inset: 0;
  opacity: 0.5;
  background-image:
    linear-gradient(to right, rgba(0,0,0,0.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(0,0,0,0.025) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
  mask-image: radial-gradient(ellipse at top right, #000 30%, transparent 80%);
}

/* Cadence-specific tinting — very restrained, more atmosphere than color */
.zone--daily   { --cadence: #c2410c; --cadence-bg: rgba(194, 65, 12, 0.04); --cadence-bg-strong: rgba(194, 65, 12, 0.10); }
.zone--weekly  { --cadence: #0e7490; --cadence-bg: rgba(14, 116, 144, 0.04); --cadence-bg-strong: rgba(14, 116, 144, 0.10); }
.zone--monthly { --cadence: #4338ca; --cadence-bg: rgba(67, 56, 202, 0.04); --cadence-bg-strong: rgba(67, 56, 202, 0.10); }

.zone {
  background:
    linear-gradient(135deg, var(--cadence-bg) 0%, transparent 60%),
    var(--card-bg);
}

.zone.is-over {
  border-color: var(--cadence);
  background:
    linear-gradient(135deg, var(--cadence-bg-strong) 0%, transparent 70%),
    var(--card-bg);
  box-shadow: 0 0 0 3px rgba(0,0,0,0.0), 0 0 0 1px var(--cadence) inset, 0 14px 28px rgba(0,0,0,0.06);
}

/* Corner brackets — like a Figma selection. Appear sharp on drag-over. */
.zone-corner { position: absolute; inset: 0; pointer-events: none; }
.zone-corner > span {
  position: absolute;
  width: 10px;
  height: 10px;
  border-color: transparent;
  border-style: solid;
  border-width: 0;
  transition: border-color 0.18s;
}
.zone-corner-tl { top: 6px; right: 6px; border-top-width: 1.5px; border-right-width: 1.5px; }
.zone-corner-tr { top: 6px; left:  6px; border-top-width: 1.5px; border-left-width:  1.5px; }
.zone-corner-bl { bottom: 6px; right: 6px; border-bottom-width: 1.5px; border-right-width: 1.5px; }
.zone-corner-br { bottom: 6px; left:  6px; border-bottom-width: 1.5px; border-left-width:  1.5px; }
.zone.is-over .zone-corner > span { border-color: var(--cadence); }

/* ───── Header ───── */
.zone-head {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
}
.zone-icon {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.03);
  color: var(--cadence);
  border: 1px solid rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
}
.zone-meta { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.zone-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--text);
}
.zone-sub {
  font-size: 11.5px;
  color: var(--text-muted);
}
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

/* ───── Empty state ───── */
.zone-empty {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  border-radius: 8px;
  border: 1px dashed transparent;
}
.zone.is-over .zone-empty {
  color: var(--cadence);
  border-color: var(--cadence);
  background: rgba(255, 255, 255, 0.6);
}

/* ───── Card chips ───── */
.zone-cards {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.zone-card {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 5px 5px 10px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--cadence);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text);
  cursor: grab;
  transition: transform 0.12s, box-shadow 0.12s, border-color 0.12s;
}
.zone-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08);
  border-color: var(--cadence);
}
.zone-card:active { cursor: grabbing; }
.zc-grip { color: var(--text-muted); display: inline-flex; }
.zc-name { font-weight: 700; }
.zc-user { color: var(--text-muted); font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 11px; letter-spacing: 0.3px; }
.zc-x {
  width: 16px;
  height: 16px;
  display: grid;
  place-items: center;
  border-radius: 4px;
  border: none;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-muted);
  cursor: pointer;
}
.zc-x:hover { background: rgba(239, 68, 68, 0.18); color: #b91c1c; }
</style>
