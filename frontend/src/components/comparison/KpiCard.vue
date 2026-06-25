<template>
  <article class="kpi" :class="`tone-${tone}`">
    <div class="kpi-head">
      <span class="kpi-icon" aria-hidden="true">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path :d="iconPath"/>
        </svg>
      </span>
      <span class="kpi-label">{{ label }}</span>
    </div>

    <div class="kpi-row">
      <span class="kpi-value">{{ value }}</span>
      <span v-if="delta && delta !== '—'" class="kpi-delta" :class="`dir-${direction}`">
        <svg v-if="direction === 'up'" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 15 12 9 18 15"/></svg>
        <svg v-else-if="direction === 'down'" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
        <span>{{ delta }}</span>
      </span>
    </div>

    <div v-if="sparkData && sparkData.length" class="kpi-spark">
      <apexchart
        :type="'area'"
        :height="44"
        :options="sparkOptions"
        :series="sparkSeries"
      />
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import VueApexCharts from 'vue3-apexcharts'

const apexchart = VueApexCharts

const props = defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  delta: { type: String, default: '—' },
  direction: { type: String, default: 'none' }, // 'up' | 'down' | 'flat' | 'none'
  tone: { type: String, default: 'amber' }, // 'amber' | 'emerald' | 'blue' | 'violet'
  sparkColor: { type: String, default: '#F57C00' },
  sparkData: { type: Array, default: () => [] },
  iconPath: { type: String, default: '' },
})

const sparkSeries = computed(() => [{ name: props.label, data: props.sparkData || [] }])
const sparkOptions = computed(() => ({
  chart: {
    sparkline: { enabled: true },
    animations: { enabled: false },
    toolbar: { show: false },
  },
  stroke: { curve: 'smooth', width: 2 },
  colors: [props.sparkColor],
  fill: {
    type: 'gradient',
    gradient: { shadeIntensity: 0.4, opacityFrom: 0.5, opacityTo: 0.05 },
  },
  tooltip: { enabled: false },
  grid: { padding: { top: 0, bottom: 0, left: 0, right: 0 } },
  yaxis: { show: false },
  xaxis: { show: false },
}))
</script>

<style scoped>
.kpi {
  position: relative;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 14px 14px 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.kpi:hover {
  transform: translateY(-1px);
  border-color: var(--text-muted);
  box-shadow: 0 8px 20px rgba(17, 12, 6, 0.06);
}
.kpi::before {
  content: '';
  position: absolute;
  top: 0;
  inset-inline-start: 0;
  width: 3px;
  height: 100%;
  background: var(--tone-color);
}

.tone-amber   { --tone-color: #F57C00; --tone-bg: rgba(245, 124, 0, 0.08); --tone-fg: #E65100; }
.tone-emerald { --tone-color: #2E844A; --tone-bg: rgba(46, 132, 74, 0.08); --tone-fg: #2E844A; }
.tone-blue    { --tone-color: #7F56D9; --tone-bg: rgba(127, 86, 217, 0.08); --tone-fg: #7F56D9; }
.tone-violet  { --tone-color: #E3066A; --tone-bg: rgba(227, 6, 106, 0.08); --tone-fg: #E3066A; }
.tone-red     { --tone-color: #C23934; --tone-bg: rgba(194, 57, 52, 0.08); --tone-fg: #C23934; }

.kpi-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.kpi-icon {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--tone-bg);
  color: var(--tone-fg);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.kpi-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

.kpi-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.kpi-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.4px;
  font-variant-numeric: tabular-nums;
}
.kpi-delta {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11.5px;
  font-weight: 700;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  padding: 3px 7px;
  border-radius: 999px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
}
.kpi-delta.dir-up   { color: #2E844A; background: rgba(46, 132, 74, 0.10); border-color: rgba(46, 132, 74, 0.24); }
.kpi-delta.dir-down { color: #C23934; background: rgba(194, 57, 52, 0.10); border-color: rgba(194, 57, 52, 0.24); }
.kpi-delta.dir-flat { color: var(--text-muted); }

.kpi-spark {
  margin-top: 2px;
  margin-inline: -8px;
  margin-bottom: -6px;
}
</style>
