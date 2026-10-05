<template>
  <!-- Part-to-whole in the hover-trace language (same as AiBarChart): ONE colour —
       the surface's accent (--viz-accent: ink in the chat, Nifra Agent teal in its
       panel) — the traced slice full, the rest at 22%; a big spring-animated readout;
       a quiet list with counts and shares. At rest it traces the largest slice. -->
  <div class="hdo" :class="{ 'hdo--in': entered }">
    <header class="hdo-head">
      <div class="hdo-read">
        <span class="hdo-k">[{{ hovered !== null ? 'נבחר' : 'המוביל' }}] · <b>{{ traced?.label }}</b></span>
        <strong class="hdo-v ltr-number">{{ fmtFull(springVal, unit) }}</strong>
      </div>
      <span class="hdo-share ltr-number">{{ traced ? fmtPct(traced.value, total) : '' }} מתוך {{ fmtFull(total, unit) }}</span>
    </header>

    <div class="hdo-body" @mouseleave="hovered = null">
      <div class="hdo-figure">
        <svg :viewBox="`0 0 ${S} ${S}`" class="hdo-svg" role="img" :aria-label="viz.title || 'התפלגות'">
          <path v-for="(sl, i) in slices" :key="sl.label" class="hdo-slice"
                :class="{ 'is-on': tracedIdx === i }" :d="sl.d" :style="{ '--i': i }"
                tabindex="0" @mouseenter="hovered = i" @focus="hovered = i" @blur="hovered = null" />
        </svg>
        <div class="hdo-center" aria-hidden="true">
          <strong class="ltr-number">{{ traced ? fmtPct(traced.value, total) : '' }}</strong>
        </div>
      </div>

      <ul class="hdo-list">
        <li v-for="(sl, i) in slices" :key="sl.label" :class="{ 'is-on': tracedIdx === i }" :style="{ '--i': i }"
            @mouseenter="hovered = i">
          <span class="hdo-name" :title="sl.label">{{ sl.label }}</span>
          <span class="hdo-bar" aria-hidden="true"><i :style="{ width: (sl.value / maxVal) * 100 + '%' }"></i></span>
          <span class="hdo-val ltr-number">{{ fmtFull(sl.value, unit) }}</span>
          <span class="hdo-pct ltr-number">{{ fmtPct(sl.value, total) }}</span>
        </li>
      </ul>
    </div>

    <p v-if="viz.insight" class="ai-chart-insight">{{ viz.insight }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { fmtFull, fmtPct, prefersReducedMotion } from './format.js'
import { useSpring } from '../../composables/useSpring.js'

const props = defineProps({ viz: { type: Object, required: true } })

const S = 200
const R_OUT = 96
const R_IN = 64
const PAD = 0.04
const MAX_SLICES = 7

const unit = computed(() => props.viz.unit || '')
const items = computed(() => {
  const clean = (props.viz.data || [])
    .filter((d) => d && d.label != null && Number(d.value) > 0)
    .map((d) => ({ label: String(d.label), value: Number(d.value) }))
    .sort((a, b) => b.value - a.value)
  if (clean.length <= MAX_SLICES) return clean
  const head = clean.slice(0, MAX_SLICES - 1)
  return [...head, { label: 'אחרות', value: clean.slice(MAX_SLICES - 1).reduce((s, d) => s + d.value, 0) }]
})
const total = computed(() => items.value.reduce((s, d) => s + d.value, 0))
const maxVal = computed(() => Math.max(...items.value.map((d) => d.value), 1))

function arc(a0, a1) {
  const p = (r, a) => [S / 2 + r * Math.sin(a), S / 2 - r * Math.cos(a)]
  const large = a1 - a0 > Math.PI ? 1 : 0
  const [x0, y0] = p(R_OUT, a0); const [x1, y1] = p(R_OUT, a1)
  const [x2, y2] = p(R_IN, a1); const [x3, y3] = p(R_IN, a0)
  return `M${x0},${y0}A${R_OUT},${R_OUT} 0 ${large} 1 ${x1},${y1}L${x2},${y2}A${R_IN},${R_IN} 0 ${large} 0 ${x3},${y3}Z`
}
const slices = computed(() => {
  const n = items.value.length
  const pad = n > 1 ? PAD : 0
  let a = 0
  return items.value.map((d) => {
    const sweep = (d.value / (total.value || 1)) * Math.PI * 2
    const a0 = a + pad / 2
    const a1 = Math.max(a0 + 0.004, a + sweep - pad / 2)
    a += sweep
    return { ...d, d: arc(a0, Math.min(a1, a0 + Math.PI * 2 - 0.0001)) }
  })
})

const hovered = ref(null)
const tracedIdx = computed(() => (hovered.value !== null ? hovered.value : 0))   // rest on the largest
const traced = computed(() => slices.value[tracedIdx.value] || null)
const springVal = useSpring(() => traced.value?.value ?? 0, { stiffness: 110, damping: 20 })

const entered = ref(false)
onMounted(() => {
  if (prefersReducedMotion()) { entered.value = true; return }
  requestAnimationFrame(() => requestAnimationFrame(() => { entered.value = true }))
})
</script>

<style scoped>
.hdo { width: 100%; --acc: var(--viz-accent, var(--primary, #181818)); }
.hdo-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin: 0 0 14px; }
.hdo-read { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.hdo-k { font-size: 12px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hdo-k b { color: var(--text-secondary); font-weight: 650; }
.hdo-v { font-size: 34px; font-weight: 800; letter-spacing: -0.035em; line-height: 1; color: var(--acc); font-variant-numeric: tabular-nums; }
.hdo-share { font-size: 12px; color: var(--text-muted); }

.hdo-body { display: grid; grid-template-columns: minmax(130px, 190px) 1fr; gap: 18px 28px; align-items: center; }
.hdo-figure { position: relative; }
.hdo-svg { width: 100%; height: auto; display: block; overflow: visible; }
/* the circle DRAWS itself: a clockwise sweep from 12 o'clock reveals the ring (user, 2026-10-05) */
@property --hdo-sweep { syntax: '<angle>'; inherits: false; initial-value: 360deg; }
.hdo-svg {
  -webkit-mask: conic-gradient(#000 var(--hdo-sweep), transparent var(--hdo-sweep));
          mask: conic-gradient(#000 var(--hdo-sweep), transparent var(--hdo-sweep));
  --hdo-sweep: 0deg;
}
.hdo--in .hdo-svg { animation: hdoDraw 1.1s cubic-bezier(0.22, 1, 0.36, 1) var(--silk-content-delay, 280ms) both; }
@keyframes hdoDraw { from { --hdo-sweep: 0deg; } to { --hdo-sweep: 360deg; } }
.hdo-slice {
  fill: var(--acc); stroke: #fff; stroke-width: 2; stroke-linejoin: round; outline: none; cursor: default;
  transform-box: view-box; transform-origin: 50% 50%;
  opacity: 0; transform: scale(0.96);
  transition:
    opacity 0.6s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + var(--i) * 70ms),
    transform 0.9s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + var(--i) * 70ms);
}
.hdo--in .hdo-slice { opacity: 0.22; transform: none; }
.hdo--in .hdo-slice.is-on { opacity: 1; transform: scale(1.03); transition-delay: 0s, 0s; }
.hdo--in .hdo-slice:not(.is-on) { transition-delay: calc(var(--silk-content-delay, 280ms) + var(--i) * 70ms), calc(var(--silk-content-delay, 280ms) + var(--i) * 70ms); }
.hdo-center { position: absolute; inset: 0; display: grid; place-items: center; pointer-events: none; }
.hdo-center strong { font-size: 20px; font-weight: 800; color: var(--acc); }

.hdo-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.hdo-list li {
  display: grid; grid-template-columns: minmax(70px, 1.2fr) 1fr auto 46px; gap: 10px; align-items: center;
  padding: 6px 8px; border-radius: 8px; font-size: 13px; color: var(--text-secondary); cursor: default;
  opacity: 0; transform: translateY(6px);
  transition: opacity 0.5s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + 200ms + var(--i) * 50ms),
              transform 0.6s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + 200ms + var(--i) * 50ms),
              background 0.2s, color 0.2s;
}
.hdo--in .hdo-list li { opacity: 1; transform: none; }
.hdo-list li.is-on { color: var(--text); background: color-mix(in srgb, var(--acc) 6%, transparent); }
.hdo-list li.is-on .hdo-name { font-weight: 700; }
.hdo-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hdo-bar { height: 4px; border-radius: 2px; background: color-mix(in srgb, var(--acc) 10%, transparent); overflow: hidden; }
.hdo-bar i { display: block; height: 100%; background: var(--acc); opacity: 0.25; border-radius: 2px; transition: opacity 0.2s; }
.hdo-list li.is-on .hdo-bar i { opacity: 1; }
.hdo-val { color: var(--text); font-variant-numeric: tabular-nums; }
.hdo-pct { color: var(--text-muted); font-variant-numeric: tabular-nums; text-align: left; }

@media (max-width: 560px) { .hdo-body { grid-template-columns: 1fr; } .hdo-figure { max-width: 170px; margin: 0 auto; } }
@media (prefers-reduced-motion: reduce) {
  .hdo-slice, .hdo-list li { transition: opacity 0.2s; transform: none; }
  .hdo-svg, .hdo--in .hdo-svg { --hdo-sweep: 360deg; animation: none; }
}
</style>
