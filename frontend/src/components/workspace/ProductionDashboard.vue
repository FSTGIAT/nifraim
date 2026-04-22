<template>
  <div class="prod-dashboard">
    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card kpi-blue clickable" @click="openDrilldown('products')">
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
          <div class="kpi-label">מוצרים</div>
        </div>
      </div>

      <div class="kpi-card kpi-cyan clickable" @click="openDrilldown('clients')">
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

      <div class="kpi-card kpi-amber clickable" :title="'₪' + Math.round(analytics.total_accumulation).toLocaleString()" @click="openDrilldown('accumulation')">
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

      <div class="kpi-card kpi-violet clickable" @click="openDrilldown('companies')">
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

      <div class="kpi-card kpi-emerald clickable" @click="openDrilldown('status')">
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

    <!-- Row 1: Company + Product Type side by side -->
    <div class="charts-row">
      <div class="chart-card" v-if="analytics.company_breakdown.length">
        <div class="chart-header">
          <h3>התפלגות לפי חברה</h3>
        </div>
        <apexchart
          type="bar"
          :height="chartsRowHeight"
          :options="companyChartOptions"
          :series="companyChartSeries"
        />
      </div>

      <div class="chart-card" v-if="analytics.product_type_breakdown.length">
        <div class="chart-header">
          <h3>התפלגות לפי סוג מוצר</h3>
        </div>
        <apexchart
          type="bar"
          :height="chartsRowHeight"
          :options="productBarOptions"
          :series="productBarSeries"
        />
      </div>
    </div>

    <!-- Row 3: Top Clients (full width) -->
    <div class="chart-card" v-if="topClientsData.length">
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
    <!-- KPI Drill-down Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="drilldown" class="dd-overlay" @click.self="drilldown = null">
          <div class="dd-card">
            <div class="dd-header">
              <h4>{{ drilldownTitle }}</h4>
              <div class="dd-header-right">
                <span class="dd-count ltr-number">{{ filteredDrillData.length }} שורות</span>
                <button class="dd-close" @click="drilldown = null">&times;</button>
              </div>
            </div>
            <div class="dd-search">
              <input v-model="ddSearch" type="text" placeholder="חיפוש..." class="dd-search-input" />
            </div>
            <div class="dd-scroll">
              <div v-if="clientsLoading" class="dd-loading">
                <div class="loader"><div class="loader-ring"></div></div>
                <span>טוען נתונים...</span>
              </div>
              <table v-else class="dd-table">
                <thead>
                  <tr>
                    <template v-if="drilldown === 'companies'">
                      <th>חברה</th>
                      <th class="th-num">לקוחות</th>
                      <th class="th-num">מוצרים</th>
                      <th class="th-num">פרמיה</th>
                      <th class="th-num">צבירה</th>
                    </template>
                    <template v-else-if="drilldown === 'status'">
                      <th>סטטוס</th>
                      <th class="th-num">מוצרים</th>
                      <th class="th-num">אחוז</th>
                    </template>
                    <template v-else-if="drilldown === 'products'">
                      <th>סוג מוצר</th>
                      <th class="th-num">כמות</th>
                      <th class="th-num">פרמיה</th>
                    </template>
                    <template v-else>
                      <th>שם</th>
                      <th>ת.ז</th>
                      <th class="th-num">מוצרים</th>
                      <th class="th-num">{{ drilldown === 'accumulation' ? 'צבירה' : 'פרמיה' }}</th>
                    </template>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, i) in filteredDrillData" :key="i">
                    <template v-if="drilldown === 'companies'">
                      <td>{{ row.company }}</td>
                      <td class="td-num"><span class="ltr-number">{{ row.unique_clients?.toLocaleString() }}</span></td>
                      <td class="td-num"><span class="ltr-number">{{ row.count?.toLocaleString() }}</span></td>
                      <td class="td-num"><span class="ltr-number">{{ formatAmount(row.premium) }}</span></td>
                      <td class="td-num"><span class="ltr-number">{{ formatAmount(row.accumulation) }}</span></td>
                    </template>
                    <template v-else-if="drilldown === 'status'">
                      <td>{{ row.status }}</td>
                      <td class="td-num"><span class="ltr-number">{{ row.count?.toLocaleString() }}</span></td>
                      <td class="td-num"><span class="ltr-number">{{ row.pct }}%</span></td>
                    </template>
                    <template v-else-if="drilldown === 'products'">
                      <td>{{ row.product_type }}</td>
                      <td class="td-num"><span class="ltr-number">{{ row.count?.toLocaleString() }}</span></td>
                      <td class="td-num"><span class="ltr-number">{{ formatAmount(row.premium) }}</span></td>
                    </template>
                    <template v-else>
                      <td>{{ row.name }}</td>
                      <td><span class="ltr-number">{{ row.id_number }}</span></td>
                      <td class="td-num"><span class="ltr-number">{{ row.products }}</span></td>
                      <td class="td-num"><span class="ltr-number">{{ formatAmount(drilldown === 'accumulation' ? row.accumulation : row.premium) }}</span></td>
                    </template>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import api from '../../api/client.js'

const props = defineProps({
  analytics: { type: Object, required: true },
})

const topMetric = ref('premium')
const drilldown = ref(null)
const ddSearch = ref('')
const clientsData = ref([])
const clientsLoading = ref(false)

const drilldownTitle = computed(() => {
  const titles = {
    products: 'פירוט מוצרים לפי סוג',
    clients: 'רשימת לקוחות',
    premium: 'לקוחות לפי פרמיה',
    accumulation: 'לקוחות לפי צבירה',
    companies: 'פירוט לפי חברה',
    status: 'פירוט לפי סטטוס',
  }
  return titles[drilldown.value] || ''
})

const drilldownData = computed(() => {
  if (!drilldown.value) return []
  const a = props.analytics

  if (drilldown.value === 'companies') {
    return a.company_breakdown || []
  }
  if (drilldown.value === 'status') {
    const total = a.status_breakdown.reduce((s, r) => s + r.count, 0)
    return a.status_breakdown.map(r => ({
      ...r,
      pct: total ? Math.round((r.count / total) * 100) : 0,
    }))
  }
  if (drilldown.value === 'products') {
    return a.product_type_breakdown || []
  }
  // clients, premium, accumulation → fetched from API
  return clientsData.value
})

const filteredDrillData = computed(() => {
  const q = ddSearch.value.toLowerCase()
  if (!q) return drilldownData.value
  return drilldownData.value.filter(r => {
    const searchable = [r.company, r.name, r.id_number, r.status, r.product_type].filter(Boolean).join(' ').toLowerCase()
    return searchable.includes(q)
  })
})

async function openDrilldown(type) {
  drilldown.value = type
  ddSearch.value = ''
  clientsData.value = []

  if (['clients', 'premium', 'accumulation'].includes(type)) {
    clientsLoading.value = true
    try {
      const sort = type === 'accumulation' ? 'accumulation' : 'premium'
      const res = await api.get('/production/clients', { params: { sort } })
      clientsData.value = res.data
    } catch (e) {
      clientsData.value = []
    } finally {
      clientsLoading.value = false
    }
  }
}

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

// Insurance company brand colors
const companyColors = {
  'אקסלנס': '#1a3b6b',
  'הפניקס': '#f57c00',
  'מנורה': '#00897b',
  'הכשרה': '#c62828',
  'מור': '#0277bd',
  'אלטשולר': '#1a237e',
  'כלל': '#6a1b9a',
  'הראל': '#2e7d32',
  'מגדל': '#d32f2f',
  'איילון': '#00838f',
  'פסגות': '#4527a0',
  'אנליסט': '#37474f',
  'ילין לפידות': '#00695c',
  'מיטב': '#0d47a1',
}

function getCompanyColor(name) {
  for (const [key, color] of Object.entries(companyColors)) {
    if (name.includes(key)) return color
  }
  return '#546e7a'
}

// Shared height for side-by-side charts — driven by the one with more items
const chartsRowHeight = computed(() => {
  const productCount = props.analytics.product_type_breakdown.length
  const companyCount = props.analytics.company_breakdown.length
  return Math.max(280, Math.max(productCount, companyCount) * 38)
})

// Company chart — each bar gets its brand color
const companyChartOptions = computed(() => ({
  chart: { type: 'bar', toolbar: { show: false }, fontFamily: 'Heebo, sans-serif' },
  plotOptions: {
    bar: { horizontal: true, borderRadius: 6, barHeight: '70%', distributed: true },
  },
  dataLabels: { enabled: true, formatter: v => '₪' + v.toLocaleString(), style: { fontSize: '12px', fontFamily: 'Heebo, sans-serif' } },
  xaxis: {
    categories: props.analytics.company_breakdown.map(c => c.company),
    labels: { show: false },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '13px', fontWeight: 600 } } },
  colors: props.analytics.company_breakdown.map(c => getCompanyColor(c.company)),
  legend: { show: false },
  tooltip: {
    y: { formatter: v => '₪' + v.toLocaleString() },
  },
  grid: { borderColor: 'var(--border-subtle)', xaxis: { lines: { show: false } } },
}))

const companyChartSeries = computed(() => [{
  name: 'צבירה',
  data: props.analytics.company_breakdown.map(c => c.accumulation),
}])

// Product type bar — teal gradient
const productBarOptions = computed(() => ({
  chart: { type: 'bar', toolbar: { show: false }, fontFamily: 'Heebo, sans-serif' },
  plotOptions: { bar: { horizontal: true, borderRadius: 5, barHeight: '55%' } },
  dataLabels: { enabled: false },
  xaxis: {
    categories: props.analytics.product_type_breakdown.map(p => p.product_type),
    labels: { style: { fontFamily: 'Heebo, sans-serif' } },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' }, maxWidth: 200 } },
  colors: ['#0891b2'],
  fill: {
    type: 'gradient',
    gradient: { shade: 'light', type: 'horizontal', shadeIntensity: 0.15, opacityFrom: 0.9, opacityTo: 1 },
  },
  tooltip: {
    y: { formatter: v => v.toLocaleString() + ' רשומות' },
  },
  grid: { borderColor: 'var(--border-subtle)' },
}))

const productBarSeries = computed(() => [{
  name: 'רשומות',
  data: props.analytics.product_type_breakdown.map(p => p.count),
}])

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
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.kpi-card:hover {
  transform: translateY(-6px) scale(1.12);
  box-shadow: 0 12px 32px rgba(0,0,0,0.10);
  border-color: rgba(0,0,0,0.08);
}

.kpi-card:active {
  transform: translateY(-1px) scale(0.98);
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
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

.kpi-blue:hover { border-color: rgba(37, 99, 235, 0.25); box-shadow: 0 12px 32px rgba(37, 99, 235, 0.12); }
.kpi-cyan:hover { border-color: rgba(34, 211, 238, 0.25); box-shadow: 0 12px 32px rgba(34, 211, 238, 0.12); }
.kpi-green:hover { border-color: rgba(16, 185, 129, 0.25); box-shadow: 0 12px 32px rgba(16, 185, 129, 0.12); }
.kpi-amber:hover { border-color: rgba(245, 158, 11, 0.25); box-shadow: 0 12px 32px rgba(245, 158, 11, 0.12); }
.kpi-violet:hover { border-color: rgba(127, 86, 217, 0.25); box-shadow: 0 12px 32px rgba(127, 86, 217, 0.12); }
.kpi-emerald:hover { border-color: rgba(16, 185, 129, 0.25); box-shadow: 0 12px 32px rgba(16, 185, 129, 0.12); }

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
  align-items: start;
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

/* KPI clickable */
.kpi-card.clickable { cursor: pointer; }
.kpi-card.clickable:hover { transform: translateY(-2px); }

/* Drill-down modal */
.dd-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1010;
  backdrop-filter: blur(4px);
}

.dd-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  width: 90%; max-width: 750px; max-height: 80vh;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.dd-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-subtle);
}

.dd-header h4 { font-size: 16px; font-weight: 700; color: var(--text); }
.dd-header-right { display: flex; align-items: center; gap: 12px; }
.dd-count { font-size: 12px; color: var(--text-muted); }

.dd-close {
  width: 30px; height: 30px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;
}

.dd-close:hover { background: var(--red-light); color: var(--red); border-color: transparent; }

.dd-search { padding: 12px 22px 0; }

.dd-search-input {
  width: 100%; padding: 8px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  font-size: 13px; font-family: inherit;
  background: var(--bg); color: var(--text);
}

.dd-search-input:focus { outline: none; border-color: var(--primary); }

.dd-scroll { overflow-y: auto; max-height: 55vh; padding: 12px 22px 18px; }

.dd-loading {
  text-align: center;
  padding: 32px;
  color: var(--text-muted);
  font-size: 13px;
}

.dd-loading .loader {
  width: 28px; height: 28px;
  position: relative;
  margin: 0 auto 10px;
}

.dd-loading .loader-ring {
  position: absolute; inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.dd-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: fixed;
}

.dd-table thead { background: var(--bg); }

.dd-table th {
  padding: 10px 12px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 2px solid var(--border-subtle);
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 1;
  white-space: nowrap;
}

.dd-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
}

.dd-table tbody tr:hover { background: var(--bg-surface); }
.dd-table tbody tr:last-child td { border-bottom: none; }

.th-num, .td-num {
  text-align: center;
  width: 100px;
}

.modal-enter-active { animation: modalIn 0.3s var(--transition); }
.modal-leave-active { animation: modalIn 0.2s var(--transition) reverse; }
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
</style>
