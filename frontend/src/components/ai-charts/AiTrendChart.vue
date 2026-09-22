<template>
  <!-- Change over time as one strip of columns (oldest → newest, left → right,
       matching every other time axis in the app). Height AND opacity scale
       with the value, so the strip reads as a texture at a glance; the
       numbers row gives the three facts that matter. -->
  <div class="aitr" :class="{ 'aitr--in': entered }">
    <p class="aitr-stats">
      <span v-for="s in stats" :key="s.k">
        {{ s.k }} <strong class="ltr-number" :class="s.cls">{{ s.v }}</strong>
      </span>
    </p>

    <div class="aitr-plot" @mouseleave="hovered = null">
      <div class="aitr-yaxis" aria-hidden="true">
        <span v-for="t in axis.ticks" :key="t" class="ltr-number" :style="{ bottom: pos(t) + '%' }">
          {{ fmtCompact(t, unit) }}
        </span>
      </div>

      <div class="aitr-area">
        <span v-for="t in axis.ticks" :key="'g' + t" class="aitr-gridline"
              :class="{ 'aitr-gridline--zero': t === 0 }" :style="{ bottom: pos(t) + '%' }" aria-hidden="true"></span>

        <div class="aitr-cols">
          <div v-for="(p, i) in points" :key="p.label + i" class="aitr-col"
               tabindex="0" role="img" :aria-label="`${p.label}: ${fmtFull(p.value, unit)}`"
               @mouseenter="hovered = i" @focus="hovered = i" @blur="hovered = null">
            <span class="aitr-bar"
                  :class="{ 'is-last': p.hi, 'is-neg': p.value < 0, 'is-dim': hovered !== null && hovered !== i }"
                  :style="{
                    bottom: (p.value < 0 ? pos(p.value) : pos(0)) + '%',
                    height: Math.max(Math.abs(pos(p.value) - pos(0)), 0.8) + '%',
                    opacity: hovered === i || p.hi ? 1 : 0.35 + 0.65 * (Math.abs(p.value) / maxAbs),
                    '--i': i,
                    '--c': p.value < 0 ? 'var(--chart-loss)' : tone.main,
                  }"></span>
            <Transition name="aitr-tip">
              <span v-if="hovered === i" class="aitr-tip"
                    :class="{ 'aitr-tip--start': i < 2, 'aitr-tip--end': i > points.length - 3 }"
                    :style="{ bottom: `calc(${Math.min(pos(Math.max(p.value, 0)), 78)}% + 8px)` }">
                <span class="aitr-tip-title">{{ p.label }}</span>
                <strong class="ltr-number">{{ fmtFull(p.value, unit) }}</strong>
                <span v-if="i > 0" class="aitr-tip-sub ltr-number">{{ deltaText(i) }}</span>
              </span>
            </Transition>
          </div>
        </div>
      </div>

      <div class="aitr-xaxis" aria-hidden="true">
        <span v-for="(p, i) in points" :key="'x' + i" :class="{ 'is-shown': showTick(i) }">{{ p.label }}</span>
      </div>
    </div>

    <p v-if="viz.insight" class="ai-chart-insight">{{ viz.insight }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { fmtFull, fmtCompact, niceTicks, prefersReducedMotion, toneFor } from './format.js'

const props = defineProps({ viz: { type: Object, required: true } })

const unit = computed(() => props.viz.unit || '')
const tone = computed(() => toneFor(props.viz.direction))
const points = computed(() => {
  const pts = (props.viz.data || [])
    .filter((d) => d && d.label != null && Number.isFinite(Number(d.value)))
    .slice(-60)
    .map((d) => ({ label: String(d.label), value: Number(d.value) }))
  const hi = props.viz.highlight_label
  return pts.map((p, i) => ({ ...p, hi: hi ? p.label === hi : i === pts.length - 1 }))
})
const vals = computed(() => points.value.map((p) => p.value))
const maxAbs = computed(() => Math.max(...vals.value.map(Math.abs), 1))
const axis = computed(() => niceTicks(Math.min(...vals.value, 0), Math.max(...vals.value, 0), 3))
function pos(v) {
  const { lo, hi } = axis.value
  return ((v - lo) / (hi - lo || 1)) * 100
}

// Label every column when few; otherwise first, last and an even spread.
function showTick(i) {
  const n = points.value.length
  if (n <= 12) return true
  const step = Math.ceil(n / 8)
  return i === 0 || i === n - 1 || (i % step === 0 && n - 1 - i >= step / 2)
}

function deltaText(i) {
  const prev = points.value[i - 1].value
  const cur = points.value[i].value
  const d = cur - prev
  const sign = d > 0 ? '+' : ''
  const pct = prev ? ` (${sign}${Math.round((d / Math.abs(prev)) * 100)}%)` : ''
  return `${sign}${fmtFull(d, unit.value)}${pct} מול הקודם`
}

const stats = computed(() => {
  const v = vals.value
  if (!v.length) return []
  const last = v[v.length - 1]
  const peakIdx = v.indexOf(Math.max(...v))
  const out = []
  if (unit.value !== '%') out.push({ k: 'סה״כ', v: fmtFull(v.reduce((a, b) => a + b, 0), unit.value) })
  out.push({ k: 'שיא', v: `${fmtFull(v[peakIdx], unit.value)} · ${points.value[peakIdx].label}` })
  out.push({ k: 'אחרון', v: fmtFull(last, unit.value) })
  if (v.length > 1 && v[v.length - 2]) {
    const ch = Math.round(((last - v[v.length - 2]) / Math.abs(v[v.length - 2])) * 100)
    out.push({ k: 'שינוי', v: `${ch > 0 ? '+' : ''}${ch}%`, cls: ch >= 0 ? 'is-up' : 'is-down' })
  }
  return out
})

const hovered = ref(null)
const entered = ref(false)
onMounted(() => {
  if (prefersReducedMotion()) { entered.value = true; return }
  requestAnimationFrame(() => requestAnimationFrame(() => { entered.value = true }))
})
</script>

<style scoped>
.aitr { width: 100%; }
.aitr-stats {
  margin: 0 0 18px;
  display: flex; flex-wrap: wrap; gap: 6px 22px;
  font-size: 12.5px; color: var(--text-muted);
}
.aitr-stats strong { color: var(--text); font-weight: 650; margin-inline-start: 4px; }
/* Direction is carried by the sign; the colour only repeats it. */
.aitr-stats strong.is-up { color: var(--green, #2E844A); }
.aitr-stats strong.is-down { color: var(--red-deep, #C23934); }

.aitr-plot {
  direction: ltr;
  display: grid;
  grid-template-columns: 52px 1fr;
  grid-template-rows: 240px auto;
  column-gap: 8px;
}
.aitr-yaxis { position: relative; font-size: 10.5px; color: var(--text-muted); }
.aitr-yaxis span { position: absolute; right: 0; transform: translateY(50%); white-space: nowrap; }

.aitr-area { position: relative; }
.aitr-gridline { position: absolute; left: 0; right: 0; height: 1px; background: var(--border-subtle); }
.aitr-gridline--zero { background: var(--border); }

.aitr-cols { position: absolute; inset: 0; display: flex; gap: 3px; }
.aitr-col { position: relative; flex: 1; min-width: 0; outline: none; }
.aitr-col:focus-visible { box-shadow: 0 0 0 2px var(--tab-ai-wash, rgba(106, 72, 201, 0.2)); border-radius: 3px; }

.aitr-bar {
  position: absolute; left: 50%; width: min(100%, 24px); transform: translateX(-50%) scaleY(0);
  transform-origin: bottom;
  border-radius: 4px 4px 0 0;
  background: linear-gradient(to top, color-mix(in srgb, var(--c) 78%, white), var(--c));
  transition:
    transform 0.8s cubic-bezier(0.2, 0.7, 0.3, 1) calc(var(--i) * 28ms),
    opacity 0.2s ease;
}
.aitr-bar.is-neg { transform-origin: top; border-radius: 0 0 4px 4px; }
.aitr--in .aitr-bar { transform: translateX(-50%) scaleY(1); }
.aitr-bar.is-dim { opacity: 0.22 !important; }

.aitr-xaxis {
  grid-column: 2; display: flex; gap: 3px; margin-top: 8px;
  font-size: 10.5px; color: var(--text-muted);
}
.aitr-xaxis span { flex: 1; min-width: 0; text-align: center; white-space: nowrap; visibility: hidden; direction: rtl; }
.aitr-xaxis span.is-shown { visibility: visible; }

.aitr-tip {
  position: absolute; left: 50%; transform: translateX(-50%);
  z-index: 3; direction: rtl;
  display: flex; flex-direction: column; gap: 1px;
  padding: 8px 11px; min-width: 120px;
  background: #1C1B1A; color: #fff; border-radius: 8px;
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.22);
  pointer-events: none; white-space: nowrap;
}
.aitr-tip--start { left: 0; transform: none; }
.aitr-tip--end { left: auto; right: 0; transform: none; }
.aitr-tip-title { font-size: 11.5px; opacity: 0.75; }
.aitr-tip strong { font-size: 15px; font-weight: 700; }
.aitr-tip-sub { font-size: 11px; opacity: 0.7; }
.aitr-tip-enter-active, .aitr-tip-leave-active { transition: opacity 0.12s; }
.aitr-tip-enter-from, .aitr-tip-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .aitr-bar { transition: opacity 0.2s; transform: translateX(-50%); }
}
</style>
