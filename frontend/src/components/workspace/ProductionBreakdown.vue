<template>
  <div v-if="loaded" class="pb-wrap">
    <!-- ── Companies ─────────────────────────────────────────────────────
         Horizontal bars: the labels are Hebrew company names, which need a
         readable line rather than a rotated tick. Insurers populate only ONE
         of accumulation / premium, so the toggle names which measure is on
         screen instead of mixing two scales on one axis. -->
    <div class="chart-card">
      <div class="chart-header">
        <h3>התפלגות לפי חברה</h3>
        <div class="chart-actions">
          <button class="toggle-btn" :class="{ active: coMetric === 'accumulation' }"
                  @click="coMetric = 'accumulation'">צבירה</button>
          <button class="toggle-btn" :class="{ active: coMetric === 'premium' }"
                  @click="coMetric = 'premium'">פרמיה</button>
        </div>
      </div>
      <p class="pb-hint">בחר חברה בגרף כדי לראות את החלוקה הפנימית שלה</p>
      <apexchart type="bar" :height="companyHeight"
                 :options="companyOptions" :series="companySeries" />
    </div>

    <!-- ── Products, split ביטוח / פיננסים ───────────────────────────────
         Two charts, never one: insurance is measured by monthly premium and
         savings by balance under management. Plotting both on one axis would
         compare quantities that have nothing to do with each other. -->
    <div class="charts-row">
      <div v-for="cat in CATS" :key="cat.key" class="chart-card">
        <div class="chart-header"><h3>{{ cat.title }}</h3></div>
        <p class="pb-hint">בחר מוצר כדי לראות את הלקוחות שמחזיקים בו</p>
        <p v-if="!products[cat.key].length" class="pb-none">אין נתונים</p>
        <apexchart v-else type="bar" :height="productHeight(cat.key)"
                   :options="productOptions(cat)" :series="productSeries(cat)" />
      </div>
    </div>

    <!-- ── One company's internals ─────────────────────────────────────── -->
    <DataModal :open="!!openCompanyRow" :title="companyModalTitle" @close="openCompany = null">
      <template v-if="openCompanyRow">
        <p v-if="openCompanyRow.entities.length > 1" class="pb-entities">
          כולל {{ openCompanyRow.entities.join(' · ') }}
        </p>
        <div class="pb-split">
          <section v-for="cat in CATS" :key="cat.key">
            <h5>{{ cat.label }}</h5>
            <p v-if="!openCompanyRow.products[cat.key].length" class="pb-none">
              אין מוצרים בקטגוריה זו
            </p>
            <table v-else class="pb-table">
              <thead><tr><th>מוצר</th><th>{{ cat.metricLabel }}</th><th>לקוחות</th></tr></thead>
              <tbody>
                <tr v-for="p in openCompanyRow.products[cat.key]" :key="p.product"
                    class="pb-row" @click="drill(cat.key, p.product, openCompanyRow.company)">
                  <td>{{ p.product }}</td>
                  <td class="pb-num"><span class="ltr-number">{{ money(p[cat.metric]) }}</span></td>
                  <td class="pb-num"><span class="ltr-number">{{ p.clients }}</span></td>
                </tr>
              </tbody>
            </table>
          </section>
        </div>
      </template>
    </DataModal>

    <!-- ── The clients behind a product ────────────────────────────────── -->
    <DataModal :open="drillOpen" :title="drillTitle"
               :subtitle="drillLoading ? '' : `${drillClients.length} לקוחות`"
               @close="closeDrill">
      <p v-if="drillLoading" class="pb-none">טוען…</p>
      <p v-else-if="!drillClients.length" class="pb-none">אין לקוחות להצגה</p>
      <table v-else class="pb-table">
        <thead><tr><th>לקוח</th><th>פרמיה</th><th>צבירה</th><th>מוצרים</th></tr></thead>
        <tbody>
          <template v-for="c in drillClients" :key="c.id_number">
            <tr class="pb-row" @click="openClient = openClient === c.id_number ? null : c.id_number">
              <td>{{ c.name || c.id_number }}</td>
              <td class="pb-num"><span class="ltr-number">{{ money(c.premium) }}</span></td>
              <td class="pb-num"><span class="ltr-number">{{ money(c.accumulation) }}</span></td>
              <td class="pb-num"><span class="ltr-number">{{ c.products.length }}</span></td>
            </tr>
            <!-- One client's full holdings, insurance and savings together. -->
            <tr v-if="openClient === c.id_number" class="pb-sub">
              <td colspan="4">
                <table class="pb-table pb-table--sub">
                  <thead>
                    <tr><th>מוצר</th><th>חברה</th><th>סוג</th><th>פרמיה</th><th>צבירה</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(p, i) in c.products" :key="i">
                      <td>{{ p.raw_product || p.product }}</td>
                      <td>{{ p.company }}</td>
                      <td>{{ p.category === 'insurance' ? 'ביטוח' : 'פיננסים' }}</td>
                      <td class="pb-num"><span class="ltr-number">{{ money(p.premium) }}</span></td>
                      <td class="pb-num"><span class="ltr-number">{{ money(p.accumulation) }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </DataModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client'
import DataModal from './DataModal.vue'
import { companyColor, CHART_PALETTE } from '../../utils/chartPalette'
import { money, axisMoney, BASE_CHART } from '../../utils/chartDefaults'

const CATS = [
  { key: 'insurance', label: 'ביטוח', title: 'ביטוח — לפי מוצר',
    metric: 'premium', metricLabel: 'פרמיה חודשית' },
  { key: 'financial', label: 'פיננסים', title: 'פיננסים — לפי אפיק',
    metric: 'accumulation', metricLabel: 'צבירה' },
]

const loaded = ref(false)
const companies = ref([])
const products = ref({ insurance: [], financial: [] })
const coMetric = ref('accumulation')
const openCompany = ref(null)

const drillOpen = ref(false)
const drillLoading = ref(false)
const drillClients = ref([])
const drillTitle = ref('')
const openClient = ref(null)

// Companies with a value for the CURRENT measure. A company that reports only
// premium would otherwise sit at zero on the צבירה view and read as "manages
// nothing" rather than "does not report a balance".
const shownCompanies = computed(() =>
  companies.value.filter(c => Number(c[coMetric.value]) > 0),
)
const openCompanyRow = computed(
  () => companies.value.find(c => c.company === openCompany.value) || null,
)
const companyModalTitle = computed(
  () => openCompanyRow.value ? `${openCompanyRow.value.company} — לפי מוצר` : '',
)
const companyHeight = computed(() => Math.max(180, shownCompanies.value.length * 46 + 60))
const productHeight = key => Math.max(180, products.value[key].length * 46 + 60)

const companySeries = computed(() => [{
  name: coMetric.value === 'premium' ? 'פרמיה' : 'צבירה',
  data: shownCompanies.value.map(c => Number(c[coMetric.value]) || 0),
}])

const companyOptions = computed(() => ({
  ...BASE_CHART,
  chart: {
    ...BASE_CHART.chart,
    type: 'bar',
    events: {
      // Carry WHICH bar was clicked. The previous chart's handler took no
      // arguments, so every company opened the same all-companies table.
      dataPointSelection: (_e, _ctx, cfg) => {
        const c = shownCompanies.value[cfg.dataPointIndex]
        if (c) openCompany.value = c.company
      },
    },
  },
  colors: shownCompanies.value.map(c => companyColor(c.company)),
  plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '62%', distributed: true } },
  dataLabels: {
    enabled: true,
    formatter: v => money(v),
    style: { fontSize: '11px', fontFamily: 'Heebo, sans-serif', colors: ['#3E3E3C'] },
    offsetX: 34,
  },
  // One series: the title names it, so a legend box would only repeat itself.
  legend: { show: false },
  xaxis: {
    categories: shownCompanies.value.map(c => c.company),
    labels: { formatter: axisMoney, style: { fontFamily: 'Heebo, sans-serif', colors: '#706E6B' } },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', colors: '#706E6B', fontSize: '13px' } } },
  tooltip: {
    ...BASE_CHART.tooltip,
    y: {
      formatter: (v, o) => {
        const c = shownCompanies.value[o.dataPointIndex]
        return `${money(v)} · ${c?.clients ?? 0} לקוחות · ${c?.count ?? 0} מוצרים`
      },
    },
  },
}))

function productSeries(cat) {
  return [{
    name: cat.metricLabel,
    data: products.value[cat.key].map(p => Number(p[cat.metric]) || 0),
  }]
}

function productOptions(cat) {
  const rows = products.value[cat.key]
  return {
    ...BASE_CHART,
    chart: {
      ...BASE_CHART.chart,
      type: 'bar',
      events: {
        dataPointSelection: (_e, _ctx, cfg) => {
          const p = rows[cfg.dataPointIndex]
          if (p) drill(cat.key, p.product, null)
        },
      },
    },
    colors: rows.map((_, i) => CHART_PALETTE[i % 11]),
    plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '62%', distributed: true } },
    dataLabels: {
      enabled: true,
      formatter: v => money(v),
      style: { fontSize: '11px', fontFamily: 'Heebo, sans-serif', colors: ['#3E3E3C'] },
      offsetX: 34,
    },
    legend: { show: false },
    xaxis: {
      categories: rows.map(p => p.product),
      labels: { formatter: axisMoney, style: { fontFamily: 'Heebo, sans-serif', colors: '#706E6B' } },
    },
    yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', colors: '#706E6B', fontSize: '13px' } } },
    tooltip: {
      ...BASE_CHART.tooltip,
      y: {
        formatter: (v, o) => {
          const p = rows[o.dataPointIndex]
          return `${money(v)} · ${p?.clients ?? 0} לקוחות`
        },
      },
    },
  }
}

async function drill(category, product, company) {
  drillOpen.value = true
  drillLoading.value = true
  openClient.value = null
  drillClients.value = []
  drillTitle.value = company ? `${company} · ${product}` : product
  try {
    const res = await api.get('/production/breakdown/clients', {
      params: { category, product, company: company || undefined },
    })
    drillClients.value = res.data.clients || []
  } catch (e) {
    drillClients.value = []
  } finally {
    drillLoading.value = false
  }
}

function closeDrill() {
  drillOpen.value = false
  openClient.value = null
}

onMounted(async () => {
  try {
    const res = await api.get('/production/breakdown')
    companies.value = res.data.companies || []
    products.value = res.data.products || { insurance: [], financial: [] }
    loaded.value = companies.value.length > 0
  } catch (e) {
    loaded.value = false
  }
})
</script>

<style scoped>
.pb-wrap { display: flex; flex-direction: column; gap: 20px; }
.chart-card {
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 20px;
}
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.chart-header h3 { font-size: 15px; font-weight: 700; color: var(--text); }
.chart-actions { display: flex; gap: 6px; }
.toggle-btn {
  padding: 4px 12px; border: none; border-radius: var(--radius-sm);
  background: var(--border-subtle); color: var(--text-muted);
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.toggle-btn.active { background: var(--primary-light); color: var(--primary); }
.pb-hint { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.pb-none { font-size: 13px; color: var(--text-muted); padding: 12px 0; }
.pb-entities { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }
.pb-split { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 700px) { .pb-split { grid-template-columns: 1fr; } }
.pb-split h5 { font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 8px; }

.pb-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.pb-table th {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border-subtle);
}
.pb-table td {
  font-size: 13px; color: var(--text); padding: 8px;
  border-bottom: 1px solid var(--border-subtle);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pb-table th:not(:first-child), .pb-table td.pb-num { text-align: center; width: 100px; }
.pb-row { cursor: pointer; }
.pb-row:hover { background: var(--border-subtle); }
.pb-sub > td { padding: 0 0 8px 0; background: var(--border-subtle); }
.pb-table--sub th, .pb-table--sub td { font-size: 12px; }
</style>
