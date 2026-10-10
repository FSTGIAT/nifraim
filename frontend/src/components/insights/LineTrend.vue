<template>
  <!-- Calls per week as ONE line that draws itself, dots on the weeks, the last week's number at its end. -->
  <div class="lt">
    <svg class="lt-svg" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" aria-hidden="true">
      <line v-for="g in 3" :key="g" x1="0" :x2="W" :y1="(H - 22) * (g / 3) + 4" :y2="(H - 22) * (g / 3) + 4" class="lt-grid" />
      <path :d="area" class="lt-area" />
      <path :d="line" class="lt-line" />
    </svg>
    <div class="lt-dots" aria-hidden="true">
      <span v-for="(p, i) in pts" :key="i" class="lt-dot" :class="{ 'is-last': i === pts.length - 1 }"
            :style="{ left: (p.x / W) * 100 + '%', top: (p.y / H) * 100 + '%', '--i': i }" :title="`${p.label}: ${p.v}`"></span>
    </div>
    <div class="lt-axis">
      <span v-for="(p, i) in pts" :key="i" class="ltr-number" :style="{ left: (p.x / W) * 100 + '%' }">{{ p.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ points: { type: Array, default: () => [] } })   // [{ label, value }] oldest → newest
const W = 300
const H = 96
const pts = computed(() => {
  const n = props.points.length
  const max = Math.max(1, ...props.points.map((p) => p.value))
  // Hebrew reads right → left: the oldest week sits on the right, this week on the left
  return props.points.map((p, i) => ({
    x: n > 1 ? W - 8 - ((W - 16) * i) / (n - 1) : W / 2,
    y: 4 + (H - 26) * (1 - p.value / max),
    v: p.value, label: p.label,
  }))
})
function smooth(ps) {
  if (!ps.length) return ''
  let d = `M ${ps[0].x} ${ps[0].y}`
  for (let i = 1; i < ps.length; i++) {
    const a = ps[i - 1], b = ps[i]
    const mx = (a.x + b.x) / 2
    d += ` C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`
  }
  return d
}
const line = computed(() => smooth(pts.value))
const area = computed(() => {
  const ps = pts.value
  if (ps.length < 2) return ''
  return `${smooth(ps)} L ${ps[ps.length - 1].x} ${H - 22} L ${ps[0].x} ${H - 22} Z`
})
</script>

<style scoped>
.lt { position: relative; height: 118px; }
.lt-svg { position: absolute; inset: 0 0 18px 0; width: 100%; height: 100px; overflow: visible; }
.lt-grid { stroke: rgba(24, 24, 24, 0.07); stroke-width: 1; vector-effect: non-scaling-stroke; stroke-dasharray: 2 4; }
.lt-area { fill: var(--tab-insights-wash); opacity: 0; animation: ltFade 0.8s ease 1.1s forwards; }
.lt-line {
  fill: none; stroke: var(--tab-insights); stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke;
  /* drawn by a wipe from the oldest week (right) — a dash trick breaks on a stretched viewBox */
  clip-path: inset(-10px -10px -10px 100%); animation: ltDraw 1.6s cubic-bezier(0.3, 0.7, 0.2, 1) 0.2s forwards;
}
.lt-dots { position: absolute; inset: 0 0 18px 0; height: 100px; pointer-events: none; }
.lt-dot {
  position: absolute; width: 7px; height: 7px; margin: -3.5px 0 0 -3.5px; border-radius: 50%; background: #fff;
  border: 1.6px solid var(--text-primary, #181818); opacity: 0; pointer-events: auto;
  animation: ltFade 0.3s ease forwards; animation-delay: calc(0.3s + var(--i) * 0.15s);
}
.lt-dot.is-last { width: 9px; height: 9px; margin: -4.5px 0 0 -4.5px; border-color: var(--tab-insights); border-width: 2px; }
.lt-axis { position: absolute; left: 0; right: 0; bottom: 0; height: 16px; }
.lt-axis span { position: absolute; transform: translateX(-50%); font-size: 10px; color: var(--text-secondary, #5C5C5C); white-space: nowrap; }
@keyframes ltDraw { to { clip-path: inset(-10px -10px -10px -10px); } }
@keyframes ltFade { to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .lt-line { animation: none; clip-path: none; } .lt-area, .lt-dot { animation: none; opacity: 1; } }
</style>
