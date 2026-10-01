<template>
  <div ref="dashRoot" class="prod-dashboard">
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

    <!-- What needs the agent's hand, worst first — each line opens its drill. -->
    <ProductionActions @open="onAction" />

    <!-- Two questions, two views. The tab used to be one 3,500px scroll that
         alternated between "what is in my book" and "was I paid correctly",
         card after card at the same weight, and agents got lost in it
         (QA 2026-09-30). Both halves stay MOUNTED (v-show) so each loads once
         and the band above can open drills that live in either. -->
    <div class="pd-switch" role="tablist" aria-label="תצוגה"
         :style="{ '--pd-i': VIEWS.findIndex(v => v.id === view) }">
      <!-- One pill that glides to the active half (same gesture as the tab strip). -->
      <span class="pd-glider" aria-hidden="true"></span>
      <button v-for="v in VIEWS" :key="v.id" role="tab" class="pd-switch-btn"
              :class="{ active: view === v.id }" :aria-selected="view === v.id"
              @click="setView(v.id)">
        <span class="pd-switch-title">{{ v.label }}</span>
        <span class="pd-switch-sub">{{ v.sub }}</span>
      </button>
    </div>

    <!-- The half you move to slides in from that side; the other hides at
         once (v-show + enter-only transition), so they never overlap. -->
    <Transition :name="'pdv-' + slideDir">
    <div v-show="view === 'book'" class="pd-view">
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
    </div>

    </Transition>

    <Transition :name="'pdv-' + slideDir">
    <div v-show="view === 'commission'" class="pd-view">
      <ProductionTrendChart @go-to-automation="$emit('go-to-automation')" />
      <!-- Actual vs agreed commission, per company. -->
      <RateAuditPanel ref="auditRef" @navigate="$emit('navigate', $event)" />
      <!-- Month-over-month movers; also owns the unpaid / checked drills. -->
      <ProductionAlerts ref="alertsRef" />
    </div>
    </Transition>

    <!-- Reaching the bottom draws a quiet growth chart behind the cards. -->
    <ProdScrollGraph />

    <!-- KPI drill: the shared shell (iPhone-style grow from the card) and
         the same language as the tab's other drills. -->
    <DataModal :open="!!drilldown" :origin="ddOrigin" :title="drilldownTitle" @close="drilldown = null">
      <KpiDrill v-if="drilldown" :kind="drilldown" :analytics="analytics" />
    </DataModal>
  </div>
</template>

<script setup>
import { computed, ref, nextTick } from 'vue'
import ProductionTrendChart from './ProductionTrendChart.vue'
import KpiGlyph from './KpiGlyph.vue'
import { CHART_PALETTE } from '../../utils/chartPalette.js'

const props = defineProps({
  analytics: { type: Object, required: true },
})

import ProductionBreakdown from './ProductionBreakdown.vue'
import RateAuditPanel from './RateAuditPanel.vue'
import ProductionAlerts from './ProductionAlerts.vue'
import ProductionActions from './ProductionActions.vue'
import ProdScrollGraph from './ProdScrollGraph.vue'
import { useScrollReveal } from '../../composables/useScrollReveal'
import DataModal from './DataModal.vue'
import KpiDrill from './KpiDrill.vue'
import { brandForLabel } from '../../utils/companyBrand'
import { invalidateCachedGet } from '../../utils/cachedGet'

// Fresh view → fresh data. Runs in setup, i.e. before any child mounts and
// reads the shared cache.
invalidateCachedGet()

const VIEWS = [
  { id: 'commission', label: 'העמלות שלי', sub: 'מה התקבל מול מה שמגיע' },
  { id: 'book', label: 'התיק שלי', sub: 'חברות, מוצרים ולקוחות' },
]
// Always opens on "העמלות שלי" (QA 2026-09-30). The last choice is NOT
// remembered: a remembered "התיק שלי" read as the default being wrong.
const view = ref('commission')
// Which way the content slides: toward the half that was chosen. In RTL the
// first tab sits on the right, so moving to a LATER tab moves leftward.
const slideDir = ref('left')
function setView(v) {
  if (v === view.value) return
  const from = VIEWS.findIndex(x => x.id === view.value)
  const to = VIEWS.findIndex(x => x.id === v)
  slideDir.value = to > from ? 'left' : 'right'
  view.value = v
  // Charts in the half that was hidden measured a 0px width when they first
  // drew; ApexCharts redraws on window resize.
  nextTick(() => window.dispatchEvent(new Event('resize')))
}

// Scroll reveal, same as the comparison tab: each card rises and fades in the
// first time it scrolls into view. A card in the hidden half reveals when that
// half is opened and it comes on screen.
const dashRoot = ref(null)
useScrollReveal(dashRoot, '.pact, .trend-card, .ra-card, .pa-card, .chart-card')

const alertsRef = ref(null)
const auditRef = ref(null)
// A "דורש טיפול" line opens the drill that answers it, grown out of the line.
function onAction({ kind, company, el }) {
  if (kind === 'unpaid') alertsRef.value?.openUnpaid(el)
  else if (kind === 'checked') alertsRef.value?.openChecked(el)
  else if (kind === 'company') auditRef.value?.openCompanyByName(company, el)
  else if (kind === 'explain') auditRef.value?.openExplain(el)
}

defineEmits(['go-to-automation', 'navigate'])

const topMetric = ref('premium')
const drilldown = ref(null)

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

const ddOrigin = ref(null)
function openDrilldown(type, originEl = null) {
  ddOrigin.value = originEl
  drilldown.value = type
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
const brandCount = computed(() => {
  const set = new Set()
  for (const r of props.analytics.company_breakdown || []) {
    const b = brandForLabel(r.company || '')
    set.add(b && b.label && b.label !== '?' ? b.label : r.company)
  }
  return set.size
})

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
    // Brands, not legal entities: the card said 16 while its drill and the
    // company chart show 11 (הפניקס ביטוח + הפניקס אקסלנס are one insurer).
    { key: 'companies', drill: 'companies', label: 'חברות', value: String(brandCount.value || a.companies_count),
      color: 'var(--chart-4)', ink: 'var(--chart-4)' },
    { key: 'active', drill: 'status', label: 'מוצרים פעילים', value: `${activePercent.value}%`,
      color: 'var(--chart-10)', ink: 'var(--chart-10)' },
  ]
})

// Bright-bold categorical palette shared across all chart bars (see
// utils/chartPalette.js). Each bar/company/category gets a clearly distinct hue.
const PALETTE_SERIES = CHART_PALETTE
// --tab-production resolved (ApexCharts can't read CSS variables).
const TAB_PRODUCTION = '#2F73C4'

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

// One measure, one colour: the Production tab's cobalt. A colour per client
// read as a legend that did not exist. Click → clients drill-down.
const topClientsChartOptions = computed(() => ({
  chart: {
    type: 'bar', toolbar: { show: false }, fontFamily: 'Heebo, sans-serif',
    animations: { enabled: true, easing: 'easeinout', speed: 700 },
    events: { dataPointSelection: () => openDrilldown(topMetric.value === 'premium' ? 'premium' : 'accumulation') },
  },
  plotOptions: { bar: { horizontal: true, borderRadius: 6, barHeight: '65%' } },
  dataLabels: { enabled: false },
  xaxis: {
    categories: topClientsData.value.map(c => c.name || c.id_number),
    labels: { style: { fontFamily: 'Heebo, sans-serif' }, formatter: v => '₪' + Math.round(v).toLocaleString() },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' } } },
  colors: [TAB_PRODUCTION],
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
  gap: 12px;   /* tighter rhythm between blocks (QA 2026-10-01) */
  animation: slideUp 0.4s var(--transition);
}

/* ── The two views ── */
.pd-view { display: flex; flex-direction: column; gap: 12px; }
.pd-switch {
  position: relative;
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
  padding: 5px; border-radius: 16px;
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
  position: sticky; top: 86px; z-index: 20; /* under the tab strip, always reachable */
}
.pd-switch-btn {
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 7px 12px; border-radius: 11px; border: none; background: transparent;
  font: inherit; color: var(--text-muted); cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}
.pd-switch-btn:hover:not(.active) { background: var(--tab-production-wash); color: var(--tab-production); }
.pd-switch-btn { position: relative; z-index: 1; }
.pd-switch-btn.active { background: transparent; color: #fff; transition: color 0.4s ease 0.2s; }
/* The gliding pill: half the bar minus the gaps, moved by index. RTL: index 0
   is on the right, and translateX(-100%) walks it to the left. */
.pd-glider {
  position: absolute; top: 5px; bottom: 5px; inset-inline-start: 5px;
  width: calc(50% - 8px);   /* (bar − 2×5px padding − 6px gap) / 2 */ border-radius: 11px; z-index: 0; pointer-events: none;
  background: var(--tab-production);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-production) 30%, transparent);
  transform: translateX(calc(var(--pd-i, 0) * (-100% - 6px)));
  /* Slow and silky (QA 2026-10-01): a long ease-out that settles softly. */
  transition: transform 0.75s cubic-bezier(0.22, 1, 0.36, 1);
}
/* Content slide — enter only; the leaving half is hidden immediately. */
.pdv-left-enter-active, .pdv-right-enter-active {
  /* The pill leads by a beat; the content follows, short travel, long settle. */
  transition: opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1) 0.1s,
              transform 0.85s cubic-bezier(0.22, 1, 0.36, 1) 0.1s;
}
.pdv-left-leave-active, .pdv-right-leave-active { display: none; }
.pdv-left-enter-from { opacity: 0; transform: translateX(-24px) scale(0.995); }
.pdv-right-enter-from { opacity: 0; transform: translateX(24px) scale(0.995); }
@media (prefers-reduced-motion: reduce) {
  .pd-glider, .pdv-left-enter-active, .pdv-right-enter-active { transition: none; }
}
.pd-switch-btn:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
.pd-switch-title { font-size: 15px; font-weight: 700; }
.pd-switch-sub { font-size: 12px; opacity: 0.8; }
@media (max-width: 640px) {
  .pd-switch { top: 70px; }
  .pd-switch-sub { display: none; }
}
@media (prefers-reduced-motion: reduce) { .pd-switch-btn { transition: none; } }

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
