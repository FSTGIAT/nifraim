<template>
  <section v-if="rows.length" class="crs" aria-labelledby="crs-title">
    <div class="crs-head">
      <div class="crs-head-text">
        <h3 id="crs-title" class="crs-title">סיכום לפי חברה</h3>
        <span class="crs-sub">גמל + ביטוח · נפרעים מול פרודוקציה</span>
      </div>

      <!-- Compact totals strip — the bottom line at a glance -->
      <div v-if="totals" class="crs-totals-strip" aria-hidden="true">
        <div class="crs-pill crs-pill--received">
          <span class="crs-pill-label">התקבל</span>
          <span class="crs-pill-value ltr-number">{{ fmtMoney(totals.received) }}</span>
        </div>
        <div class="crs-pill crs-pill--expected">
          <span class="crs-pill-label">צפי</span>
          <span class="crs-pill-value ltr-number">{{ fmtMoney(totals.expected) }}</span>
        </div>
        <div class="crs-pill crs-pill--gap" :class="{ zero: !(totals.gap > 0) }">
          <span class="crs-pill-label">פער</span>
          <span class="crs-pill-value ltr-number">{{ fmtMoney(totals.gap) }}</span>
        </div>
      </div>
    </div>

    <!-- Customers by company — every company, not only the ones with a gap.
         Click a company → the donut becomes that company's matched / not paid
         / only-in-נפרעים split; click a part → the customer list. Counts are
         the same per-customer statuses the KPIs and status donut use. -->
    <div v-if="pieRows.length" class="crs-chart">
      <div class="crs-chart-head">
        <h4 class="crs-chart-title">{{ focusRow ? focusRow.company : 'לקוחות לפי חברה' }}</h4>
        <span class="crs-chart-sub">{{ focusRow ? 'לחצו על חלק לרשימת הלקוחות' : 'לחצו על חברה לפירוט' }}</span>
      </div>
      <!-- The way back sits BESIDE the pie and slides in when a company is
           open (QA 2026-10-01: it was a pill far off in the header). -->
      <div class="crs-chart-stage">
        <Transition name="crs-back">
          <button v-if="focusRow" type="button" class="crs-back" @click="focusKey = null"
                  title="חזרה לכל החברות" aria-label="חזרה לכל החברות">
            <span class="crs-back-ic">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
              </svg>
            </span>
            <span class="crs-back-txt">כל החברות</span>
          </button>
        </Transition>
        <div class="crs-chart-wrap">
          <Transition name="crs-pie" mode="out-in">
            <apexchart
              :key="focusKey || '__all__'"
              type="donut"
              height="380"
              width="100%"
              :options="donutOptions"
              :series="donutData.series"
            />
          </Transition>
        </div>
      </div>
    </div>

    <!-- Company rows as cards — the app's drill language (QA 2026-10-01: the
         wide table read as a spreadsheet). One card per insurer, labelled
         figures in fixed columns, the collection bar, and a matching total
         card. Works on every width — no separate phone table. -->
    <ul class="cr-list">
      <li v-for="(row, i) in rows" :key="row.company" :style="{ '--d': Math.min(i, 10) * 40 + 'ms' }">
        <button type="button" class="cr-row" :aria-label="'פירוט ' + row.company" @click="openRow(row)">
          <span class="cr-co">
            <span class="crs-avatar" :style="avatarStyle(row.company)" aria-hidden="true">
              <CompanyLogo :company="row.company" :size="18" :frame="false" />
            </span>
            <span class="cr-co-txt">
              <span class="cr-name">{{ row.company }}</span>
              <small v-if="row.produced || row.matched">
                <span class="ltr-number">{{ fmtInt(row.produced) }}</span> מוצרים ·
                <span class="ltr-number">{{ fmtInt(row.matched) }}</span> תואמו
              </small>
            </span>
          </span>
          <span class="cr-fig">
            <template v-if="row.received >= 0.5">
              <small>התקבל</small><span class="ltr-number">{{ fmtMoney(row.received) }}</span>
            </template>
          </span>
          <span class="cr-fig cr-fig--muted">
            <template v-if="row.expected >= 0.5">
              <small>צפי</small><span class="ltr-number">{{ fmtMoney(row.expected) }}</span>
            </template>
          </span>
          <span class="cr-fig">
            <template v-if="row.gap >= 0.5">
              <small>פער</small><span class="ltr-number" :class="gapClass(row)">{{ fmtMoney(row.gap) }}</span>
            </template>
          </span>
          <span class="cr-unpaid">
            <span v-if="row.unpaid > 0" class="crs-chip crs-chip--warn"
                  :title="fmtInt(row.unpaid_products) + ' מוצרים'">
              <span class="ltr-number">{{ fmtInt(row.unpaid) }}</span> לא שולמו
            </span>
          </span>
          <span class="crs-progress" :class="'is-' + pctState(row)" role="img"
                :aria-label="'נגבו ' + pctLabel(row) + ' מהצפי'" :title="pctTitle(row)">
            <span class="crs-progress-track"><span class="crs-progress-fill" :style="{ width: pctWidth(row) }"></span></span>
            <span class="crs-progress-pct ltr-number">{{ pctLabel(row) }}</span>
          </span>
          <svg class="crs-chevron" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
      </li>
      <li v-if="totals">
        <div class="cr-row cr-row--total">
          <span class="cr-co">
            <span class="cr-co-txt">
              <span class="cr-name">סה״כ</span>
              <small><span class="ltr-number">{{ fmtInt(totals.produced) }}</span> מוצרים ·
                <span class="ltr-number">{{ fmtInt(totals.matched) }}</span> תואמו</small>
            </span>
          </span>
          <span class="cr-fig"><template v-if="totals.received >= 0.5"><small>התקבל</small><span class="ltr-number">{{ fmtMoney(totals.received) }}</span></template></span>
          <span class="cr-fig cr-fig--muted"><template v-if="totals.expected >= 0.5"><small>צפי</small><span class="ltr-number">{{ fmtMoney(totals.expected) }}</span></template></span>
          <span class="cr-fig"><template v-if="totals.gap >= 0.5"><small>פער</small><span class="ltr-number" :class="gapClass(totals)">{{ fmtMoney(totals.gap) }}</span></template></span>
          <span class="cr-unpaid">
            <span v-if="totals.unpaid > 0" class="crs-chip crs-chip--warn"><span class="ltr-number">{{ fmtInt(totals.unpaid) }}</span> לא שולמו</span>
          </span>
          <span class="crs-progress" :class="'is-' + pctState(totals)" :title="pctTitle(totals)">
            <span class="crs-progress-track"><span class="crs-progress-fill" :style="{ width: pctWidth(totals) }"></span></span>
            <span class="crs-progress-pct ltr-number">{{ pctLabel(totals) }}</span>
          </span>
          <span></span>
        </div>
      </li>
    </ul>
    <UnpaidCompanyModal
      :open="unpaidModal.open"
      :company="unpaidModal.company"
      :data="unpaidModal.data"
      :loading="unpaidModal.loading"
      :error="unpaidModal.error"
      @close="unpaidModal.open = false"
    />
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { brandForLabel } from '../../utils/companyBrand.js'
import CompanyLogo from '../workspace/CompanyLogo.vue'
import UnpaidCompanyModal from './UnpaidCompanyModal.vue'
import { useComparisonStore } from '../../stores/comparison.js'
import { assignNearestDistinct, STATUS_COLORS } from '../../utils/chartPalette.js'
import { normalizeCompany } from '../../utils/companyNorm.js'

const props = defineProps({
  summary: { type: Object, default: null }, // { companies: [...], totals: {...} }
  // companyStatusBreakdown() rows over the whole book (see utils/).
  companyBreakdown: { type: Array, default: () => [] },
})
const emit = defineEmits(['show-customers'])

const rows = computed(() => props.summary?.companies || [])
const totals = computed(() => props.summary?.totals || null)

// ── "לקוחות לפי חברה" donut (two levels) ─────────────────────────────────
// Up to 10 companies get their own slice (palette slots 1-11 are validated);
// the rest roll into "אחרות", which drills like a company would not — it has
// no single breakdown — so clicking it does nothing.
const MAX_SLICES = 10
const STATUS_ORDER = [
  { key: 'matched', label: 'נמצא בשניהם' },
  { key: 'only_production', label: 'לא שולם' },
  { key: 'only_commission', label: 'רק בנפרעים' },
]

const pieRows = computed(() => props.companyBreakdown || [])

// Every insurer always gets a slice. One with no data in this comparison is a
// small grey slice — no %, tooltip "אין נתונים", not clickable — so the agent
// sees which companies haven't reported instead of them silently missing.
const ALL_INSURERS = ['הפניקס', 'מגדל', 'מנורה', 'הראל', 'כלל', 'מור', 'אלטשולר', 'מיטב', 'הכשרה', 'ילין', 'אנליסט']
const NO_DATA_COLOR = '#D5D5D8'
function sameCompany(a, b) {
  const na = normalizeCompany(a) || a
  const nb = normalizeCompany(b) || b
  return na === nb || na.startsWith(nb) || nb.startsWith(na)
}
const emptyCompanies = computed(() =>
  ALL_INSURERS.filter((n) => !pieRows.value.some((r) => sameCompany(r.company, n)))
)
const focusKey = ref(null)
const focusRow = computed(() => pieRows.value.find((r) => r.key === focusKey.value) || null)
// A new comparison can drop the focused company — fall back to all companies.
watch(pieRows, () => { if (focusKey.value && !focusRow.value) focusKey.value = null })

// ApexCharts fills need concrete colors — resolve any CSS-var fallback to hex.
function donutColor(company) {
  const c = companyColor(company)
  return typeof c === 'string' && c.startsWith('var(') ? '#4E9DD0' : c
}

const donutData = computed(() => {
  const r = focusRow.value
  if (r) {
    const parts = STATUS_ORDER.filter((s) => r[s.key] > 0)
    return {
      labels: parts.map((s) => s.label),
      series: parts.map((s) => r[s.key]),
      colors: parts.map((s) => STATUS_COLORS[s.key]),
      keys: parts.map((s) => s.key),
    }
  }
  const head = pieRows.value.slice(0, MAX_SLICES)
  const tail = pieRows.value.slice(MAX_SLICES)
  const labels = head.map((x) => x.company)
  const series = head.map((x) => x.total)
  const colors = head.map((x) => donutColor(x.company))
  const keys = head.map((x) => x.key)
  if (tail.length) {
    labels.push('אחרות')
    series.push(tail.reduce((sum, x) => sum + x.total, 0))
    colors.push('#B9B9BE')
    keys.push(null)
  }
  // Grey no-data slices: a fixed ~3% sliver each, so they read as present but
  // never compete with real data.
  const dataSum = series.reduce((a, v) => a + v, 0)
  const sliver = Math.max(1, Math.round(dataSum * 0.03))
  for (const name of emptyCompanies.value) {
    labels.push(name)
    series.push(sliver)
    colors.push(NO_DATA_COLOR)
    keys.push('empty:' + name)
  }
  return { labels, series, colors, keys }
})

// Level 1 centre = number of companies, NOT a customer sum: a customer with
// products at two companies sits in both slices, so the slices add up to more
// than the book's distinct customers (821 vs the KPI's 562 on live data).
const donutTotal = computed(() =>
  focusRow.value ? focusRow.value.total : pieRows.value.length + emptyCompanies.value.length
)
const isEmptySlice = (i) => String(donutData.value.keys[i] || '').startsWith('empty:')

function onSlice(index) {
  const key = donutData.value.keys[index]
  if (!key || isEmptySlice(index)) return
  const r = focusRow.value
  // Deferred: the level change remounts the chart (:key), and doing that inside
  // ApexCharts' own click handler makes it query a destroyed chart.
  if (!r) { setTimeout(() => { focusKey.value = key }, 0); return }
  const status = STATUS_ORDER.find((s) => s.key === key)
  emit('show-customers', { title: `${r.company} — ${status.label}`, customers: r.customers[key] })
}

// Table row / card: a company with unpaid customers explains WHY (its unpaid
// customers, their products and the expected commission); otherwise it opens
// the company's customer list.
const comparisonStore = useComparisonStore()
const unpaidModal = ref({ open: false, company: '', data: null, loading: false, error: '' })
async function openRow(row) {
  if (!(row.unpaid > 0)) { openCompany(row.company); return }
  unpaidModal.value = { open: true, company: row.company, data: null, loading: true, error: '' }
  try {
    const data = await comparisonStore.fetchCompanyUnpaid(row.company)
    if (unpaidModal.value.company === row.company) unpaidModal.value.data = data
  } catch {
    unpaidModal.value.error = 'טעינת הפירוט נכשלה. נסו שוב.'
  } finally {
    unpaidModal.value.loading = false
  }
}

// → that company's customers, every status.
function openCompany(company) {
  const k = normalizeCompany(company) || company
  const r = pieRows.value.find((x) => x.key === k || x.company === company)
  if (!r) return
  const customers = [...r.customers.matched, ...r.customers.only_production, ...r.customers.only_commission]
  emit('show-customers', { title: `${r.company} — כל הלקוחות`, customers })
}

const donutOptions = computed(() => ({
  chart: {
    type: 'donut',
    fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
    events: {
      dataPointSelection: (_e, _ctx, cfg) => onSlice(cfg.dataPointIndex),
    },
  },
  labels: donutData.value.labels,
  colors: donutData.value.colors,
  stroke: { width: 3, colors: ['#ffffff'] },
  dataLabels: {
    enabled: true,
    // % of REAL customers — the grey no-data slivers must not dilute it.
    formatter: (_pct, o) => {
      if (isEmptySlice(o.seriesIndex)) return ''
      const v = Number(o.w.globals.series[o.seriesIndex]) || 0
      const real = donutData.value.series.reduce((a, x, i) => a + (isEmptySlice(i) ? 0 : x), 0)
      const pct = real ? (v / real) * 100 : 0
      // No legend any more — a large slice names itself; small ones on hover.
      if (pct < 4) return ''
      const name = o.w.globals.labels[o.seriesIndex] || ''
      return pct >= 7 ? [name, `${Math.round(pct)}%`] : `${Math.round(pct)}%`
    },
    style: { fontFamily: 'Heebo, sans-serif', fontSize: '12px', fontWeight: 700 },
    dropShadow: { enabled: false },
  },
  // Legend removed (QA 2026-10-01): slices carry their names.
  legend: {
    show: false,
    position: 'bottom',
    fontFamily: 'Heebo, sans-serif',
    fontSize: '12px',
    labels: { colors: '#706E6B' },
    markers: { width: 10, height: 10, radius: 3 },
    itemMargin: { horizontal: 8, vertical: 3 },
    onItemClick: { toggleDataSeries: false },
  },
  plotOptions: {
    pie: {
      expandOnClick: false,
      donut: {
        size: '52%',   /* a thicker ring (was 66%) */
        labels: {
          show: true,
          name: { fontFamily: 'Heebo, sans-serif', fontSize: '12px', color: '#706E6B' },
          value: {
            fontFamily: 'Heebo, sans-serif',
            fontSize: '26px',
            fontWeight: 800,
            color: '#181818',
            formatter: (v, w) => {
              const i = w?.globals?.series?.indexOf(Number(v))
              return i != null && i >= 0 && isEmptySlice(i) ? 'אין נתונים' : fmtInt(Number(v))
            },
          },
          total: {
            show: true,
            label: focusRow.value ? 'לקוחות' : 'חברות',
            fontFamily: 'Heebo, sans-serif',
            fontSize: '12px',
            color: '#706E6B',
            formatter: () => fmtInt(donutTotal.value),
          },
        },
      },
    },
  },
  tooltip: {
    y: { formatter: (v, o) => (isEmptySlice(o?.dataPointIndex) ? 'אין נתונים' : `${fmtInt(Number(v))} לקוחות`) },
    style: { fontFamily: 'Heebo, sans-serif' },
  },
  states: { active: { filter: { type: 'none' } } },
}))

// One distinct palette color per company, anchored to its brand hue — the
// SAME assignment mechanism the automation canvas uses, so a company keeps
// its color across tabs.
// Keyed over table rows AND pie companies so the donut and the table agree.
const colorMap = computed(() => {
  const names = [...new Set([...rows.value.map((r) => r.company), ...pieRows.value.map((r) => r.company)])]
  return assignNearestDistinct(names.map((n) => ({ key: n, brand: brandForLabel(n).color })))
})

function companyColor(company) {
  return colorMap.value.get(company) || 'var(--chart-2, #4E9DD0)'
}

function avatarStyle(company) {
  const c = companyColor(company)
  return {
    color: c,
    background: `color-mix(in srgb, ${c} 13%, white)`,
    borderColor: `color-mix(in srgb, ${c} 30%, transparent)`,
  }
}

// Collection rate: received out of expected (expected = received + open gap).
function pct(row) {
  const expected = Number(row?.expected || 0)
  const received = Number(row?.received || 0)
  if (expected <= 0) return received > 0 ? 1 : null
  return Math.min(received / expected, 1)
}

// Collection % is only honest when every unpaid customer has an expected
// amount. Unpaid products with none (no agreement rate / no base) add ₪0 to
// the gap, so "received ÷ expected" reads 100% while customers went unpaid
// (QA 2026-10-01: מנורה, 156 unpaid, 100%).
//   unknown — unpaid customers exist and NONE were priced → can't compute
//   partial — some unpriced → the % is an upper bound ("עד X%")
function pctState(row) {
  const unpriced = Number(row?.unpriced_products || 0)
  if (Number(row?.unpaid || 0) > 0 && Number(row?.gap || 0) < 0.5) return 'unknown'
  if (unpriced > 0) return 'partial'
  return 'ok'
}

function pctWidth(row) {
  if (pctState(row) === 'unknown') return '0%'
  const p = pct(row)
  return p === null ? '0%' : `${Math.round(p * 100)}%`
}

function pctLabel(row) {
  const st = pctState(row)
  if (st === 'unknown') return 'לא ניתן לחשב'
  const p = pct(row)
  if (p === null) return ''
  return (st === 'partial' ? 'עד ' : '') + `${Math.round(p * 100)}%`
}

function pctTitle(row) {
  const st = pctState(row)
  if (st === 'unknown') {
    return `${fmtInt(row.unpaid)} לקוחות לא שולמו בלי סכום צפוי — אין שיעור הסכם או בסיס לחישוב, ולכן אי אפשר לדעת כמה נגבה`
  }
  if (st === 'partial') {
    return `${fmtInt(row.unpriced_products)} מוצרים שלא שולמו אינם מתומחרים — האחוז האמיתי נמוך מזה`
  }
  return ''
}

// Red only for a gap worth chasing — the same thresholds as every other gap in
// the app (≥ ₪100 AND ≥ 10% of what was expected); smaller ones stay grey.
function gapClass(row) {
  const gap = Number(row.gap) || 0
  const exp = Number(row.expected) || 0
  return gap >= 100 && (!exp || gap / exp >= 0.1) ? 'num-gap' : 'num-muted'
}

function fmtInt(n) {
  return Number(n || 0).toLocaleString('en-US')
}
function fmtMoney(n) {
  const v = Number(n || 0)
  return '₪' + Math.round(v).toLocaleString('en-US')
}
</script>

<style scoped>
.crs {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle, #e5e7eb);
  border-radius: var(--radius-md, 14px);
  padding: 16px 18px;
  margin-top: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.crs-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.crs-head-text {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.crs-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text, #181818);
}

.crs-sub {
  font-size: 12px;
  color: var(--text-muted, #706E6B);
  white-space: nowrap;
}

/* Totals strip */
.crs-totals-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.crs-pill {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid transparent;
}

.crs-pill-label { font-weight: 500; opacity: 0.85; }
.crs-pill-value { font-weight: 700; }

.crs-pill--received {
  background: var(--green-light, #EBF7EE);
  color: var(--green-deep, #1B5E20);
  border-color: rgba(46, 132, 74, 0.2);
}

.crs-pill--expected {
  background: var(--bg, #F3F3F3);
  color: var(--text-secondary, #3E3E3C);
  border-color: var(--border-subtle, #E5E5E5);
}

.crs-pill--gap {
  background: var(--red-light, #FEF1EE);
  color: var(--red-deep, #C23934);
  border-color: rgba(194, 57, 52, 0.2);
}

.crs-pill--gap.zero {
  background: var(--bg, #F3F3F3);
  color: var(--text-muted, #706E6B);
  border-color: var(--border-subtle, #E5E5E5);
}

/* "לא שולם לפי חברה" donut */
.crs-chart {
  margin: 4px 0 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-subtle, #e5e7eb);
}

.crs-chart-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 4px;
}

.crs-chart-title {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text, #181818);
}

.crs-chart-sub {
  font-size: 12px;
  color: var(--text-muted, #706E6B);
}

/* Three columns: the back button's own slot, the pie, an equal empty slot —
   so the pie never shifts when the button slides in. */
.crs-chart-stage {
  display: grid; grid-template-columns: 90px minmax(0, 560px) 90px;
  align-items: center; justify-content: center; gap: 12px;
}
.crs-chart-stage > .crs-back { grid-column: 1; justify-self: center; }
.crs-chart-stage > .crs-chart-wrap { grid-column: 2; }
.crs-chart-wrap { direction: ltr; width: 100%; }

/* Back to all companies — beside the pie, medium, the tab's green. */
.crs-back {
  display: inline-flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 0; border: none; background: none; font: inherit; cursor: pointer;
  color: var(--tab-comparison, #2E844A);
}
.crs-back-ic {
  width: 46px; height: 46px; border-radius: 50%;
  display: grid; place-items: center;
  border: 1.5px solid color-mix(in srgb, var(--tab-comparison, #2E844A) 45%, transparent);
  background: var(--card-bg, #fff);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-comparison, #2E844A) 16%, transparent);
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}
.crs-back:hover .crs-back-ic { background: var(--tab-comparison, #2E844A); color: #fff; transform: translateX(3px); }
.crs-back-txt { font-size: 12px; font-weight: 700; }
.crs-back:focus-visible { outline: none; }
.crs-back:focus-visible .crs-back-ic { outline: 2px solid var(--tab-comparison, #2E844A); outline-offset: 3px; }
.crs-back-enter-active { transition: opacity 0.45s ease 0.15s, transform 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.15s; }
.crs-back-leave-active { transition: opacity 0.2s ease, transform 0.25s ease; }
.crs-back-enter-from, .crs-back-leave-to { opacity: 0; transform: translateX(16px) scale(0.9); }

/* The pie swaps level with a soft scale-fade. */
.crs-pie-enter-active { transition: opacity 0.45s ease, transform 0.55s cubic-bezier(0.22, 1, 0.36, 1); }
.crs-pie-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.crs-pie-enter-from { opacity: 0; transform: scale(0.94); }
.crs-pie-leave-to { opacity: 0; transform: scale(1.03); }
@media (prefers-reduced-motion: reduce) {
  .crs-back-enter-active, .crs-back-leave-active, .crs-pie-enter-active, .crs-pie-leave-active, .crs-back-ic { transition: none; }
}
@media (max-width: 640px) {
  .crs-chart-stage { grid-template-columns: minmax(0, 1fr); }
  .crs-chart-stage > .crs-back, .crs-chart-stage > .crs-chart-wrap { grid-column: 1; }
}

/* Table */
.crs-table-wrap { overflow-x: auto; }

.crs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.crs-table th,
.crs-table td {
  padding: 10px 8px;
  text-align: center;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.crs-table th {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted, #706E6B);
  border-bottom: 1px solid var(--border-subtle, #e5e7eb);
}

.crs-table th.t-name,
.crs-table td.t-name {
  text-align: start;
  min-width: 160px;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crs-table td.t-name {
  display: flex;
  align-items: center;
  gap: 9px;
  font-weight: 600;
  color: var(--text, #181818);
}

.t-bar { min-width: 130px; }
.t-go { width: 34px; }

.crs-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.crs-company {
  overflow: hidden;
  text-overflow: ellipsis;
}

.crs-row {
  cursor: pointer;
  transition: background 0.15s var(--transition, ease);
}

.crs-row:hover { background: rgba(0, 0, 0, 0.025); }

.crs-row:focus-visible {
  outline: 2px solid var(--tab-comparison);
  outline-offset: -2px;
  border-radius: 6px;
}

.crs-row td { border-bottom: 1px solid #f1f1f3; }

.crs-row:hover .crs-chevron { transform: translateX(-2px); color: var(--text, #181818); }

.crs-chevron {
  color: var(--text-muted, #706E6B);
  transition: transform 0.2s var(--transition, ease), color 0.2s;
}

/* Number semantics */
.num-matched { color: var(--green-deep, #1B5E20); font-weight: 600; }
.num-muted { color: var(--text-muted, #706E6B); }
.num-gap { color: var(--red-deep, #C23934); font-weight: 700; }

.crs-chip {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.crs-chip--warn {
  background: var(--amber-light, #FFF3E0);
  color: #9A6B12;
  border: 1px solid rgba(201, 162, 39, 0.25);
}

/* Received-vs-expected progress */
.crs-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* A bar, not a hairline (QA 2026-10-01): 14px, softly squared ends. */
.crs-progress-track {
  flex: 1;
  height: 14px;
  border-radius: 5px;
  background: var(--bg, #F0F0F0);
  overflow: hidden;
  min-width: 70px;
}

/* When money is missing, the uncollected remainder reads as a red tint */
/* One colour for every bar (QA 2026-10-01) — the gap is carried by the red
   number, not by a red-tinted track. */
.crs-progress-track.has-gap { background: var(--bg, #F0F0F0); }

.crs-progress-fill {
  height: 100%;
  border-radius: 5px;
  background: var(--tab-comparison, #2E844A);
  transform-origin: right center;   /* RTL: grows from the start side */
  animation: crsBarIn 0.9s cubic-bezier(0.22, 1, 0.36, 1) both;
  transition: width 0.4s var(--transition, ease);
}
@keyframes crsBarIn { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@media (prefers-reduced-motion: reduce) { .crs-progress-fill { animation: none; } }

.crs-progress-pct {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted, #706E6B);
  min-width: 34px;
  text-align: start;
}

/* Totals row */
/* Same height as every other row — a thin divider, not a thick band. */
.crs-total td {
  border-top: 1px solid var(--border-subtle, #e5e7eb);
  font-weight: 700;
  color: var(--text, #181818);
}

.crs-total td.t-name { display: table-cell; }

/* Stacked cards (mobile) */
.crs-cards {
  display: none;
  list-style: none;
  margin: 0;
  padding: 0;
  flex-direction: column;
  gap: 10px;
}

.crs-card {
  width: 100%;
  text-align: start;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-subtle, #e5e7eb);
  border-radius: 12px;
  padding: 12px 14px;
  font-family: inherit;
  font-size: 13px;
  color: var(--text, #181818);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.crs-card:active { background: rgba(0, 0, 0, 0.03); }

.crs-card-top {
  display: flex;
  align-items: center;
  gap: 9px;
}

.crs-card-top .crs-company { font-weight: 700; flex: 1; }
.crs-card-top .crs-chevron { flex-shrink: 0; }

.crs-card-nums {
  display: flex;
  gap: 16px;
}

.crs-card-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.crs-card-label {
  font-size: 11px;
  color: var(--text-muted, #706E6B);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

@media (max-width: 720px) {
  .crs-table-wrap { display: none; }
  .crs-cards { display: flex; }
  .crs-totals-strip { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .crs-progress-fill, .crs-chevron, .crs-row { transition: none; }
}
/* ── Company cards (replace the table) ── */
.cr-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.cr-list li { animation: crIn 0.4s cubic-bezier(0.2, 0, 0.2, 1) both; animation-delay: var(--d); }
@keyframes crIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.cr-row {
  width: 100%; display: grid; align-items: center; gap: 14px;
  grid-template-columns: minmax(170px, 1.5fr) 100px 100px 90px 110px minmax(150px, 1.3fr) 16px;
  padding: 12px 16px; border: 1px solid var(--border-subtle, #e5e7eb); border-radius: 12px;
  background: var(--card-bg, #fff); font: inherit; color: var(--text, #181818); text-align: right;
  cursor: pointer; transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.cr-row:hover { border-color: var(--tab-comparison, #2E844A); box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-comparison, #2E844A) 12%, transparent); }
.cr-row:focus-visible { outline: 2px solid var(--tab-comparison, #2E844A); outline-offset: 2px; }
.cr-row--total { cursor: default; background: var(--bg, #F3F3F3); border-color: transparent; }
.cr-row--total:hover { box-shadow: none; border-color: transparent; }
.cr-co { display: flex; align-items: center; gap: 10px; min-width: 0; }
.cr-co-txt { display: flex; flex-direction: column; min-width: 0; }
.cr-name { font-size: 14.5px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cr-co-txt small { font-size: 11.5px; color: var(--text-muted, #706E6B); }
.cr-fig { display: flex; flex-direction: column; align-items: flex-start; font-size: 15px; font-weight: 800; }
.cr-fig small { font-size: 11px; font-weight: 500; color: var(--text-muted, #706E6B); }
.cr-fig--muted > span { color: var(--text-secondary, #3E3E3C); font-weight: 700; }
.cr-unpaid { display: flex; }
.cr-row .crs-progress { display: flex; align-items: center; gap: 8px; }
/* spans in the card → make the bar parts blocks, or their width is ignored */
.cr-row .crs-progress-track, .cr-row .crs-progress-fill { display: block; }
.cr-row .crs-chevron { color: var(--text-muted, #706E6B); }
@media (max-width: 900px) {
  .cr-row { grid-template-columns: minmax(0, 1fr) 90px 90px 14px; row-gap: 10px; }
  .cr-row > .cr-fig--muted, .cr-row > .cr-unpaid { display: none; }
  .cr-row > .crs-progress { grid-column: 1 / -1; grid-row: 2; }
}
@media (prefers-reduced-motion: reduce) { .cr-list li { animation: none; } .cr-row { transition: none; } }
/* Collection % that can't be trusted says so. */
.crs-progress.is-unknown .crs-progress-pct { color: var(--amber, #8A6300); font-weight: 700; white-space: nowrap; }
.crs-progress.is-unknown .crs-progress-track {
  background: repeating-linear-gradient(-45deg, var(--bg, #F3F3F3) 0 6px, color-mix(in srgb, var(--amber, #8A6300) 10%, var(--bg, #F3F3F3)) 6px 12px);
}
.crs-progress.is-partial .crs-progress-pct { color: var(--text, #181818); font-weight: 700; white-space: nowrap; }
.crs-progress.is-partial .crs-progress-fill { opacity: 0.55; }
.crs-progress[title]:not([title=""]) { cursor: help; }
</style>
