<template>
  <div class="bi-dashboard">
    <!-- KPI Cards Row — same design as the Production KPIs: category colour,
         duotone badge + oversized corner glyph (KpiGlyph), calm hover. -->
    <!-- KPIs in one panel, spaced from the bar above and the hero below. The
         "לא שולם" card is the one that needs the agent — it breathes softly
         and glows on hover (QA 2026-10-01). -->
    <div class="kpi-panel" :class="{ 'kpi-panel--joined': props.joined }">
    <div class="kpi-row">
      <div
        v-for="k in kpiCards" :key="k.key"
        class="kpi-card" :class="{ clickable: !!k.open, 'kpi-card--alert': k.key === 'unpaid' && Number(k.value) > 0 }"
        :style="{ '--k': k.color, '--k-ink': k.ink }"
        :title="k.title || null"
        :role="k.open ? 'button' : null" :tabindex="k.open ? 0 : null"
        @click="k.open && k.open($event.currentTarget)" @keydown.enter="k.open && k.open($event.currentTarget)"
      >
        <span class="kpi-ghost" aria-hidden="true"><KpiGlyph :name="k.glyph" :size="92" :stroke="1.2" /></span>
        <span class="kpi-icon"><KpiGlyph :name="k.glyph" :size="22" /></span>
        <span class="kpi-data">
          <span class="kpi-value" :class="{ 'ltr-number': k.ltr }">{{ k.value }}</span>
          <span class="kpi-label">{{ k.label }}</span>
        </span>
        <!-- Mail / Excel moved into the list this card opens (they covered
             the number here — QA 2026-10-01). -->
      </div>
    </div>
    <!-- Empty savings funds (₪0 accumulation, no premium) are not unpaid —
         nothing to earn on — so the comparison lists them apart (QA
         2026-10-01). One quiet line, opens the same customer list. -->
    <button v-if="props.noValueCustomers.length" type="button" class="kpi-novalue"
            @click="openFilterModal('קופות ריקות או לא פעילות', props.noValueCustomers, $event.currentTarget)">
      <span class="ltr-number">{{ props.noValueCustomers.length }}</span>
      לקוחות עם קופות ריקות או לא פעילות — אין עליהן עמלה, לא נספרו כ"לא שולם"
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
           stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6" /></svg>
    </button>

    </div>

    <!-- HERO: Customer Status Distribution -->
    <div class="hero-card">
      <div class="hero-header">
        <h2 class="hero-title">התפלגות לקוחות</h2>
        <span class="hero-badge">{{ statusTotal }} לקוחות</span>
      </div>
      <div class="hero-body">
        <apexchart
          type="donut"
          :height="270"
          :options="statusDonutOptions"
          :series="statusDonutSeries"
          @dataPointSelection="onStatusClick"
        />
      </div>
      <div class="hero-stats">
        <div
          v-for="(item, i) in statusItems"
          :key="i"
          class="hero-stat"
          @click="onLegendClick(item.key)"
        >
          <span class="hero-stat-dot" :style="{ background: item.color }"></span>
          <div class="hero-stat-info">
            <span class="hero-stat-count">{{ item.count }}</span>
            <span class="hero-stat-label">{{ item.label }}</span>
          </div>
          <span class="hero-stat-pct" :style="{ color: item.color }">{{ pctOf(item.count) }}%</span>
        </div>
      </div>

      <!-- Same distribution per COMPANY. The merged נפרעים file covers every
           company, so "how many are unpaid" is only half the answer — this
           says at which company. Click a segment to drill straight in. -->
      <div v-if="companyStatusRows.length > 1" class="hero-bycompany">
        <div class="hbc-head">
          <h3 class="hbc-title">לפי חברה</h3>
          <span class="hbc-hint">לחצו על עמודה לצלילה לחברה</span>
        </div>
        <apexchart
          type="bar"
          :height="Math.max(190, companyStatusRows.length * 38 + 70)"
          :options="companyStatusOptions"
          :series="companyStatusSeries"
        />
        <p class="hbc-note">לקוח המחזיק מוצרים בכמה חברות נספר בכל אחת מהן.</p>
      </div>
    </div>

    <!-- The company pill bar was removed (QA 2026-10-01). Company drills now
         filter only the list they open, never the whole page. -->


    <!-- The unpaid card was removed (QA 2026-10-01): the "לא שולם" KPI above
         already opens the same list and carries mail + Excel. -->

    <!-- Top Clients -->
    <div v-if="topClientsData.length > 0" class="chart-card wide-card tc-card">
      <div class="chart-header">
        <h3>{{ isGemel ? 'לקוחות לפי צבירה' : 'לקוחות לפי פרמיה' }}</h3>
        <div class="chart-actions">
          <button
            v-for="n in topNOptions"
            :key="n"
            class="toggle-btn"
            :class="{ active: topN === n }"
            @click="topN = n"
          >{{ n }}</button>
        </div>
      </div>
      <apexchart
        type="bar"
        :height="topN > 30 ? 400 : 300"
        :options="topClientsChartOptions"
        :series="topClientsChartSeries"
        @dataPointSelection="onTopClientClick"
      />
    </div>

    <!-- Product Breakdown Treemap -->
    <div class="chart-card wide-card product-card">
      <div class="chart-header">
        <h3>עמלה לפי מוצר</h3>
        <div class="chart-actions">
          <button
            class="toggle-btn"
            :class="{ active: productMetric === 'count' }"
            @click="productMetric = 'count'"
          >כמות</button>
          <button
            class="toggle-btn"
            :class="{ active: productMetric === 'amount' }"
            @click="productMetric = 'amount'"
          >סכום</button>
        </div>
      </div>
      <apexchart
        v-if="productTreemapSeries[0].data.length > 0"
        type="treemap"
        :height="340"
        :options="productTreemapOptions"
        :series="productTreemapSeries"
        @dataPointSelection="onProductClick"
      />
      <div v-else class="empty-chart">
        <span>אין נתוני מוצרים</span>
      </div>
    </div>

    <!-- Detail Modal (single customer) -->
    <CustomerDetailModal
      :customer="detailCustomer"
      :origin="detailOrigin"
      :commissionRates="commissionRates"
      :category="props.categoryLabel"
      :userName="authStore.user?.full_name || ''"
      @close="detailCustomer = null"
      @drill="onDrillFromModal"
    />

    <!-- Customer list (chart / KPI click) — the shared centred drill with
         the iPhone-style grow, in the comparison green (QA 2026-10-01). -->
    <DataModal :open="filterModal.open" :origin="fmOrigin" :title="filterModal.title"
               :badge="filterModal.customers.length" :period="periodLabel"
               accent="var(--tab-comparison)" @close="closeFilterModal">
      <!-- "רק בנפרעים" explains itself before the list (QA 2026-10-01). -->
      <CustomerBridge v-if="filterModal.kind === 'only' && props.population && props.population.commission_only"
                      mode="only" :population="props.population" class="fm-explain" />
      <CompareCustomerList :customers="filterModal.customers" :rates="commissionRates"
                           :actions="filterModal.actions || null"
                           :initial-company="filterModal.company || null"
                           :paid-view="!!filterModal.paidView"
                           :category="props.categoryLabel"
                           @open="(c, el) => openDetailFromFilter(c, el)" />
    </DataModal>

    <!-- סה״כ לקוחות → why this number differs from the production tab. -->
    <DataModal :open="bridgeOpen" :origin="bridgeOrigin" title="סה״כ לקוחות"
               :badge="props.population?.total" :period="periodLabel"
               accent="var(--tab-comparison)" @close="bridgeOpen = false">
      <CustomerBridge v-if="props.population" :population="props.population"
                      :paid="kpiMatched.length" :unpaid="kpiUnpaid.length" />
    </DataModal>

  </div>
</template>

<script setup>
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import KpiGlyph from '../workspace/KpiGlyph.vue'
import CustomerBridge from './CustomerBridge.vue'
import { ref, computed, watch, onMounted, onUnmounted, toRef, nextTick } from 'vue'
import * as XLSX from 'xlsx'
import api from '../../api/client.js'
import { useAuthStore } from '../../stores/auth.js'
import { openMailCompose } from '../../utils/mailHelper.js'
import { calcExpectedCommission } from '../../utils/commissionCalc.js'
import { CHART_PALETTE, STATUS_COLORS } from '../../utils/chartPalette.js'
import { companyStatusBreakdown } from '../../utils/companyStatusBreakdown.js'
import CustomerDetailModal from './CustomerDetailModal.vue'
import CompareCustomerList from './CompareCustomerList.vue'
import { expectedFor } from '../../utils/expectedCommission.js'
import DataModal from '../workspace/DataModal.vue'
import { useAiViewContext } from '../../composables/useAiViewContext.js'
import { useAiContextStore } from '../../stores/aiContext.js'

const props = defineProps({
  customers: { type: Array, required: true },
  // only-production customers whose every product is an empty savings fund
  noValueCustomers: { type: Array, default: () => [] },
  // summary.population — the exact production ↔ comparison customer bridge
  population: { type: Object, default: null },
  categoryLabel: { type: String, default: '' },
  companySource: { type: String, default: '' },
  companySources: { type: Array, default: () => [] },
  // Company clicked in the cross-company summary — preselects the matching
  // pill once companySources is populated, then emits initial-company-applied
  // so the parent clears it (manual pill clicks aren't overridden later).
  initialCompany: { type: String, default: '' },
  // Period of the production file driving this comparison ("2026-04-01").
  // When set, the period chip displays it next to category, and the
  // "עמלות שהתקבלו" KPI labels itself with the period — so the user can
  // see at a glance "this is April's commissions, not lifetime totals".
  periodMonth: { type: String, default: '' },
  // Sits directly under the tab's file bar → drawn as one card with it.
  joined: { type: Boolean, default: false },
  periodFilesCount: { type: Number, default: 0 },
  periodFilesExcluded: { type: Number, default: 0 },
})

const emit = defineEmits(['drill-customer', 'initial-company-applied', 'mismatch'])

const authStore = useAuthStore()
const productMetric = ref('count')
const detailCustomer = ref(null)
const commissionRates = ref([])
const showUnpaidStrip = ref(false)
const companyFilter = ref(null)

// The AI no longer owns a card, a sheet or a viz panel here — one widget on
// the workspace rail does, and the sheet lives with it. This view's only job
// is to keep the store told what is on screen, and to stop claiming context
// once it unmounts (otherwise the assistant would still describe a comparison
// the agent has navigated away from).
// The mismatch figures and their drill-in now live in the tab toolbar as one
// icon, so the parent needs both. The strip they replaced spent a full-width
// band restating a number the icon carries in a badge.

const aiCtx = useAiContextStore()
const aiViewContext = useAiViewContext({
  viewKey: 'commission-comparison',
  customers: toRef(props, 'customers'),
  categoryLabel: toRef(props, 'categoryLabel'),
  companySources: toRef(props, 'companySources'),
})
watch(aiViewContext, (ctx) => aiCtx.publish(ctx), { immediate: true })
onUnmounted(() => aiCtx.clear())

onMounted(async () => {
  try {
    const res = await api.get('/commission-rates')
    commissionRates.value = res.data
  } catch (e) { /* rates not available */ }
  // Reveal unpaid strip with delay for smooth entrance
  setTimeout(() => { showUnpaidStrip.value = true }, 600)
})

// ─── Computed data ───

function fuzzyCompanyMatch(a, b) {
  if (!a || !b) return false
  const al = a.toLowerCase()
  const bl = b.toLowerCase()
  return al.includes(bl) || bl.includes(al)
}

function matchesCompanyFilter(productCompany) {
  if (!companyFilter.value) return false
  return fuzzyCompanyMatch(productCompany, companyFilter.value)
}

// Preselect the pill matching initialCompany (drill from the summary table).
// Waits for companySources to populate; falls back to "הכל" when no pill
// matches. Emits so the parent clears the one-shot prop.
watch(
  [() => props.initialCompany, () => props.companySources],
  ([company, sources]) => {
    if (!company || !(sources || []).length) return
    // The pill bar only renders for >1 sources — never apply a filter the
    // user can't see or clear.
    // No page-wide filter any more (the pill bar that showed and cleared it
    // is gone) — the whole book stays in view.
    emit('initial-company-applied')
  },
  { immediate: true },
)

const displayCustomers = computed(() => {
  if (!companyFilter.value) return props.customers
  return props.customers.filter(c => {
    // Check commission products
    const commProducts = c.commission_products || []
    const matchedProducts = c.product_matches?.matched || []
    const unmatchedComm = c.product_matches?.unmatched_commission || []
    const prodProducts = c.production_products || []
    const unmatchedProd = c.product_matches?.unmatched_production || []
    const allProducts = [...commProducts, ...matchedProducts, ...unmatchedComm, ...prodProducts, ...unmatchedProd]
    return allProducts.some(p => matchesCompanyFilter(p.company || p.company_full || ''))
  })
})

const commissionCustomers = computed(() =>
  displayCustomers.value.filter(c => c.match_status === 'matched' || c.match_status === 'only_commission')
)

const isGemel = computed(() => {
  const label = props.categoryLabel || ''
  return label.includes('גמל') || label.includes('השתלמות')
})

const matchedCustomers = computed(() => displayCustomers.value.filter(c => c.match_status === 'matched'))
const onlyProdCustomers = computed(() => displayCustomers.value.filter(c => c.match_status === 'only_production'))
const onlyCommCustomers = computed(() => displayCustomers.value.filter(c => c.match_status === 'only_commission'))

// Item 5: For gemel, exclude customers where ALL production products have accumulation = 0/null
function unpaidOf(onlyProd) {
  if (!isGemel.value) return onlyProd
  return onlyProd.filter(c => {
    const products = c.production_products || c.product_matches?.unmatched_production || []
    return products.some(p => p.accumulation != null && p.accumulation > 0)
  })
}
const effectiveUnpaidCustomers = computed(() => unpaidOf(onlyProdCustomers.value))

// ── KPI row: ALWAYS the whole book ──
// The KPIs are the fixed frame of reference. They read props.customers, never
// the company filter — a click on a chart, pill or summary drill used to
// rewrite them. Total = the same three buckets the status donut sums, so the
// headline and the donut agree (it used to count only נפרעים customers: 540
// against the donut's 562).
const kpiMatched = computed(() => props.customers.filter(c => c.match_status === 'matched'))
const kpiUnpaid = computed(() => unpaidOf(props.customers.filter(c => c.match_status === 'only_production')))
const kpiOnlyComm = computed(() => props.customers.filter(c => c.match_status === 'only_commission'))
const kpiTotalCustomers = computed(() =>
  kpiMatched.value.length + kpiUnpaid.value.length + kpiOnlyComm.value.length
)
const kpiCommissionCustomers = computed(() => [...kpiMatched.value, ...kpiOnlyComm.value])

const totalCommission = computed(() =>
  kpiCommissionCustomers.value.reduce((sum, c) => sum + (c.total_commission || 0), 0)
)

const totalBalance = computed(() => {
  let total = 0
  for (const c of kpiCommissionCustomers.value) {
    const matched = c.product_matches?.matched || []
    for (const p of matched) {
      total += (p.balance || 0)
    }
    const unmatchedComm = c.product_matches?.unmatched_commission || []
    for (const p of unmatchedComm) {
      total += (p.balance || 0)
    }
  }
  return total
})

// Strip Hebrew definite article ה (e.g. הפניקס → פניקס)
function stripHe(s) { return s.startsWith('ה') && s.length > 2 ? s.slice(1) : null }

// Category hints for preferring the right rate when multiple match (e.g. פניקס גמל vs פניקס פוליסות)
const INSURANCE_HINTS = ['פוליסות', 'ביטוח', 'פוליסה']
const GEMEL_HINTS = ['גמל', 'השתלמות']

function getCategoryHints(product) {
  if (props.categoryLabel) {
    if (props.categoryLabel.includes('ביטוח')) return INSURANCE_HINTS
    if (props.categoryLabel.includes('גמל')) return GEMEL_HINTS
  }
  // Fallback: infer from product data
  if (product.accumulation && product.accumulation > 0) return GEMEL_HINTS
  if (product.premium && product.premium > 0) return INSURANCE_HINTS
  return null
}

// Rate lookup for unpaid expected commission calculation
function findRate(product) {
  if (!commissionRates.value.length) return null
  const base = [product.company, product.company_full].filter(Boolean)
  const candidates = [...base]
  for (const c of base) { const s = stripHe(c); if (s) candidates.push(s) }
  // Collect all matching rates
  const matches = new Set()
  for (const companyName of candidates) {
    const cl = companyName.toLowerCase()
    const fw = cl.split(/[\s\-]/)[0]
    for (const r of commissionRates.value) {
      const rn = r.company_name.toLowerCase()
      if (r.company_name === companyName || cl.includes(rn) || rn.includes(cl)
          || (fw.length > 2 && rn.startsWith(fw))) {
        matches.add(r)
      }
    }
  }
  if (matches.size === 0) return null
  const arr = [...matches]
  if (arr.length === 1) return arr[0].rate
  // Prefer rate matching the category
  const hints = getCategoryHints(product)
  if (hints) {
    const preferred = arr.find(r => hints.some(h => r.company_name.includes(h)))
    if (preferred) return preferred.rate
  }
  return arr[0].rate
}

// Unpaid expected commission for a list of unpaid customers.
function unpaidChargeOf(list) {
  let expectedTotal = 0
  let rawTotal = 0
  for (const c of list) {
    for (const p of (c.production_products || [])) {
      // The shared rule (backend price first) — the same number the customer
      // list and the customer window show. The old company-name matcher made
      // this card read ₪3,636 against ₪254 in the list it opens.
      const exp = expectedFor(p, commissionRates.value, props.categoryLabel)
      if (exp != null) expectedTotal += exp
      rawTotal += (p.premium || 0) || (p.accumulation || 0)
    }
  }
  return expectedTotal || rawTotal
}
// Strip below the charts follows the active filter; the KPI never does.
const totalUnpaidCharge = computed(() => unpaidChargeOf(effectiveUnpaidCustomers.value))
const kpiUnpaidCharge = computed(() => unpaidChargeOf(kpiUnpaid.value))

// The six KPI cards (colour = category; ink = text-safe shade for the badge).
const bridgeOpen = ref(false)
const bridgeOrigin = ref(null)

const kpiCards = computed(() => [
  { key: 'total', glyph: 'matched-customers', label: 'סה״כ לקוחות', value: kpiTotalCustomers.value,
    color: 'var(--tab-comparison)', ink: 'var(--tab-comparison)',
    // Opens the bridge: production → checked → + only-in-נפרעים = this number.
    open: props.population ? (el) => { bridgeOrigin.value = el; bridgeOpen.value = true } : null },
  { key: 'unpaid', glyph: 'unpaid', label: 'לא שולם', value: kpiUnpaid.value.length,
    color: '#E04B48', ink: '#C23934',
    open: (el) => openFilterModal('לא שולם', kpiUnpaid.value, el, { mail: (list) => sendAllUnpaidMail(list || kpiUnpaid.value), excel: (list) => downloadUnpaidExcel(list || kpiUnpaid.value) }),
    actions: kpiUnpaid.value.length ? { mail: () => sendAllUnpaidMail(kpiUnpaid.value), excel: () => downloadUnpaidExcel(kpiUnpaid.value), mailTitle: 'שלח מייל על כל הלקוחות שלא שולמו' } : null },
  { key: 'only', glyph: 'only-comm', label: 'רק בנפרעים', value: kpiOnlyComm.value.length,
    color: '#4E9DD0', ink: '#35719A',
    open: (el) => openFilterModal('רק בנפרעים', kpiOnlyComm.value, el, { mail: (list) => sendOnlyCommissionMail(list || kpiOnlyComm.value), excel: (list) => downloadOnlyCommissionExcel(list || kpiOnlyComm.value) }, 'only'),
    actions: kpiOnlyComm.value.length ? { mail: () => sendOnlyCommissionMail(kpiOnlyComm.value), excel: () => downloadOnlyCommissionExcel(kpiOnlyComm.value), mailTitle: 'שלח מייל על לקוחות שרק בנפרעים' } : null },
  { key: 'charge', glyph: 'charge', label: 'חיוב לא משולם', value: formatAmount(kpiUnpaidCharge.value), ltr: true, title: 'סה"כ חיוב לא משולם',
    color: '#D6336C', ink: '#C42B60' },
  { key: 'received', glyph: 'received', label: 'עמלות שהתקבלו', value: formatAmount(totalCommission.value), ltr: true,
    title: 'לפי הדיווח האחרון מכל חברה', color: '#0FA39B', ink: '#1E7D78' },
  { key: 'balance', glyph: 'balance', label: 'סה"כ יתרה', value: formatCompact(totalBalance.value), ltr: true,
    title: formatAmount(totalBalance.value), color: '#2F73C4', ink: '#2F73C4' },
])

// ─── Top Clients ───

const topNOptions = [15, 20, 50, 100]
const topN = ref(15)

// A pension fund line — by product type, or by name when the type is missing
// (מבטחים החדשה / משלימה, מקפת are pension funds by name).
const PENSION_NAME_RE = /פנסי|מבטחים החדשה|מבטחים משלימה|מקפת/
function isPensionLine(p) {
  return PENSION_NAME_RE.test(p.product_type || '') || PENSION_NAME_RE.test(p.product || '')
}
// Shared by the chart and the customer window so the two never disagree.
function insurancePremiumOf(c) {
  return [...(c.production_products || []), ...(c.paid_production_products || [])]
    .filter(p => !isPensionLine(p))
    .reduce((s, p) => s + (Number(p.premium) || 0), 0)
}

const topClientsData = computed(() => {
  const list = displayCustomers.value.map(c => {
    const name = customerName(c)
    let value = 0
    let productCount = 0
    if (isGemel.value) {
      // Gemel: sum accumulation only from company-specific data (matched + commission)
      const matchAccum = (c.product_matches?.matched || []).reduce((s, p) => s + (p.balance || p.accumulation || 0), 0)
      const commAccum = (c.product_matches?.unmatched_commission || []).reduce((s, p) => s + (p.balance || 0), 0)
      value = matchAccum + commAccum
      productCount = (c.production_products || []).length + (c.commission_products || []).length
    } else {
      // Insurance premium only. A pension fund's "premium" is its monthly
      // deposit, not an insurance premium (QA 2026-10-02: מבטחים funds pushed
      // customers to the top). Read every production line — paid ones too:
      // `total_premium` was narrowed server-side to the unpaid lines of a
      // partially-paid customer.
      value = insurancePremiumOf(c)
      productCount = (c.production_products || []).length + (c.commission_products || []).length
    }
    return {
      id_number: c.id_number,
      name,
      value,
      status: c.match_status,
      productCount,
      _raw: c,
    }
  })
    .filter(c => c.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, topN.value)

  const maxVal = list.length > 0 ? list[0].value : 1
  return list.map(c => ({ ...c, pct: Math.round((c.value / maxVal) * 100) }))
})

const topClientsChartSeries = computed(() => [{
  name: isGemel.value ? 'צבירה' : 'פרמיה',
  data: topClientsData.value.map(c => ({
    x: c.name,
    y: Math.round(c.value),
  })),
}])

const topClientsChartOptions = computed(() => ({
  chart: {
    fontFamily: 'Heebo, sans-serif',
    background: 'transparent',
    toolbar: { show: false },
  },
  plotOptions: {
    bar: {
      borderRadius: 4,
      columnWidth: '60%',
      distributed: true,
    },
  },
  colors: CHART_PALETTE,
  legend: { show: false },
  dataLabels: {
    enabled: topN.value <= 20,
    formatter: (val) => formatCompact(val),
    style: { fontFamily: 'Heebo, sans-serif', fontWeight: 700, fontSize: '10px', colors: ['#fff'] },
    dropShadow: { enabled: true, top: 0, left: 0, blur: 2, opacity: 0.5, color: '#000' },
  },
  xaxis: {
    labels: {
      show: topN.value <= 30,
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '10px', fontWeight: 600, colors: '#706E6B' },
      rotate: -45,
      rotateAlways: topClientsData.value.length > 8,
      trim: true,
      maxHeight: 80,
    },
  },
  yaxis: {
    labels: {
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' },
      formatter: (val) => formatCompact(val),
    },
  },
  grid: {
    borderColor: '#E5E5E5',
    strokeDashArray: 3,
  },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif' },
    y: { formatter: (val) => '₪ ' + Number(val).toLocaleString('he-IL') },
  },
  states: {
    hover: { filter: { type: 'darken', value: 0.08 } },
    active: { filter: { type: 'none' } },
  },
}))

function onTopClientClick(_event, _chartCtx, config) {
  const client = topClientsData.value[config.dataPointIndex]
  if (client) openDetailFromFilter(client._raw)
}

// Status donut — all three statuses. Colours come from the chart palette like
// every other chart here (they were three off-palette brand hexes).
const statusItems = computed(() => [
  { key: 'matched', label: 'נמצא בשניהם', count: matchedCustomers.value.length, color: STATUS_COLORS.matched },
  { key: 'only_production', label: 'לא שולם', count: effectiveUnpaidCustomers.value.length, color: STATUS_COLORS.only_production },
  { key: 'only_commission', label: 'רק בנפרעים', count: onlyCommCustomers.value.length, color: STATUS_COLORS.only_commission },
])

// Total shown in the hero badge and used as the percentage denominator.
// Must match the sum of visible stats — for gemel, effectiveUnpaidCustomers
// drops zero-accumulation rows, so displayCustomers.length would be larger
// than the three cards sum and the %s wouldn't add up to 100.
const statusTotal = computed(() =>
  statusItems.value.reduce((sum, s) => sum + s.count, 0)
)

// ── Agreement vs. actually-paid mismatches ───────────────────────────────
// Derived from the products themselves rather than the summary, so a drill
// into one company reports that company's mismatches, not the whole book's.
function fmtMoney(n) { return '₪' + Math.round(Math.abs(n || 0)).toLocaleString('en-US') }

const mismatchAlert = computed(() => {
  let count = 0, under = 0, over = 0, overCount = 0
  for (const c of displayCustomers.value) {
    const lines = [
      ...(c.commission_products || []),
      ...((c.product_matches?.matched) || []),
    ]
    for (const p of lines) {
      const gap = p?.commission_gap
      if (gap == null) continue
      count += 1
      if (gap > 0) under += gap
      else { over += -gap; overCount += 1 }
    }
  }
  return { count, under, over, overCount }
})

// The tab toolbar renders these as one icon with a badge, so they have to
// travel up. `immediate` because the toolbar must be right on first paint,
// not only after the next recompute.
watch(mismatchAlert, (v) => emit('mismatch', v), { immediate: true, deep: true })

// ── Same distribution, broken down BY COMPANY ────────────────────────────
// The נפרעים side is now one merged file covering every company, so a single
// donut answers "how many customers are unpaid" but not "at which company" —
// which is the actionable half. A customer is counted once per company they
// hold a product with, so the per-company columns can sum to more than the
// headline total; that's intended, not double counting.
const companyBreakdownAll = computed(() =>
  companyStatusBreakdown(props.customers, new Set(kpiUnpaid.value.map(c => c.id_number)))
)

const companyStatusRows = computed(() =>
  companyStatusBreakdown(displayCustomers.value, new Set(effectiveUnpaidCustomers.value.map(c => c.id_number)))
)

// Declared after everything it references (a const above its use is a TDZ
// crash that `vite build` never catches).
defineExpose({
  showMismatchCustomers: () => onLegendClick('matched'),
  // Lets the page-level company summary open the same customer list modal.
  openCustomerList: (title, customers) => openFilterModal(title, customers),
  // Whole-book per-company split for the page-level summary pie — built with
  // the KPI's unpaid set so its numbers match the KPIs exactly.
  companyBreakdownAll,
})

const companyStatusSeries = computed(() => [
  { name: 'נמצא בשניהם', data: companyStatusRows.value.map(r => r.matched) },
  { name: 'לא שולם', data: companyStatusRows.value.map(r => r.only_production) },
  { name: 'רק בנפרעים', data: companyStatusRows.value.map(r => r.only_commission) },
])

const companyStatusOptions = computed(() => ({
  chart: {
    type: 'bar', stacked: true, fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
    events: {
      dataPointSelection: (_e, _ctx, cfg) => {
        const row = companyStatusRows.value[cfg.dataPointIndex]
        const key = ['matched', 'only_production', 'only_commission'][cfg.seriesIndex]
        if (row) onCompanyStatusClick(row, key)
      },
    },
  },
  plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '70%' } },
  colors: statusItems.value.map(s => s.color),
  xaxis: { categories: companyStatusRows.value.map(r => r.company) },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '12px' } } },
  legend: { position: 'top', horizontalAlign: 'right', fontFamily: 'Heebo, sans-serif' },
  dataLabels: { enabled: true, style: { fontSize: '11px', fontFamily: 'Heebo, sans-serif' } },
  tooltip: { y: { formatter: (v) => `${v} לקוחות` } },
  grid: { borderColor: 'rgba(0,0,0,0.06)' },
}))

// Clicking a segment opens EXACTLY the customers that segment counts — the
// list always equals the bar's number, and holds only customers whose status
// is AT this company (QA 2026-10-02: the Harel "לא שולם" drill listed
// customers unpaid at מיטב). The list opens on this company's tab.
function onCompanyStatusClick(row, statusKey) {
  const labels = { matched: 'נמצא בשניהם', only_production: 'לא שולם', only_commission: 'רק בנפרעים' }
  const list = row.customers?.[statusKey] || []
  if (!list.length) return
  openFilterModal(`${labels[statusKey]} · ${row.company}`, list, null, null, null, row.company)
  filterModal.value.paidView = statusKey === 'matched'
}

// Product breakdown
const productBreakdown = computed(() => {
  const map = {}
  for (const c of commissionCustomers.value) {
    const matched = c.product_matches?.matched || []
    for (const p of matched) {
      const product = p.production_product || p.commission_product || 'לא ידוע'
      if (!map[product]) map[product] = { count: 0, amount: 0 }
      map[product].count++
      map[product].amount += (p.commission || 0)
    }
    const unmatchedComm = c.product_matches?.unmatched_commission || []
    for (const p of unmatchedComm) {
      const product = p.product || 'לא ידוע'
      if (!map[product]) map[product] = { count: 0, amount: 0 }
      map[product].count++
      map[product].amount += (p.commission || 0)
    }
  }
  return Object.entries(map)
    .map(([name, data]) => ({ name, ...data }))
    .sort((a, b) => b.amount - a.amount)
})

function onDrillFromModal(idNumber) {
  detailCustomer.value = null
  if (idNumber) emit('drill-customer', idNumber)
}

function pctOf(count) {
  if (!statusTotal.value) return 0
  return ((count / statusTotal.value) * 100).toFixed(0)
}

// ─── Charts ───

const statusDonutSeries = computed(() => statusItems.value.map(s => s.count))

const statusDonutOptions = computed(() => ({
  labels: statusItems.value.map(s => s.label),
  colors: statusItems.value.map(s => s.color),
  chart: {
    fontFamily: 'Heebo, sans-serif',
    background: 'transparent',
    events: {},
  },
  theme: { mode: 'light' },
  stroke: { show: false },
  legend: { show: false },
  dataLabels: {
    enabled: true,
    formatter: (val) => val.toFixed(0) + '%',
    style: { fontFamily: 'Heebo, sans-serif', fontWeight: 700, fontSize: '14px', colors: ['#fff'] },
    dropShadow: { enabled: false },
  },
  plotOptions: {
    pie: {
      donut: {
        size: '62%',
        labels: {
          show: true,
          name: { show: true, fontFamily: 'Heebo, sans-serif', color: '#706E6B', fontSize: '14px' },
          value: { show: true, fontFamily: 'Heebo, sans-serif', fontWeight: 800, fontSize: '32px', color: '#181818' },
          total: {
            show: true,
            label: 'סה"כ',
            fontFamily: 'Heebo, sans-serif',
            fontSize: '14px',
            color: '#706E6B',
            formatter: () => displayCustomers.value.length,
          },
        },
      },
      expandOnClick: false,
    },
  },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif' },
  },
  states: {
    hover: { filter: { type: 'darken', value: 0.05 } },
    active: { filter: { type: 'none' } },
  },
}))

// Product treemap
const treemapColors = CHART_PALETTE

const productTreemapSeries = computed(() => [{
  data: productBreakdown.value.map(p => ({
    x: p.name,
    y: productMetric.value === 'count' ? p.count : Math.round(p.amount),
  }))
}])

const productTreemapOptions = computed(() => ({
  chart: {
    fontFamily: 'Heebo, sans-serif',
    background: 'transparent',
    toolbar: { show: false },
  },
  theme: { mode: 'light' },
  colors: treemapColors,
  plotOptions: {
    treemap: {
      distributed: true,
      enableShades: false,
    },
  },
  dataLabels: {
    enabled: true,
    style: {
      fontFamily: 'Heebo, sans-serif',
      fontWeight: 700,
      fontSize: '14px',
    },
    formatter: function(text, op) {
      const val = op.value
      if (productMetric.value === 'amount') {
        return [text, formatCompact(val)]
      }
      return [text, val + ' מוצרים']
    },
    offsetY: -2,
  },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif' },
    y: {
      formatter: (val) => productMetric.value === 'amount'
        ? '₪ ' + Number(val).toLocaleString('he-IL')
        : val + ' מוצרים',
    },
  },
  legend: { show: false },
}))

// ─── Filter Modal ───
const filterModal = ref({ open: false, title: '', customers: [] })
const filterSearchQuery = ref('')
const productFilter = ref(null)
const productFilterOpen = ref(false)

const modalProducts = computed(() => {
  const products = new Set()
  for (const c of filterModal.value.customers) {
    for (const p of (c.production_products || [])) { if (p.product) products.add(p.product) }
    for (const p of (c.commission_products || [])) { if (p.product) products.add(p.product) }
    for (const p of (c.product_matches?.matched || [])) {
      const name = p.production_product || p.commission_product || p.product
      if (name) products.add(name)
    }
    for (const p of (c.product_matches?.unmatched_production || [])) { if (p.product) products.add(p.product) }
    for (const p of (c.product_matches?.unmatched_commission || [])) { if (p.product) products.add(p.product) }
  }
  return [...products].sort()
})

const filteredModalCustomers = computed(() => {
  let list = filterModal.value.customers
  if (productFilter.value) {
    list = list.filter(c => {
      const allProducts = [
        ...(c.production_products || []).map(p => p.product),
        ...(c.commission_products || []).map(p => p.product),
        ...(c.product_matches?.matched || []).map(p => p.production_product || p.commission_product || p.product),
        ...(c.product_matches?.unmatched_production || []).map(p => p.product),
        ...(c.product_matches?.unmatched_commission || []).map(p => p.product),
      ]
      return allProducts.some(name => name === productFilter.value)
    })
  }
  if (filterSearchQuery.value) {
    const q = filterSearchQuery.value.toLowerCase()
    list = list.filter(c =>
      (customerName(c).toLowerCase().includes(q)) ||
      (c.id_number && c.id_number.includes(q))
    )
  }
  return list
})

// The drill grows out of what was pressed (DataModal `origin`).
const fmOrigin = ref(null)
const detailOrigin = ref(null)
const periodLabel = computed(() => (props.periodMonth ? `נפרעים ${String(props.periodMonth).slice(0, 7)}` : ''))

function openFilterModal(title, customers, originEl = null, actions = null, kind = null, company = null) {
  fmOrigin.value = originEl
  filterModal.value = { open: true, title, customers, actions, kind, company }
  productFilter.value = null
  productFilterOpen.value = false
}

function closeFilterModal() {
  filterModal.value = { open: false, title: '', customers: [] }
  filterSearchQuery.value = ''
  productFilter.value = null
  productFilterOpen.value = false
}

function customerName(c) {
  return [c.first_name, c.last_name].filter(Boolean).join(' ') || '—'
}

function openDetailFromFilter(c, el = null) {
  detailOrigin.value = el
  const matched = (c.product_matches?.matched || []).map(p => ({
    product: p.production_product || p.commission_product || '—',
    company: p.company || '',
    accumulation: p.accumulation || 0,
    premium: p.premium || 0,
    balance: p.balance || 0,
    commission: p.commission || 0,
    policy_number: p.policy_number,
    track: p.track || null,
    management_fee: p.management_fee ?? null,
    management_fee_amount: p.management_fee_amount ?? null,
    rate: p.rate ?? null,
    expected_commission: p.expected_commission ?? null,
    expected_is_estimate: p.expected_is_estimate ?? null,
    commission_gap: p.commission_gap ?? null,
    rate_note: p.rate_note ?? null,
    // Paid under the policy owner's ID (family policy) — commission counted on the owner.
    paid_via_id: p.paid_via_id || null,
    owner_commission: p.owner_commission ?? null,
    paid: true,
  }))
  const unmatched = (c.product_matches?.unmatched_production || []).map(p => ({
    product: p.product || '—',
    company: p.company || '',
    company_full: p.company_full || '',
    accumulation: p.accumulation || 0,
    premium: p.premium || 0,
    balance: 0,
    commission: 0,
    policy_number: p.policy_number,
    sign_date: p.sign_date || null,
    track: p.track || null,
    rate: p.rate ?? null,
    expected_commission: p.expected_commission ?? null,
    expected_is_estimate: p.expected_is_estimate ?? null,
    commission_gap: p.commission_gap ?? null,
    rate_note: p.rate_note ?? null,
    paid: false,
  }))
  const unmatchedComm = (c.product_matches?.unmatched_commission || []).map(p => ({
    product: p.product || '—',
    company: p.company || '',
    accumulation: 0,
    premium: 0,
    balance: p.balance || 0,
    commission: p.commission || 0,
    policy_number: p.account || '',
    fund_type: p.fund_type || null,
    management_fee: p.management_fee ?? null,
    management_fee_amount: p.management_fee_amount ?? null,
    rate: p.rate ?? null,
    expected_commission: p.expected_commission ?? null,
    expected_is_estimate: p.expected_is_estimate ?? null,
    commission_gap: p.commission_gap ?? null,
    rate_note: p.rate_note ?? null,
    paid: true,
    source: 'commission_only',
  }))
  const matchedAccounts = new Set([
    ...matched.map(p => p.policy_number),
    ...unmatchedComm.map(p => p.policy_number),
  ].filter(Boolean))
  const commProducts = (c.commission_products || [])
    .filter(p => !matchedAccounts.has(p.account))
    .map(p => ({
      product: p.product || '—',
      company: p.company || '',
      accumulation: 0,
      premium: 0,
      balance: p.balance || 0,
      commission: p.commission || 0,
      policy_number: p.account || '',
      fund_type: p.fund_type || null,
      management_fee: p.management_fee ?? null,
      management_fee_amount: p.management_fee_amount ?? null,
      rate: p.rate ?? null,
      expected_commission: p.expected_commission ?? null,
      expected_is_estimate: p.expected_is_estimate ?? null,
      commission_gap: p.commission_gap ?? null,
      rate_note: p.rate_note ?? null,
      paid: true,
      source: 'commission_only',
    }))
  const allProducts = [...matched, ...unmatchedComm, ...commProducts, ...unmatched]

  detailCustomer.value = {
    id_number: c.id_number,
    name: customerName(c),
    paid_count: c.paid_count || 0,
    unpaid_count: c.unpaid_count || 0,
    commission_count: c.commission_count || 0,
    total_commission: c.total_commission || 0,
    paid_commission: matched.reduce((s, p) => s + (p.commission || 0), 0),
    client_phone: c.client_phone || null,
    client_email: c.client_email || null,
    employer_name: c.employer_name || null,
    employer_id: c.employer_id || null,
    // Insurance premium without pension deposits — the figure the
    // "לקוחות לפי פרמיה" chart shows for this customer.
    insurance_premium: insurancePremiumOf(c),
    products: allProducts,
  }
}

// ─── Chart events ───

function onStatusClick(_event, _chartCtx, config) {
  const keys = ['matched', 'only_production', 'only_commission']
  const labels = { matched: 'נמצא בשניהם', only_production: 'לא שולם', only_commission: 'רק בנפרעים' }
  const key = keys[config.dataPointIndex]
  if (key) {
    onLegendClick(key)
  }
}

function onLegendClick(key) {
  const labels = { matched: 'נמצא בשניהם', only_production: 'לא שולם', only_commission: 'רק בנפרעים' }
  const filtered = key === 'only_production'
    ? effectiveUnpaidCustomers.value
    : displayCustomers.value.filter(c => c.match_status === key)
  openFilterModal(labels[key] || key, filtered)
}

function onProductClick(_event, _chartCtx, config) {
  const product = productBreakdown.value[config.dataPointIndex]
  if (product) {
    const filtered = commissionCustomers.value.filter(c => {
      const matched = c.product_matches?.matched || []
      const unmatchedComm = c.product_matches?.unmatched_commission || []
      return [...matched, ...unmatchedComm].some(p => {
        const pName = p.production_product || p.commission_product || p.product || 'לא ידוע'
        return pName === product.name
      })
    })
    openFilterModal('מוצר — ' + product.name, filtered)
  }
}

// ─── Mail for unpaid customers ───

function findRateObj(product) {
  if (!commissionRates.value.length) return null
  const base = [product.company, product.company_full].filter(Boolean)
  const candidates = [...base]
  for (const c of base) { const s = stripHe(c); if (s) candidates.push(s) }
  const matches = new Set()
  for (const companyName of candidates) {
    const cl = companyName.toLowerCase()
    const fw = cl.split(/[\s\-]/)[0]
    for (const r of commissionRates.value) {
      const rn = r.company_name.toLowerCase()
      if (r.company_name === companyName || cl.includes(rn) || rn.includes(cl)
          || (fw.length > 2 && rn.startsWith(fw))) {
        matches.add(r)
      }
    }
  }
  if (matches.size === 0) return null
  const arr = [...matches]
  if (arr.length === 1) return arr[0]
  const hints = getCategoryHints(product)
  if (hints) {
    const preferred = arr.find(r => hints.some(h => r.company_name.includes(h)))
    if (preferred) return preferred
  }
  return arr[0]
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d)) return dateStr
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

async function sendAllUnpaidMail(list) {
  const customers = Array.isArray(list) ? list : effectiveUnpaidCustomers.value
  if (!customers.length) return

  // Build customer lines with product details and premium
  const lines = customers.map(c => {
    const name = customerName(c)
    const products = c.production_products || c.product_matches?.unmatched_production || []
    const productLines = products.map(p => {
      const date = p.sign_date ? formatDate(p.sign_date) : ''
      const premiumStr = p.premium > 0 ? ` פרמיה: ₪${Math.round(p.premium)}` : ''
      const policyStr = p.policy_number ? ` | מס׳ פוליסה/חשבון: ${p.policy_number}` : ''
      return `  - ${p.product || ''}${policyStr}${date ? ' מתאריך ' + date : ''}${premiumStr}`
    }).join('\n')
    return `- ${name} ת.ז ${c.id_number}:\n${productLines}`
  }).join('\n')

  // Find company email from first customer's products
  let companyEmail = ''
  for (const c of customers) {
    const products = c.production_products || c.product_matches?.unmatched_production || []
    for (const p of products) {
      const rate = findRateObj(p)
      if (rate?.company_email) {
        companyEmail = rate.company_email
        break
      }
    }
    if (companyEmail) break
  }

  const userName = authStore.user?.full_name || ''
  const subject = `בקשת תשלום עמלות נפרעים - ${customers.length} לקוחות`
  const body = `שלום רב,

עבור הלקוחות הבאים לא התקבלו עמלות נפרעים:

${lines}

קובץ אקסל עם פירוט הלקוחות הורד למחשבך — צרף אותו למייל זה.

אודה לטיפולכם ותשלום רטרו בגין לקוחות אלו.

בברכה,
${userName}`

  downloadUnpaidExcel(customers)
  await openMailCompose({ to: companyEmail, subject, body })
}

function downloadUnpaidExcel(list) {
  const customers = Array.isArray(list) ? list : effectiveUnpaidCustomers.value
  if (!customers.length) return

  const rows = []
  for (const c of customers) {
    const name = customerName(c)
    const products = c.production_products || c.product_matches?.unmatched_production || []
    if (products.length === 0) {
      rows.push({
        'שם לקוח': name,
        'ת.ז': c.id_number,
        'מוצר': '',
        'חברה': '',
        'תאריך הצטרפות': '',
        'פרמיה': '',
        'צבירה': '',
      })
    } else {
      for (const p of products) {
        rows.push({
          'שם לקוח': name,
          'ת.ז': c.id_number,
          'מוצר': p.product || '',
          'מס׳ פוליסה/חשבון': p.policy_number || '',
          'חברה': p.company || p.company_full || '',
          'תאריך הצטרפות': p.sign_date ? formatDate(p.sign_date) : '',
          'פרמיה': p.premium || 0,
          'צבירה': p.accumulation || 0,
        })
      }
    }
  }

  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'לא שולם')
  XLSX.writeFile(wb, `לא_שולם_${new Date().toLocaleDateString('he-IL')}.xlsx`)
}

// ─── Only-commission mail & Excel ───

async function sendOnlyCommissionMail(list) {
  const customers = Array.isArray(list) ? list : onlyCommCustomers.value
  if (!customers.length) return

  const lines = customers.map(c => {
    const name = customerName(c)
    const products = c.commission_products || c.product_matches?.unmatched_commission || []
    if (!products.length) return `- ${name} ת.ז ${c.id_number}`
    const productLines = products.map(p => {
      const parts = [p.product || p.product_type || '']
      if (p.account) parts.push(`חשבון: ${p.account}`)
      if (p.balance > 0) parts.push(`יתרה: ₪${Math.round(p.balance)}`)
      if (p.commission > 0) parts.push(`עמלה: ₪${Math.round(p.commission)}`)
      return `  - ${parts.filter(Boolean).join(' | ')}`
    }).join('\n')
    return `- ${name} ת.ז ${c.id_number}:\n${productLines}`
  }).join('\n')

  let companyEmail = ''
  for (const c of customers) {
    const products = c.commission_products || c.product_matches?.unmatched_commission || []
    for (const p of products) {
      const rate = findRateObj(p)
      if (rate?.company_email) {
        companyEmail = rate.company_email
        break
      }
    }
    if (companyEmail) break
  }

  const userName = authStore.user?.full_name || ''
  const subject = `בירור — לקוחות המופיעים רק בנפרעים (${customers.length})`
  const body = `שלום רב,

הלקוחות הבאים מופיעים בדוח הנפרעים אך לא נמצאים בפרודוקציה שלי:

${lines}

אודה לבירור והבהרה לגבי לקוחות אלו.

בברכה,
${userName}`

  try { downloadOnlyCommissionExcel(customers) } catch { /* ignore Excel error */ }
  await openMailCompose({ to: companyEmail, subject, body })
}

function downloadOnlyCommissionExcel(list) {
  const customers = Array.isArray(list) ? list : onlyCommCustomers.value
  if (!customers.length) return

  const rows = []
  for (const c of customers) {
    const name = customerName(c)
    const products = c.commission_products || c.product_matches?.unmatched_commission || []
    if (products.length === 0) {
      rows.push({ 'שם לקוח': name, 'ת.ז': c.id_number, 'מוצר': '', 'חשבון': '', 'חברה': '', 'יתרה': '', 'עמלה': '' })
    } else {
      for (const p of products) {
        rows.push({
          'שם לקוח': name,
          'ת.ז': c.id_number,
          'מוצר': p.product || '',
          'חשבון': p.account || '',
          'חברה': p.company || '',
          'יתרה': p.balance || 0,
          'עמלה': p.commission || 0,
        })
      }
    }
  }

  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'רק בנפרעים')
  XLSX.writeFile(wb, `רק_בנפרעים_${new Date().toLocaleDateString('he-IL')}.xlsx`)
}

// ─── Formatters ───

function formatAmount(val) {
  if (val == null || val === 0) return '—'
  return '₪ ' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function formatCompact(val) {
  if (val == null || val === 0) return '₪0'
  if (val >= 1000000) return '₪' + (val / 1000000).toFixed(1) + 'M'
  if (val >= 1000) return '₪' + (val / 1000).toFixed(0) + 'K'
  return '₪' + Math.round(val)
}
</script>

<style scoped>
.bi-dashboard {
  margin-bottom: 24px;
}

.company-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  background: var(--primary-light);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}
.company-filter-bar .company-pill {
  padding: 6px 14px;
  border-radius: 18px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-alt, #F3F3F3);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--text-muted);
  white-space: nowrap;
}
.company-filter-bar .company-pill:hover { border-color: var(--brand); color: var(--brand); }
.company-filter-bar .company-pill.active { background: var(--brand); color: #fff; border-color: var(--brand); }

/* ── Hero Card ── */
.hero-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 28px 24px 20px;
  margin-bottom: 16px;
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}

/* The three-colour strip across the top of this card was removed (QA
   2026-10-01: "clean it") — the chart below already carries the colours. */

.hero-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.hero-title {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.3px;
}

.hero-badge {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
  background: rgba(46, 132, 74, 0.08);
  padding: 5px 14px;
  border-radius: 20px;
}

.hero-body {
  display: flex;
  justify-content: center;
}

.hero-stats {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 12px;
}

/* Per-company breakdown of the same three statuses */
.hero-bycompany {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}
.hbc-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 2px;
}
.hbc-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}
.hbc-hint {
  font-size: 11.5px;
  color: var(--text-muted);
}
.hbc-note {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--text-muted);
}
@media (max-width: 640px) {
  .hbc-head { flex-direction: column; gap: 2px; }
}

.hero-stat {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  border-radius: 12px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 140px;
}

.hero-stat:hover {
  background: var(--primary-light);
  border-color: var(--primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.hero-stat-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.hero-stat-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.hero-stat-count {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  line-height: 1.2;
}

.hero-stat-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.hero-stat-pct {
  font-size: 14px;
  font-weight: 800;
  flex-shrink: 0;
}

/* ── KPI Row ── */
/* Six cards, six columns. This was repeat(5, 1fr) with six cards, so
   "סה"כ יתרה" dropped onto a second line on every screen. An auto-fill
   minmax() (the production tab's rule) only looks right at some widths — with
   six cards it re-wraps as the container narrows, so the count is explicit. */
.kpi-novalue {
  display: flex; align-items: center; gap: 6px; margin: 8px 6px 0; padding: 4px 4px;
  border: none; background: none; font: inherit; font-size: 12.5px; color: var(--text-muted); cursor: pointer;
}
.kpi-novalue .ltr-number { font-weight: 700; color: var(--text); }
.kpi-novalue:hover { color: var(--tab-comparison); }
.kpi-novalue:focus-visible { outline: 2px solid var(--tab-comparison); outline-offset: 2px; border-radius: 6px; }
.kpi-panel {
  margin: 12px 0 18px; padding: 10px;
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: 18px;
  box-shadow: var(--shadow-sm);
}
/* Continues the file bar above: no gap, square top, a thin divider. */
.kpi-panel--joined {
  margin-top: 0; border-radius: 0 0 18px 18px;
  border-top: 1px solid var(--border-subtle);
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}
/* The unpaid card: a quiet red frame and a slow breath — noticeable, never loud. */
.kpi-card--alert {
  border-color: color-mix(in srgb, var(--k) 45%, transparent);
  background:
    radial-gradient(120% 90% at 0% 100%, color-mix(in srgb, var(--k) 16%, transparent) 0%, transparent 65%),
    color-mix(in srgb, var(--k) 4%, var(--card-bg));
  animation: kpiBreath 3s ease-in-out infinite;
}
.kpi-card--alert:hover {
  transform: translateY(-3px) scale(1.02);
  border-color: var(--k);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--k) 14%, transparent),
              0 14px 32px color-mix(in srgb, var(--k) 30%, transparent);
  animation-play-state: paused;
}
.kpi-card--alert .kpi-value { color: var(--k-ink); }
@keyframes kpiBreath {
  0%, 100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--k) 0%, transparent), var(--shadow-sm); }
  50% { box-shadow: 0 0 0 6px color-mix(in srgb, var(--k) 12%, transparent), 0 8px 22px color-mix(in srgb, var(--k) 18%, transparent); }
}
@media (prefers-reduced-motion: reduce) { .kpi-card--alert { animation: none; } }
@media (max-width: 1240px) {
  .kpi-row { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 720px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}

.kpi-card {
  position: relative; overflow: hidden;
  display: flex; align-items: center; gap: 12px;
  padding: 11px 12px 11px 14px; min-height: 68px;
  background:
    radial-gradient(120% 90% at 0% 100%, color-mix(in srgb, var(--k) 9%, transparent) 0%, transparent 60%),
    var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.kpi-card.clickable { cursor: pointer; }
.kpi-card:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--k) 30%, transparent);
  box-shadow: 0 10px 26px color-mix(in srgb, var(--k) 16%, transparent);
}
.kpi-card:focus-visible { outline: 2px solid var(--k); outline-offset: 2px; }
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
  color: var(--text-primary, #181818); line-height: 1.15; white-space: nowrap;
}
.kpi-label { font-size: 12.5px; font-weight: 600; color: var(--text-secondary, #706E6B); margin-top: 3px; white-space: nowrap; }
.kpi-actions { position: absolute; top: 8px; inset-inline-end: 8px; display: flex; gap: 4px; z-index: 1; }
.kpi-action-btn {
  width: 26px; height: 26px; border-radius: 8px; padding: 0; cursor: pointer;
  display: grid; place-items: center;
  color: var(--k-ink); background: var(--card-bg);
  border: 1px solid color-mix(in srgb, var(--k) 25%, transparent);
  transition: background 0.15s ease, color 0.15s ease;
}
.kpi-action-btn:hover { background: var(--k-ink); color: #fff; }
@media (prefers-reduced-motion: reduce) { .kpi-card, .kpi-ghost { transition: none; } }

/* ── Chart Cards ── */
.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease;
}

.chart-card:hover {
  box-shadow: var(--shadow-md);
}

.wide-card {
  grid-column: 1 / -1;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.chart-header h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

/* ── Toggle Buttons ── */
.chart-actions {
  display: flex;
  gap: 2px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 2px;
}

.toggle-btn {
  padding: 5px 14px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn.active {
  background: var(--primary);
  color: #FFFFFF;
}

.toggle-btn:hover:not(.active) {
  color: var(--text);
}

/* ── Filter Modal ── */
.fm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.fm-card {
  width: 100%;
  max-width: 520px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
}

.fm-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: #F3F3F3;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.fm-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  flex: 1;
}

.fm-count {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg);
  padding: 3px 10px;
  border-radius: 10px;
}

.fm-close {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.fm-close:hover { background: var(--border-subtle); color: var(--text); }

.fm-filter-collapse {
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.fm-filter-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 22px;
  background: transparent;
  border: none;
  font-family: inherit;
  font-size: 12.5px;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.12s;
}
.fm-filter-trigger:hover { background: var(--bg-alt, #F3F3F3); }
.fm-filter-trigger.is-active { color: var(--brand); font-weight: 600; }
.fm-filter-trigger > span:not(.fm-filter-count) {
  flex: 1;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fm-filter-count {
  background: var(--bg-alt, #F3F3F3);
  color: var(--text-muted);
  padding: 1px 7px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}
.fm-filter-trigger.is-active .fm-filter-count {
  background: var(--brand);
  color: #fff;
}
.fm-filter-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 4px;
}
.fm-filter-clear:hover { background: var(--border-subtle); color: var(--text); }
.fm-filter-chevron {
  transition: transform 0.18s;
  color: var(--text-muted);
}
.fm-filter-chevron.open { transform: rotate(180deg); }

.fm-product-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 22px 12px;
  max-height: 140px;
  overflow-y: auto;
}
.fm-product-filter .company-pill,
.fm-company-filter .company-pill {
  padding: 4px 12px;
  border-radius: 16px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-alt, #F3F3F3);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--text-muted);
  white-space: nowrap;
}
.fm-product-filter .company-pill:hover,
.fm-company-filter .company-pill:hover { border-color: var(--brand); color: var(--brand); }
.fm-product-filter .company-pill.active,
.fm-company-filter .company-pill.active { background: var(--brand); color: #fff; border-color: var(--brand); }

.fm-company-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 22px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.fm-search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.fm-search-wrap svg { color: var(--text-muted); flex-shrink: 0; }
.fm-search {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  font-family: inherit;
  color: var(--text);
  background: transparent;
}
.fm-search::placeholder { color: var(--text-muted); }

.fm-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 10px;
}

.fm-list::-webkit-scrollbar { width: 4px; }
.fm-list::-webkit-scrollbar-track { background: transparent; }
.fm-list::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.1); border-radius: 4px; }

.fm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s;
  border-bottom: 1px solid #E5E5E5;
}
.fm-row:last-child { border-bottom: none; }
.fm-row:hover { background: var(--primary-light); }

.fm-row-info { flex: 1; min-width: 0; }
.fm-row-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fm-row-sub {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.fm-row-stats {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.fm-chip {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 8px;
  white-space: nowrap;
}
.fm-chip-ok { background: var(--green-light); color: var(--green); }
.fm-chip-commission { background: var(--green-light); color: var(--green); }
.fm-chip-violet { background: rgba(127, 86, 217, 0.08); color: var(--accent-violet); }

.fm-arrow {
  color: var(--light-gray);
  flex-shrink: 0;
  transition: transform 0.15s;
}
.fm-row:hover .fm-arrow { transform: translateX(-3px); color: var(--primary); }

.fm-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-size: 13px;
}

/* Modal transitions */
.modal-enter-active { animation: modalIn 0.2s ease-out; }
.modal-leave-active { animation: modalIn 0.12s ease reverse; }
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* ── Top Clients ── */
.tc-card { margin-bottom: 16px; }

.empty-chart {
  text-align: center;
  padding: 48px 16px;
  color: var(--text-muted);
  font-size: 14px;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

@media (max-width: 1100px) {
  .kpi-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) {
  .hero-stats {
    flex-direction: column;
    align-items: stretch;
  }
  .hero-stat {
    min-width: 0;
  }
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .kpi-row {
    grid-template-columns: 1fr;
  }
}

/* ── Unpaid notification strip ── */
.unpaid-strip {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid rgba(201, 162, 39, 0.2);
  border-inline-start: 4px solid #8A6300;
  background: linear-gradient(135deg, rgba(201, 162, 39, 0.04) 0%, rgba(201, 162, 39, 0.08) 100%);
  overflow: hidden;
}

.unpaid-strip-pulse {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: rgba(201, 162, 39, 0.05);
  animation: stripPulse 3s ease-in-out infinite;
  pointer-events: none;
}
@keyframes stripPulse {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}

.unpaid-strip-content {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  position: relative;
  z-index: 1;
}

.unpaid-strip-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(201, 162, 39, 0.12);
  color: #8A6300;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  animation: iconBounce 2s ease-in-out 1;
}
@keyframes iconBounce {
  0%, 100% { transform: translateY(0); }
  15% { transform: translateY(-4px); }
  30% { transform: translateY(0); }
  45% { transform: translateY(-2px); }
  60% { transform: translateY(0); }
}

.unpaid-strip-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.5;
}
.unpaid-strip-text strong {
  color: #8A6300;
  font-weight: 800;
}
.unpaid-strip-amount {
  color: var(--text-secondary);
  font-weight: 500;
}
.unpaid-strip-amount strong {
  color: var(--amber); /* unpaid = warning state, matches the strip */
  font-weight: 800;
}

.unpaid-strip-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  margin-inline-start: auto;
}

.unpaid-strip-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  border: 1px solid;
  transition: all 0.2s var(--transition);
  white-space: nowrap;
}
.unpaid-strip-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(0,0,0,0.08);
}
.unpaid-strip-btn svg { flex-shrink: 0; }

.unpaid-strip-view {
  background: rgba(46, 132, 74, 0.06);
  color: var(--primary);
  border-color: rgba(46, 132, 74, 0.2);
}
.unpaid-strip-view:hover { background: rgba(46, 132, 74, 0.12); border-color: var(--primary); }

.unpaid-strip-mail {
  background: rgba(201, 162, 39, 0.06);
  color: #8A6300;
  border-color: rgba(201, 162, 39, 0.2);
}
.unpaid-strip-mail:hover { background: rgba(201, 162, 39, 0.12); border-color: #8A6300; }

.unpaid-strip-excel {
  background: rgba(46, 132, 74, 0.06);
  color: #2E844A;
  border-color: rgba(46, 132, 74, 0.2);
}
.unpaid-strip-excel:hover { background: rgba(46, 132, 74, 0.12); border-color: #2E844A; }

.unpaid-strip-dismiss {
  position: relative;
  z-index: 1;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}
.unpaid-strip-dismiss:hover { background: rgba(201, 162, 39, 0.1); color: #8A6300; }

/* Strip transition */
.unpaid-strip-enter-active {
  animation: stripSlideIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.unpaid-strip-leave-active {
  animation: stripSlideIn 0.25s ease reverse;
}
@keyframes stripSlideIn {
  from {
    opacity: 0;
    transform: translateY(-12px) scaleY(0.9);
    max-height: 0;
  }
  to {
    opacity: 1;
    transform: translateY(0) scaleY(1);
    max-height: 80px;
  }
}

@media (max-width: 700px) {
  .unpaid-strip-content { flex-wrap: wrap; }
  .unpaid-strip-actions { width: 100%; justify-content: flex-start; }
}


/* Agreement-vs-paid mismatch alert */
.gap-alert {
  display: flex; align-items: center; gap: 12px;
  padding: 13px 16px; margin-bottom: 14px;
  background: color-mix(in srgb, var(--chart-4) 8%, var(--card-bg));
  border: 1px solid color-mix(in srgb, var(--chart-4) 38%, transparent);
  border-radius: var(--radius-lg, 16px);
}
.ga-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; flex: none; border-radius: 9px;
  background: color-mix(in srgb, var(--chart-4) 16%, transparent);
  color: var(--chart-4);
}
.ga-text { display: flex; flex-direction: column; gap: 2px; flex: 1 1 auto; min-width: 0; }
.ga-text strong { font-size: 13.5px; font-weight: 700; color: var(--text); }
.ga-sub { font-size: 11.5px; color: var(--text-secondary); }
.ga-action {
  flex: none; padding: 8px 14px; border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--chart-4) 40%, transparent);
  background: var(--card-bg); color: var(--chart-4);
  font-family: inherit; font-size: 12.5px; font-weight: 650; cursor: pointer;
}
.ga-action:hover { background: color-mix(in srgb, var(--chart-4) 10%, var(--card-bg)); }
@media (max-width: 640px) {
  .gap-alert { flex-wrap: wrap; }
  .ga-action { width: 100%; }
}
.fm-explain { margin-bottom: 14px; }
</style>
