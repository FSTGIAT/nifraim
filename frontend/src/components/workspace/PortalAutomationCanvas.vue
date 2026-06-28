<template>
  <div class="auto-canvas" :class="{ 'is-empty': !credentials.length }">
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
        <p>הוסף פרטי התחברות לפורטל של חברת ביטוח, והדוחות יורידו את עצמם.</p>
        <button class="btn-add btn-add--cta" type="button" @click="$emit('add')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14" /><path d="M12 5v14" />
          </svg>
          <span>הוסף פורטל</span>
        </button>
      </div>
    </div>

    <!-- ── Cards grouped by company, in framed panels ───────── -->
    <div v-else class="groups">
      <section v-for="g in groups" :key="g.key" class="company-panel">
        <header class="panel-head" :style="{ '--brand': g.color, '--brand-tint': groupTint(g.color) }">
          <span class="group-icon" aria-hidden="true">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <path :d="g.brand.iconPath" />
            </svg>
          </span>
          <span class="group-name">{{ g.label }}</span>
          <span class="group-count ltr-number">{{ g.creds.length }}</span>

          <!-- Per-company health -->
          <span class="health" :title="`${g.health.ok}/${g.health.total} תקינים`">
            <span class="health-dots" aria-hidden="true">
              <span
                v-for="(d, i) in g.health.dots"
                :key="i"
                class="health-dot"
                :class="`health-dot--${d}`"
              ></span>
            </span>
            <span class="health-label">{{ g.health.ok }}/{{ g.health.total }} תקינים</span>
          </span>
        </header>

        <TransitionGroup name="card-flip" tag="div" class="cards-grid">
          <div v-for="cred in g.creds" :key="cred.id" class="card-slot">
            <PortalCard
              :cred="cred"
              :wash-color="credColor(cred.portal_kind)"
              :is-running="isRunning(cred.id)"
              :portal-label="portalLabel(cred.portal_kind)"
              :active-run="activeRun"
              @run="$emit('run', cred.id)"
              @edit="$emit('edit', cred)"
              @delete="$emit('delete', cred.id)"
              @view-error="(msg) => $emit('view-error', { cred, message: msg })"
            />
          </div>
        </TransitionGroup>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PortalCard from './PortalCard.vue'
import { brandFor, brandForLabel } from '../../utils/companyBrand.js'
import { nearestChartColor, assignNearestDistinct } from '../../utils/chartPalette.js'

const props = defineProps({
  credentials: { type: Array, required: true },
  portalLabel: { type: Function, required: true },
  activeRun: { type: Object, default: null },
  activeRunId: { type: String, default: null },
})

defineEmits(['run', 'edit', 'delete', 'add', 'view-error'])

// Distinct on-palette color per company (nearest-to-brand, de-duplicated so
// several red insurers don't collapse to the same red).
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

// Group credentials by company — Harel/Clal/… variants collapse under one
// heading via brandForLabel's substring match on the portal's display label.
const groups = computed(() => {
  const map = new Map()
  for (const c of props.credentials || []) {
    const lbl = props.portalLabel(c.portal_kind)
    const b = brandForLabel(lbl)
    const key = b.label && b.label !== '?' ? b.label : lbl
    if (!map.has(key)) {
      map.set(key, {
        key,
        label: key,
        brand: b,
        color: credColor(c.portal_kind),
        creds: [],
      })
    }
    map.get(key).creds.push(c)
  }
  // Per-company health: how many of the company's portals last ran OK, plus a
  // compact dot row (one per credential, newest last_run_status).
  return Array.from(map.values()).map((g) => {
    const total = g.creds.length
    const ok = g.creds.filter((c) => c.last_run_status === 'success').length
    const dots = g.creds.map((c) => {
      const s = c.last_run_status
      if (s === 'success') return 'success'
      if (s === 'failed' || s === 'timeout') return 'failed'
      if (!s) return 'empty'
      return 'running'
    })
    return { ...g, health: { ok, total, dots } }
  })
})

function groupTint(hex) {
  const clean = (hex || '#706E6B').replace('#', '')
  const full = clean.length === 3 ? clean.split('').map((ch) => ch + ch).join('') : clean
  const n = parseInt(full, 16)
  return `rgba(${(n >> 16) & 0xff}, ${(n >> 8) & 0xff}, ${n & 0xff}, 0.12)`
}

function isRunning(credId) {
  return props.activeRunId && props.activeRun?.credential_id === credId
}
</script>

<style scoped>
.auto-canvas {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 420px;
}

/* ─── Add-portal button (empty-state CTA) ────────────────── */
.btn-add {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #4E9DD0, #1FA88C);  /* pastel sky → teal */
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

/* ─── Company panels ─────────────────────────────────────── */
.groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.company-panel {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg, 16px);
  padding: 14px 16px 16px;
  box-shadow: 0 1px 2px rgba(26, 20, 16, 0.03), 0 4px 14px rgba(26, 20, 16, 0.04);
}
.panel-head {
  display: flex;
  align-items: center;
  gap: 9px;
  padding-bottom: 12px;
  margin-bottom: 14px;
  border-bottom: 1px dashed var(--border-subtle);
}
.group-icon {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  color: var(--brand);
  background: var(--brand-tint);
}
.group-name {
  font-size: 14.5px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.2px;
}
.group-count {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11px;
  font-weight: 800;
  color: var(--text-muted);
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  padding: 2px 9px;
  line-height: 1.4;
}
/* Per-company health — pushed to the inline-end of the header */
.health {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-inline-start: auto;
}
.health-dots { display: inline-flex; gap: 3px; }
.health-dot { width: 7px; height: 7px; border-radius: 50%; background: rgba(0,0,0,0.10); }
.health-dot--success { background: var(--green); }
.health-dot--failed  { background: var(--red); }
.health-dot--running { background: #1FA88C; }
.health-dot--empty   { background: rgba(0,0,0,0.10); }
.health-label { font-size: 11px; font-weight: 700; color: var(--text-muted); white-space: nowrap; }

/* ─── Cards grid — fills the panel row (auto-fit) ─────────── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  position: relative;
}
.card-slot { transition: opacity 0.28s ease; }

/* FLIP move/enter/leave for the cards grid */
.card-flip-enter-active, .card-flip-leave-active, .card-flip-move {
  transition: all 0.36s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.card-flip-enter-from { opacity: 0; transform: scale(0.92) translateY(8px); }
.card-flip-leave-to   { opacity: 0; transform: scale(0.92) translateX(40px); position: absolute; }
.card-flip-leave-active { position: absolute; }

/* ─── Empty state ────────────────────────────────────────── */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 20px;
  min-height: 380px;
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

/* ─── Staggered entrance — credential cards ──────────────── */
@keyframes auto-rise {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.card-slot {
  animation: auto-rise 300ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
.card-slot:nth-child(1) { animation-delay: 40ms; }
.card-slot:nth-child(2) { animation-delay: 80ms; }
.card-slot:nth-child(3) { animation-delay: 120ms; }
.card-slot:nth-child(4) { animation-delay: 160ms; }
.card-slot:nth-child(5) { animation-delay: 200ms; }
.card-slot:nth-child(6) { animation-delay: 240ms; }
.card-slot:nth-child(7) { animation-delay: 280ms; }
.card-slot:nth-child(8) { animation-delay: 320ms; }

@media (prefers-reduced-motion: reduce) {
  .card-slot { animation: none; transform: none; }
}
</style>
