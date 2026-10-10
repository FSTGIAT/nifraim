<template>
  <!-- Bars as LINES: a thin hairline track, a stroked line that draws itself in, a dot at its end,
       the number beside it. Top `limit` rows; the rest fold behind one "עוד N" line. -->
  <div class="lb" :class="{ 'lb--hovering': hovering }" @mouseleave="$emit('hover', null)">
    <button v-for="(it, i) in visible" :key="it.key" type="button" class="lb-row"
            :class="{ 'is-hot': isHot(it) }" :style="{ '--i': i }"
            @mouseenter="$emit('hover', it)" @mouseleave="$emit('hover', null)" @click="$emit('hover', null); $emit('select', it, $event.currentTarget)">
      <span class="lb-label">{{ it.label }}</span>
      <span class="lb-track" aria-hidden="true">
        <span class="lb-draw" :style="{ width: pct(it) + '%' }"></span>
        <span class="lb-dot" :style="{ insetInlineStart: pct(it) + '%' }"></span>
      </span>
      <span class="lb-num ltr-number">{{ it.value }}</span>
    </button>
    <button v-if="rest > 0" type="button" class="lb-more" @click="all = !all">
      {{ all ? 'פחות' : `עוד ${rest}` }}
      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" :style="{ transform: all ? 'rotate(180deg)' : '' }" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },   // [{ key, label, value, callIds? }]
  limit: { type: Number, default: 5 },
  hotKey: { type: String, default: null },     // the hovered row (everything else dims)
  hotCalls: { type: Object, default: null },   // a Set of call ids hovered elsewhere
})
defineEmits(['select', 'hover'])
const all = ref(false)
const visible = computed(() => (all.value ? props.items : props.items.slice(0, props.limit)))
const rest = computed(() => Math.max(0, props.items.length - props.limit))
const max = computed(() => Math.max(1, ...props.items.map((x) => x.value)))
const pct = (it) => Math.max(3, (it.value / max.value) * 100)
const hovering = computed(() => !!props.hotKey || !!props.hotCalls)
function isHot(it) {
  if (props.hotKey) return props.hotKey === it.key
  return !!props.hotCalls && (it.callIds || []).some((id) => props.hotCalls.has(id))
}
</script>

<style scoped>
.lb { --lb-label: 140px; --lb-num: 26px; display: flex; flex-direction: column; gap: 2px; }
.lb-row {
  position: relative; display: grid; grid-template-columns: var(--lb-label) 1fr var(--lb-num); align-items: center; gap: 12px;
  padding: 7px 4px; border: none; background: none; font: inherit; cursor: pointer; text-align: start; color: inherit; border-radius: 10px;
  transition: opacity 0.2s ease, background 0.2s ease;
}
.lb-row:hover, .lb-row.is-hot { background: var(--tab-insights-wash); }
.lb--hovering .lb-row:not(.is-hot) { opacity: 0.35; }
.lb-label { font-size: 14px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lb-track { position: relative; height: 10px; }
.lb-track::before { content: ''; position: absolute; inset-inline: 0; top: 50%; border-top: 1px solid rgba(24, 24, 24, 0.12); }
/* the line draws itself from the label side (RTL: right → left) */
.lb-draw {
  position: absolute; inset-inline-start: 0; top: 50%; height: 2px; margin-top: -1px; border-radius: 2px;
  background: var(--text-primary, #181818); transform-origin: right center; transform: scaleX(0);
  animation: lbDraw 1.1s cubic-bezier(0.3, 0.7, 0.2, 1) forwards; animation-delay: calc(0.15s + var(--i) * 0.09s);
}
.lb-row:first-child .lb-draw, .lb-row.is-hot .lb-draw { background: var(--tab-insights); height: 2.5px; }
.lb-dot {
  position: absolute; top: 50%; width: 8px; height: 8px; margin-top: -4px; margin-inline-start: -4px; border-radius: 50%;
  background: #fff; border: 2px solid var(--text-primary, #181818); opacity: 0;
  animation: lbDot 0.3s ease forwards; animation-delay: calc(1.05s + var(--i) * 0.09s);
}
.lb-row:first-child .lb-dot, .lb-row.is-hot .lb-dot { border-color: var(--tab-insights); }
.lb-num { font-size: 15px; font-weight: 800; text-align: center; }
.lb-row:first-child .lb-num { color: var(--tab-insights-ink); }
.lb-more {
  align-self: flex-start; display: inline-flex; align-items: center; gap: 4px; margin-top: 2px; padding: 4px 8px; border: none; background: none;
  font: inherit; font-size: 12px; font-weight: 700; color: var(--tab-insights-ink); cursor: pointer; border-radius: 8px;
}
.lb-more:hover { background: var(--tab-insights-wash); }
.lb-more svg { transition: transform 0.3s ease; }
@keyframes lbDraw { to { transform: scaleX(1); } }
@keyframes lbDot { to { opacity: 1; } }
@media (max-width: 720px) { .lb { --lb-label: 92px; } }
@media (prefers-reduced-motion: reduce) { .lb-draw { animation: none; transform: none; } .lb-dot { animation: none; opacity: 1; } }
</style>
