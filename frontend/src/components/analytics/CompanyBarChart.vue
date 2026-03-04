<template>
  <div class="chart-card">
    <h3>השוואה לפי חברה</h3>
    <div v-if="data.length === 0" class="empty">אין נתונים להצגה</div>
    <apexchart
      v-else
      type="bar"
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

const series = computed(() => [
  {
    name: 'סכום / יתרה',
    data: props.data.map(d => Math.round(d.total_expected)),
  },
  {
    name: 'בפועל / עמלה',
    data: props.data.map(d => Math.round(d.total_actual)),
  },
])

const chartOptions = computed(() => ({
  chart: {
    fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
  },
  colors: ['#2563EB', 'var(--green)'],
  plotOptions: {
    bar: {
      borderRadius: 4,
      columnWidth: '60%',
      dataLabels: { position: 'top' },
    },
  },
  dataLabels: { enabled: false },
  xaxis: {
    categories: props.data.map(d => d.company),
    labels: {
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' },
      rotate: -45,
      rotateAlways: props.data.length > 5,
      trim: true,
      maxHeight: 80,
    },
  },
  yaxis: {
    opposite: true,
    labels: {
      style: { fontFamily: 'Heebo, sans-serif' },
      formatter: (val) => '₪' + val.toLocaleString('he-IL'),
    },
  },
  legend: {
    position: 'bottom',
    fontFamily: 'Heebo, sans-serif',
    fontSize: '13px',
  },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif' },
    y: {
      formatter: (val) => '₪ ' + val.toLocaleString('he-IL'),
    },
  },
  grid: {
    borderColor: '#F3F4F6',
  },
  responsive: [{
    breakpoint: 480,
    options: {
      chart: { height: 280 },
      plotOptions: { bar: { columnWidth: '80%' } },
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
