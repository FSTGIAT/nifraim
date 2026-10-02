<template>
  <!-- Hover-trace bar chart — the agent's chosen style (ported from the React
       "hover trace" component to Vue, RTL): ink columns, every column at 20%
       except the traced one, a dashed level line that springs to the traced
       value with a value pill, and a big spring-animated readout on top.
       At rest it traces the leader; hovering moves the trace. -->
  <div class="htb" :class="{ 'htb--in': entered }">
    <header class="htb-head">
      <div class="htb-read">
        <span class="htb-k">[{{ metric }}]</span>
        <strong class="htb-v ltr-number">{{ fmtFull(springVal, unit) }}</strong>
      </div>
      <div class="htb-side">
        <span class="htb-k">[{{ hovered !== null ? 'נבחר' : 'המוביל' }}]</span>
        <span class="htb-label">{{ traced?.label }}</span>
        <span v-if="showShare && traced" class="htb-share ltr-number">{{ fmtPct(Math.abs(traced.value), total) }} מהסך</span>
      </div>
    </header>

    <div class="htb-plot" @mouseleave="hovered = null">
      <!-- the trace: dashed level, pill at the start (right, RTL), dot at the end -->
      <div v-if="traced && entered" class="htb-line" :style="{ bottom: springPos + '%' }" aria-hidden="true">
        <b class="htb-pill ltr-number">{{ fmtFull(traced.value, unit) }}</b>
        <i class="htb-dot"></i>
      </div>

      <div class="htb-cols">
        <div v-for="(r, i) in rows" :key="r.label + i" class="htb-col"
             tabindex="0" role="img" :aria-label="`${r.label}: ${fmtFull(r.value, unit)}`"
             @mouseenter="hovered = i" @focus="hovered = i" @blur="hovered = null">
          <span class="htb-bar"
                :class="{ 'is-on': tracedIdx === i, 'is-hover': hovered === i }"
                :style="{ height: Math.max(r.h, 0.8) + '%', '--i': i }"></span>
        </div>
      </div>
    </div>

    <div class="htb-x" aria-hidden="true">
      <span v-for="(r, i) in rows" :key="'x' + i" :class="{ 'is-on': tracedIdx === i }" :title="r.label">{{ short(r.label) }}</span>
    </div>

    <p v-if="viz.insight" class="ai-chart-insight">{{ viz.insight }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { fmtFull, fmtPct, prefersReducedMotion } from './format.js'
import { useSpring } from '../../composables/useSpring.js'

const props = defineProps({ viz: { type: Object, required: true } })

const unit = computed(() => props.viz.unit || '')
const metric = computed(() => props.viz.yLabel || props.viz.title || 'ערך')
const raw = computed(() =>
  (props.viz.data || [])
    .filter((d) => d && d.label != null && Number.isFinite(Number(d.value)))
    .slice(0, 16)
    .map((d) => ({ label: String(d.label), value: Number(d.value), id: d.id })),
)
// Columns plot magnitude from one baseline; the sign stays on the value.
const maxAbs = computed(() => Math.max(...raw.value.map((d) => Math.abs(d.value)), 1))
const rows = computed(() => raw.value.map((d) => ({ ...d, h: (Math.abs(d.value) / maxAbs.value) * 100 })))

const total = computed(() => raw.value.reduce((s, d) => s + Math.abs(d.value), 0))
const showShare = computed(() => unit.value !== '%' && raw.value.length > 1)

const hovered = ref(null)
const leaderIdx = computed(() => {
  const hi = props.viz.highlight_label
  const i = hi ? rows.value.findIndex((r) => r.label === hi) : -1
  if (i >= 0) return i
  let best = 0
  rows.value.forEach((r, j) => { if (Math.abs(r.value) > Math.abs(rows.value[best].value)) best = j })
  return best
})
const tracedIdx = computed(() => (hovered.value !== null ? hovered.value : leaderIdx.value))
const traced = computed(() => rows.value[tracedIdx.value] || null)
// same spring as the original component (stiffness 110, damping 20)
const springVal = useSpring(() => traced.value?.value ?? 0, { stiffness: 110, damping: 20 })
const springPos = useSpring(() => traced.value?.h ?? 0, { stiffness: 110, damping: 20 })

// the original slices labels to 3 letters; Hebrew names need a little more
const short = (s) => (s.length > 9 ? s.slice(0, 8) + '…' : s)

const entered = ref(false)
onMounted(() => {
  if (prefersReducedMotion()) { entered.value = true; return }
  requestAnimationFrame(() => requestAnimationFrame(() => { entered.value = true }))
})
</script>

<style scoped>
.htb { width: 100%; --ink: var(--primary, #181818); }

.htb-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin: 0 0 18px; }
.htb-read, .htb-side { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.htb-side { align-items: flex-end; text-align: left; }
.htb-k { font-size: 11px; color: var(--text-muted); letter-spacing: 0.01em; }
.htb-v {
  font-size: 34px; font-weight: 800; letter-spacing: -0.035em; line-height: 1;
  color: var(--ink); font-variant-numeric: tabular-nums;
}
.htb-label { font-size: 13px; font-weight: 700; color: var(--ink); max-width: 260px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.htb-share { font-size: 11.5px; color: var(--text-muted); }

.htb-plot { position: relative; height: 240px; }
.htb-cols { position: absolute; inset: 0; display: flex; align-items: flex-end; gap: 8px; }
.htb-col { position: relative; flex: 1; min-width: 0; height: 100%; display: flex; align-items: flex-end; justify-content: center; outline: none; cursor: default; }
.htb-col:focus-visible .htb-bar { box-shadow: 0 0 0 2px var(--border); }

.htb-bar {
  width: min(100%, 46px); border-radius: 4px;
  background: var(--ink); opacity: 0.2;
  transform: scaleY(0); transform-origin: bottom;
  transition:
    transform 1s var(--ease-silk, cubic-bezier(0.32, 0.72, 0, 1)) calc(var(--silk-content-delay, 280ms) + var(--i) * var(--silk-stagger, 40ms)),
    opacity 0.2s ease, box-shadow 0.2s ease;
}
.htb--in .htb-bar { transform: scaleY(1); }
.htb-bar.is-on { opacity: 1; }
.htb-bar.is-hover { box-shadow: 0 0 0 1px rgba(24, 24, 24, 0.35); }

/* the dashed level line + value pill (RTL: pill at the start/right, dot at the end) */
.htb-line {
  position: absolute; left: 0; right: 0; height: 0; z-index: 2; pointer-events: none;
  border-top: 1.5px dashed var(--ink);
  animation: htbIn .5s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + 650ms) both;
}
.htb-pill {
  position: absolute; right: 0; top: -10px;
  padding: 0 7px; border-radius: 4px; line-height: 18px;
  background: var(--ink); color: #fff; font-size: 11px; font-weight: 600; font-variant-numeric: tabular-nums;
}
.htb-dot { position: absolute; left: -3px; top: -4px; width: 7px; height: 7px; border-radius: 50%; background: var(--ink); }
@keyframes htbIn { from { opacity: 0; } to { opacity: 1; } }

.htb-x { display: flex; gap: 8px; margin-top: 10px; }
.htb-x span {
  flex: 1; min-width: 0; text-align: center; font-size: 11.5px; color: var(--text-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: color 0.2s;
}
.htb-x span.is-on { color: var(--ink); font-weight: 700; }

@media (prefers-reduced-motion: reduce) {
  .htb-bar { transition: opacity 0.2s; transform: none; }
  .htb-line { animation: none; }
}
@media (max-width: 560px) {
  .htb-v { font-size: 26px; }
  .htb-plot { height: 200px; }
  .htb-cols, .htb-x { gap: 4px; }
}
</style>
