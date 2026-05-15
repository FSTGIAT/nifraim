<template>
  <article class="ic-card">
    <header class="ic-head">
      <div class="ic-titles">
        <h4 class="ic-title">{{ title }}</h4>
        <p class="ic-sub">{{ subtitle }}</p>
      </div>
      <span v-if="totalLabel" class="ic-total">{{ totalLabel }}</span>
    </header>

    <div class="ic-chart">
      <div v-if="!hasData" class="ic-empty">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <line x1="12" y1="20" x2="12" y2="10"/>
          <line x1="18" y1="20" x2="18" y2="4"/>
          <line x1="6" y1="20" x2="6" y2="16"/>
        </svg>
        <p>אין נתונים זמינים עדיין</p>
      </div>
      <apexchart
        v-else
        :type="'bar'"
        :height="chartHeight"
        :options="chartOptions"
        :series="chartSeries"
        @dataPointSelection="onBarClick"
      />
    </div>

    <footer class="ic-footer">
      <button v-if="hasData" type="button" class="ic-cta" @click="emit('open-all')">
        ראה הכל ({{ items.length }})
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M19 12H5M12 5l-7 7 7 7"/>
        </svg>
      </button>
    </footer>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import VueApexCharts from 'vue3-apexcharts'
import { shortShekel } from '../../utils/monthDeltas.js'

const apexchart = VueApexCharts

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  totalLabel: { type: String, default: '' },
  // items: [{ label: string, amount: number, meta: string }]
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['select', 'open-all'])

const ORANGE_SHADES = ['#C2410C', '#DD6B20', '#ED7D2D', '#F57C00', '#FF8E26', '#FF9F40', '#FFB266', '#FFC68C']

const hasData = computed(() => props.items.length > 0)
const chartHeight = computed(() => Math.max(220, 50 + props.items.length * 38))

const chartSeries = computed(() => [{
  name: 'סך חיוב פתוח',
  data: props.items.map((c) => Number(c.amount || 0)),
}])

function truncateHe(text, max = 22) {
  if (!text) return ''
  const s = String(text)
  if (s.length <= max) return s
  return s.slice(0, max - 1) + '…'
}

const chartOptions = computed(() => ({
  chart: {
    type: 'bar',
    toolbar: { show: false },
    fontFamily: 'inherit',
    animations: { enabled: true, easing: 'easeout', speed: 600 },
    events: {
      // capture clicks on the bar AND on the row label area
      dataPointSelection: (_, __, ctx) => {
        const idx = ctx?.dataPointIndex
        if (idx != null && idx >= 0) emit('select', props.items[idx])
      },
    },
  },
  plotOptions: {
    bar: {
      horizontal: true,
      barHeight: '58%',
      borderRadius: 6,
      borderRadiusApplication: 'end',
      distributed: true,
      dataLabels: { position: 'top' },
    },
  },
  colors: ORANGE_SHADES.slice(0, props.items.length),
  dataLabels: {
    enabled: true,
    formatter: (val) => shortShekel(val),
    offsetX: 8,
    style: {
      fontFamily: 'Heebo, sans-serif',
      fontSize: '11.5px',
      fontWeight: 700,
      colors: ['#1f1b16'],
    },
  },
  xaxis: {
    categories: props.items.map((c) => truncateHe(c.label, 24)),
    labels: { show: false },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: {
    labels: {
      maxWidth: 160,
      style: {
        fontFamily: 'Heebo, sans-serif',
        fontSize: '13px',
        fontWeight: 700,
        colors: '#1f1b16',
      },
    },
  },
  grid: {
    show: true,
    borderColor: 'rgba(0,0,0,0.04)',
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: true } },
    padding: { left: 0, right: 80, top: 0, bottom: 0 },
  },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif', fontSize: '12px' },
    custom({ seriesIndex, dataPointIndex, w }) {
      const item = props.items[dataPointIndex] || {}
      const value = w.config.series[seriesIndex].data[dataPointIndex]
      return `
        <div style="padding:8px 10px;font-family:Heebo,sans-serif;direction:rtl">
          <div style="font-weight:700;margin-bottom:4px;color:#1f1b16">${item.label || ''}</div>
          <div style="font-family:ui-monospace,Menlo,monospace;color:#c2410c;font-weight:700">${shortShekel(value)}</div>
          ${item.meta ? `<div style="font-size:11px;color:#6b7280;margin-top:2px">${item.meta}</div>` : ''}
        </div>`
    },
  },
  legend: { show: false },
  states: {
    hover: { filter: { type: 'lighten', value: 0.06 } },
    active: { filter: { type: 'darken', value: 0.08 } },
  },
}))

function onBarClick(_, __, opts) {
  const idx = opts?.dataPointIndex
  if (idx != null && idx >= 0) emit('select', props.items[idx])
}
</script>

<style scoped>
.ic-card {
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  box-shadow:
    0 1px 0 rgba(17, 12, 6, 0.02),
    0 8px 22px rgba(17, 12, 6, 0.04),
    0 24px 60px rgba(17, 12, 6, 0.05);
  padding: 18px 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  overflow: hidden;
  font-family: 'Heebo', sans-serif;
}
.ic-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: linear-gradient(90deg, transparent 0%, #F57C00 50%, transparent 100%);
}

.ic-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}
.ic-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.ic-title { margin: 0; font-size: 16px; font-weight: 800; color: var(--text); letter-spacing: -0.2px; }
.ic-sub { margin: 0; font-size: 12px; color: var(--text-muted); }
.ic-total {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: var(--primary-deep, #c2410c);
  background: rgba(245, 124, 0, 0.08);
  border: 1px solid rgba(245, 124, 0, 0.22);
  padding: 3px 10px;
  border-radius: 999px;
  flex-shrink: 0;
}

.ic-chart {
  position: relative;
  margin: 0 -4px;
  cursor: pointer;
}
.ic-empty {
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted);
}
.ic-empty p { margin: 0; font-size: 13px; }

.ic-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
  border-top: 1px solid var(--border-subtle);
}
.ic-cta {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: transparent;
  border: none;
  color: var(--primary-deep, #c2410c);
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}
.ic-cta:hover { background: rgba(245, 124, 0, 0.08); }
</style>
