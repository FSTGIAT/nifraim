<template>
  <!-- Ranked bars, RTL: label on the right, bar grows away from it, value in
       its own tabular column. Emphasis form — the highlighted row carries the
       full hue, the rest a lighter step of the SAME hue (one series = one
       colour; colour never encodes rank). -->
  <div class="aibar" :class="{ 'aibar--in': entered, 'aibar--hovering': hovered !== null }">
    <p class="aibar-stats">
      <span v-for="s in stats" :key="s.k">
        {{ s.k }} <strong class="ltr-number">{{ s.v }}</strong>
      </span>
    </p>

    <div class="aibar-grid" :style="{ '--rows': rows.length }" @mouseleave="hovered = null">
      <!-- Hairline grid behind the tracks; ticks are clean round numbers. -->
      <div class="aibar-gridlines" aria-hidden="true">
        <span v-for="t in axis.ticks" :key="t" class="aibar-gridline"
              :class="{ 'aibar-gridline--zero': t === 0 }"
              :style="{ right: pos(t) + '%' }"></span>
      </div>

      <template v-for="(r, i) in rows" :key="r.label + i">
        <div class="aibar-label" :class="{ 'is-hi': r.hi, 'is-hover': hovered === i }"
             :style="{ gridRow: i + 1 }" :title="r.label">{{ r.label }}</div>
        <div class="aibar-track" tabindex="0" role="img" :style="{ gridRow: i + 1 }"
             :aria-label="`${r.label}: ${fmtFull(r.value, unit)}`"
             @mouseenter="hovered = i" @focus="hovered = i" @blur="hovered = null">
          <span class="aibar-bar"
                :class="[r.neg ? 'aibar-bar--neg' : 'aibar-bar--pos', { 'is-hi': r.hi, 'is-dim': hovered !== null && hovered !== i }]"
                :style="{
                  right: r.start + '%',
                  width: Math.max(r.width, 0.6) + '%',
                  '--i': i,
                  '--c': r.hi ? tone.main : tone.soft,
                }"></span>
          <Transition name="aibar-tip">
            <span v-if="hovered === i" class="aibar-tip"
                  :style="{ right: `min(${r.start + r.width}%, calc(100% - 150px))` }">
              <span class="aibar-tip-title">{{ r.label }}</span>
              <strong class="ltr-number">{{ fmtFull(r.value, unit) }}</strong>
              <span class="aibar-tip-sub">
                מקום {{ i + 1 }}<template v-if="showShare"> · <span class="ltr-number">{{ fmtPct(Math.abs(r.value), total) }}</span> מהסך</template>
              </span>
            </span>
          </Transition>
        </div>
        <div class="aibar-value" :class="{ 'is-hi': r.hi }" :style="{ gridRow: i + 1 }">
          <span class="ltr-number">{{ fmtFull(r.value, unit) }}</span>
        </div>
      </template>

      <div class="aibar-axis" aria-hidden="true" :style="{ gridRow: rows.length + 1 }">
        <span v-for="t in axis.ticks" :key="t" class="ltr-number"
              :style="{ right: pos(t) + '%' }">{{ fmtCompact(magnitudes ? Math.abs(t) : t, unit) }}</span>
      </div>
    </div>

    <p v-if="viz.insight" class="ai-chart-insight">{{ viz.insight }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { fmtFull, fmtCompact, fmtPct, niceTicks, prefersReducedMotion, toneFor } from './format.js'

const props = defineProps({ viz: { type: Object, required: true } })

const unit = computed(() => props.viz.unit || '')
const tone = computed(() => toneFor(props.viz.direction))
const raw = computed(() =>
  (props.viz.data || [])
    .filter((d) => d && d.label != null && Number.isFinite(Number(d.value)))
    .slice(0, 12)
    .map((d) => ({ label: String(d.label), value: Number(d.value), id: d.id })),
)

// "Biggest declines" arrive all-negative. Plot their magnitude from the same
// baseline as any ranking; the minus sign stays on the value.
const magnitudes = computed(() => raw.value.length > 0 && raw.value.every((d) => d.value <= 0))
const plotVals = computed(() => raw.value.map((d) => (magnitudes.value ? Math.abs(d.value) : d.value)))

const axis = computed(() => niceTicks(Math.min(...plotVals.value, 0), Math.max(...plotVals.value, 0), 4))
function pos(v) {
  const { lo, hi } = axis.value
  return ((v - lo) / (hi - lo || 1)) * 100
}

const highlight = computed(() => props.viz.highlight_label || raw.value[0]?.label)
const rows = computed(() => {
  const zero = pos(0)
  return raw.value.map((d, i) => {
    const v = plotVals.value[i]
    const w = Math.abs(pos(v) - zero)
    return { ...d, neg: v < 0, start: v < 0 ? zero - w : zero, width: w, hi: d.label === highlight.value }
  })
})

const total = computed(() => raw.value.reduce((s, d) => s + Math.abs(d.value), 0))
// A share of the sum only means something for additive amounts — never for rates.
const showShare = computed(() => unit.value !== '%' && raw.value.length > 1)
const stats = computed(() => {
  const vals = raw.value.map((d) => d.value)
  if (!vals.length) return []
  if (!showShare.value) {
    return [
      { k: 'גבוה', v: fmtFull(Math.max(...vals), unit.value) },
      { k: 'נמוך', v: fmtFull(Math.min(...vals), unit.value) },
      { k: 'פריטים', v: String(vals.length) },
    ]
  }
  const top = rows.value.find((r) => r.hi) || rows.value[0]
  return [
    { k: 'סה״כ', v: fmtFull(vals.reduce((a, b) => a + b, 0), unit.value) },
    { k: 'ממוצע', v: fmtFull(vals.reduce((a, b) => a + b, 0) / vals.length, unit.value) },
    { k: 'המוביל', v: `${top.label} · ${fmtPct(Math.abs(top.value), total.value)} מהסך` },
  ]
})

const hovered = ref(null)
const entered = ref(false)
onMounted(() => {
  if (prefersReducedMotion()) { entered.value = true; return }
  requestAnimationFrame(() => requestAnimationFrame(() => { entered.value = true }))
})
</script>

<style scoped>
.aibar { width: 100%; }

.aibar-stats {
  margin: 0 0 18px;
  display: flex; flex-wrap: wrap; gap: 6px 22px;
  font-size: 12.5px; color: var(--text-muted);
}
.aibar-stats strong { color: var(--text); font-weight: 650; margin-inline-start: 4px; }

.aibar-grid {
  position: relative;
  display: grid;
  grid-template-columns: minmax(96px, 30%) 1fr minmax(84px, auto);
  column-gap: 14px;
  row-gap: 10px;
  align-items: center;
}

.aibar-gridlines {
  grid-column: 2; grid-row: 1 / span var(--rows);
  position: relative; align-self: stretch;
  pointer-events: none;
}
.aibar-gridline {
  position: absolute; top: -4px; bottom: -4px; width: 1px;
  background: var(--border-subtle);
}
.aibar-gridline--zero { background: var(--border); }

.aibar-label {
  grid-column: 1;
  font-size: 13.5px; color: var(--text-secondary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  transition: color 0.2s;
}
.aibar-label.is-hi { color: var(--text); font-weight: 650; }
.aibar-label.is-hover { color: var(--text); }

.aibar-track {
  grid-column: 2;
  position: relative; height: 26px;
  outline: none; cursor: default;
}
.aibar-track:focus-visible { box-shadow: 0 0 0 2px var(--tab-ai-wash, rgba(106, 72, 201, 0.2)); border-radius: 4px; }

.aibar-bar {
  position: absolute; top: 50%; height: 18px; margin-top: -9px;
  background: linear-gradient(to left, var(--c), color-mix(in srgb, var(--c) 72%, white));
  transform: scaleX(0);
  transition:
    transform 1.05s cubic-bezier(0.85, 0, 0.15, 1) calc(var(--i) * 55ms),
    opacity 0.25s ease;
}
/* 4px rounded data-end, square at the baseline. Positioned with physical
   `right` (this chart is RTL-only): positive bars grow from the baseline
   toward the left. Logical inset would flip inside any .ltr-number span. */
.aibar-bar--pos { transform-origin: right center; border-radius: 4px 0 0 4px; }
.aibar-bar--neg {
  transform-origin: left center; border-radius: 0 4px 4px 0;
  background: linear-gradient(to right, var(--c), color-mix(in srgb, var(--c) 72%, white));
}
.aibar--in .aibar-bar { transform: scaleX(1); }
.aibar-bar.is-dim { opacity: 0.3; }

.aibar-value {
  grid-column: 3;
  font-size: 13.5px; color: var(--text-secondary);
  font-variant-numeric: tabular-nums; text-align: left;
}
.aibar-value.is-hi { color: var(--text); font-weight: 700; }

.aibar-axis {
  grid-column: 2; position: relative; height: 16px; margin-top: 2px;
  font-size: 10.5px; color: var(--text-muted);
}
.aibar-axis span { position: absolute; transform: translateX(50%); white-space: nowrap; }

.aibar-tip {
  position: absolute; bottom: calc(100% + 6px); z-index: 3;
  display: flex; flex-direction: column; gap: 1px;
  min-width: 140px; padding: 8px 11px;
  background: #1C1B1A; color: #fff;
  border-radius: 8px; box-shadow: 0 8px 22px rgba(0, 0, 0, 0.22);
  pointer-events: none; white-space: nowrap;
}
.aibar-tip-title { font-size: 11.5px; opacity: 0.75; }
.aibar-tip strong { font-size: 15px; font-weight: 700; }
.aibar-tip-sub { font-size: 11px; opacity: 0.7; }
.aibar-tip-enter-active, .aibar-tip-leave-active { transition: opacity 0.12s, transform 0.12s; }
.aibar-tip-enter-from, .aibar-tip-leave-to { opacity: 0; transform: translateY(4px); }

@media (prefers-reduced-motion: reduce) {
  .aibar-bar { transition: opacity 0.2s; transform: none; }
}
@media (max-width: 560px) {
  .aibar-grid { grid-template-columns: minmax(70px, 34%) 1fr auto; column-gap: 8px; }
}
</style>
