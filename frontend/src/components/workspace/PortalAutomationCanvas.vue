<template>
  <div class="auto-canvas" :class="{ 'is-empty': !credentials.length }">
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
        <p>הוסף פרטי התחברות לפורטל של חברת ביטוח, והדוחות יורידו את עצמם.</p>
        <button class="btn-add btn-add--cta" type="button" @click="$emit('add')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14" /><path d="M12 5v14" />
          </svg>
          <span>הוסף פורטל</span>
        </button>
      </div>
    </div>

    <!-- ── Cards grid — full-width responsive ──────────────── -->
    <TransitionGroup v-else name="card-flip" tag="div" class="cards-grid">
      <div v-for="cred in credentials" :key="cred.id" class="card-slot">
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
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PortalCard from './PortalCard.vue'
import { brandFor } from '../../utils/companyBrand.js'
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

const paneSub = computed(() => {
  const total = props.credentials.length
  if (!total) return 'עוד אין פורטלים מחוברים'
  return `${total} פורטל${total === 1 ? '' : 'ים'} מחובר${total === 1 ? '' : 'ים'}`
})

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

/* ─── Header ─────────────────────────────────────────────── */
.pane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--border-subtle);
}
.pane-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pane-title { font-size: 15px; font-weight: 800; color: var(--text); letter-spacing: -0.2px; }
.pane-sub { font-size: 12px; color: var(--text-muted); }

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

/* ─── Cards grid — full-width responsive ─────────────────── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
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
