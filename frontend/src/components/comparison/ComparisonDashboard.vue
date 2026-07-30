<template>
  <div class="bi-dashboard">
    <!-- AI insight card (התמונה הכוללת) -->
    <AiInsightCard
      v-if="aiViewContext"
      :view-context="aiViewContext"
      @open-sheet="openAiSheet"
    />

    <!-- ALERT: payments that disagree with the agreement. Only firm rates
         (an agreement line that names the product) reach here, so every row
         is a claim the agent can actually take to the insurer. -->
    <div v-if="mismatchAlert.count" class="gap-alert" role="alert">
      <span class="ga-icon" aria-hidden="true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
      </span>
      <div class="ga-text">
        <strong>
          <span class="ltr-number">{{ mismatchAlert.count }}</span>
          מוצרים שולמו בסכום שונה מהשיעור שבהסכם
        </strong>
        <span class="ga-sub">
          חסר סה"כ <span class="ltr-number">{{ fmtMoney(mismatchAlert.under) }}</span>
          <template v-if="mismatchAlert.overCount">
            · שולם ביתר <span class="ltr-number">{{ fmtMoney(mismatchAlert.over) }}</span>
          </template>
          · מחושב לפי האחוז שבטבלת העמלות מול מה שדווח בנפרעים
        </span>
      </div>
      <button class="ga-action" @click="onLegendClick('matched')">הצג לקוחות</button>
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
          <div class="kpi-label">עמלות שהתקבלו (לפי דיווח אחרון מכל חברה)</div>
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
            <div v-if="modalProducts.length > 1" class="fm-filter-collapse">
              <button class="fm-filter-trigger" :class="{ 'is-active': productFilter }" @click="productFilterOpen = !productFilterOpen">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
                </svg>
                <span>{{ productFilter || 'סנן לפי מוצר' }}</span>
                <span class="fm-filter-count">{{ modalProducts.length }}</span>
                <button v-if="productFilter" class="fm-filter-clear" @click.stop="productFilter = null" title="נקה סינון">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
                <svg class="fm-filter-chevron" :class="{ open: productFilterOpen }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              <div v-if="productFilterOpen" class="fm-product-filter">
                <button class="company-pill" :class="{ active: !productFilter }" @click="productFilter = null; productFilterOpen = false">הכל</button>
                <button v-for="p in modalProducts" :key="p" class="company-pill" :class="{ active: productFilter === p }" @click="productFilter = p; productFilterOpen = false">{{ p }}</button>
              </div>
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

    <!-- AI conversation sheet (teleported to body) -->
    <AiConversationSheet
      v-model:open="aiSheetOpen"
      :view-title="aiViewContext?.viewTitle || ''"
      :view-context="aiViewContext?.viewContextString || ''"
      :initial-question="aiInitialQuestion"
      @latest-vizs="onLatestVizs"
    />

    <!-- AI Remotion viz — centered modal overlay. Mirrors ProductionComparison.vue
         so vizs emitted from the chat sheet actually render here too. -->
    <AiVizPanel
      v-model:open="aiVizOpen"
      :vizs="activeVizs"
    />

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, toRef } from 'vue'
import * as XLSX from 'xlsx'
import api from '../../api/client.js'
import { useAuthStore } from '../../stores/auth.js'
import { openMailCompose } from '../../utils/mailHelper.js'
import { calcExpectedCommission } from '../../utils/commissionCalc.js'
import { CHART_PALETTE } from '../../utils/chartPalette.js'
import { normalizeCompany } from '../../utils/companyNorm.js'
import CustomerDetailModal from './CustomerDetailModal.vue'
import AiInsightCard from '../workspace/AiInsightCard.vue'
import AiConversationSheet from '../workspace/AiConversationSheet.vue'
import AiVizPanel from '../workspace/AiVizPanel.vue'
import { useAiViewContext } from '../../composables/useAiViewContext.js'

const props = defineProps({
  customers: { type: Array, required: true },
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
  periodFilesCount: { type: Number, default: 0 },
  periodFilesExcluded: { type: Number, default: 0 },
})

const emit = defineEmits(['drill-customer', 'initial-company-applied'])

const authStore = useAuthStore()
const productMetric = ref('count')
const detailCustomer = ref(null)
const commissionRates = ref([])
const showUnpaidStrip = ref(false)
const companyFilter = ref(null)

// AI assistant — inline insight card + side conversation sheet (mirrors ProductionComparison.vue)
const aiSheetOpen = ref(false)
const aiInitialQuestion = ref('')
const aiViewContext = useAiViewContext({
  viewKey: 'commission-comparison',
  customers: toRef(props, 'customers'),
  categoryLabel: toRef(props, 'categoryLabel'),
  companySources: toRef(props, 'companySources'),
})
function openAiSheet(question) {
  aiInitialQuestion.value = question || ''
  aiSheetOpen.value = true
}
watch(aiSheetOpen, (isOpen) => {
  if (!isOpen) {
    aiInitialQuestion.value = ''
    aiVizOpen.value = false
  }
})

const aiVizOpen = ref(false)
const activeVizs = ref(null)
function onLatestVizs(vizs) {
  activeVizs.value = vizs
  if (Array.isArray(vizs) && vizs.length) aiVizOpen.value = true
}

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
    if (sources.length > 1) {
      companyFilter.value = sources.find((src) => fuzzyCompanyMatch(src, company)) || null
    }
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

// Status donut — all three statuses
const statusItems = computed(() => [
  { key: 'matched', label: 'נמצא בשניהם', count: matchedCustomers.value.length, color: '#2E844A' },
  { key: 'only_production', label: 'לא שולם', count: effectiveUnpaidCustomers.value.length, color: '#E8720A' },
  { key: 'only_commission', label: 'רק בנפרעים', count: onlyCommCustomers.value.length, color: '#7F56D9' },
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

// ── Same distribution, broken down BY COMPANY ────────────────────────────
// The נפרעים side is now one merged file covering every company, so a single
// donut answers "how many customers are unpaid" but not "at which company" —
// which is the actionable half. A customer is counted once per company they
// hold a product with, so the per-company columns can sum to more than the
// headline total; that's intended, not double counting.
const companyStatusRows = computed(() => {
  const unpaidIds = new Set(effectiveUnpaidCustomers.value.map(c => c.id_number))
  const map = new Map()
  const bump = (key, displayName, statusKey) => {
    if (!map.has(key)) {
      map.set(key, { company: displayName, matched: 0, only_production: 0, only_commission: 0 })
    }
    const row = map.get(key)
    // Same insurer can arrive under several spellings (short 'מגדל' from the
    // commission side vs legal 'מגדל חברה לביטוח בע"מ' from the merged
    // production file). Show the shortest so the axis stays readable.
    if (displayName.length < row.company.length) row.company = displayName
    row[statusKey] += 1
  }
  for (const c of displayCustomers.value) {
    // only_production customers with no exposure are excluded from "unpaid"
    // in the headline, so they must be excluded here too or the two disagree.
    if (c.match_status === 'only_production' && !unpaidIds.has(c.id_number)) continue
    const products = [
      ...(c.production_products || []),
      ...(c.commission_products || []),
      ...(c.product_matches?.matched || []),
      ...(c.product_matches?.unmatched_production || []),
      ...(c.product_matches?.unmatched_commission || []),
    ]
    // `company` FIRST — it is the SHORT brand name, resolved server-side by
    // `_extract_short_company` from the record's own company column, and it is
    // consistent across the production and commission sides. `company_full`
    // is the raw legal name, so preferring it splits one insurer into two
    // ('מגדל' and 'מגדל חברה לביטוח בע"מ') on this chart.
    const names = products.map(p => p.company || p.company_full).filter(Boolean)
    if (!names.length && c.company) names.push(c.company)
    // Deduplicate on the NORMALIZED key, not the raw string. Two spellings of
    // one insurer on the same customer would otherwise bump the same bar
    // twice — that inflated מגדל from 73 customers to 145 on live data.
    const byKey = new Map()
    for (const raw of names) {
      const name = String(raw).trim()
      if (!name) continue
      const k = normalizeCompany(name) || name
      const prev = byKey.get(k)
      if (!prev || name.length < prev.length) byKey.set(k, name)
    }
    if (!byKey.size) {
      // No company on any of this customer's products. Bucket it rather than
      // drop it — otherwise the per-company bars quietly total less than the
      // headline and a customer disappears with no explanation.
      bump('__none__', 'ללא שיוך חברה', c.match_status)
    } else {
      for (const [k, displayName] of byKey) bump(k, displayName, c.match_status)
    }
  }
  return [...map.values()]
    .map(r => ({ ...r, total: r.matched + r.only_production + r.only_commission }))
    .filter(r => r.total > 0)
    .sort((a, b) => b.total - a.total)
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

// Clicking a segment filters to that company AND opens that status list —
// the same drill the donut does, one level more specific.
function onCompanyStatusClick(row, statusKey) {
  const src = props.companySources.find(s => fuzzyCompanyMatch(s, row.company))
  companyFilter.value = src || row.company
  onLegendClick(statusKey)
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

function openFilterModal(title, customers) {
  filterModal.value = { open: true, title, customers }
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
  await openMailCompose({ to: companyEmail, subject, body })
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
  await openMailCompose({ to: companyEmail, subject, body })
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
.kpi-cyan .kpi-icon { background: rgba(46, 132, 74, 0.1); color: #2E844A; }
.kpi-violet .kpi-icon { background: rgba(127, 86, 217, 0.1); color: #7F56D9; }
.kpi-violet .kpi-value { color: #7F56D9; }

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
  color: #E65100;
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
  background: rgba(245, 124, 0, 0.06);
  color: var(--primary);
  border-color: rgba(245, 124, 0, 0.2);
}
.unpaid-strip-view:hover { background: rgba(245, 124, 0, 0.12); border-color: var(--primary); }

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
</style>
