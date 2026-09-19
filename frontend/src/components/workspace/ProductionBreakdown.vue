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
      <!-- EVERY company gets a bar, including one whose value on the active
           measure is 0. The chart used to plot only `metric > 0` and demote
           the rest to chips below it, so with צבירה selected (the default) a
           book holding הראל, מנורה, כלל and איילון rendered two bars — which
           reads as "those companies are missing", not as "they report the
           other measure". Both numbers now ride on every row. -->
      <apexchart v-if="shownCompanies.length" type="bar" :height="companyHeight"
                 :options="companyOptions" :series="companySeries" />
      <p v-else class="pb-none">אין נתוני פרודוקציה להצגה</p>

      <!-- A zero bar has to say WHY it is zero. The three causes need
           different actions and must not read alike. -->
      <div v-if="zeroCompanies.length" class="pb-zeros">
        <div v-for="c in zeroCompanies" :key="c.company" class="pb-zero"
             @click="openCompany = c.company">
          <span class="pb-zero-name">{{ c.company }}</span>
          <span class="pb-zero-nums">
            <span class="pb-zero-unit">צבירה</span>
            <span class="ltr-number">{{ c.accumulation ? money(c.accumulation) : '—' }}</span>
            <span class="pb-zero-sep">·</span>
            <span class="pb-zero-unit">פרמיה</span>
            <span class="ltr-number">{{ c.premium ? money(c.premium) : '—' }}</span>
            <template v-if="c.commission">
              <span class="pb-zero-sep">·</span>
              <span class="pb-zero-unit">עמלה</span>
              <span class="ltr-number">{{ money(c.commission) }}</span>
            </template>
          </span>
          <span class="pb-zero-why">{{ zeroReason(c) }}</span>
        </div>
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
        <!-- An empty category is never just "no data". Two different things
             produce it, and both are worth saying:
               * the companies that would supply financial production publish
                 נפרעים only — there is no such report to download;
               * accumulation the insurers DO report can sit on rows that also
                 carry premium, which classifies them as ביטוח. That money is
                 in the book, just on the other card — and a bare "אין נתונים"
                 beside ₪1.77M of held balance reads as data loss. -->
        <div v-if="!products[cat.key].length" class="pb-empty">
          <p class="pb-empty-lead">אין מוצרים בקטגוריה זו</p>
          <p v-if="cat.key === 'financial' && crossAccumulation > 0" class="pb-empty-note">
            עם זאת, <strong class="ltr-number">{{ money(crossAccumulation) }}</strong> של צבירה
            מוחזקים במוצרים שמסווגים כביטוח (שורות שנושאות גם פרמיה) — הם מופיעים בכרטיס
            "ביטוח — לפי מוצר" ובפירוט של כל חברה.
          </p>
          <p v-if="cat.key === 'financial' && noReport.length" class="pb-empty-note">
            החברות שמספקות מוצרים פיננסיים — {{ noReport.join(' · ') }} —
            אינן מפרסמות דוח פרודוקציה בפורטל, אלא נפרעים בלבד.
          </p>
          <p v-if="cat.key === 'insurance' && crossPremium > 0" class="pb-empty-note">
            עם זאת, <strong class="ltr-number">{{ money(crossPremium) }}</strong> של פרמיה
            נרשמים על מוצרים שמסווגים כפיננסיים.
          </p>
        </div>
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
            <CompanyProductRows :rows="labelled(cat.key, openCompanyRow.products[cat.key])"
                                @drill="drill(cat.key, $event.product, openCompanyRow.company)" />
          </section>
        </div>
      </template>
    </DataModal>

    <!-- ── The clients behind a product ────────────────────────────────── -->
    <DataModal :open="drillOpen" :title="drillTitle"
               :subtitle="drillLoading ? '' : `${drillClients.length} לקוחות`"
               @close="closeDrill">
      <!-- Filters requested by QA 2026-09-18: cut the drill by חברה, by מוצר
           and by ת.ז. Company/product narrow the SERVER query (the same
           params the chart already uses); the text box filters in place so
           typing an id stays instant. -->
      <div class="pb-filters">
        <select v-model="fCompany" @change="refetchDrill">
          <option :value="null">כל החברות</option>
          <option v-for="c in companies" :key="c.company" :value="c.company">{{ c.company }}</option>
        </select>
        <select v-model="fProduct" @change="refetchDrill">
          <option :value="null">כל המוצרים</option>
          <option v-for="o in drillProductOptions" :key="o.key" :value="o.key">{{ o.label }}</option>
        </select>
        <input v-model="fQuery" type="search" placeholder="חיפוש לפי ת.ז או שם" />
        <button v-if="fCompany || fProduct || fQuery" class="pb-filters-clear"
                @click="clearFilters">נקה</button>
      </div>
      <p v-if="drillLoading" class="pb-none">טוען…</p>
      <p v-else-if="!filteredDrill.length" class="pb-none">אין לקוחות להצגה</p>
      <ClientRows v-else :rows="filteredDrill" :identical="drillIdentical" />
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

// The פיננסים card is titled "לפי אפיק", and an agent expects to read
// גמל / השתלמות / פוליסות חיסכון there. `product_taxonomy` already produces
// those keys, but two real savings families arrive under names that mean
// nothing on a savings axis: Harel prices its savings policies as `מגוון`,
// and Phoenix's MU book files accumulation-bearing policies as `חיים`.
//
// This maps the LABEL only. The raw key is what `/breakdown/clients` filters
// on, so it is what still gets sent on a drill — and the backend taxonomy is
// deliberately left alone (`product_taxonomy.py` carries an explicit
// "Do not 'fix' it" for accumulation-bearing life policies).
// Labels must stay DISTINCT: the backend already emits a real
// `פוליסת חיסכון` bucket (₪50.5M live), so renaming `חיים` onto it would put
// two differently-sized bars under one identical name. These say what the
// product is without pretending it is the same thing.
const FINANCIAL_LABELS = {
  'חיים': 'ביטוח חיים עם חיסכון',
  'ביטוח חיים': 'ביטוח חיים עם חיסכון',
  'מגוון': 'מגוון — פוליסת חיסכון',
}

function productLabel(catKey, product) {
  if (catKey !== 'financial') return product
  return FINANCIAL_LABELS[product] || product
}

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
// Every company, ordered by the measure on screen — none dropped. The two
// measures are kept side by side because insurers populate only one of them
// and the agent asked to see both per company (QA 2026-09-18 item 8).
const shownCompanies = computed(() =>
  [...companies.value].sort((a, b) => {
    const m = Number(b[coMetric.value] || 0) - Number(a[coMetric.value] || 0)
    if (m) return m
    const other = coMetric.value === 'premium' ? 'accumulation' : 'premium'
    return Number(b[other] || 0) - Number(a[other] || 0)
  }),
)
// Companies whose bar is zero on the ACTIVE measure — each gets a named reason
// rather than an unexplained empty row.
const zeroCompanies = computed(() =>
  shownCompanies.value.filter(c => !(Number(c[coMetric.value]) > 0)),
)

function zeroReason(c) {
  const other = coMetric.value === 'premium' ? 'accumulation' : 'premium'
  if (Number(c[other]) > 0) {
    return coMetric.value === 'premium'
      ? 'מדווחת צבירה, לא פרמיה'
      : 'מדווחת פרמיה, לא צבירה'
  }
  // Neither measure — the file itself came without money columns. Live: הראל
  // ships 1,729 production rows with פרמיה and צבירה both empty.
  return c.rate_reason || 'הקובץ הגיע ללא נתוני פרמיה וצבירה'
}
// Money held on the OTHER side of the split — the reason an empty card is not
// the same as an empty book.
const crossAccumulation = computed(
  () => products.value.insurance.reduce((sum, p) => sum + (Number(p.accumulation) || 0), 0),
)
const crossPremium = computed(
  () => products.value.financial.reduce((sum, p) => sum + (Number(p.premium) || 0), 0),
)

const noReport = computed(
  () => missing.value.filter(m => m.reason === 'no_report').map(m => m.company),
)
const notReceived = computed(
  () => missing.value.filter(m => m.reason !== 'no_report').map(m => m.company),
)
const openCompanyRow = computed(
  () => companies.value.find(c => c.company === openCompany.value) || null,
)
function labelled(catKey, rows) {
  return (rows || []).map(p => ({ ...p, label: productLabel(catKey, p.product) }))
}

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
        if (!c) return money(v)
        const other = coMetric.value === 'premium' ? 'accumulation' : 'premium'
        const otherLabel = coMetric.value === 'premium' ? 'צבירה' : 'פרמיה'
        const parts = [`${money(v)}`, `${otherLabel} ${money(c[other] || 0)}`]
        if (c.commission) parts.push(`עמלה ${money(c.commission)}`)
        parts.push(`${c.clients ?? 0} לקוחות`, `${c.count ?? 0} מוצרים`)
        return parts.join(' · ')
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
      categories: rows.map(p => productLabel(cat.key, p.product)),
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

const fCompany = ref(null)
const fProduct = ref(null)
const fQuery = ref('')
const drillCategory = ref(null)

// Every product available in the drilled category, with the same display
// mapping the charts use.
const drillProductOptions = computed(() => {
  const key = drillCategory.value
  if (!key) return []
  return (products.value[key] || []).map(p => ({
    key: p.product, label: productLabel(key, p.product),
  }))
})

// The ת.ז / name box filters the loaded list — no round-trip per keystroke.
const filteredDrill = computed(() => {
  const q = fQuery.value.trim()
  if (!q) return drillClients.value
  return drillClients.value.filter(
    c => (c.id_number || '').includes(q) || (c.name || '').includes(q),
  )
})

function clearFilters() {
  fCompany.value = null
  fProduct.value = null
  fQuery.value = ''
  refetchDrill()
}

async function refetchDrill() {
  await drill(drillCategory.value, fProduct.value, fCompany.value, true)
}

async function drill(category, product, company, keepFilters = false) {
  // Close the company modal first — both overlays are z-index 1010, so
  // opening the client list on top of it stacked two dimmed layers and the
  // Esc key closed only the upper one.
  openCompany.value = null
  drillOpen.value = true
  drillLoading.value = true
  drillIdentical.value = null
  drillClients.value = []
  drillCategory.value = category
  if (!keepFilters) {
    fCompany.value = company || null
    fProduct.value = product || null
    fQuery.value = ''
  }
  const shownProduct = product ? productLabel(category, product) : null
  drillTitle.value = company
    ? `${company}${shownProduct ? ' · ' + shownProduct : ''}`
    : (shownProduct || 'כל הלקוחות')
  try {
    const res = await api.get('/production/breakdown/clients', {
      params: {
        category: category || undefined,
        product: product || undefined,
        company: company || undefined,
      },
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

/* One line per company whose bar is zero on the active measure — both
   numbers and the reason, so an empty bar is never just an empty bar. */
.pb-zeros {
  margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--border-subtle);
  display: flex; flex-direction: column;
}
.pb-zero {
  display: grid; grid-template-columns: minmax(90px, 1fr) auto 1.2fr;
  align-items: baseline; gap: 12px;
  padding: 6px 4px; border-radius: var(--radius-sm); cursor: pointer;
}
.pb-zero:hover { background: var(--border-subtle); }
.pb-zero-name { font-size: 12.5px; color: var(--text); font-weight: 600; }
.pb-zero-nums { display: flex; align-items: baseline; gap: 5px; font-size: 12px; color: var(--text); }
.pb-zero-unit { font-size: 10px; color: var(--text-muted); }
.pb-zero-sep { color: var(--text-muted); opacity: 0.6; margin: 0 3px; }
.pb-zero-why { font-size: 11.5px; color: var(--text-muted); text-align: left; }

/* Drill filters */
.pb-filters {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  margin-bottom: 12px; padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
}
.pb-filters select, .pb-filters input {
  font-family: inherit; font-size: 12.5px; color: var(--text);
  padding: 6px 10px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle); background: var(--card-bg);
}
.pb-filters input { flex: 1; min-width: 150px; }
.pb-filters select { max-width: 190px; }
.pb-filters-clear {
  border: none; background: none; font-family: inherit; font-size: 12px;
  color: var(--text-muted); cursor: pointer; text-decoration: underline;
}
.pb-filters-clear:hover { color: var(--text); }

.pb-empty { padding: 10px 0 4px; }
.pb-empty-lead { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
.pb-empty-note {
  font-size: 12px; color: var(--text-muted); line-height: 1.8; margin-top: 6px;
  padding: 9px 11px; border-radius: var(--radius-sm); background: var(--border-subtle);
}
.pb-empty-note strong { color: var(--text); }

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
