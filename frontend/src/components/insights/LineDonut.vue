<template>
  <!-- A donut as LINES: thin stroked arcs with gaps, drawn in one after the other; the big number in
       the middle; one short word per arc beside it. -->
  <div class="ld">
    <svg class="ld-svg" viewBox="0 0 120 120" aria-hidden="true">
      <circle cx="60" cy="60" r="46" class="ld-track" />
      <circle v-for="(a, i) in arcs" :key="a.key" cx="60" cy="60" r="46" class="ld-arc" :class="{ 'is-hot': hot === a.key, 'is-main': i === 0 }"
              :style="{ '--len': a.len, '--off': a.off, '--i': i }" pathLength="100"
              @mouseenter="hot = a.key" @mouseleave="hot = null" @click="$emit('select', a, $event.currentTarget)" />
      <text x="60" y="60" class="ld-big">{{ lead.pct }}%</text>
      <text x="60" y="77" class="ld-small">{{ lead.label }}</text>
    </svg>
    <ul class="ld-legend">
      <li v-for="(a, i) in arcs" :key="a.key" :class="{ 'is-hot': hot === a.key, 'is-main': i === 0 }"
          @mouseenter="hot = a.key" @mouseleave="hot = null">
        <button type="button" @click="$emit('select', a, $event.currentTarget)">
          <span class="ld-mark" aria-hidden="true"></span>{{ a.label }} <b class="ltr-number">{{ a.value }}</b>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },   // [{ key, label, value }]
})
defineEmits(['select'])
const hot = ref(null)
const total = computed(() => props.items.reduce((s, x) => s + x.value, 0))
const lead = computed(() => {   // the centre names the biggest arc as a share — never a second "total" to reconcile
  const a = arcs.value.find((x) => x.key === hot.value) || arcs.value[0]
  return a ? { pct: Math.round((a.value / Math.max(1, total.value)) * 100), label: a.label } : { pct: 0, label: '' }
})
const GAP = 2.2
const arcs = computed(() => {
  let off = 0
  const list = props.items.filter((x) => x.value > 0).sort((a, b) => b.value - a.value)
  return list.map((x) => {
    const share = (x.value / Math.max(1, total.value)) * 100
    const a = { ...x, len: Math.max(0.6, share - (list.length > 1 ? GAP : 0)), off }
    off += share
    return a
  })
})
</script>

<style scoped>
.ld { display: flex; align-items: center; gap: 18px; }
.ld-svg { width: 132px; height: 132px; flex-shrink: 0; transform: rotate(-90deg); overflow: visible; }
.ld-track { fill: none; stroke: rgba(24, 24, 24, 0.07); stroke-width: 1; }
.ld-arc {
  fill: none; stroke: var(--text-primary, #181818); stroke-width: 2; stroke-linecap: round; cursor: pointer;
  stroke-dasharray: 0 100; stroke-dashoffset: calc(var(--off) * -1);
  animation: ldDraw 1s cubic-bezier(0.3, 0.7, 0.2, 1) forwards; animation-delay: calc(0.2s + var(--i) * 0.25s);
  transition: stroke-width 0.2s ease;
}
.ld-arc.is-main { stroke: var(--tab-insights); }
.ld-arc.is-hot { stroke-width: 4; }
.ld-big, .ld-small { transform: rotate(90deg); transform-origin: 60px 60px; text-anchor: middle; font-family: 'Heebo', sans-serif; }
.ld-big { font-size: 24px; font-weight: 800; fill: var(--text-primary, #181818); }
.ld-small { font-size: 10px; fill: var(--text-secondary, #5C5C5C); }
.ld-legend { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ld-legend button { display: flex; align-items: center; gap: 8px; padding: 4px 6px; border: none; background: none; font: inherit; font-size: 13px; cursor: pointer; border-radius: 8px; color: inherit; transition: background 0.2s; }
.ld-legend li.is-hot button { background: var(--tab-insights-wash); }
.ld-legend b { font-weight: 800; }
.ld-mark { width: 14px; height: 0; border-top: 2px solid var(--text-primary, #181818); border-radius: 2px; }
.ld-legend li.is-main .ld-mark { border-color: var(--tab-insights); }
@keyframes ldDraw { from { stroke-dasharray: 0 100; } to { stroke-dasharray: var(--len) 100; } }
@media (prefers-reduced-motion: reduce) { .ld-arc { animation: none; stroke-dasharray: var(--len) 100; } }
</style>
