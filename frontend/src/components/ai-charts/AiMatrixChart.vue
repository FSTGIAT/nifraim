<template>
  <!-- Who holds what: customers × product categories, in the hover-trace language.
       A filled dot (the surface's ONE accent) = holds it; a faint ring = a gap → the
       cross-sell is visible at a glance. A thin bar beside each name = premium/צבירה.
       The traced row is full strength, the rest soft; the readout springs to it. -->
  <div class="hmx" :class="{ 'hmx--in': entered }">
    <header class="hmx-head">
      <div class="hmx-read">
        <span class="hmx-k">[{{ hovered !== null ? 'נבחר' : 'המוביל' }}] · <b>{{ traced?.label }}</b></span>
        <strong class="hmx-v ltr-number">{{ fmtFull(springVal, unit) }}</strong>
      </div>
      <span v-if="traced" class="hmx-meta">{{ held(traced) }} מתוך {{ columns.length }} סוגי מוצרים<template v-if="traced.companies?.length"> · {{ traced.companies.join(', ') }}</template></span>
    </header>

    <div class="hmx-grid" :style="{ '--cols': columns.length }" @mouseleave="hovered = null">
      <span class="hmx-corner" aria-hidden="true"></span>
      <span v-for="c in columns" :key="'h' + c" class="hmx-col" :title="c">{{ c }}</span>

      <template v-for="(r, i) in rows" :key="r.label + i">
        <div class="hmx-name" :class="{ 'is-on': tracedIdx === i }" @mouseenter="hovered = i">
          <span class="hmx-label" :title="r.label">{{ r.label }}</span>
          <span class="hmx-bar" aria-hidden="true"><i :style="{ width: (Math.abs(r.value || 0) / maxVal) * 100 + '%', '--i': i }"></i></span>
        </div>
        <span v-for="(c, j) in columns" :key="c + i" class="hmx-cell" :class="{ 'is-on': tracedIdx === i }"
              :aria-label="`${r.label} — ${c}: ${r.cells[c] ? 'יש' : 'אין'}`" role="img" @mouseenter="hovered = i">
          <i class="hmx-dot" :class="r.cells[c] ? 'is-held' : 'is-gap'" :style="{ '--d': i * columns.length + j }"></i>
        </span>
      </template>
    </div>

    <p class="hmx-legend"><i class="hmx-dot is-held"></i> יש ללקוח <i class="hmx-dot is-gap"></i> אין — הזדמנות</p>
    <p v-if="viz.insight" class="ai-chart-insight">{{ viz.insight }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { fmtFull, prefersReducedMotion } from './format.js'
import { useSpring } from '../../composables/useSpring.js'

const props = defineProps({ viz: { type: Object, required: true } })
const unit = computed(() => props.viz.unit || '₪')
const columns = computed(() => props.viz.columns || [])
const rows = computed(() => (props.viz.rows || []).slice(0, 12))
const maxVal = computed(() => Math.max(...rows.value.map((r) => Math.abs(r.value || 0)), 1))
const held = (r) => columns.value.filter((c) => r.cells?.[c]).length

const hovered = ref(null)
const tracedIdx = computed(() => (hovered.value !== null ? hovered.value : 0))
const traced = computed(() => rows.value[tracedIdx.value] || null)
const springVal = useSpring(() => traced.value?.value ?? 0, { stiffness: 110, damping: 20 })

const entered = ref(false)
onMounted(() => {
  if (prefersReducedMotion()) { entered.value = true; return }
  requestAnimationFrame(() => requestAnimationFrame(() => { entered.value = true }))
})
</script>

<style scoped>
.hmx { width: 100%; --acc: var(--viz-accent, var(--primary, #181818)); }
.hmx-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin: 0 0 14px; }
.hmx-read { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.hmx-k { font-size: 12px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hmx-k b { color: var(--text-secondary); font-weight: 650; }
.hmx-v { font-size: 30px; font-weight: 800; letter-spacing: -0.035em; line-height: 1; color: var(--acc); font-variant-numeric: tabular-nums; }
.hmx-meta { font-size: 12px; color: var(--text-muted); text-align: left; }

.hmx-grid {
  display: grid; grid-template-columns: minmax(120px, 1.6fr) repeat(var(--cols), minmax(34px, 1fr));
  align-items: center; row-gap: 4px; column-gap: 2px;
}
.hmx-col { font-size: 11px; font-weight: 700; color: var(--text-muted); text-align: center; padding-bottom: 6px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-bottom: 2px solid color-mix(in srgb, var(--acc) 40%, transparent); }
.hmx-corner { border-bottom: 2px solid color-mix(in srgb, var(--acc) 40%, transparent); align-self: stretch; }

.hmx-name { display: flex; flex-direction: column; gap: 4px; padding: 6px 8px 6px 4px; border-radius: 8px; cursor: default; min-width: 0; }
.hmx-label { font-size: 13px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: color 0.2s; }
.hmx-name.is-on .hmx-label { color: var(--text); font-weight: 700; }
.hmx-bar { height: 3px; border-radius: 2px; background: color-mix(in srgb, var(--acc) 8%, transparent); overflow: hidden; }
.hmx-bar i { display: block; height: 100%; border-radius: 2px; background: var(--acc); opacity: 0.3; transform-origin: right center; transform: scaleX(0);
  transition: transform 0.9s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + var(--i) * 50ms), opacity 0.2s; }
.hmx--in .hmx-bar i { transform: scaleX(1); }
.hmx-name.is-on .hmx-bar i { opacity: 1; }

.hmx-cell { display: grid; place-items: center; height: 34px; border-radius: 6px; cursor: default; transition: background 0.2s; }
.hmx-cell.is-on, .hmx-name.is-on { background: color-mix(in srgb, var(--acc) 6%, transparent); }

.hmx-dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; }
.hmx-cell .hmx-dot { transform: scale(0); opacity: 0;
  transition: transform 0.5s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + var(--d) * 14ms),
              opacity 0.4s ease calc(var(--silk-content-delay, 280ms) + var(--d) * 14ms); }
.hmx--in .hmx-cell .hmx-dot { transform: scale(1); opacity: 1; }
.hmx-dot.is-held { background: var(--acc); }
.hmx-cell:not(.is-on) .hmx-dot.is-held { opacity: 0.55; }
.hmx--in .hmx-cell:not(.is-on) .hmx-dot.is-held { opacity: 0.55; }
.hmx-dot.is-gap { background: transparent; box-shadow: inset 0 0 0 1.5px color-mix(in srgb, var(--acc) 28%, transparent); }

.hmx-legend { display: flex; align-items: center; gap: 6px; margin: 12px 0 0; font-size: 11.5px; color: var(--text-muted); }
.hmx-legend .hmx-dot { width: 9px; height: 9px; }
.hmx-legend .hmx-dot.is-gap { margin-inline-start: 10px; }

@media (prefers-reduced-motion: reduce) {
  .hmx-cell .hmx-dot, .hmx-bar i { transition: none; transform: none; opacity: 1; }
}
</style>
