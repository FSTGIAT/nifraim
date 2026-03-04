<template>
  <div class="chart-card">
    <h3>התפלגות סטטוסים</h3>
    <div v-if="data.length === 0" class="empty">אין נתונים להצגה</div>
    <apexchart
      v-else
      type="donut"
      :height="320"
      :options="chartOptions"
      :series="series"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const statusColors = {
  paid_match: 'var(--green)',
  paid_mismatch: '#F59E0B',
  unpaid: 'var(--red)',
  cancelled: '#8B5CF6',
  no_data: '#6B7280',
  matched: '#2563EB',
  missing_from_report: '#EA580C',
  extra_in_report: '#7C3AED',
}

const series = computed(() => props.data.map(d => d.count))

const chartOptions = computed(() => ({
  labels: props.data.map(d => d.status_label),
  colors: props.data.map(d => statusColors[d.status] || '#6B7280'),
  chart: {
    fontFamily: 'Heebo, sans-serif',
  },
  legend: {
    position: 'bottom',
    fontFamily: 'Heebo, sans-serif',
    fontSize: '13px',
  },
  dataLabels: {
    enabled: true,
    formatter: (val) => val.toFixed(1) + '%',
    style: { fontFamily: 'Heebo, sans-serif', fontWeight: 600 },
  },
  plotOptions: {
    pie: {
      donut: {
        size: '55%',
        labels: {
          show: true,
          total: {
            show: true,
            label: 'סה"כ',
            fontFamily: 'Heebo, sans-serif',
            fontSize: '16px',
            fontWeight: 700,
          },
        },
      },
    },
  },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif' },
    y: {
      formatter: (val) => val + ' רשומות',
    },
  },
  responsive: [{
    breakpoint: 480,
    options: {
      chart: { height: 280 },
      legend: { position: 'bottom' },
    },
  }],
}))
</script>

<style scoped>
.chart-card {
  background: white;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text);
}

.empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 48px 16px;
  font-size: 14px;
}
</style>
