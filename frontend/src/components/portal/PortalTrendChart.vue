<template>
  <div v-if="snapshots.length >= 2" class="trend-chart-card">
    <div class="chart-header">
      <div class="chart-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      </div>
      <h3>מגמות לאורך זמן</h3>
    </div>
    <apexchart
      type="area"
      height="260"
      :options="chartOptions"
      :series="series"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  snapshots: { type: Array, default: () => [] },
})

const sortedSnapshots = computed(() =>
  [...props.snapshots].reverse()
)

const series = computed(() => [
  {
    name: 'פרמיה',
    data: sortedSnapshots.value.map(s => s.kpi?.total_premium ?? 0),
  },
  {
    name: 'צבירה',
    data: sortedSnapshots.value.map(s => s.kpi?.total_accumulation ?? 0),
  },
])

const chartOptions = computed(() => ({
  chart: {
    fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: {
      enabled: true,
      easing: 'easeinout',
      speed: 600,
    },
  },
  colors: ['var(--primary, #E8660A)', '#A8703A'],
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.35,
      opacityTo: 0.05,
      stops: [0, 100],
    },
  },
  stroke: {
    curve: 'smooth',
    width: 2.5,
  },
  dataLabels: { enabled: false },
  xaxis: {
    categories: sortedSnapshots.value.map(s => s.period_label || ''),
    labels: {
      style: {
        fontFamily: 'Heebo, sans-serif',
        fontSize: '11px',
        colors: 'var(--text-muted, #94a3b8)',
      },
    },
  },
  yaxis: {
    labels: {
      formatter: (val) => `₪${val.toLocaleString('he-IL', { maximumFractionDigits: 0 })}`,
      style: {
        fontFamily: 'Heebo, sans-serif',
        fontSize: '11px',
        colors: 'var(--text-muted, #94a3b8)',
      },
    },
  },
  tooltip: {
    y: {
      formatter: (val) => `₪${val.toLocaleString('he-IL', { maximumFractionDigits: 0 })}`,
    },
  },
  legend: {
    position: 'top',
    horizontalAlign: 'right',
    fontFamily: 'Heebo, sans-serif',
    fontSize: '12px',
    labels: { colors: 'var(--text-secondary, #64748b)' },
  },
  grid: {
    borderColor: 'var(--border-subtle, #e2e8f0)',
    strokeDashArray: 3,
  },
}))
</script>

<style scoped>
.trend-chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: 20px;
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.chart-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--primary-light);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.chart-header h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}
</style>
