<template>
  <div class="prod-comparison">
    <!-- No history -->
    <div v-if="!history.length && !comparisonResult" class="empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
      <p>אין קבצים קודמים להשוואה — החלף את קובץ הפרודוקציה ותוכל להשוות</p>
    </div>

    <!-- File selector -->
    <div v-else-if="!comparisonResult && !comparing" class="selector-section">
      <h4 class="selector-title">בחר קובץ קודם להשוואה</h4>
      <div class="history-grid">
        <div
          v-for="f in history"
          :key="f.id"
          class="history-card"
          :class="{ selected: selectedFileId === f.id }"
          @click="selectedFileId = f.id"
        >
          <div class="hc-radio">
            <div class="hc-radio-inner" v-if="selectedFileId === f.id"></div>
          </div>
          <div class="hc-info">
            <span class="hc-name">{{ f.filename }}</span>
            <span class="hc-meta">
              <span class="ltr-number">{{ f.record_count.toLocaleString() }}</span> רשומות
              · {{ formatDate(f.uploaded_at) }}
            </span>
          </div>
        </div>
      </div>
      <button
        class="btn-compare"
        :disabled="!selectedFileId"
        @click="runCompare"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <span>השווה קבצים</span>
      </button>
    </div>

    <!-- Comparing -->
    <div v-else-if="comparing" class="loading-state">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span>משווה קבצים...</span>
    </div>

    <!-- Results -->
    <div v-else-if="comparisonResult" class="results-section">
      <div class="results-header">
        <h4>תוצאות השוואה</h4>
        <button class="btn-back" @click="$emit('reset')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 19 5 12 12 5"/>
          </svg>
          חזרה
        </button>
      </div>

      <!-- Summary KPI strip -->
      <div class="summary-strip">
        <div class="summary-badge badge-green" @click="openCategory('new')">
          <span class="ltr-number">{{ comparisonResult.summary.new_count }}</span>
          <span>חדשים</span>
        </div>
        <div class="summary-badge badge-red" @click="openCategory('removed')">
          <span class="ltr-number">{{ comparisonResult.summary.removed_count }}</span>
          <span>הוסרו</span>
        </div>
        <div class="summary-badge badge-amber" @click="openCategory('changed')">
          <span class="ltr-number">{{ comparisonResult.summary.changed_count }}</span>
          <span>שונו</span>
        </div>
        <div class="summary-badge badge-gray">
          <span class="ltr-number">{{ comparisonResult.summary.unchanged_count }}</span>
          <span>ללא שינוי</span>
        </div>
      </div>

      <!-- Donut Chart -->
      <div class="chart-card">
        <div class="chart-title-row">
          <span class="chart-title">התפלגות שינויים</span>
          <span class="chart-subtitle">לחץ על פרוסה לצפייה בפרטים</span>
        </div>
        <apexchart
          type="donut"
          height="400"
          :options="chartOptions"
          :series="chartSeries"
          @dataPointSelection="onChartClick"
        />
        <!-- Custom legend -->
        <div class="chart-legend">
          <div
            v-for="(cat, i) in CATEGORIES"
            :key="cat.key"
            class="legend-item"
            :class="{ clickable: cat.key !== 'unchanged' }"
            @click="cat.key !== 'unchanged' && openCategory(cat.key)"
          >
            <span class="legend-dot" :style="{ background: cat.color }"></span>
            <span class="legend-label">{{ cat.label }}</span>
            <span class="legend-value ltr-number">{{ chartSeries[i]?.toLocaleString() || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- Company breakdown charts -->
      <div class="charts-grid">
        <!-- New by company -->
        <div class="chart-card chart-card-half" v-if="newByCompany.series.length">
          <div class="chart-title-row">
            <span class="chart-title">חדשים לפי חברה</span>
            <span class="chart-badge badge-green"><span class="ltr-number">{{ comparisonResult.summary.new_count }}</span></span>
          </div>
          <apexchart
            type="donut"
            height="380"
            :options="newByCompany.options"
            :series="newByCompany.series"
            @dataPointSelection="(e, chart, config) => onCompanyChartClick('new', newByCompany.labels, config)"
          />
          <div class="chart-legend">
            <div
              v-for="(label, i) in newByCompany.labels"
              :key="label"
              class="legend-item clickable"
              @click="onCompanyChartClick('new', newByCompany.labels, { dataPointIndex: i })"
            >
              <span class="legend-dot" :style="{ background: COMPANY_COLORS[i % COMPANY_COLORS.length] }"></span>
              <span class="legend-label">{{ label }}</span>
              <span class="legend-value ltr-number">{{ newByCompany.series[i]?.toLocaleString() }}</span>
            </div>
          </div>
        </div>

        <!-- Removed by company -->
        <div class="chart-card chart-card-half" v-if="removedByCompany.series.length">
          <div class="chart-title-row">
            <span class="chart-title">הוסרו לפי חברה</span>
            <span class="chart-badge badge-red"><span class="ltr-number">{{ comparisonResult.summary.removed_count }}</span></span>
          </div>
          <apexchart
            type="donut"
            height="380"
            :options="removedByCompany.options"
            :series="removedByCompany.series"
            @dataPointSelection="(e, chart, config) => onCompanyChartClick('removed', removedByCompany.labels, config)"
          />
          <div class="chart-legend">
            <div
              v-for="(label, i) in removedByCompany.labels"
              :key="label"
              class="legend-item clickable"
              @click="onCompanyChartClick('removed', removedByCompany.labels, { dataPointIndex: i })"
            >
              <span class="legend-dot" :style="{ background: COMPANY_COLORS[(i + 4) % COMPANY_COLORS.length] }"></span>
              <span class="legend-label">{{ label }}</span>
              <span class="legend-value ltr-number">{{ removedByCompany.series[i]?.toLocaleString() }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== Changed Insights Section ===== -->
      <div v-if="changedInsights.totalClients > 0" class="changed-section">
        <div class="changed-section-header">
          <span class="changed-section-title">שונו — תובנות</span>
          <span class="chart-badge badge-amber"><span class="ltr-number">{{ changedInsights.totalClients }}</span> לקוחות</span>
        </div>

        <!-- KPI cards -->
        <div class="changed-kpi-strip">
          <div class="changed-kpi" :class="changedInsights.totalPremiumDiff >= 0 ? 'kpi-green' : 'kpi-red'">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.totalPremiumDiff >= 0 ? '+' : '' }}{{ formatAmount(changedInsights.totalPremiumDiff) }}</span>
            <span class="changed-kpi-label">שינוי פרמיה כולל</span>
          </div>
          <div class="changed-kpi" :class="changedInsights.totalAccumulationDiff >= 0 ? 'kpi-green' : 'kpi-red'">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.totalAccumulationDiff >= 0 ? '+' : '' }}{{ formatAmount(changedInsights.totalAccumulationDiff) }}</span>
            <span class="changed-kpi-label">שינוי צבירה כולל</span>
          </div>
          <div class="changed-kpi kpi-clickable" @click="openChangedByType('פרמיה')">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.premiumCount }}</span>
            <span class="changed-kpi-label">שינוי פרמיה</span>
          </div>
          <div class="changed-kpi kpi-clickable" @click="openChangedByType('צבירה')">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.accumulationCount }}</span>
            <span class="changed-kpi-label">שינוי צבירה</span>
          </div>
          <div class="changed-kpi kpi-clickable" @click="openChangedByType('מוצרים')">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.productCount }}</span>
            <span class="changed-kpi-label">שינוי מוצרים</span>
          </div>
        </div>

        <!-- Charts row: donut + bar -->
        <div class="charts-grid">
          <!-- Change type donut -->
          <div class="chart-card chart-card-half">
            <div class="chart-title-row">
              <span class="chart-title">שונו לפי סוג שינוי</span>
              <span class="chart-subtitle">לחץ על פרוסה לצפייה בפרטים</span>
            </div>
            <apexchart
              type="donut"
              height="380"
              :options="changeTypeChartOptions"
              :series="changeTypeChartSeries"
              @dataPointSelection="onChangeTypeChartClick"
            />
            <div class="chart-legend">
              <div
                v-for="(ct, i) in CHANGE_TYPES"
                :key="ct.field"
                class="legend-item clickable"
                @click="openChangedByType(ct.field)"
              >
                <span class="legend-dot" :style="{ background: ct.color }"></span>
                <span class="legend-label">{{ ct.label }}</span>
                <span class="legend-value ltr-number">{{ changeTypeChartSeries[i]?.toLocaleString() || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- Top changers bar chart -->
          <div class="chart-card chart-card-half">
            <div class="chart-title-row">
              <span class="chart-title">גדולי השינויים</span>
              <div class="bar-toggle">
                <button
                  class="bar-toggle-btn"
                  :class="{ active: barMode === 'premium' }"
                  @click="barMode = 'premium'"
                >פרמיה</button>
                <button
                  class="bar-toggle-btn"
                  :class="{ active: barMode === 'accumulation' }"
                  @click="barMode = 'accumulation'"
                >צבירה</button>
              </div>
            </div>
            <apexchart
              type="bar"
              height="380"
              :options="topChangersChartOptions"
              :series="topChangersChartSeries"
              @dataPointSelection="onBarChartClick"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Filter Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="filterModal.open" class="fm-overlay" @click.self="closeModal">
          <div class="fm-card">
            <!-- List view -->
            <template v-if="!detailCustomer">
              <div class="fm-header">
                <div class="fm-header-info">
                  <span class="fm-title">{{ filterModal.title }}</span>
                  <span class="fm-count">
                    <span class="ltr-number">{{ filterModal.customers.length }}</span> לקוחות
                  </span>
                </div>
                <button class="fm-close" @click="closeModal">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>

              <!-- Search -->
              <div class="fm-search-wrap">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input v-model="searchQuery" class="fm-search" placeholder="חיפוש לפי שם או ת.ז." />
              </div>

              <div class="fm-list">
                <div
                  v-for="c in filteredCustomers"
                  :key="c.id_number"
                  class="fm-row"
                  @click="openDetail(c)"
                >
                  <div class="fm-row-main">
                    <span class="fm-row-name">{{ c.name }}</span>
                    <span class="fm-row-id ltr-number">{{ c.id_number }}</span>
                    <span class="fm-row-company">{{ c.company }}</span>
                  </div>
                  <div class="fm-row-stats">
                    <span v-if="c.premium" class="fm-row-stat">פרמיה <span class="ltr-number">{{ formatAmount(c.premium) }}</span></span>
                    <span v-if="c.accumulation" class="fm-row-stat">צבירה <span class="ltr-number">{{ formatAmount(c.accumulation) }}</span></span>
                    <span class="fm-row-stat">
                      <span class="ltr-number">{{ c.products_count }}</span> מוצרים
                    </span>
                  </div>
                  <svg class="fm-row-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="15 18 9 12 15 6"/>
                  </svg>
                </div>
                <div v-if="!filteredCustomers.length" class="fm-empty">לא נמצאו תוצאות</div>
              </div>
            </template>

            <!-- Detail view -->
            <template v-else>
              <div class="fm-header">
                <button class="fm-back-btn" @click="detailCustomer = null">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"/>
                    <polyline points="12 19 5 12 12 5"/>
                  </svg>
                  חזרה לרשימה
                </button>
                <button class="fm-close" @click="closeModal">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>

              <div class="detail-content">
                <!-- Customer info card -->
                <div class="detail-info-card">
                  <div class="detail-name">{{ detailCustomer.name }}</div>
                  <div class="detail-meta">
                    <span class="ltr-number">{{ detailCustomer.id_number }}</span>
                    <span class="detail-sep">·</span>
                    <span>{{ detailCustomer.company }}</span>
                  </div>
                  <div class="detail-stats">
                    <div class="detail-stat">
                      <span class="detail-stat-label">פרמיה</span>
                      <span class="detail-stat-value ltr-number">{{ formatAmount(detailCustomer.premium) }}</span>
                    </div>
                    <div class="detail-stat">
                      <span class="detail-stat-label">צבירה</span>
                      <span class="detail-stat-value ltr-number">{{ formatAmount(detailCustomer.accumulation) }}</span>
                    </div>
                    <div class="detail-stat">
                      <span class="detail-stat-label">מוצרים</span>
                      <span class="detail-stat-value ltr-number">{{ detailCustomer.products_count }}</span>
                    </div>
                  </div>
                </div>

                <!-- Changes (for changed customers) -->
                <div v-if="filterModal.category === 'changed' && detailCustomer.changes?.length" class="detail-changes">
                  <h5 class="detail-changes-title">שינויים שזוהו</h5>

                  <!-- Premium / accumulation diffs -->
                  <div v-if="detailCustomer.premium_diff || detailCustomer.accumulation_diff" class="detail-diffs-row">
                    <div v-if="detailCustomer.premium_diff" class="detail-diff-badge" :class="detailCustomer.premium_diff > 0 ? 'diff-up' : 'diff-down'">
                      פרמיה {{ detailCustomer.premium_diff > 0 ? '+' : '' }}<span class="ltr-number">{{ formatAmount(detailCustomer.premium_diff) }}</span>
                    </div>
                    <div v-if="detailCustomer.accumulation_diff" class="detail-diff-badge" :class="detailCustomer.accumulation_diff > 0 ? 'diff-up' : 'diff-down'">
                      צבירה {{ detailCustomer.accumulation_diff > 0 ? '+' : '' }}<span class="ltr-number">{{ formatAmount(detailCustomer.accumulation_diff) }}</span>
                    </div>
                  </div>

                  <div class="detail-changes-list">
                    <div v-for="ch in detailCustomer.changes" :key="ch.field" class="detail-change-row">
                      <span class="detail-change-field">{{ ch.field }}</span>
                      <div class="detail-change-vals">
                        <span class="detail-val-old ltr-number">{{ formatVal(ch.old_val) }}</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                        </svg>
                        <span class="detail-val-new ltr-number">{{ formatVal(ch.new_val) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
  comparisonResult: { type: Object, default: null },
  comparing: { type: Boolean, default: false },
  currentFileId: { type: String, default: null },
})

const emit = defineEmits(['compare', 'reset'])

const selectedFileId = ref(null)
const searchQuery = ref('')
const detailCustomer = ref(null)

const filterModal = reactive({
  open: false,
  title: '',
  category: '',
  customers: [],
})

// Chart
const CATEGORIES = [
  { key: 'new', label: 'חדשים', color: '#10b981' },
  { key: 'removed', label: 'הוסרו', color: '#ef4444' },
  { key: 'changed', label: 'שונו', color: '#f59e0b' },
  { key: 'unchanged', label: 'ללא שינוי', color: '#94a3b8' },
]

const chartSeries = computed(() => {
  if (!props.comparisonResult) return []
  const s = props.comparisonResult.summary
  return [s.new_count, s.removed_count, s.changed_count, s.unchanged_count]
})

const chartOptions = computed(() => ({
  labels: CATEGORIES.map(c => c.label),
  colors: CATEGORIES.map(c => c.color),
  chart: {
    fontFamily: 'Heebo, sans-serif',
    animations: { enabled: true, easing: 'easeinout', speed: 800 },
    dropShadow: { enabled: true, top: 4, left: 0, blur: 12, opacity: 0.08 },
  },
  plotOptions: {
    pie: {
      expandOnClick: true,
      donut: {
        size: '58%',
        labels: {
          show: true,
          name: { fontSize: '15px', fontWeight: 700, offsetY: -4 },
          value: { fontSize: '26px', fontWeight: 800, offsetY: 4, formatter: (val) => Number(val).toLocaleString() },
          total: {
            show: true,
            label: 'סה"כ לקוחות',
            fontSize: '12px',
            fontWeight: 600,
            color: '#64748b',
            formatter: (w) => w.globals.seriesTotals.reduce((a, b) => a + b, 0).toLocaleString()
          }
        }
      }
    }
  },
  dataLabels: {
    enabled: true,
    formatter: (val) => val > 3 ? val.toFixed(0) + '%' : '',
    style: { fontSize: '12px', fontWeight: 700, colors: ['#fff'] },
    dropShadow: { enabled: true, top: 1, left: 0, blur: 2, opacity: 0.3 },
  },
  legend: {
    show: false,
  },
  stroke: { width: 3, colors: ['#fff'] },
  tooltip: {
    y: { formatter: (val) => val.toLocaleString() + ' לקוחות' }
  },
}))

// Company palette for sub-charts
const COMPANY_COLORS = [
  '#6366f1', '#06b6d4', '#f43f5e', '#8b5cf6', '#14b8a6',
  '#ec4899', '#f97316', '#0ea5e9', '#84cc16', '#a855f7',
  '#eab308', '#64748b',
]

function groupByCompany(clients) {
  const map = {}
  for (const c of clients) {
    const co = c.company || 'לא ידוע'
    map[co] = (map[co] || 0) + 1
  }
  // Sort descending
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1])
  return { labels: entries.map(e => e[0]), series: entries.map(e => e[1]) }
}

function makeCompanyChartOptions(labels, colorOffset = 0) {
  return {
    labels,
    colors: labels.map((_, i) => COMPANY_COLORS[(i + colorOffset) % COMPANY_COLORS.length]),
    chart: {
      fontFamily: 'Heebo, sans-serif',
      animations: { enabled: true, easing: 'easeinout', speed: 800 },
      dropShadow: { enabled: true, top: 4, left: 0, blur: 12, opacity: 0.08 },
    },
    plotOptions: {
      pie: {
        expandOnClick: true,
        donut: {
          size: '58%',
          labels: {
            show: true,
            name: { fontSize: '14px', fontWeight: 700, offsetY: -4 },
            value: { fontSize: '24px', fontWeight: 800, offsetY: 4, formatter: (val) => Number(val).toLocaleString() },
            total: {
              show: true,
              label: 'סה"כ',
              fontSize: '11px',
              fontWeight: 600,
              color: '#64748b',
              formatter: (w) => w.globals.seriesTotals.reduce((a, b) => a + b, 0).toLocaleString()
            }
          }
        }
      }
    },
    dataLabels: {
      enabled: true,
      formatter: (val) => val > 5 ? val.toFixed(0) + '%' : '',
      style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] },
      dropShadow: { enabled: true, top: 1, left: 0, blur: 2, opacity: 0.3 },
    },
    legend: {
      show: false,
    },
    stroke: { width: 3, colors: ['#fff'] },
    tooltip: {
      y: { formatter: (val) => val.toLocaleString() + ' לקוחות' }
    },
  }
}

const newByCompany = computed(() => {
  if (!props.comparisonResult?.new_clients?.length) return { labels: [], series: [], options: {} }
  const { labels, series } = groupByCompany(props.comparisonResult.new_clients)
  return { labels, series, options: makeCompanyChartOptions(labels, 0) }
})

const removedByCompany = computed(() => {
  if (!props.comparisonResult?.removed_clients?.length) return { labels: [], series: [], options: {} }
  const { labels, series } = groupByCompany(props.comparisonResult.removed_clients)
  return { labels, series, options: makeCompanyChartOptions(labels, 4) }
})

// ===== Changed Insights =====
const CHANGE_TYPES = [
  { field: 'פרמיה', label: 'פרמיה', color: '#6366f1' },
  { field: 'צבירה', label: 'צבירה', color: '#06b6d4' },
  { field: 'מוצרים', label: 'מוצרים', color: '#f59e0b' },
]

const barMode = ref('premium')

const changedInsights = computed(() => {
  const clients = props.comparisonResult?.changed_clients || []
  if (!clients.length) return { totalClients: 0, totalPremiumDiff: 0, totalAccumulationDiff: 0, premiumCount: 0, accumulationCount: 0, productCount: 0, topPremium: [], topAccumulation: [] }

  let totalPremiumDiff = 0
  let totalAccumulationDiff = 0
  let premiumCount = 0
  let accumulationCount = 0
  let productCount = 0

  for (const c of clients) {
    totalPremiumDiff += (c.premium_diff || 0)
    totalAccumulationDiff += (c.accumulation_diff || 0)
    if (c.changes?.some(ch => ch.field === 'פרמיה')) premiumCount++
    if (c.changes?.some(ch => ch.field === 'צבירה')) accumulationCount++
    if (c.changes?.some(ch => ch.field === 'מוצרים')) productCount++
  }

  const topPremium = [...clients]
    .filter(c => c.premium_diff)
    .sort((a, b) => Math.abs(b.premium_diff) - Math.abs(a.premium_diff))
    .slice(0, 10)

  const topAccumulation = [...clients]
    .filter(c => c.accumulation_diff)
    .sort((a, b) => Math.abs(b.accumulation_diff) - Math.abs(a.accumulation_diff))
    .slice(0, 10)

  return { totalClients: clients.length, totalPremiumDiff, totalAccumulationDiff, premiumCount, accumulationCount, productCount, topPremium, topAccumulation }
})

const changeTypeChartSeries = computed(() => {
  const ins = changedInsights.value
  return [ins.premiumCount, ins.accumulationCount, ins.productCount]
})

const changeTypeChartOptions = computed(() => ({
  labels: CHANGE_TYPES.map(c => c.label),
  colors: CHANGE_TYPES.map(c => c.color),
  chart: {
    fontFamily: 'Heebo, sans-serif',
    animations: { enabled: true, easing: 'easeinout', speed: 800 },
    dropShadow: { enabled: true, top: 4, left: 0, blur: 12, opacity: 0.08 },
  },
  plotOptions: {
    pie: {
      expandOnClick: true,
      donut: {
        size: '58%',
        labels: {
          show: true,
          name: { fontSize: '14px', fontWeight: 700, offsetY: -4 },
          value: { fontSize: '24px', fontWeight: 800, offsetY: 4, formatter: (val) => Number(val).toLocaleString() },
          total: {
            show: true,
            label: 'סוגי שינויים',
            fontSize: '11px',
            fontWeight: 600,
            color: '#64748b',
            formatter: (w) => w.globals.seriesTotals.reduce((a, b) => a + b, 0).toLocaleString()
          }
        }
      }
    }
  },
  dataLabels: {
    enabled: true,
    formatter: (val) => val > 5 ? val.toFixed(0) + '%' : '',
    style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] },
    dropShadow: { enabled: true, top: 1, left: 0, blur: 2, opacity: 0.3 },
  },
  legend: { show: false },
  stroke: { width: 3, colors: ['#fff'] },
  tooltip: {
    y: { formatter: (val) => val.toLocaleString() + ' לקוחות' }
  },
}))

const topChangersData = computed(() => {
  const ins = changedInsights.value
  return barMode.value === 'premium' ? ins.topPremium : ins.topAccumulation
})

const topChangersChartSeries = computed(() => {
  const data = topChangersData.value
  const diffKey = barMode.value === 'premium' ? 'premium_diff' : 'accumulation_diff'
  return [{
    name: barMode.value === 'premium' ? 'שינוי פרמיה' : 'שינוי צבירה',
    data: data.map(c => Math.round(c[diffKey] || 0)),
  }]
})

const topChangersChartOptions = computed(() => {
  const data = topChangersData.value
  const diffKey = barMode.value === 'premium' ? 'premium_diff' : 'accumulation_diff'
  const names = data.map(c => c.name || c.id_number || '---')
  return {
    chart: {
      fontFamily: 'Heebo, sans-serif',
      toolbar: { show: false },
    },
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 4,
        barHeight: '65%',
        distributed: true,
        colors: {
          ranges: [
            { from: -999999999, to: -0.01, color: '#ef4444' },
            { from: 0, to: 999999999, color: '#10b981' },
          ]
        }
      }
    },
    colors: data.map(c => (c[diffKey] || 0) >= 0 ? '#10b981' : '#ef4444'),
    dataLabels: {
      enabled: true,
      formatter: (val) => (val >= 0 ? '+' : '') + '₪' + Math.abs(val).toLocaleString(),
      style: { fontSize: '11px', fontWeight: 700, colors: ['#1e293b'] },
      offsetX: 6,
    },
    xaxis: {
      labels: {
        formatter: (val) => '₪' + Math.abs(Math.round(val)).toLocaleString(),
        style: { fontFamily: 'Heebo, sans-serif', fontSize: '10px' },
      }
    },
    yaxis: {
      labels: {
        style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', fontWeight: 600 },
        maxWidth: 120,
      }
    },
    labels: names,
    legend: { show: false },
    tooltip: {
      y: { formatter: (val) => (val >= 0 ? '+' : '') + '₪' + Math.abs(val).toLocaleString() }
    },
    grid: {
      borderColor: 'var(--border-subtle)',
      xaxis: { lines: { show: true } },
      yaxis: { lines: { show: false } },
    },
  }
})

function onChangeTypeChartClick(_e, _chart, config) {
  const idx = config.dataPointIndex
  if (idx < 0) return
  openChangedByType(CHANGE_TYPES[idx].field)
}

function openChangedByType(field) {
  const clients = props.comparisonResult?.changed_clients || []
  const filtered = clients.filter(c => c.changes?.some(ch => ch.field === field))
  if (!filtered.length) return

  filterModal.open = true
  filterModal.title = `שונו — ${field}`
  filterModal.category = 'changed'
  filterModal.customers = filtered
  searchQuery.value = ''
  detailCustomer.value = null
}

function onBarChartClick(_e, _chart, config) {
  const idx = config.dataPointIndex
  if (idx < 0) return
  const data = topChangersData.value
  if (idx < data.length) {
    openDetail(data[idx])
    // Also ensure modal is open with changed clients context
    if (!filterModal.open) {
      filterModal.open = true
      filterModal.title = 'גדולי השינויים'
      filterModal.category = 'changed'
      filterModal.customers = props.comparisonResult?.changed_clients || []
      searchQuery.value = ''
    }
  }
}

function onCompanyChartClick(category, labels, config) {
  const idx = config.dataPointIndex
  if (idx < 0) return
  const company = labels[idx]
  const r = props.comparisonResult
  if (!r) return

  const clientsMap = { new: r.new_clients, removed: r.removed_clients }
  const titlesMap = { new: 'חדשים', removed: 'הוסרו' }
  const clients = (clientsMap[category] || []).filter(c => (c.company || 'לא ידוע') === company)

  if (!clients.length) return

  filterModal.open = true
  filterModal.title = `${titlesMap[category]} — ${company}`
  filterModal.category = category
  filterModal.customers = clients
  searchQuery.value = ''
  detailCustomer.value = null
}

const filteredCustomers = computed(() => {
  if (!searchQuery.value) return filterModal.customers
  const q = searchQuery.value.toLowerCase()
  return filterModal.customers.filter(c =>
    (c.name && c.name.toLowerCase().includes(q)) ||
    (c.id_number && c.id_number.includes(q))
  )
})

function onChartClick(_e, _chart, config) {
  const idx = config.dataPointIndex
  if (idx < 0) return
  const cat = CATEGORIES[idx]
  openCategory(cat.key)
}

function openCategory(key) {
  const r = props.comparisonResult
  if (!r) return

  if (key === 'unchanged') return // no client list available

  const map = {
    new: { title: 'לקוחות חדשים', customers: r.new_clients },
    removed: { title: 'לקוחות שהוסרו', customers: r.removed_clients },
    changed: { title: 'לקוחות ששונו', customers: r.changed_clients },
  }

  const info = map[key]
  if (!info || !info.customers?.length) return

  filterModal.open = true
  filterModal.title = info.title
  filterModal.category = key
  filterModal.customers = info.customers
  searchQuery.value = ''
  detailCustomer.value = null
}

function openDetail(customer) {
  detailCustomer.value = customer
}

function closeModal() {
  filterModal.open = false
  detailCustomer.value = null
}

function runCompare() {
  if (selectedFileId.value && props.currentFileId) {
    emit('compare', props.currentFileId, selectedFileId.value)
  }
}

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatAmount(val) {
  if (!val || val === 0) return '₪0'
  return '₪' + Math.round(val).toLocaleString()
}

function formatVal(val) {
  if (typeof val === 'number') return formatAmount(val)
  return val
}
</script>

<style scoped>
.prod-comparison {
  animation: slideUp 0.4s var(--transition);
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-muted);
}

.empty-state svg { margin-bottom: 12px; opacity: 0.3; }
.empty-state p { font-size: 14px; }

/* Selector */
.selector-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selector-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.history-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--card-bg);
  border: 1.5px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.25s var(--transition);
}

.history-card:hover {
  border-color: var(--border);
  background: var(--bg-surface);
}

.history-card.selected {
  border-color: var(--primary);
  background: var(--primary-light);
}

.hc-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.2s;
}

.history-card.selected .hc-radio {
  border-color: var(--primary);
}

.hc-radio-inner {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--primary);
}

.hc-info { display: flex; flex-direction: column; gap: 2px; }
.hc-name { font-size: 13px; font-weight: 600; color: var(--text); word-break: break-all; }
.hc-meta { font-size: 11px; color: var(--text-muted); }

.btn-compare {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 28px;
  background: linear-gradient(135deg, var(--accent-violet), var(--primary-deep));
  color: white;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  align-self: flex-start;
  transition: all 0.3s var(--transition);
}

.btn-compare:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(127, 86, 217, 0.15);
}

.btn-compare:disabled { opacity: 0.4; cursor: not-allowed; }

/* Loading */
.loading-state {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loader {
  width: 36px;
  height: 36px;
  position: relative;
  margin: 0 auto 14px;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 5px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

/* Results */
.results-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.results-header h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 8px;
  transition: all 0.2s;
}

.btn-back:hover {
  color: var(--text);
  background: var(--bg-surface);
}

/* Summary strip */
.summary-strip {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.summary-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.summary-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.summary-badge.badge-gray {
  cursor: default;
}

.summary-badge.badge-gray:hover {
  transform: none;
  box-shadow: none;
}

.badge-green { background: var(--green-light); color: var(--accent-emerald); }
.badge-red { background: var(--red-light); color: var(--red); }
.badge-amber { background: var(--amber-light); color: var(--amber); }
.badge-gray { background: var(--border-subtle); color: var(--text-muted); }

/* Chart card */
.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg, 16px);
  padding: 28px 24px 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.chart-title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 4px;
  padding: 0 4px;
}

.chart-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.chart-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

/* Custom legend */
.chart-legend {
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
  padding: 0 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s;
}

.legend-item.clickable {
  cursor: pointer;
}

.legend-item.clickable:hover {
  border-color: var(--border);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.legend-value {
  font-size: 13px;
  font-weight: 800;
  color: var(--text);
}

/* Charts grid */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media (max-width: 700px) {
  .charts-grid { grid-template-columns: 1fr; }
}

.chart-card-half {
  padding: 20px 16px 12px;
}

.chart-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 8px;
}

/* ===== Changed Insights Section ===== */
.changed-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.changed-section-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.changed-section-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
}

.changed-kpi-strip {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.changed-kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 20px;
  border-radius: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  flex: 1;
  min-width: 110px;
  transition: all 0.2s;
}

.changed-kpi.kpi-clickable {
  cursor: pointer;
}

.changed-kpi.kpi-clickable:hover {
  border-color: var(--border);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.changed-kpi.kpi-green { border-color: rgba(16, 185, 129, 0.25); background: rgba(16, 185, 129, 0.06); }
.changed-kpi.kpi-red { border-color: rgba(239, 68, 68, 0.25); background: rgba(239, 68, 68, 0.06); }

.changed-kpi-value {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
}

.kpi-green .changed-kpi-value { color: var(--accent-emerald); }
.kpi-red .changed-kpi-value { color: var(--red); }

.changed-kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

/* Bar chart toggle */
.bar-toggle {
  display: flex;
  gap: 2px;
  background: var(--bg-surface);
  border-radius: 8px;
  padding: 2px;
  border: 1px solid var(--border-subtle);
}

.bar-toggle-btn {
  padding: 4px 14px;
  font-size: 11px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.2s;
}

.bar-toggle-btn.active {
  background: var(--card-bg);
  color: var(--text);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.bar-toggle-btn:not(.active):hover {
  color: var(--text-secondary);
}

/* ===== Filter Modal ===== */
.fm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.fm-card {
  background: var(--card-bg, #fff);
  border-radius: var(--radius-lg, 16px);
  width: 100%;
  max-width: 620px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18);
}

.fm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.fm-header-info {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.fm-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.fm-count {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.fm-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-muted);
  transition: all 0.2s;
  flex-shrink: 0;
}

.fm-close:hover {
  background: var(--bg-surface);
  color: var(--text);
}

.fm-back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--primary);
  transition: opacity 0.2s;
}

.fm-back-btn:hover { opacity: 0.7; }

/* Search */
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

/* List */
.fm-list {
  overflow-y: auto;
  flex: 1;
}

.fm-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 22px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid var(--border-subtle);
}

.fm-row:last-child { border-bottom: none; }

.fm-row:hover { background: var(--bg-surface); }

.fm-row-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.fm-row-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
}

.fm-row-id {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.fm-row-company {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.fm-row-stats {
  display: flex;
  gap: 10px;
  margin-inline-start: auto;
  flex-shrink: 0;
}

.fm-row-stat {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.fm-row-chevron {
  color: var(--text-muted);
  opacity: 0.4;
  flex-shrink: 0;
}

.fm-empty {
  padding: 32px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

/* ===== Detail view ===== */
.detail-content {
  padding: 22px;
  overflow-y: auto;
  flex: 1;
}

.detail-info-card {
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 20px;
}

.detail-name {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 4px;
}

.detail-meta {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.detail-sep { margin: 0 6px; }

.detail-stats {
  display: flex;
  gap: 24px;
}

.detail-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-stat-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.detail-stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

/* Changes section */
.detail-changes {
  margin-top: 4px;
}

.detail-changes-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12px;
}

.detail-diffs-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.detail-diff-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 8px;
}

.diff-up { background: var(--green-light); color: var(--accent-emerald); }
.diff-down { background: var(--red-light); color: var(--red); }

.detail-changes-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-change-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--bg-surface);
}

.detail-change-row:nth-child(odd) {
  background: transparent;
}

.detail-change-field {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 80px;
}

.detail-change-vals {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-change-vals svg { color: var(--text-muted); opacity: 0.4; flex-shrink: 0; }

.detail-val-old {
  font-size: 13px;
  color: var(--red);
  text-decoration: line-through;
  opacity: 0.7;
}

.detail-val-new {
  font-size: 13px;
  color: var(--accent-emerald);
  font-weight: 600;
}

/* ===== Modal transition ===== */
.modal-enter-active { animation: modalIn 0.25s ease; }
.modal-leave-active { animation: modalIn 0.2s ease reverse; }

@keyframes modalIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-enter-active .fm-card { animation: cardIn 0.25s ease; }
.modal-leave-active .fm-card { animation: cardIn 0.2s ease reverse; }

@keyframes cardIn {
  from { opacity: 0; transform: scale(0.95) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* Collapse transition (kept for potential reuse) */
.collapse-enter-active { animation: collapseIn 0.25s ease; }
.collapse-leave-active { animation: collapseIn 0.2s ease reverse; }

@keyframes collapseIn {
  from { opacity: 0; max-height: 0; }
  to { opacity: 1; max-height: 2000px; }
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
