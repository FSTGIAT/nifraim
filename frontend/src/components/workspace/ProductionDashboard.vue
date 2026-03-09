<template>
  <div class="prod-dashboard">
    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card kpi-blue">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ analytics.total_records.toLocaleString() }}</div>
          <div class="kpi-label">רשומות</div>
        </div>
      </div>

      <div class="kpi-card kpi-cyan">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87"/>
            <path d="M16 3.13a4 4 0 010 7.75"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ analytics.unique_clients.toLocaleString() }}</div>
          <div class="kpi-label">לקוחות</div>
        </div>
      </div>

      <div class="kpi-card kpi-green" :title="'₪' + Math.round(analytics.total_premium).toLocaleString()">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="1" x2="12" y2="23"/>
            <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ formatAmount(analytics.total_premium) }}</div>
          <div class="kpi-label">סה"כ פרמיה</div>
        </div>
      </div>

      <div class="kpi-card kpi-amber" :title="'₪' + Math.round(analytics.total_accumulation).toLocaleString()">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
            <line x1="1" y1="10" x2="23" y2="10"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ formatAmount(analytics.total_accumulation) }}</div>
          <div class="kpi-label">סה"כ צבירה</div>
        </div>
      </div>

      <div class="kpi-card kpi-violet">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ analytics.companies_count }}</div>
          <div class="kpi-label">חברות</div>
        </div>
      </div>

      <div class="kpi-card kpi-emerald">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ activePercent }}%</div>
          <div class="kpi-label">מוצרים פעילים</div>
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-row">
      <!-- Company Breakdown -->
      <div class="chart-card" v-if="analytics.company_breakdown.length">
        <div class="chart-header">
          <h3>התפלגות לפי חברה</h3>
        </div>
        <apexchart
          type="bar"
          :height="companyChartHeight"
          :options="companyChartOptions"
          :series="companyChartSeries"
        />
      </div>

      <!-- Product Type Bar -->
      <div class="chart-card" v-if="analytics.product_type_breakdown.length">
        <div class="chart-header">
          <h3>התפלגות לפי סוג מוצר</h3>
        </div>
        <apexchart
          type="bar"
          :height="productChartHeight"
          :options="productBarOptions"
          :series="productBarSeries"
        />
      </div>
    </div>

    <!-- Status Donut -->
    <div class="chart-card chart-narrow" v-if="analytics.status_breakdown.length">
      <div class="chart-header">
        <h3>סטטוס מוצרים</h3>
      </div>
      <apexchart
        type="donut"
        :height="280"
        :options="statusDonutOptions"
        :series="statusDonutSeries"
      />
    </div>

    <!-- Top Clients -->
    <div class="chart-card wide-card" v-if="topClientsData.length">
      <div class="chart-header">
        <h3>{{ topMetric === 'premium' ? 'לקוחות לפי פרמיה' : 'לקוחות לפי צבירה' }}</h3>
        <div class="chart-actions">
          <button class="toggle-btn" :class="{ active: topMetric === 'premium' }" @click="topMetric = 'premium'">פרמיה</button>
          <button class="toggle-btn" :class="{ active: topMetric === 'accumulation' }" @click="topMetric = 'accumulation'">צבירה</button>
        </div>
      </div>
      <apexchart
        type="bar"
        :height="320"
        :options="topClientsChartOptions"
        :series="topClientsChartSeries"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  analytics: { type: Object, required: true },
})

const topMetric = ref('premium')

function formatAmount(val) {
  if (!val || val === 0) return '₪0'
  const abs = Math.abs(val)
  if (abs >= 1_000_000) return '₪' + (val / 1_000_000).toFixed(1) + 'M'
  if (abs >= 10_000) return '₪' + Math.round(val / 1000).toLocaleString() + 'K'
  return '₪' + Math.round(val).toLocaleString()
}

const activePercent = computed(() => {
  const statuses = props.analytics.status_breakdown
  if (!statuses.length) return 0
  const total = statuses.reduce((s, r) => s + r.count, 0)
  const active = statuses.find(s => s.status === 'פעיל')
  if (!active || !total) return 0
  return Math.round((active.count / total) * 100)
})

// Company chart
const companyChartHeight = computed(() => Math.max(250, props.analytics.company_breakdown.length * 40))

const companyChartOptions = computed(() => ({
  chart: { type: 'bar', toolbar: { show: false }, fontFamily: 'Heebo, sans-serif' },
  plotOptions: { bar: { horizontal: true, borderRadius: 6, barHeight: '60%' } },
  dataLabels: { enabled: false },
  xaxis: {
    categories: props.analytics.company_breakdown.map(c => c.company),
    labels: { style: { fontFamily: 'Heebo, sans-serif' } },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif' } } },
  colors: ['#4f6bed'],
  tooltip: {
    y: { formatter: v => v.toLocaleString() + ' רשומות' },
  },
  grid: { borderColor: 'var(--border-subtle)' },
}))

const companyChartSeries = computed(() => [{
  name: 'רשומות',
  data: props.analytics.company_breakdown.map(c => c.count),
}])

// Product type bar
const productChartHeight = computed(() => Math.max(250, props.analytics.product_type_breakdown.length * 40))

const productBarOptions = computed(() => ({
  chart: { type: 'bar', toolbar: { show: false }, fontFamily: 'Heebo, sans-serif' },
  plotOptions: { bar: { horizontal: true, borderRadius: 6, barHeight: '60%' } },
  dataLabels: { enabled: false },
  xaxis: {
    categories: props.analytics.product_type_breakdown.map(p => p.product_type),
    labels: { style: { fontFamily: 'Heebo, sans-serif' } },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' } } },
  colors: ['#7f56d9'],
  tooltip: {
    y: { formatter: v => v.toLocaleString() + ' רשומות' },
  },
  grid: { borderColor: 'var(--border-subtle)' },
}))

const productBarSeries = computed(() => [{
  name: 'רשומות',
  data: props.analytics.product_type_breakdown.map(p => p.count),
}])

// Status donut
const statusColors = { 'פעיל': '#10b981', 'לא פעיל': '#ef4444', 'מוקפא': '#f59e0b', 'מבוטל': '#94a3b8' }

const statusDonutOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif' },
  labels: props.analytics.status_breakdown.map(s => s.status),
  colors: props.analytics.status_breakdown.map(s => statusColors[s.status] || '#94a3b8'),
  legend: { position: 'bottom', fontFamily: 'Heebo, sans-serif', fontSize: '12px' },
  dataLabels: { enabled: true, formatter: (val) => Math.round(val) + '%' },
}))

const statusDonutSeries = computed(() =>
  props.analytics.status_breakdown.map(s => s.count)
)

// Top clients chart
const topClientsData = computed(() =>
  topMetric.value === 'premium'
    ? props.analytics.top_clients_premium.filter(c => c.premium > 0)
    : props.analytics.top_clients_accumulation.filter(c => c.accumulation > 0)
)

const topClientsChartOptions = computed(() => ({
  chart: { type: 'bar', toolbar: { show: false }, fontFamily: 'Heebo, sans-serif' },
  plotOptions: { bar: { horizontal: true, borderRadius: 6, barHeight: '65%' } },
  dataLabels: { enabled: false },
  xaxis: {
    categories: topClientsData.value.map(c => c.name || c.id_number),
    labels: {
      style: { fontFamily: 'Heebo, sans-serif' },
      formatter: v => '₪' + Math.round(v).toLocaleString(),
    },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' } } },
  colors: [topMetric.value === 'premium' ? '#10b981' : '#f59e0b'],
  tooltip: {
    y: { formatter: v => '₪' + Math.round(v).toLocaleString() },
  },
  grid: { borderColor: 'var(--border-subtle)' },
}))

const topClientsChartSeries = computed(() => [{
  name: topMetric.value === 'premium' ? 'פרמיה' : 'צבירה',
  data: topClientsData.value.map(c => topMetric.value === 'premium' ? c.premium : c.accumulation),
}])
</script>

<style scoped>
.prod-dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: slideUp 0.4s var(--transition);
}

/* KPI Row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(155px, 1fr));
  gap: 12px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  transition: all 0.25s var(--transition);
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.06);
}

.kpi-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-blue .kpi-icon { background: var(--primary-light); color: var(--primary); }
.kpi-cyan .kpi-icon { background: rgba(34, 211, 238, 0.1); color: #22d3ee; }
.kpi-green .kpi-icon { background: var(--green-light); color: var(--accent-emerald); }
.kpi-amber .kpi-icon { background: var(--amber-light); color: var(--amber); }
.kpi-violet .kpi-icon { background: rgba(127, 86, 217, 0.1); color: var(--accent-violet); }
.kpi-emerald .kpi-icon { background: rgba(16, 185, 129, 0.1); color: #10b981; }

.kpi-data { min-width: 0; }

.kpi-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.2;
}

.kpi-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* Charts */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 800px) {
  .charts-row { grid-template-columns: 1fr; }
}

.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px;
}

.chart-narrow {
  max-width: 420px;
}

.wide-card {
  width: 100%;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.chart-header h3 {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.chart-actions {
  display: flex;
  gap: 4px;
}

.toggle-btn {
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  font-family: inherit;
  background: var(--border-subtle);
  color: var(--text-muted);
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn.active {
  background: var(--primary-light);
  color: var(--primary);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
