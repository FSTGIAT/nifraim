<template>
  <!-- The portal wheel — the tab's own world (gears): a toothed ring, one logo
       node per company sitting on the rim, evenly spaced so it scales to any
       count. Each node owns an arc of the ring coloured by its health. The
       centre is the big "X/Y תקינים" and the last run. Idle, the gear turns
       very slowly; a node lifts on hover with a small tooltip; a click turns
       the wheel (spring) until that company is on top, then the list scrolls
       to it. -->
  <div ref="rootEl" class="pw" :style="{ '--sz': size + 'px' }" @mouseleave="hover = null">
    <svg class="pw-svg" :viewBox="`0 0 ${size} ${size}`" aria-hidden="true">
      <g :style="{ transform: `rotate(${rot}deg)`, transformOrigin: '50% 50%' }">
        <!-- the gear: teeth around the outside -->
        <path class="pw-teeth" :d="teethPath" />
        <circle class="pw-ring-track" :cx="c" :cy="c" :r="R" />
        <!-- one arc per company, coloured by its health -->
        <path v-for="(n, i) in nodes" :key="'a' + n.key" class="pw-arc" :class="'pw-arc--' + n.tone"
              pathLength="1" :d="arcPath(i)" :style="{ animationDelay: (i * 40) + 'ms' }" />
        <circle class="pw-hub" :cx="c" :cy="c" :r="R * 0.56" />
      </g>
    </svg>

    <!-- logo nodes ride the rim but stay upright -->
    <button v-for="(n, i) in nodes" :key="n.key" type="button" class="pw-node"
            :class="['pw-node--' + n.tone, { 'is-hover': hover === i }]"
            :style="nodeStyle(i)" :aria-label="`${n.label}: ${n.ok} מתוך ${n.total} תקינים`"
            @mouseenter="hover = i" @focus="hover = i" @blur="hover = null" @click="select(i)">
      <CompanyLogo :company="n.label" :size="logoSize" :frame="false" />
    </button>

    <!-- centre -->
    <div class="pw-center">
      <span class="pw-num ltr-number">{{ healthy }}<span class="pw-den">/{{ total }}</span></span>
      <span class="pw-lbl">תקינים</span>
      <span v-if="lastRunLabel" class="pw-last">ריצה אחרונה {{ lastRunLabel }}</span>
    </div>

    <!-- tooltip -->
    <Transition name="pw-tip">
      <div v-if="hover !== null && nodes[hover]" class="pw-tip" :style="tipStyle" role="tooltip">
        <strong>{{ nodes[hover].label }}</strong>
        <span class="pw-tip-row">
          <i v-for="(d, k) in nodes[hover].dots" :key="k" :class="'pw-dot pw-dot--' + d"></i>
          <span class="ltr-number">{{ nodes[hover].ok }}/{{ nodes[hover].total }}</span>
        </span>
        <span v-if="nodes[hover].lastRunAt" class="pw-tip-when">{{ rel(nodes[hover].lastRunAt) }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import CompanyLogo from './CompanyLogo.vue'
import { relativeHebrew } from '../../utils/relativeTime.js'

const props = defineProps({
  companies: { type: Array, default: () => [] }, // [{key,label,ok,total,dots,lastRunAt}]
  lastRunAt: { type: String, default: null },
  size: { type: Number, default: 264 },
})
const emit = defineEmits(['select'])

const c = computed(() => props.size / 2)
const R = computed(() => props.size * 0.36)
const n = computed(() => Math.max(1, props.companies.length))
// nodes shrink as the count grows so they stay evenly spaced on the rim
const nodeSize = computed(() => Math.round(Math.max(22, Math.min(46, ((2 * Math.PI * R.value) / n.value) * 0.62))))
const logoSize = computed(() => Math.round(nodeSize.value * 0.5))

const nodes = computed(() => props.companies.map((co) => {
  const tone = !co.total || co.dots.every((d) => d === 'none') ? 'none'
    : co.ok === co.total ? 'ok'
    : co.ok === 0 ? 'fail'
    : 'partial'
  return { ...co, tone }
}))
const healthy = computed(() => props.companies.reduce((s, co) => s + co.ok, 0))
const total = computed(() => props.companies.reduce((s, co) => s + co.total, 0))
const rel = (iso) => (iso ? relativeHebrew(iso) : '')
const lastRunLabel = computed(() => rel(props.lastRunAt))

// node i sits at angle -90° + i·step (the first company starts at the top)
const step = computed(() => 360 / n.value)
const baseAngle = (i) => -90 + i * step.value

// ── rotation: a very slow idle turn, a spring when a node is chosen ──
const rot = ref(0)
const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const hover = ref(null)
let raf = 0
let last = 0
let target = null
let vel = 0
function tick(t) {
  const dt = Math.min(0.05, (t - (last || t)) / 1000)
  last = t
  if (target !== null) {
    // critically-damped-ish spring toward the chosen angle
    const force = (target - rot.value) * 90 - vel * 16
    vel += force * dt
    rot.value += vel * dt
    if (Math.abs(target - rot.value) < 0.05 && Math.abs(vel) < 0.05) { rot.value = target; target = null; vel = 0 }
  } else if (hover.value === null && !reduced) {
    rot.value += dt * 1.6 // ~4 minutes per turn
  }
  raf = requestAnimationFrame(tick)
}
onMounted(() => { raf = requestAnimationFrame(tick) })
onBeforeUnmount(() => cancelAnimationFrame(raf))

function select(i) {
  // bring node i to the top (-90°): rot + base(i) ≡ -90 → rot = -i·step, nearest turn
  const want = -i * step.value
  const k = Math.round((rot.value - want) / 360)
  const dest = want + k * 360
  if (reduced) rot.value = dest
  else target = dest
  setTimeout(() => emit('select', props.companies[i]), reduced ? 0 : 520)
}

function polar(angleDeg, radius) {
  const a = (angleDeg * Math.PI) / 180
  return [c.value + Math.cos(a) * radius, c.value + Math.sin(a) * radius]
}
function nodeStyle(i) {
  const [x, y] = polar(baseAngle(i) + rot.value, R.value)
  const s = nodeSize.value
  return { width: s + 'px', height: s + 'px', left: (x - s / 2) + 'px', top: (y - s / 2) + 'px', '--d': (i * 45) + 'ms' }
}
const tipStyle = computed(() => {
  const i = hover.value
  const [x, y] = polar(baseAngle(i) + rot.value, R.value)
  const below = y < c.value // nodes in the upper half show the tip below them
  return { left: x + 'px', top: (below ? y + nodeSize.value / 2 + 8 : y - nodeSize.value / 2 - 8) + 'px', transform: `translate(-50%, ${below ? '0' : '-100%'})` }
})

// each node's arc on the ring: centred on the node, with a small gap
function arcPath(i) {
  const half = step.value / 2 - Math.min(6, step.value * 0.12)
  const a0 = baseAngle(i) - half
  const a1 = baseAngle(i) + half
  const [x0, y0] = polar(a0, R.value)
  const [x1, y1] = polar(a1, R.value)
  const large = a1 - a0 > 180 ? 1 : 0
  return `M${x0.toFixed(2)} ${y0.toFixed(2)} A${R.value} ${R.value} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`
}
// gear teeth around the outside of the ring
const teethPath = computed(() => {
  const teeth = 36
  const r0 = R.value + 16
  const r1 = R.value + 22
  let d = ''
  for (let k = 0; k < teeth; k++) {
    const a = (k / teeth) * 360
    const w = (360 / teeth) * 0.28
    const p = [polar(a - w, r0), polar(a - w * 0.6, r1), polar(a + w * 0.6, r1), polar(a + w, r0)]
    d += `M${p[0][0].toFixed(1)} ${p[0][1].toFixed(1)}L${p[1][0].toFixed(1)} ${p[1][1].toFixed(1)}L${p[2][0].toFixed(1)} ${p[2][1].toFixed(1)}L${p[3][0].toFixed(1)} ${p[3][1].toFixed(1)}`
  }
  return d
})
</script>

<style scoped>
.pw { --acc: var(--tab-automation, #0E8C8A); position: relative; width: var(--sz); height: var(--sz); margin: 0 auto; }
.pw-svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
.pw-teeth { fill: none; stroke: color-mix(in srgb, var(--text) 16%, transparent); stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.pw-ring-track { fill: none; stroke: color-mix(in srgb, var(--text) 7%, transparent); stroke-width: 10; }
.pw-arc { fill: none; stroke-width: 10; stroke-linecap: round; stroke-dasharray: 1; stroke-dashoffset: 1; animation: pwDraw 0.8s cubic-bezier(0.32, 0.72, 0, 1) forwards; }
.pw-arc--ok { stroke: var(--acc); }
.pw-arc--partial { stroke: var(--amber); }
.pw-arc--fail { stroke: var(--red); }
.pw-arc--none { stroke: color-mix(in srgb, var(--text) 18%, transparent); }
@keyframes pwDraw { to { stroke-dashoffset: 0; } }
.pw-hub { fill: var(--card-bg); stroke: color-mix(in srgb, var(--text) 8%, transparent); stroke-width: 1; stroke-dasharray: 2 5; }

.pw-node {
  position: absolute; display: grid; place-items: center; padding: 0; border-radius: 50%; cursor: pointer;
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  box-shadow: 0 2px 8px rgba(24, 24, 24, 0.10);
  transition: transform 0.25s cubic-bezier(0.34, 1.6, 0.5, 1), box-shadow 0.2s ease;
  animation: pwIn 0.5s cubic-bezier(0.34, 1.5, 0.5, 1) var(--d) both;
}
.pw-node--fail { box-shadow: 0 2px 8px rgba(24, 24, 24, 0.10), 0 0 0 2px rgba(234, 0, 30, 0.25); }
.pw-node--partial { box-shadow: 0 2px 8px rgba(24, 24, 24, 0.10), 0 0 0 2px color-mix(in srgb, var(--amber) 35%, transparent); }
.pw-node.is-hover { transform: translateY(-4px) scale(1.15); box-shadow: 0 10px 22px rgba(24, 24, 24, 0.18); z-index: 2; }
.pw-node:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
@keyframes pwIn { from { transform: scale(0.4); opacity: 0; } to { transform: none; opacity: 1; } }

.pw-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; pointer-events: none; }
.pw-num { font-size: 40px; font-weight: 900; letter-spacing: -0.04em; line-height: 1; color: var(--text); }
.pw-den { font-size: 20px; font-weight: 700; color: var(--text-muted); }
.pw-lbl { margin-top: 2px; font-size: 13px; font-weight: 600; color: var(--text-muted); }
.pw-last { margin-top: 6px; font-size: 11.5px; color: var(--text-muted); }

.pw-tip {
  position: absolute; z-index: 5; pointer-events: none; display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 8px 12px; border-radius: 12px; background: #181818; color: #fff; white-space: nowrap;
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.25); font-size: 12px;
}
.pw-tip strong { font-size: 13.5px; font-weight: 800; }
.pw-tip-row { display: inline-flex; align-items: center; gap: 4px; }
.pw-tip-row span { margin-inline-start: 4px; color: rgba(255, 255, 255, 0.7); }
.pw-tip-when { color: rgba(255, 255, 255, 0.6); }
.pw-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255, 255, 255, 0.25); }
.pw-dot--ok { background: #5BC48A; }
.pw-dot--fail { background: #FF6B7A; }
.pw-dot--live { background: #6FD3CF; }
.pw-tip-enter-active, .pw-tip-leave-active { transition: opacity 0.15s ease; }
.pw-tip-enter-from, .pw-tip-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .pw-arc, .pw-node { animation: none; stroke-dashoffset: 0; }
  .pw-node { transition: none; }
}
</style>
