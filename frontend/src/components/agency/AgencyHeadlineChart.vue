<template>
  <div class="hl-card">
    <div class="hl-head">
      <div>
        <div class="hl-eyebrow">פרודוקציה לאורך זמן</div>
        <h2 class="hl-title">חודש מול חודש — סך הפרמיה בסוכנות</h2>
      </div>
      <div class="hl-stats" v-if="latestVsPrev">
        <div class="hl-stat">
          <div class="hl-stat-label">חודש אחרון</div>
          <div class="hl-stat-val ltr-number">{{ formatCurrency(latestVsPrev.curr) }}</div>
        </div>
        <div class="hl-stat" :class="{ up: pctChange >= 0, down: pctChange < 0 }" v-if="latestVsPrev.prev">
          <div class="hl-stat-label">שינוי</div>
          <div class="hl-stat-val ltr-number">
            <span v-if="pctChange >= 0">▲</span>
            <span v-else>▼</span>
            {{ Math.abs(pctChange).toFixed(1) }}%
          </div>
        </div>
      </div>
    </div>

    <div v-if="!hasData" class="hl-empty">
      <div class="hl-empty-art">
        <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="20" x2="18" y2="10"/>
          <line x1="12" y1="20" x2="12" y2="4"/>
          <line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
      </div>
      <p>אין עדיין נתוני פרודוקציה — העלה קבצים או הזמן סוכנים כדי לראות מגמה.</p>
    </div>

    <div v-else class="hl-chart">
      <apexchart type="area" height="280" :options="chartOptions" :series="chartSeries" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  trends: { type: Array, default: () => [] },
})

const sortedTrends = computed(() => [...props.trends].sort((a, b) => (a.period || '').localeCompare(b.period || '')))
const hasData = computed(() => sortedTrends.value.length > 0)

const chartSeries = computed(() => [{
  name: 'פרמיה',
  data: sortedTrends.value.map(t => Math.round(t.total_premium)),
}])

const chartOptions = computed(() => ({
  chart: {
    type: 'area',
    fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
    sparkline: { enabled: false },
    animations: { enabled: true, easing: 'easeOutCubic', speed: 700 },
  },
  colors: ['#E8660A'],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 3 },
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.45,
      opacityTo: 0.05,
      stops: [0, 95, 100],
      colorStops: [
        { offset: 0, color: '#FF9800', opacity: 0.45 },
        { offset: 100, color: '#FFB74D', opacity: 0.02 },
      ],
    },
  },
  markers: {
    size: 5,
    colors: ['#fff'],
    strokeColors: '#E8660A',
    strokeWidth: 2.5,
    hover: { size: 7 },
  },
  grid: {
    borderColor: 'rgba(45, 37, 34, 0.08)',
    strokeDashArray: 4,
    padding: { left: 8, right: 8, top: 0, bottom: 0 },
  },
  xaxis: {
    categories: sortedTrends.value.map(t => t.period),
    labels: { style: { fontSize: '11px', colors: 'rgba(45, 37, 34, 0.55)' } },
    axisTicks: { show: false },
    axisBorder: { show: false },
  },
  yaxis: {
    labels: {
      style: { fontSize: '11px', colors: 'rgba(45, 37, 34, 0.55)' },
      formatter: (v) => '₪' + Math.round(Number(v) / 1000) + 'K',
    },
  },
  tooltip: {
    theme: 'light',
    y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') },
  },
}))

const latestVsPrev = computed(() => {
  const arr = sortedTrends.value
  if (!arr.length) return null
  return {
    curr: arr[arr.length - 1].total_premium,
    prev: arr.length >= 2 ? arr[arr.length - 2].total_premium : null,
  }
})
const pctChange = computed(() => {
  const v = latestVsPrev.value
  if (!v?.prev) return 0
  return ((v.curr - v.prev) / v.prev) * 100
})

function formatCurrency(v) {
  if (v == null) return '—'
  return '₪ ' + Math.round(Number(v)).toLocaleString('he-IL')
}
</script>

<style scoped>
.hl-card {
  background: #FFFFFF;
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 18px;
  padding: 22px 24px;
  box-shadow: 0 12px 40px -20px rgba(45, 37, 34, 0.18);
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}
.hl-card::before {
  content: ''; position: absolute; inset: 0 0 auto 0; height: 4px;
  background: linear-gradient(90deg, #E8660A 0%, #FFB74D 50%, #E8660A 100%);
}
.hl-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 18px; margin-bottom: 14px;
}
.hl-eyebrow {
  font-size: 11px; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase;
  color: #C85A00;
  margin-bottom: 4px;
}
.hl-title { font-size: 18px; font-weight: 800; color: #2D2522; letter-spacing: -0.3px; }
.hl-stats { display: flex; gap: 18px; }
.hl-stat { text-align: left; }
.hl-stat-label { font-size: 11px; color: rgba(45, 37, 34, 0.55); font-weight: 600; }
.hl-stat-val { font-size: 18px; font-weight: 800; color: #2D2522; margin-top: 2px; }
.hl-stat.up .hl-stat-val { color: #2E844A; }
.hl-stat.down .hl-stat-val { color: #8C1D2A; }

.hl-empty {
  text-align: center; padding: 60px 20px; color: rgba(45, 37, 34, 0.55);
}
.hl-empty-art { color: rgba(232, 102, 10, 0.35); margin-bottom: 14px; }

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }
</style>
