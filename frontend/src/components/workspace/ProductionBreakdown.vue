<template>
  <div v-if="loaded" class="pb-wrap">
    <!-- ── Companies ─────────────────────────────────────────────────────
         Horizontal bars: the labels are Hebrew company names, which need a
         readable line rather than a rotated tick. Insurers populate only ONE
         of accumulation / premium, so the toggle names which measure is on
         screen instead of mixing two scales on one axis. -->
    <div class="chart-card">
      <div class="chart-header">
        <h3>
          התפלגות לפי חברה
          <span class="pb-count ltr-number">{{ companies.length }}</span>
        </h3>
        <div class="chart-actions">
          <button class="toggle-btn" :class="{ active: coMetric === 'accumulation' }"
                  @click="coMetric = 'accumulation'">צבירה</button>
          <button class="toggle-btn" :class="{ active: coMetric === 'premium' }"
                  @click="coMetric = 'premium'">פרמיה</button>
        </div>
      </div>
      <p class="pb-hint">בחר חברה בגרף כדי לראות את החלוקה הפנימית שלה</p>
      <apexchart v-if="shownCompanies.length" type="bar" :height="companyHeight"
                 :options="companyOptions" :series="companySeries" />
      <p v-else class="pb-none">אף חברה לא מדווחת {{ coMetric === 'premium' ? 'פרמיה' : 'צבירה' }}</p>

      <!-- Named, not dropped: each of these is clickable into its own
           breakdown, so a company is never invisible just because it reports
           the other measure. -->
      <div v-if="otherCompanies.length" class="pb-others">
        <span class="pb-others-lead">
          ללא {{ coMetric === 'premium' ? 'פרמיה' : 'צבירה' }} מדווחת:
        </span>
        <button v-for="c in otherCompanies" :key="c.company" class="pb-other"
                @click="openCompany = c.company">
          {{ c.company }}
          <span class="ltr-number">{{ money(c[coMetric === 'premium' ? 'accumulation' : 'premium']) }}</span>
          <span class="pb-other-unit">{{ otherMetricLabel }}</span>
        </button>
      </div>

      <!-- Why the chart has fewer bars than the agent has portals. Two
           different causes, and merging them makes a real failure look like a
           fact of life: six gemel houses publish נפרעים ONLY — there is no
           production report to download — while כלל publishes one whose
           download failed. -->
      <p v-if="noReport.length" class="pb-absent">
        <span class="pb-absent-lead">ללא דוח פרודוקציה בפורטל:</span>
        {{ noReport.join(' · ') }}
        <span class="pb-absent-note">(חברות גמל ופנסיה — הפורטלים שלהן מספקים נפרעים בלבד)</span>
      </p>
      <p v-if="notReceived.length" class="pb-absent pb-absent--warn">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span class="pb-absent-lead">לא התקבלה פרודוקציה:</span>
        {{ notReceived.join(' · ') }}
        <span class="pb-absent-note">(הפורטל מספק דוח — ההורדה לא הושלמה)</span>
      </p>
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
            <CompanyProductRows :rows="openCompanyRow.products[cat.key]"
                                @drill="drill(cat.key, $event.product, openCompanyRow.company)" />
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
      <ClientRows v-else :rows="drillClients" :identical="drillIdentical" />
    </DataModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client'
import DataModal from './DataModal.vue'
import CompanyProductRows from './CompanyProductRows.vue'
import ClientRows from './ClientRows.vue'
import { assignCompanyColors, CHART_PALETTE } from '../../utils/chartPalette'
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
const missing = ref([])
const coMetric = ref('accumulation')
const openCompany = ref(null)

const drillOpen = ref(false)
const drillLoading = ref(false)
const drillClients = ref([])
const drillTitle = ref('')
const drillIdentical = ref(null)

// Companies with a value for the CURRENT measure.
//
// Those without one are NOT discarded — they are named under the chart. Live,
// a book where only one insurer reports a balance rendered a chart with a
// single bar and no hint that three other companies existed, which reads as
// broken rather than as "these three report premium, not a balance".
const shownCompanies = computed(() =>
  companies.value.filter(c => Number(c[coMetric.value]) > 0),
)
const otherCompanies = computed(() =>
  companies.value.filter(c => !(Number(c[coMetric.value]) > 0)),
)
const noReport = computed(
  () => missing.value.filter(m => m.reason === 'no_report').map(m => m.company),
)
const notReceived = computed(
  () => missing.value.filter(m => m.reason !== 'no_report').map(m => m.company),
)
const otherMetricLabel = computed(
  () => (coMetric.value === 'premium' ? 'צבירה' : 'פרמיה'),
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
  colors: (() => {
    // Distinct per company within THIS chart — see assignCompanyColors.
    const map = assignCompanyColors(shownCompanies.value.map(c => c.company))
    return shownCompanies.value.map(c => map.get(c.company))
  })(),
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
  drillIdentical.value = null
  drillClients.value = []
  drillTitle.value = company ? `${company} · ${product}` : product
  try {
    const res = await api.get('/production/breakdown/clients', {
      params: { category, product, company: company || undefined },
    })
    drillClients.value = res.data.clients || []
    drillIdentical.value = res.data.identical_value || null
  } catch (e) {
    drillClients.value = []
  } finally {
    drillLoading.value = false
  }
}

function closeDrill() {
  drillOpen.value = false
}

onMounted(async () => {
  try {
    const res = await api.get('/production/breakdown')
    companies.value = res.data.companies || []
    products.value = res.data.products || { insurance: [], financial: [] }
    missing.value = res.data.missing || []
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
.pb-count {
  display: inline-block; margin-right: 7px; padding: 1px 8px;
  border-radius: 10px; background: var(--border-subtle);
  color: var(--text-muted); font-size: 11px; font-weight: 700; vertical-align: 2px;
}
.pb-absent {
  display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap;
  margin-top: 12px; font-size: 11.5px; color: var(--text-muted); line-height: 1.7;
}
.pb-absent svg { align-self: center; color: var(--amber); }
.pb-absent-lead { font-weight: 700; color: var(--text); }
.pb-absent-note { opacity: 0.8; }
.pb-absent--warn .pb-absent-lead { color: var(--amber); }

.pb-others {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle);
}
.pb-others-lead { font-size: 11px; color: var(--text-muted); }
.pb-other {
  display: inline-flex; align-items: baseline; gap: 6px;
  padding: 4px 10px; border-radius: 12px;
  border: 1px solid var(--border-subtle); background: none;
  font-family: inherit; font-size: 12px; color: var(--text); cursor: pointer;
}
.pb-other:hover { border-color: var(--text-muted); background: var(--border-subtle); }
.pb-other-unit { font-size: 10px; color: var(--text-muted); }

.pb-none { font-size: 13px; color: var(--text-muted); padding: 12px 0; }
.pb-entities { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }
/* Stacked, not side by side. Two five-column row components sharing one modal
   width crushed both: the columns overlapped and the צבירה figure was cut off.
   Each category now gets the full width. */
.pb-split { display: flex; flex-direction: column; gap: 22px; }
.pb-split h5 {
  font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 8px;
  display: flex; align-items: center; gap: 8px;
}
.pb-split h5::after {
  content: ''; flex: 1; height: 1px; background: var(--border-subtle);
}

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
