<template>
  <div class="prod-dashboard">
    <!-- KPI Row -->
    <div class="kpi-row">
      <button
        v-for="k in kpis" :key="k.key" type="button"
        class="kpi-card" :style="{ '--k': k.color, '--k-ink': k.ink }"
        :title="k.title || null" @click="openDrilldown(k.drill, $event.currentTarget)"
      >
        <span class="kpi-ghost" aria-hidden="true"><KpiGlyph :name="k.key" :size="92" :stroke="1.2" /></span>
        <span class="kpi-icon"><KpiGlyph :name="k.key" :size="22" /></span>
        <span class="kpi-data">
          <span class="kpi-value ltr-number">{{ k.value }}</span>
          <span class="kpi-label">{{ k.label }}</span>
        </span>
      </button>
    </div>

    <!-- Hero chart: commission trend (most important — sits directly under KPIs) -->
    <ProductionTrendChart @go-to-automation="$emit('go-to-automation')" />

    <!-- Unpaid clients + biggest movers, then actual vs agreed commission. -->
    <ProductionAlerts />

    <!-- Actual vs agreed commission, per company, with the alerts on top. -->
    <RateAuditPanel />

    <!-- Company and product distributions.
         These replace two ApexCharts bar charts that grouped on the RAW
         columns and discarded which bar was clicked. Raw grouping split one
         insurer across its legal entities (מנורה ביטוח + מנורה פנסיה וגמל) and
         reported one product under four spellings (חיים / ביטוח חיים /
         ר.ת.-מורחב חיים ביטוחים / ר.ת.-מורחב חיים פוליסות = 561 rows), and
         every `dataPointSelection` handler took no arguments, so clicking any
         company or product opened the same flat all-companies table. -->
    <ProductionBreakdown />

    <!-- Row 3: Top Clients (full width; click a bar → drill-down) -->
    <div class="chart-card" v-if="hasTopClientsData">
      <div class="chart-header">
        <h3>{{ topMetric === 'premium' ? 'לקוחות לפי פרמיה' : 'לקוחות לפי צבירה' }}</h3>
        <div class="chart-actions">
          <button class="toggle-btn" :class="{ active: topMetric === 'premium' }" @click="topMetric = 'premium'">פרמיה</button>
          <button class="toggle-btn" :class="{ active: topMetric === 'accumulation' }" @click="topMetric = 'accumulation'">צבירה</button>
        </div>
      </div>
      <apexchart
        v-if="topClientsData.length"
        type="bar"
        :height="320"
        :options="topClientsChartOptions"
        :series="topClientsChartSeries"
      />
      <div v-else class="chart-empty">
        אין נתוני {{ topMetric === 'premium' ? 'פרמיה' : 'צבירה' }} להצגה
      </div>
    </div>
    <!-- KPI Drill-down Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="drilldown" class="dd-overlay" @click.self="closeDrilldown">
          <div ref="ddCardEl" class="dd-card">
            <div class="dd-header">
              <h4>{{ drilldownTitle }}</h4>
              <div class="dd-header-right">
                <span class="dd-count ltr-number">{{ filteredDrillData.length }} שורות</span>
                <button class="dd-close" @click="closeDrilldown">&times;</button>
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
import { computed, ref, nextTick } from 'vue'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import api from '../../api/client.js'
import ProductionTrendChart from './ProductionTrendChart.vue'
import KpiGlyph from './KpiGlyph.vue'
import { CHART_PALETTE } from '../../utils/chartPalette.js'

const props = defineProps({
  analytics: { type: Object, required: true },
})

import ProductionBreakdown from './ProductionBreakdown.vue'
import RateAuditPanel from './RateAuditPanel.vue'
import ProductionAlerts from './ProductionAlerts.vue'

defineEmits(['go-to-automation'])

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

// iPhone-style: the drill-down grows out of the tapped KPI card and folds back
// into it (composables/useOriginMorph), like the השוואת נפרעים KPIs.
const originMorph = useOriginMorph()
const ddCardEl = ref(null)
async function closeDrilldown() {
  if (originMorph.hasOrigin()) await originMorph.shrink(ddCardEl.value)
  drilldown.value = null
}

async function openDrilldown(type, originEl = null) {
  originMorph.remember(originEl)
  drilldown.value = type
  if (originEl) nextTick(() => originMorph.grow(ddCardEl.value))
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

// KPI cards. Colour = category (CHART_PALETTE via --chart-*), products wear the
// Production tab cobalt; `ink` is the text-safe shade for the badge glyph.
const kpis = computed(() => {
  const a = props.analytics
  return [
    { key: 'products', drill: 'products', label: 'מוצרים', value: a.total_records.toLocaleString(),
      color: 'var(--tab-production)', ink: 'var(--tab-production)' },
    { key: 'clients', drill: 'clients', label: 'לקוחות', value: a.unique_clients.toLocaleString(),
      color: 'var(--chart-6)', ink: 'var(--tab-emails-ink, #C42B60)' },
    { key: 'accumulation', drill: 'accumulation', label: 'סה"כ צבירה', value: formatAmount(a.total_accumulation),
      title: '₪' + Math.round(a.total_accumulation).toLocaleString(),
      color: 'var(--chart-7)', ink: 'var(--tab-recruits-ink, #1E7D78)' },
    { key: 'companies', drill: 'companies', label: 'חברות', value: String(a.companies_count),
      color: 'var(--chart-4)', ink: 'var(--chart-4)' },
    { key: 'active', drill: 'status', label: 'מוצרים פעילים', value: `${activePercent.value}%`,
      color: 'var(--chart-10)', ink: 'var(--chart-10)' },
  ]
})

// Bright-bold categorical palette shared across all chart bars (see
// utils/chartPalette.js). Each bar/company/category gets a clearly distinct hue.
const PALETTE_SERIES = CHART_PALETTE

// The company / product-type bar charts that lived here were replaced by
// <ProductionBreakdown>, which groups on the canonical company and product
// keys and carries the click target through to a real drill-down.

// Top clients (premium/accumulation toggle).
const topClientsData = computed(() =>
  topMetric.value === 'premium'
    ? props.analytics.top_clients_premium.filter(c => c.premium > 0)
    : props.analytics.top_clients_accumulation.filter(c => c.accumulation > 0)
)

// Card stays visible if EITHER metric has data, so the toggle doesn't disappear
// when the user switches to a metric the uploaded file lacks (e.g. pure-premium files).
const hasTopClientsData = computed(() =>
  props.analytics.top_clients_premium.some(c => c.premium > 0) ||
  props.analytics.top_clients_accumulation.some(c => c.accumulation > 0)
)

// Each client bar gets its own palette color (distributed). Click → clients drill-down.
const topClientsChartOptions = computed(() => ({
  chart: {
    type: 'bar', toolbar: { show: false }, fontFamily: 'Heebo, sans-serif',
    animations: { enabled: true, easing: 'easeinout', speed: 700 },
    events: { dataPointSelection: () => openDrilldown(topMetric.value === 'premium' ? 'premium' : 'accumulation') },
  },
  plotOptions: { bar: { horizontal: true, borderRadius: 6, barHeight: '65%', distributed: true } },
  dataLabels: { enabled: false },
  xaxis: {
    categories: topClientsData.value.map(c => c.name || c.id_number),
    labels: { style: { fontFamily: 'Heebo, sans-serif' }, formatter: v => '₪' + Math.round(v).toLocaleString() },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' } } },
  colors: PALETTE_SERIES,
  legend: { show: false },
  states: { active: { filter: { type: 'none' } } },
  tooltip: { y: { formatter: v => '₪' + Math.round(v).toLocaleString() } },
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
  grid-template-columns: repeat(5, minmax(0, 1fr)); /* 5 cards span the page */
  gap: 12px;
}
@media (max-width: 860px) { .kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 640px) { .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); } }

.kpi-card {
  position: relative; overflow: hidden;
  display: flex; align-items: center; gap: 12px;
  padding: 16px 16px 16px 18px; min-height: 84px;
  font-family: inherit; text-align: start; color: inherit;
  background:
    radial-gradient(120% 90% at 0% 100%, color-mix(in srgb, var(--k) 9%, transparent) 0%, transparent 60%),
    var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.kpi-card:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--k) 30%, transparent);
  box-shadow: 0 10px 26px color-mix(in srgb, var(--k) 16%, transparent);
}
.kpi-card:active { transform: translateY(0); }
.kpi-card:focus-visible { outline: 2px solid var(--k); outline-offset: 2px; }

/* the oversized faint glyph tucked into the far corner */
.kpi-ghost {
  position: absolute; inset-inline-end: -14px; bottom: -18px;
  color: var(--k); opacity: 0.09; pointer-events: none;
  transition: transform 0.35s ease, opacity 0.35s ease;
}
.kpi-card:hover .kpi-ghost { transform: rotate(-8deg) scale(1.06); opacity: 0.14; }

.kpi-icon {
  position: relative; flex-shrink: 0;
  width: 44px; height: 44px; border-radius: 14px;
  display: grid; place-items: center;
  color: var(--k-ink);
  background: color-mix(in srgb, var(--k) 13%, var(--card-bg));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--k) 18%, transparent);
}

.kpi-data { position: relative; min-width: 0; display: flex; flex-direction: column; }

.kpi-value {
  font-size: 22px; font-weight: 800; letter-spacing: -0.02em;
  color: var(--text-primary, #181818); line-height: 1.15;
}

.kpi-label {
  font-size: 12.5px; font-weight: 600;
  color: var(--text-secondary, #706E6B); margin-top: 3px;
}

@media (prefers-reduced-motion: reduce) {
  .kpi-card, .kpi-ghost { transition: none; }
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

.chart-empty {
  height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 14px;
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
