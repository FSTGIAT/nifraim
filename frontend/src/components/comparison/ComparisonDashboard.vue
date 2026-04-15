<template>
  <div class="bi-dashboard">
    <!-- Category + Company Header -->
    <div v-if="props.categoryLabel || props.companySource" class="comparison-header-bar">
      <span v-if="props.companySource" class="header-company">{{ props.companySource }}</span>
      <span v-if="props.categoryLabel" class="header-category">{{ props.categoryLabel }}</span>
    </div>

    <!-- HERO: Customer Status Distribution -->
    <div class="hero-card">
      <div class="hero-header">
        <h2 class="hero-title">התפלגות לקוחות</h2>
        <span class="hero-badge">{{ displayCustomers.length }} לקוחות</span>
      </div>
      <div class="hero-body">
        <apexchart
          type="donut"
          :height="340"
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
    </div>

    <!-- Company filter (when multiple commission files) -->
    <div v-if="props.companySources.length > 1" class="company-filter-bar">
      <button class="company-pill" :class="{ active: !companyFilter }" @click="companyFilter = null">הכל ({{ props.customers.length }})</button>
      <button v-for="src in props.companySources" :key="src" class="company-pill" :class="{ active: companyFilter === src }" @click="companyFilter = src">{{ src }}</button>
    </div>

    <!-- KPI Cards Row -->
    <div class="kpi-row">
      <div class="kpi-card kpi-blue">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87"/>
            <path d="M16 3.13a4 4 0 010 7.75"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value">{{ commissionCustomerCount }}</div>
          <div class="kpi-label">לקוחות בנפרעים</div>
        </div>
      </div>
      <div class="kpi-card kpi-amber" @click="onLegendClick('only_production')" style="cursor:pointer">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value">{{ effectiveUnpaidCustomers.length }}</div>
          <div class="kpi-label">לא שולם</div>
        </div>
        <div v-if="effectiveUnpaidCustomers.length > 0" class="kpi-actions">
          <button
            class="kpi-action-btn kpi-action-mail"
            @click.stop="sendAllUnpaidMail"
            title="שלח מייל על כל הלקוחות שלא שולמו"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2"/>
              <path d="M22 7l-10 7L2 7"/>
            </svg>
          </button>
          <button
            class="kpi-action-btn kpi-action-excel"
            @click.stop="downloadUnpaidExcel"
            title="הורד לאקסל"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <polyline points="9 15 12 18 15 15"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="kpi-card kpi-violet" @click="onLegendClick('only_commission')" style="cursor:pointer">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value">{{ onlyCommCustomers.length }}</div>
          <div class="kpi-label">רק בנפרעים</div>
        </div>
        <div v-if="onlyCommCustomers.length > 0" class="kpi-actions">
          <button
            class="kpi-action-btn kpi-action-mail"
            @click.stop="sendOnlyCommissionMail"
            title="שלח מייל על לקוחות שרק בנפרעים"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2"/>
              <path d="M22 7l-10 7L2 7"/>
            </svg>
          </button>
          <button
            class="kpi-action-btn kpi-action-excel"
            @click.stop="downloadOnlyCommissionExcel"
            title="הורד לאקסל"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <polyline points="9 15 12 18 15 15"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="kpi-card kpi-red">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ formatAmount(totalUnpaidCharge) }}</div>
          <div class="kpi-label">סה"כ חיוב לא משולם</div>
        </div>
      </div>
      <div class="kpi-card kpi-green">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="1" x2="12" y2="23"/>
            <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ formatAmount(totalCommission) }}</div>
          <div class="kpi-label">סה"כ עמלה</div>
        </div>
      </div>
      <div class="kpi-card kpi-cyan">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
            <line x1="1" y1="10" x2="23" y2="10"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value ltr-number">{{ formatAmount(totalBalance) }}</div>
          <div class="kpi-label">סה"כ יתרה</div>
        </div>
      </div>
    </div>

    <!-- Unpaid notification strip -->
    <Transition name="unpaid-strip">
      <div v-if="showUnpaidStrip && effectiveUnpaidCustomers.length > 0" class="unpaid-strip">
        <div class="unpaid-strip-pulse"></div>
        <div class="unpaid-strip-content">
          <div class="unpaid-strip-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </div>
          <div class="unpaid-strip-text">
            <strong>{{ effectiveUnpaidCustomers.length }}</strong> לקוחות ללא תשלום עמלה
            <span v-if="totalUnpaidCharge > 0" class="unpaid-strip-amount">
              — הפסד משוער <strong class="ltr-number">{{ formatAmount(totalUnpaidCharge) }}</strong>
            </span>
          </div>
          <div class="unpaid-strip-actions">
            <button class="unpaid-strip-btn unpaid-strip-view" @click="onLegendClick('only_production')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              הצג
            </button>
            <button class="unpaid-strip-btn unpaid-strip-mail" @click="sendAllUnpaidMail">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>
              שלח מייל
            </button>
            <button class="unpaid-strip-btn unpaid-strip-excel" @click="downloadUnpaidExcel">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><polyline points="9 15 12 18 15 15"/></svg>
              Excel
            </button>
          </div>
        </div>
        <button class="unpaid-strip-dismiss" @click="showUnpaidStrip = false" title="הסתר">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </Transition>

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
      :commissionRates="commissionRates"
      :category="props.categoryLabel"
      :userName="authStore.user?.full_name || ''"
      @close="detailCustomer = null"
      @drill="onDrillFromModal"
    />

    <!-- Filter Modal (customer list from chart click) -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="filterModal.open" class="fm-overlay" @click.self="closeFilterModal">
          <div class="fm-card">
            <div class="fm-header">
              <div class="fm-title">{{ filterModal.title }}</div>
              <span class="fm-count">{{ filteredModalCustomers.length }} לקוחות</span>
              <button class="fm-close" @click="closeFilterModal">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div v-if="modalProducts.length > 1" class="fm-product-filter">
              <button class="company-pill" :class="{ active: !productFilter }" @click="productFilter = null">הכל</button>
              <button v-for="p in modalProducts" :key="p" class="company-pill" :class="{ active: productFilter === p }" @click="productFilter = p">{{ p }}</button>
            </div>
            <div class="fm-search-wrap">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input v-model="filterSearchQuery" class="fm-search" placeholder="חיפוש לפי שם או ת.ז." />
            </div>
            <div class="fm-list">
              <div
                v-for="c in filteredModalCustomers"
                :key="c.id_number"
                class="fm-row"
                @click="openDetailFromFilter(c)"
              >
                <div class="fm-row-info">
                  <div class="fm-row-name">{{ customerName(c) }}</div>
                  <div class="fm-row-sub">
                    <span class="ltr-number">{{ c.id_number }}</span>
                    <span v-if="c.commission_count">{{ c.commission_count }} מוצרים</span>
                  </div>
                </div>
                <div class="fm-row-stats">
                  <span v-if="c.total_commission > 0" class="fm-chip fm-chip-commission">{{ formatCompact(c.total_commission) }}</span>
                  <span v-if="c.match_status === 'matched'" class="fm-chip fm-chip-ok">בשניהם</span>
                  <span v-else-if="c.match_status === 'only_commission'" class="fm-chip fm-chip-violet">רק בנפרעים</span>
                </div>
                <svg class="fm-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
              </div>
              <div v-if="filteredModalCustomers.length === 0" class="fm-empty">אין תוצאות</div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Clipboard notification -->
    <Transition name="clipboard-toast">
      <div v-if="clipboardNotice" class="clipboard-toast">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        תוכן המייל הועתק ללוח — הדבק בגוף ההודעה
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import api from '../../api/client.js'
import { useAuthStore } from '../../stores/auth.js'
import { openMailCompose } from '../../utils/mailHelper.js'
import { calcExpectedCommission } from '../../utils/commissionCalc.js'
import CustomerDetailModal from './CustomerDetailModal.vue'

const props = defineProps({
  customers: { type: Array, required: true },
  categoryLabel: { type: String, default: '' },
  companySource: { type: String, default: '' },
  companySources: { type: Array, default: () => [] },
})

const emit = defineEmits(['drill-customer'])

const authStore = useAuthStore()
const productMetric = ref('count')
const detailCustomer = ref(null)
const commissionRates = ref([])
const clipboardNotice = ref(false)
const showUnpaidStrip = ref(false)
const companyFilter = ref(null)

onMounted(async () => {
  try {
    const res = await api.get('/commission-rates')
    commissionRates.value = res.data
  } catch (e) { /* rates not available */ }
  // Reveal unpaid strip with delay for smooth entrance
  setTimeout(() => { showUnpaidStrip.value = true }, 600)
})

// ─── Computed data ───

function matchesCompanyFilter(productCompany) {
  if (!companyFilter.value || !productCompany) return false
  const lower = productCompany.toLowerCase()
  const cl = companyFilter.value.toLowerCase()
  return lower.includes(cl) || cl.includes(lower)
}

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
const effectiveUnpaidCustomers = computed(() => {
  if (!isGemel.value) return onlyProdCustomers.value
  return onlyProdCustomers.value.filter(c => {
    const products = c.production_products || c.product_matches?.unmatched_production || []
    return products.some(p => p.accumulation != null && p.accumulation > 0)
  })
})

const commissionCustomerCount = computed(() => commissionCustomers.value.length)

const totalCommission = computed(() =>
  commissionCustomers.value.reduce((sum, c) => sum + (c.total_commission || 0), 0)
)

const totalBalance = computed(() => {
  let total = 0
  for (const c of commissionCustomers.value) {
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

// KPI: total unpaid expected commission for effective unpaid customers
const totalUnpaidCharge = computed(() => {
  let expectedTotal = 0
  let rawTotal = 0
  for (const c of effectiveUnpaidCustomers.value) {
    for (const p of (c.production_products || [])) {
      const rate = findRate(p)
      if (rate) {
        const exp = calcExpectedCommission(p, rate)
        if (exp != null) expectedTotal += exp
      }
      rawTotal += (p.premium || 0) || (p.accumulation || 0)
    }
  }
  return expectedTotal || rawTotal
})

// ─── Top Clients ───

const topNOptions = [15, 20, 50, 100]
const topN = ref(15)

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
      // Insurance: total premium
      value = c.total_premium || 0
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

const STATUS_COLORS = { matched: '#F57C00', only_production: '#E8720A', only_commission: '#7F56D9' }

const topClientsChartSeries = computed(() => [{
  name: isGemel.value ? 'צבירה' : 'פרמיה',
  data: topClientsData.value.map(c => ({
    x: c.name,
    y: Math.round(c.value),
    fillColor: STATUS_COLORS[c.status] || '#F57C00',
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
  legend: { show: false },
  dataLabels: {
    enabled: topN.value <= 20,
    formatter: (val) => formatCompact(val),
    style: { fontFamily: 'Heebo, sans-serif', fontWeight: 700, fontSize: '10px', colors: ['#fff'] },
    dropShadow: { enabled: false },
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
    borderColor: '#F0F0F0',
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

// Status donut — all three statuses
const statusItems = computed(() => [
  { key: 'matched', label: 'נמצא בשניהם', count: matchedCustomers.value.length, color: '#2E844A' },
  { key: 'only_production', label: 'לא שולם', count: effectiveUnpaidCustomers.value.length, color: '#E8720A' },
  { key: 'only_commission', label: 'רק בנפרעים', count: onlyCommCustomers.value.length, color: '#7F56D9' },
])

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
  if (!displayCustomers.value.length) return 0
  return ((count / displayCustomers.value.length) * 100).toFixed(0)
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
const treemapColors = ['#F57C00', '#2E844A', '#7F56D9', '#06A59A', '#E8720A', '#C23934', '#38BDF8', '#F472B6', '#6366F1']

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

function openFilterModal(title, customers) {
  filterModal.value = { open: true, title, customers }
  productFilter.value = null
}

function closeFilterModal() {
  filterModal.value = { open: false, title: '', customers: [] }
  filterSearchQuery.value = ''
  productFilter.value = null
}

function customerName(c) {
  return [c.first_name, c.last_name].filter(Boolean).join(' ') || '—'
}

function openDetailFromFilter(c) {
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

async function sendAllUnpaidMail() {
  const customers = effectiveUnpaidCustomers.value
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

  downloadUnpaidExcel()
  const status = await openMailCompose({ to: companyEmail, subject, body })
  if (status === 'clipboard') {
    clipboardNotice.value = true
    setTimeout(() => { clipboardNotice.value = false }, 4000)
  }
}

function downloadUnpaidExcel() {
  const customers = effectiveUnpaidCustomers.value
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

async function sendOnlyCommissionMail() {
  const customers = onlyCommCustomers.value
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

  try { downloadOnlyCommissionExcel() } catch { /* ignore Excel error */ }
  const status = await openMailCompose({ to: companyEmail, subject, body })
  if (status === 'clipboard') {
    clipboardNotice.value = true
    setTimeout(() => { clipboardNotice.value = false }, 4000)
  }
}

function downloadOnlyCommissionExcel() {
  const customers = onlyCommCustomers.value
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
  background: var(--bg-alt, #f8f8f8);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--text-muted);
  white-space: nowrap;
}
.company-filter-bar .company-pill:hover { border-color: var(--brand); color: var(--brand); }
.company-filter-bar .company-pill.active { background: var(--brand); color: #fff; border-color: var(--brand); }

.comparison-header-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--primary-light);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.header-company {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.header-category {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  background: rgba(99, 102, 241, 0.08);
  padding: 3px 10px;
  border-radius: 12px;
}

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

.hero-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #F57C00 0%, #F57C00 50%, #E8720A 50%, #E8720A 75%, #7F56D9 75%, #7F56D9 100%);
}

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
  background: rgba(245, 124, 0, 0.08);
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
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease;
}

.kpi-card:hover {
  box-shadow: var(--shadow-md);
}

.kpi-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-blue .kpi-icon { background: rgba(245, 124, 0, 0.1); color: #F57C00; }
.kpi-amber .kpi-icon { background: rgba(232, 114, 10, 0.1); color: #E8720A; }
.kpi-amber .kpi-value { color: #E8720A; }
.kpi-red .kpi-icon { background: rgba(194, 57, 52, 0.1); color: #C23934; }
.kpi-red .kpi-value { color: #C23934; }
.kpi-green .kpi-icon { background: rgba(46, 132, 74, 0.1); color: #2E844A; }
.kpi-cyan .kpi-icon { background: rgba(6, 165, 154, 0.1); color: #06A59A; }
.kpi-violet .kpi-icon { background: rgba(139, 92, 246, 0.1); color: #8B5CF6; }
.kpi-violet .kpi-value { color: #8B5CF6; }

.kpi-data { min-width: 0; }
.kpi-value {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.5px;
  line-height: 1.2;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-top: 2px;
}

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
  background: #F7F8FA;
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

.fm-product-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 22px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.fm-product-filter .company-pill,
.fm-company-filter .company-pill {
  padding: 4px 12px;
  border-radius: 16px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-alt, #f8f8f8);
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
  border-bottom: 1px solid #F0F0F0;
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

.kpi-actions {
  display: flex;
  gap: 4px;
  margin-inline-start: auto;
  flex-shrink: 0;
}
.kpi-action-btn {
  background: none;
  border: 1px solid rgba(232, 114, 10, 0.3);
  border-radius: 8px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #E8720A;
  transition: all 0.15s;
}
.kpi-action-btn:hover {
  background: rgba(232, 114, 10, 0.1);
  border-color: #E8720A;
  transform: translateY(-1px);
}
.kpi-action-excel {
  color: #2E844A;
  border-color: rgba(46, 132, 74, 0.3);
}
.kpi-action-excel:hover {
  background: rgba(46, 132, 74, 0.1);
  border-color: #2E844A;
}

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
  border: 1px solid rgba(232, 114, 10, 0.2);
  border-inline-start: 4px solid #E8720A;
  background: linear-gradient(135deg, rgba(232, 114, 10, 0.04) 0%, rgba(232, 114, 10, 0.08) 100%);
  overflow: hidden;
}

.unpaid-strip-pulse {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: rgba(232, 114, 10, 0.05);
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
  background: rgba(232, 114, 10, 0.12);
  color: #E8720A;
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
  color: #E8720A;
  font-weight: 800;
}
.unpaid-strip-amount {
  color: var(--text-secondary);
  font-weight: 500;
}
.unpaid-strip-amount strong {
  color: #c0540a;
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
  background: rgba(1, 118, 211, 0.06);
  color: var(--primary);
  border-color: rgba(1, 118, 211, 0.2);
}
.unpaid-strip-view:hover { background: rgba(1, 118, 211, 0.12); border-color: var(--primary); }

.unpaid-strip-mail {
  background: rgba(232, 114, 10, 0.06);
  color: #E8720A;
  border-color: rgba(232, 114, 10, 0.2);
}
.unpaid-strip-mail:hover { background: rgba(232, 114, 10, 0.12); border-color: #E8720A; }

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
.unpaid-strip-dismiss:hover { background: rgba(232, 114, 10, 0.1); color: #E8720A; }

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

/* ── Clipboard toast ── */
.clipboard-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--text, #1a1a1a);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  white-space: nowrap;
}
.clipboard-toast svg { flex-shrink: 0; }
.clipboard-toast-enter-active { animation: toastIn 0.3s ease-out; }
.clipboard-toast-leave-active { animation: toastIn 0.2s ease reverse; }
@keyframes toastIn {
  from { opacity: 0; transform: translateX(-50%) translateY(12px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
</style>
