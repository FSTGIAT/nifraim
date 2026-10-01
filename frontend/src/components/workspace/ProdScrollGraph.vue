<template>
  <!-- Bottom-of-page finale (QA 2026-09-30): reaching the end of the
       Production tab draws a quiet growth chart BEHIND the cards — bars rise
       in a stagger, then a trend line draws itself across them and a dot
       rides to its end. Pure decoration: tab cobalt, faint (fill ≤ 0.1,
       stroke ≤ 0.35 per nifraim-style), pointer-events off, and it leaves
       again when the agent scrolls back up. -->
  <div ref="sentinel" class="psg-sentinel" aria-hidden="true"></div>
  <div class="psg" :class="{ 'psg--on': on }" :style="color ? { color } : null" aria-hidden="true">
    <svg class="psg-svg" viewBox="0 0 1200 320" preserveAspectRatio="none">
      <defs>
        <linearGradient id="psgBar" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="currentColor" stop-opacity="0.16" />
          <stop offset="100%" stop-color="currentColor" stop-opacity="0.02" />
        </linearGradient>
        <linearGradient id="psgArea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="currentColor" stop-opacity="0.10" />
          <stop offset="100%" stop-color="currentColor" stop-opacity="0" />
        </linearGradient>
      </defs>
      <!-- baseline grid -->
      <line v-for="g in 3" :key="'g' + g" x1="0" x2="1200" :y1="320 - g * 80" :y2="320 - g * 80"
            class="psg-grid" />
      <!-- bars -->
      <rect v-for="(b, i) in bars" :key="'b' + i" class="psg-bar"
            :x="b.x" :y="320 - b.h" :width="b.w" :height="b.h" rx="6"
            fill="url(#psgBar)" :style="{ '--i': i }" />
      <!-- trend area + line -->
      <path class="psg-area" :d="areaPath" fill="url(#psgArea)" />
      <path class="psg-line" :d="linePath" pathLength="1" />
      <circle class="psg-dot" :cx="last.x" :cy="last.y" r="7" />
      <circle class="psg-dot-halo" :cx="last.x" :cy="last.y" r="7" />
    </svg>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

// The owning tab's colour (default: Production cobalt via CSS). The comparison
// tab passes var(--tab-comparison).
defineProps({ color: { type: String, default: '' } })

// A fixed, gently rising shape — decoration, not data (numbers live in the
// cards above; a real series here would invite reading it as one).
const N = 12
const heights = [0.30, 0.38, 0.34, 0.46, 0.43, 0.55, 0.52, 0.63, 0.60, 0.71, 0.76, 0.86]
const slot = 1200 / N
const bars = heights.map((h, i) => ({ x: i * slot + slot * 0.22, w: slot * 0.56, h: h * 250 }))
const pts = heights.map((h, i) => ({ x: i * slot + slot / 2, y: 320 - h * 250 - 26 }))
const last = pts[pts.length - 1]

// Smooth curve through the points (Catmull-Rom → cubic Bézier).
function smooth(p) {
  let d = `M ${p[0].x} ${p[0].y}`
  for (let i = 0; i < p.length - 1; i++) {
    const p0 = p[i - 1] || p[i], p1 = p[i], p2 = p[i + 1], p3 = p[i + 2] || p2
    const c1x = p1.x + (p2.x - p0.x) / 6, c1y = p1.y + (p2.y - p0.y) / 6
    const c2x = p2.x - (p3.x - p1.x) / 6, c2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`
  }
  return d
}
const linePath = smooth(pts)
const areaPath = `${linePath} L ${last.x} 320 L ${pts[0].x} 320 Z`

const sentinel = ref(null)
const on = ref(false)
let io = null
onMounted(() => {
  if (typeof IntersectionObserver === 'undefined' || !sentinel.value) return
  // On when the page's end is on screen; off again once it scrolls away.
  io = new IntersectionObserver(([e]) => { on.value = e.isIntersecting }, { rootMargin: '0px 0px 40px 0px' })
  io.observe(sentinel.value)
})
onBeforeUnmount(() => io?.disconnect())
</script>

<style scoped>
.psg-sentinel { height: 1px; margin-top: -1px; }

/* Behind the cards: a negative z-index inside the dashboard's stacking
   context paints above the page but below every card. Fixed to the viewport
   bottom, so it rises from the edge the agent just scrolled to. */
.psg {
  position: fixed; inset-inline: 0; bottom: 0; height: min(42vh, 360px);
  z-index: -1; pointer-events: none; color: var(--tab-production);
  opacity: 0; transition: opacity 0.6s ease;
}
.psg--on { opacity: 1; }
.psg-svg { width: 100%; height: 100%; display: block; }

.psg-grid { stroke: currentColor; stroke-opacity: 0.08; stroke-width: 1; stroke-dasharray: 4 8; }

.psg-bar {
  transform-box: fill-box; transform-origin: bottom;
  transform: scaleY(0);
  transition: transform 0.9s cubic-bezier(0.32, 0.72, 0, 1);
  transition-delay: calc(var(--i) * 60ms);
}
.psg--on .psg-bar { transform: scaleY(1); }

.psg-area { opacity: 0; transition: opacity 0.8s ease 0.9s; }
.psg--on .psg-area { opacity: 1; }

.psg-line {
  fill: none; stroke: currentColor; stroke-opacity: 0.32; stroke-width: 3;
  stroke-linecap: round; stroke-linejoin: round;
  stroke-dasharray: 1; stroke-dashoffset: 1;
  vector-effect: non-scaling-stroke;
  transition: stroke-dashoffset 1.6s cubic-bezier(0.45, 0, 0.2, 1) 0.5s;
}
.psg--on .psg-line { stroke-dashoffset: 0; }

.psg-dot { fill: currentColor; fill-opacity: 0.35; opacity: 0; transition: opacity 0.3s ease 2.05s; }
.psg--on .psg-dot { opacity: 1; }
.psg-dot-halo { fill: none; stroke: currentColor; stroke-opacity: 0.25; stroke-width: 2; opacity: 0;
  transform-box: fill-box; transform-origin: center; }
.psg--on .psg-dot-halo { animation: psgHalo 2.4s ease-out 2.1s infinite; }
@keyframes psgHalo {
  0% { opacity: 0.8; transform: scale(1); }
  100% { opacity: 0; transform: scale(3.2); }
}

@media (prefers-reduced-motion: reduce) {
  .psg, .psg-bar, .psg-area, .psg-line, .psg-dot { transition: none; }
  .psg--on .psg-dot-halo { animation: none; }
}
</style>
