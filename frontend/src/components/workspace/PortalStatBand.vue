<template>
  <div class="cockpit">
    <span class="cockpit-orb" aria-hidden="true"></span>

    <!-- Section 1 — health gauge -->
    <div class="gauge">
      <svg viewBox="0 0 84 84" class="gauge-svg" aria-hidden="true">
        <defs>
          <linearGradient id="pg-ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#5B6EE1" />
            <stop offset="0.5" stop-color="#4E9DD0" />
            <stop offset="1" stop-color="#1FA88C" />
          </linearGradient>
        </defs>
        <circle cx="42" cy="42" r="35" fill="none" stroke="#E9ECF4" stroke-width="7" />
        <circle
          class="gauge-fill"
          cx="42" cy="42" r="35" fill="none"
          stroke="url(#pg-ring)" stroke-width="7" stroke-linecap="round"
          :stroke-dasharray="C" :stroke-dashoffset="ringOffset"
          transform="rotate(-90 42 42)"
        />
      </svg>
      <div class="gauge-center">
        <span class="gauge-num ltr-number">{{ healthyShown }}<span class="gauge-den">/{{ total }}</span></span>
        <span class="gauge-lbl">תקינים</span>
      </div>
    </div>

    <span class="cockpit-sep" aria-hidden="true"></span>

    <!-- Section 2 — stat tiles -->
    <div class="tiles">
      <div v-for="t in tiles" :key="t.key" class="tile">
        <span class="tile-ico" :style="{ background: t.soft, color: t.deep }" v-html="t.icon"></span>
        <div class="tile-body">
          <span class="tile-val ltr-number" :style="t.valueColor ? { color: t.valueColor } : null">{{ t.display }}</span>
          <span class="tile-lbl">{{ t.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { relativeHebrew } from '../../utils/relativeTime.js'

const store = usePortalAutomationStore()

const ICONS = {
  active: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h8l-1 8 10-12h-8l1-8z"/></svg>',
  total: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 17.5 9 5 9-5"/></svg>',
  last: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7.5V12l3 2"/></svg>',
}
const HUE = {
  indigo: { soft: '#EEF0FE', deep: '#3A4BC0' },
  blue: { soft: '#E7F2FA', deep: '#2C6E9E' },
  purple: { soft: '#EFEAFA', deep: '#5F429F' },
}
const STATUS_INK = { green: '#0E7A64', amber: '#9A6B12', red: '#C23934' }

const total = computed(() => store.credentials.length)
const active = computed(() => store.credentials.filter((c) => c.is_active).length)
const healthy = computed(() => store.credentials.filter((c) => c.last_run_status === 'success').length)

const lastRun = computed(() => {
  const b = store.latestBatch
  if (!b) return { value: '—', tone: null }
  const when = b.finished_at || b.started_at
  const txt = when ? relativeHebrew(when) : '—'
  const tone = b.status === 'failed' ? 'red' : b.status === 'partial' ? 'amber' : 'green'
  return { value: txt, tone }
})

// ── Count-up (client rAF; small easing entrance) ──
let rafs = []
function useCountUp(source) {
  const shown = ref(0)
  watch(source, (to) => {
    if (typeof to !== 'number') { shown.value = to; return }
    const from = typeof shown.value === 'number' ? shown.value : 0
    if (from === to) { shown.value = to; return }
    const start = performance.now(), dur = 650
    const step = (t) => {
      const p = Math.min(1, (t - start) / dur)
      const e = 1 - Math.pow(1 - p, 3)
      shown.value = Math.round(from + (to - from) * e)
      if (p < 1) rafs.push(requestAnimationFrame(step))
    }
    rafs.push(requestAnimationFrame(step))
  }, { immediate: true })
  return shown
}
const totalShown = useCountUp(total)
const activeShown = useCountUp(active)
const healthyShown = useCountUp(healthy)

// ── Ring draw ──
const C = +(2 * Math.PI * 35).toFixed(2)
const ringOffset = ref(C)
onMounted(() => {
  rafs.push(requestAnimationFrame(() => {
    const pct = total.value ? healthy.value / total.value : 0
    ringOffset.value = +(C * (1 - pct)).toFixed(2)
  }))
})
watch([healthy, total], () => {
  const pct = total.value ? healthy.value / total.value : 0
  ringOffset.value = +(C * (1 - pct)).toFixed(2)
})
onBeforeUnmount(() => rafs.forEach(cancelAnimationFrame))

const tiles = computed(() => [
  { key: 'total', label: 'סה״כ פורטלים', display: totalShown.value, icon: ICONS.total, ...HUE.indigo },
  { key: 'active', label: 'פעילים', display: activeShown.value, icon: ICONS.active, ...HUE.blue },
  { key: 'last', label: 'ריצה אחרונה', display: lastRun.value.value, icon: ICONS.last, ...HUE.purple, valueColor: STATUS_INK[lastRun.value.tone] || null },
])
</script>

<style scoped>
.cockpit {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 18px 22px;
  border-radius: 18px;
  border: 1px solid rgba(91, 110, 225, 0.12);
  background:
    radial-gradient(120% 160% at 0% 0%, rgba(31, 168, 140, 0.06) 0%, transparent 55%),
    linear-gradient(135deg, #FBFBFE 0%, #F5F8FD 100%);
  box-shadow: 0 10px 28px rgba(46, 60, 130, 0.06);
  flex-wrap: wrap;
}
.cockpit-orb {
  position: absolute;
  top: -60%; inset-inline-start: -6%;
  width: 40%; height: 200%;
  background: radial-gradient(circle, rgba(91, 110, 225, 0.08), transparent 68%);
  pointer-events: none;
}

/* ── Gauge ── */
.gauge { position: relative; flex-shrink: 0; width: 92px; height: 92px; }
.gauge-svg { width: 92px; height: 92px; display: block; }
.gauge-fill { transition: stroke-dashoffset 1s cubic-bezier(0.22, 1, 0.36, 1); }
.gauge-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;
}
.gauge-num { font-size: 21px; font-weight: 800; color: #181818; letter-spacing: -0.5px; line-height: 1; }
.gauge-den { font-size: 13px; font-weight: 700; color: rgba(24, 24, 24, 0.4); }
.gauge-lbl { font-size: 10.5px; font-weight: 700; color: var(--text-muted); }

.cockpit-sep { width: 1px; align-self: stretch; margin: 6px 0; background: linear-gradient(180deg, transparent, rgba(24,24,24,0.1), transparent); }

/* ── Stat tiles ── */
.tiles {
  position: relative;
  flex: 1; min-width: 220px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}
.tile {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(24, 24, 24, 0.05);
}
.tile-ico { flex-shrink: 0; width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; }
.tile-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.tile-val { font-size: 21px; font-weight: 800; color: #181818; letter-spacing: -0.5px; line-height: 1.05; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tile-lbl { font-size: 11.5px; font-weight: 700; color: var(--text-muted); }

@media (prefers-reduced-motion: reduce) {
  .gauge-fill { transition: none; }
}
@media (max-width: 560px) {
  .cockpit-sep { display: none; }
  .gauge { margin: 0 auto; }
}
</style>
