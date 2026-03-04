<template>
  <div class="chart-card">
    <h3>מוצרים מובילים</h3>
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

const sorted = computed(() => [...props.data].reverse())

const series = computed(() => [{
  name: 'סכום צפוי',
  data: sorted.value.map(d => Math.round(d.total_amount)),
}])

const chartOptions = computed(() => ({
  chart: {
    fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
  },
  colors: ['#8B5CF6'],
  plotOptions: {
    bar: {
      horizontal: true,
      borderRadius: 4,
      barHeight: '65%',
      distributed: false,
    },
  },
  dataLabels: {
    enabled: true,
    formatter: (val) => '₪' + val.toLocaleString('he-IL'),
    style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', fontWeight: 500 },
    offsetX: 4,
  },
  xaxis: {
    categories: sorted.value.map(d => d.product),
    labels: {
      style: { fontFamily: 'Heebo, sans-serif' },
      formatter: (val) => '₪' + Number(val).toLocaleString('he-IL'),
    },
  },
  yaxis: {
    opposite: true,
    labels: {
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '12px' },
      maxWidth: 200,
    },
  },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif' },
    y: {
      formatter: (val) => '₪ ' + val.toLocaleString('he-IL'),
    },
  },
  grid: {
    borderColor: '#F3F4F6',
    xaxis: { lines: { show: true } },
    yaxis: { lines: { show: false } },
  },
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
