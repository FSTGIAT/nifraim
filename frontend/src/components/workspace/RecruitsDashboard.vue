<template>
  <div class="rd-dashboard">
    <!-- Back button -->
    <button class="rd-back" @click="$emit('back')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6"/>
      </svg>
      <span>חזרה</span>
    </button>

    <!-- Hero: Donut chart -->
    <div class="hero-card">
      <div class="hero-header">
        <h2 class="hero-title">התפלגות מוצרים</h2>
        <span class="hero-badge">{{ result.total_clients }} לקוחות</span>
      </div>
      <div class="hero-body">
        <apexchart
          type="donut"
          :height="320"
          :options="donutOptions"
          :series="donutSeries"
        />
      </div>
      <div class="hero-stats">
        <div
          v-for="(item, i) in statusItems"
          :key="i"
          class="hero-stat"
          @click="filterBy(item.key)"
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

    <!-- KPI row -->
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
          <div class="kpi-value">{{ result.total_clients }}</div>
          <div class="kpi-label">סה"כ לקוחות</div>
        </div>
      </div>
      <div class="kpi-card kpi-green">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value">{{ result.found }}</div>
          <div class="kpi-label">נמצאו בפרודוקציה</div>
        </div>
      </div>
      <div class="kpi-card kpi-amber">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value">{{ result.not_found }}</div>
          <div class="kpi-label">לא נמצאו</div>
        </div>
      </div>
      <div class="kpi-card kpi-violet" v-if="result.companies.length > 0">
        <div class="kpi-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
            <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/>
          </svg>
        </div>
        <div class="kpi-data">
          <div class="kpi-value">{{ result.companies.length }}</div>
          <div class="kpi-label">חברות</div>
        </div>
      </div>
    </div>

    <!-- Results list -->
    <div class="results-card">
      <div class="results-header">
        <h3>פירוט לקוחות</h3>
        <div class="results-filter">
          <button
            v-for="f in filterOptions"
            :key="f.key"
            class="toggle-btn"
            :class="{ active: activeFilter === f.key }"
            @click="activeFilter = f.key"
          >{{ f.label }}</button>
        </div>
      </div>
      <div class="results-list">
        <div
          v-for="client in filteredResults"
          :key="client.id_number"
          class="client-row"
          :class="'status-' + client.match_status"
        >
          <div class="client-main" @click="toggleExpand(client.id_number)">
            <div class="client-dot" :class="'dot-' + client.match_status"></div>
            <div class="client-info">
              <span class="client-name">{{ clientName(client) }}</span>
              <span class="client-id ltr-number">{{ client.id_number }}</span>
            </div>
            <div class="client-badges">
              <span class="badge" :class="'badge-' + client.match_status">
                {{ statusLabel(client.match_status) }}
              </span>
              <span class="badge badge-count">{{ client.found_count }}/{{ client.total_count }}</span>
            </div>
            <svg
              class="expand-arrow"
              :class="{ expanded: expandedId === client.id_number }"
              width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            >
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>
          <Transition name="expand">
            <div v-if="expandedId === client.id_number" class="client-products">
              <div
                v-for="(p, i) in client.products"
                :key="i"
                class="product-row"
                :class="'prod-' + p.status"
              >
                <div class="prod-status-dot" :class="'pdot-' + p.status"></div>
                <div class="prod-info">
                  <span class="prod-name">{{ p.product || 'מוצר' }}</span>
                  <span class="prod-company" v-if="p.company">{{ p.company }}</span>
                </div>
                <div class="prod-meta">
                  <span v-if="p.policy_number" class="prod-policy ltr-number">{{ p.policy_number }}</span>
                  <span v-if="p.expected_amount" class="prod-amount ltr-number">₪{{ formatNum(p.expected_amount) }}</span>
                  <span class="prod-status-label" :class="'psl-' + p.status">{{ productStatusLabel(p.status) }}</span>
                </div>
              </div>
            </div>
          </Transition>
        </div>
        <div v-if="filteredResults.length === 0" class="empty-results">
          אין תוצאות לסינון הנוכחי
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  result: { type: Object, required: true },
})

defineEmits(['back'])

const expandedId = ref(null)
const activeFilter = ref('all')

const filterOptions = [
  { key: 'all', label: 'הכל' },
  { key: 'not_found', label: 'לא נמצא' },
  { key: 'client_only', label: 'לקוח בלבד' },
  { key: 'partial_match', label: 'חלקי' },
  { key: 'full_match', label: 'נמצא' },
]

const statusItems = computed(() => [
  { key: 'found', label: 'נמצא בפרודוקציה', count: props.result.found, color: '#2E844A' },
  { key: 'client_only', label: 'לקוח קיים, מוצר חסר', count: props.result.client_only, color: '#F57C00' },
  { key: 'not_found', label: 'לא נמצא', count: props.result.not_found, color: '#E8720A' },
])

const donutSeries = computed(() => statusItems.value.map(s => s.count))

const donutOptions = computed(() => ({
  labels: statusItems.value.map(s => s.label),
  colors: statusItems.value.map(s => s.color),
  chart: {
    fontFamily: 'Heebo, sans-serif',
    background: 'transparent',
  },
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
            label: 'סה"כ מוצרים',
            fontFamily: 'Heebo, sans-serif',
            fontSize: '13px',
            color: '#706E6B',
            formatter: () => props.result.total_products,
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

const filteredResults = computed(() => {
  if (activeFilter.value === 'all') return props.result.results
  return props.result.results.filter(c => c.match_status === activeFilter.value)
})

function filterBy(key) {
  if (key === 'found') activeFilter.value = 'full_match'
  else if (key === 'not_found') activeFilter.value = 'not_found'
  else if (key === 'client_only') activeFilter.value = 'client_only'
  else activeFilter.value = 'all'
}

function pctOf(count) {
  const total = props.result.total_products
  if (!total) return 0
  return ((count / total) * 100).toFixed(0)
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function clientName(c) {
  return [c.first_name, c.last_name].filter(Boolean).join(' ') || '—'
}

function statusLabel(status) {
  const map = { full_match: 'נמצא', partial_match: 'חלקי', client_only: 'לקוח בלבד', not_found: 'לא נמצא' }
  return map[status] || status
}

function productStatusLabel(status) {
  const map = { found: 'נמצא', client_only: 'לקוח בלבד', not_found: 'לא נמצא' }
  return map[status] || status
}

function formatNum(val) {
  if (val == null) return ''
  return Number(val).toLocaleString('he-IL')
}
</script>

<style scoped>
.rd-dashboard {
  animation: slideUp 0.4s var(--transition);
}

.rd-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 16px;
}

.rd-back:hover {
  color: var(--text);
  border-color: var(--primary);
  background: var(--primary-light);
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
  background: linear-gradient(90deg, #2E844A 0%, #2E844A 40%, #F57C00 40%, #F57C00 65%, #E8720A 65%, #E8720A 100%);
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
  grid-template-columns: repeat(4, 1fr);
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
.kpi-green .kpi-icon { background: rgba(46, 132, 74, 0.1); color: #2E844A; }
.kpi-amber .kpi-icon { background: rgba(232, 114, 10, 0.1); color: #E8720A; }
.kpi-amber .kpi-value { color: #E8720A; }
.kpi-violet .kpi-icon { background: rgba(127, 86, 217, 0.1); color: #7F56D9; }

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

/* ── Results Card ── */
.results-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.results-header h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.results-filter {
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

.results-list {
  max-height: 600px;
  overflow-y: auto;
}

.results-list::-webkit-scrollbar { width: 4px; }
.results-list::-webkit-scrollbar-track { background: transparent; }
.results-list::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.1); border-radius: 4px; }

/* ── Client Row ── */
.client-row {
  border-bottom: 1px solid var(--border-subtle);
}

.client-row:last-child {
  border-bottom: none;
}

.client-main {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  cursor: pointer;
  transition: background 0.12s;
}

.client-main:hover {
  background: var(--primary-light);
}

.client-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-full_match { background: #2E844A; }
.dot-partial_match { background: #F57C00; }
.dot-client_only { background: #7F56D9; }
.dot-not_found { background: #E8720A; }

.client-info {
  flex: 1;
  display: flex;
  gap: 10px;
  align-items: center;
  min-width: 0;
}

.client-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.client-id {
  font-size: 11px;
  color: var(--text-muted);
  font-family: monospace;
}

.client-badges {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.badge {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 8px;
  white-space: nowrap;
}

.badge-full_match { background: rgba(46, 132, 74, 0.1); color: #2E844A; }
.badge-partial_match { background: rgba(245, 124, 0, 0.1); color: #F57C00; }
.badge-client_only { background: rgba(127, 86, 217, 0.1); color: #7F56D9; }
.badge-not_found { background: rgba(232, 114, 10, 0.1); color: #E8720A; }
.badge-count { background: var(--border-subtle); color: var(--text-muted); }

.expand-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.expand-arrow.expanded {
  transform: rotate(180deg);
}

/* ── Expandable products ── */
.client-products {
  padding: 0 20px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.product-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--bg);
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.prod-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pdot-found { background: #2E844A; }
.pdot-client_only { background: #F57C00; }
.pdot-not_found { background: #E8720A; }

.prod-info {
  flex: 1;
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.prod-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
}

.prod-company {
  font-size: 11px;
  color: var(--text-muted);
}

.prod-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}

.prod-policy {
  font-size: 10px;
  color: var(--text-muted);
  font-family: monospace;
}

.prod-amount {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
}

.prod-status-label {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 6px;
}

.psl-found { background: rgba(46, 132, 74, 0.1); color: #2E844A; }
.psl-client_only { background: rgba(245, 124, 0, 0.1); color: #F57C00; }
.psl-not_found { background: rgba(232, 114, 10, 0.1); color: #E8720A; }

.empty-results {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-size: 13px;
}

/* ── Transitions ── */
.expand-enter-active {
  animation: expandIn 0.2s ease-out;
}
.expand-leave-active {
  animation: expandIn 0.15s ease reverse;
}
@keyframes expandIn {
  from { opacity: 0; max-height: 0; }
  to { opacity: 1; max-height: 500px; }
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
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
</style>
