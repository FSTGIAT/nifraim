<template>
  <!-- Part-to-whole. Slices take the validated categorical palette in FIXED
       order (by the entity's position, largest first) — never recycled; past
       7 the tail folds into "אחרות". The legend is the identity channel,
       with value + share, and hover is synced both ways. -->
  <div class="aido" :class="{ 'aido--in': entered }">
    <div class="aido-figure" @mouseleave="hovered = null">
      <svg :viewBox="`0 0 ${S} ${S}`" class="aido-svg" role="img" :aria-label="viz.title || 'התפלגות'">
        <g>
          <path v-for="(sl, i) in slices" :key="sl.label"
                class="aido-slice"
                :class="{ 'is-dim': hovered !== null && hovered !== i, 'is-hover': hovered === i }"
                :d="sl.d"
                :style="{ '--i': i, fill: sl.color, stroke: sl.color }"
                tabindex="0"
                @mouseenter="hovered = i" @focus="hovered = i" @blur="hovered = null" />
        </g>
      </svg>
      <div class="aido-center" aria-hidden="true">
        <span class="aido-center-k">{{ focus ? focus.label : 'סה״כ' }}</span>
        <strong class="ltr-number">{{ fmtCompact(focus ? focus.value : total, unit) }}</strong>
        <span class="aido-center-sub ltr-number">{{ focus ? fmtPct(focus.value, total) : `${slices.length} פלחים` }}</span>
      </div>
    </div>

    <ul class="aido-legend" @mouseleave="hovered = null">
      <li v-for="(sl, i) in slices" :key="sl.label"
          :class="{ 'is-dim': hovered !== null && hovered !== i, 'is-hi': sl.hi }"
          @mouseenter="hovered = i">
        <span class="aido-swatch" :style="{ background: sl.color }"></span>
        <span class="aido-name" :title="sl.label">{{ sl.label }}</span>
        <span class="aido-val ltr-number">{{ fmtFull(sl.value, unit) }}</span>
        <span class="aido-pct ltr-number">{{ fmtPct(sl.value, total) }}</span>
      </li>
    </ul>

    <p v-if="viz.insight" class="ai-chart-insight">{{ viz.insight }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { CHART_PALETTE } from '../../utils/chartPalette.js'
import { fmtFull, fmtCompact, fmtPct, prefersReducedMotion } from './format.js'

const props = defineProps({ viz: { type: Object, required: true } })

const S = 240
const R_OUT = 112
const R_IN = 74
const PAD = 0.035 // radians of surface between slices — the 2px gap at this size
const MAX_SLICES = 7 // then fold — slots past 11 are unvalidated, and 7 is the soft cap

const unit = computed(() => props.viz.unit || '')
const items = computed(() => {
  const clean = (props.viz.data || [])
    .filter((d) => d && d.label != null && Number(d.value) > 0)
    .map((d) => ({ label: String(d.label), value: Number(d.value) }))
    .sort((a, b) => b.value - a.value)
  if (clean.length <= MAX_SLICES) return clean
  const head = clean.slice(0, MAX_SLICES - 1)
  const rest = clean.slice(MAX_SLICES - 1).reduce((s, d) => s + d.value, 0)
  return [...head, { label: 'אחרות', value: rest, other: true }]
})
const total = computed(() => items.value.reduce((s, d) => s + d.value, 0))

function arc(a0, a1) {
  // Annular sector, clockwise from 12 o'clock.
  const p = (r, a) => [S / 2 + r * Math.sin(a), S / 2 - r * Math.cos(a)]
  const large = a1 - a0 > Math.PI ? 1 : 0
  const [x0, y0] = p(R_OUT, a0)
  const [x1, y1] = p(R_OUT, a1)
  const [x2, y2] = p(R_IN, a1)
  const [x3, y3] = p(R_IN, a0)
  return `M${x0},${y0}A${R_OUT},${R_OUT} 0 ${large} 1 ${x1},${y1}L${x2},${y2}A${R_IN},${R_IN} 0 ${large} 0 ${x3},${y3}Z`
}

const slices = computed(() => {
  const n = items.value.length
  const pad = n > 1 ? PAD : 0
  let a = 0
  return items.value.map((d, i) => {
    const sweep = (d.value / (total.value || 1)) * Math.PI * 2
    const a0 = a + pad / 2
    const a1 = Math.max(a0 + 0.004, a + sweep - pad / 2)
    a += sweep
    return {
      ...d,
      d: arc(a0, Math.min(a1, a0 + Math.PI * 2 - 0.0001)),
      color: d.other ? 'var(--chart-absent)' : CHART_PALETTE[i % 11],
      hi: d.label === props.viz.highlight_label,
    }
  })
})

const hovered = ref(null)
const focus = computed(() => (hovered.value === null ? null : slices.value[hovered.value]))
const entered = ref(false)
onMounted(() => {
  if (prefersReducedMotion()) { entered.value = true; return }
  requestAnimationFrame(() => requestAnimationFrame(() => { entered.value = true }))
})
</script>

<style scoped>
.aido {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(200px, 260px) 1fr;
  gap: 12px 32px;
  align-items: center;
}
.aido-figure { position: relative; }
.aido-svg { width: 100%; height: auto; display: block; overflow: visible; }

.aido-slice {
  stroke-width: 3; stroke-linejoin: round; /* softens the four corners */
  outline: none; cursor: default;
  transform-box: view-box; transform-origin: 50% 50%;
  opacity: 0; transform: scale(0.86) rotate(-12deg);
  transition:
    opacity 0.5s ease calc(var(--i) * 70ms),
    transform 0.7s cubic-bezier(0.2, 0.7, 0.3, 1) calc(var(--i) * 70ms);
}
.aido--in .aido-slice { opacity: 1; transform: none; }
.aido--in .aido-slice.is-dim { opacity: 0.28; transition-delay: 0s; }
.aido--in .aido-slice.is-hover { transform: scale(1.035); transition-delay: 0s; }

.aido-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  pointer-events: none; text-align: center; padding: 0 22%;
}
.aido-center-k { font-size: 12px; color: var(--text-muted); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.aido-center strong { font-size: 24px; font-weight: 700; color: var(--text); line-height: 1.2; }
.aido-center-sub { font-size: 12px; color: var(--text-muted); }

.aido-legend { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.aido-legend li {
  display: grid; grid-template-columns: 12px 1fr auto 48px; gap: 10px; align-items: center;
  padding: 7px 10px; border-radius: 8px;
  font-size: 13.5px; color: var(--text-secondary);
  transition: opacity 0.2s, background 0.2s;
}
.aido-legend li:hover { background: var(--glass-hover, #F7F7F7); }
.aido-legend li.is-dim { opacity: 0.4; }
.aido-legend li.is-hi .aido-name { color: var(--text); font-weight: 650; }
.aido-swatch { width: 12px; height: 12px; border-radius: 3px; }
.aido-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.aido-val { color: var(--text); font-variant-numeric: tabular-nums; }
.aido-pct { color: var(--text-muted); font-variant-numeric: tabular-nums; text-align: left; }

.aido .ai-chart-insight { grid-column: 1 / -1; }

@media (max-width: 620px) {
  .aido { grid-template-columns: 1fr; }
  .aido-figure { max-width: 240px; margin: 0 auto; }
}
@media (prefers-reduced-motion: reduce) {
  .aido-slice { transition: opacity 0.2s; transform: none; }
}
</style>
