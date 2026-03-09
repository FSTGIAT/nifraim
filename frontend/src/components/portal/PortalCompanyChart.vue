<template>
  <div class="chart-card">
    <h3>התפלגות לפי חברה</h3>
    <div v-if="breakdown.length" class="chart-container" ref="chartContainer"></div>
    <p v-else class="empty">אין נתונים</p>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'

const props = defineProps({
  breakdown: Array,
})

const chartContainer = ref(null)
let chart = null

const colors = ['#F57C00', '#7F56D9', '#2E844A', '#E3066A', '#0EA5E9', '#E8720A', '#6366F1', '#14B8A6']

async function renderChart() {
  if (!chartContainer.value || !props.breakdown?.length) return

  const ApexCharts = (await import('apexcharts')).default

  if (chart) chart.destroy()

  const labels = props.breakdown.map(b => b.company)
  const series = props.breakdown.map(b => b.premium)

  chart = new ApexCharts(chartContainer.value, {
    chart: {
      type: 'donut',
      height: 280,
      fontFamily: 'Heebo, sans-serif',
    },
    series,
    labels,
    colors: colors.slice(0, labels.length),
    legend: {
      position: 'bottom',
      fontSize: '12px',
      fontWeight: 600,
      labels: { colors: '#706E6B' },
      markers: { width: 10, height: 10, radius: 3 },
    },
    dataLabels: {
      enabled: true,
      formatter: (val) => `${val.toFixed(0)}%`,
      style: { fontSize: '12px', fontWeight: 700 },
    },
    plotOptions: {
      pie: {
        donut: {
          size: '55%',
          labels: {
            show: true,
            total: {
              show: true,
              label: 'סה"כ פרמיה',
              fontSize: '12px',
              color: '#706E6B',
              formatter: (w) => {
                const total = w.globals.seriesTotals.reduce((a, b) => a + b, 0)
                return new Intl.NumberFormat('he-IL', { style: 'currency', currency: 'ILS', maximumFractionDigits: 0 }).format(total)
              },
            },
          },
        },
      },
    },
    tooltip: {
      y: {
        formatter: (val) => new Intl.NumberFormat('he-IL', { style: 'currency', currency: 'ILS', maximumFractionDigits: 0 }).format(val),
      },
    },
  })
  chart.render()
}

onMounted(() => {
  nextTick(renderChart)
})

watch(() => props.breakdown, () => {
  nextTick(renderChart)
}, { deep: true })
</script>

<style scoped>
.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px 20px;
}

h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 8px;
}

.chart-container { min-height: 280px; }

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 40px 0;
  font-size: 14px;
}
</style>
