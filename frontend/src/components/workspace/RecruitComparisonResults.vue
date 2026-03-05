<template>
  <div class="comparison-results glass-card">
    <div class="results-header">
      <div class="header-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <h3>תוצאות בדיקה</h3>
      </div>
      <button class="btn-close" @click="recruitsStore.resetComparison()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- Chart + KPI row -->
    <div class="dashboard-row">
      <div class="chart-box">
        <apexchart
          v-if="chartReady"
          type="donut"
          :options="chartOptions"
          :series="chartSeries"
          height="240"
        />
      </div>
      <div class="kpi-row">
        <div class="kpi found-kpi" @click="activeFilter = 'found'">
          <span class="kpi-num ltr-number">{{ result.found }}</span>
          <span class="kpi-lbl">נמצאו</span>
          <span class="kpi-pct ltr-number">{{ foundPct }}%</span>
        </div>
        <div class="kpi missing-kpi" @click="activeFilter = 'not_found'">
          <span class="kpi-num ltr-number">{{ result.not_found }}</span>
          <span class="kpi-lbl">לא נמצאו</span>
          <span class="kpi-pct ltr-number">{{ missingPct }}%</span>
        </div>
        <div class="kpi total-kpi" @click="activeFilter = 'all'">
          <span class="kpi-num ltr-number">{{ result.total }}</span>
          <span class="kpi-lbl">סה"כ</span>
        </div>
      </div>
    </div>

    <!-- Segmented filter -->
    <div class="seg-filter">
      <button :class="{ active: activeFilter === 'all' }" @click="activeFilter = 'all'">הכל <b>{{ result.total }}</b></button>
      <button :class="{ active: activeFilter === 'found' }" @click="activeFilter = 'found'">נמצאו <b>{{ result.found }}</b></button>
      <button :class="{ active: activeFilter === 'not_found' }" @click="activeFilter = 'not_found'">לא נמצאו <b>{{ result.not_found }}</b></button>
    </div>

    <!-- Results table -->
    <div class="tbl-wrap">
      <table class="tbl">
        <thead>
          <tr>
            <th class="th-status"></th>
            <th>שם</th>
            <th>ת.ז</th>
            <th>חברה</th>
            <th>מוצר</th>
            <th>מוצרים בפרודוקציה</th>
            <th>פרמיה</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in paginatedResults"
            :key="item.recruit_id"
            class="tbl-row"
            :class="{ 'row-found': item.found_in_production, 'row-missing': !item.found_in_production }"
            @click="openDetail(item)"
          >
            <td class="td-status">
              <span v-if="item.found_in_production" class="dot dot-found"></span>
              <span v-else class="dot dot-missing"></span>
            </td>
            <td class="td-name">{{ item.first_name }} {{ item.last_name }}</td>
            <td class="td-id ltr-number">{{ item.id_number }}</td>
            <td class="td-company">{{ item.company || '—' }}</td>
            <td class="td-product">{{ item.product || '—' }}</td>
            <td class="td-prod-count ltr-number">
              <span v-if="item.found_in_production" class="prod-badge">{{ item.production_products.length }}</span>
              <span v-else class="prod-badge prod-badge-zero">0</span>
            </td>
            <td class="td-premium ltr-number">
              <template v-if="item.production_premium > 0">₪{{ fmtNum(item.production_premium) }}</template>
              <template v-else>—</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="totalPages > 1">
      <button class="pg" :disabled="currentPage === 1" @click="currentPage--">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
      <template v-for="p in visiblePages" :key="p">
        <span v-if="p === '...'" class="pg-dots">...</span>
        <button v-else class="pg" :class="{ active: p === currentPage }" @click="currentPage = p">{{ p }}</button>
      </template>
      <button class="pg" :disabled="currentPage === totalPages" @click="currentPage++">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <span class="pg-info">{{ currentPage }} / {{ totalPages }}</span>
    </div>

    <!-- Detail Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="detailItem" class="modal-overlay" @click.self="detailItem = null">
          <div class="modal-card">
            <div class="modal-head">
              <button class="modal-x" @click="detailItem = null">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
              <div class="modal-id-row">
                <div>
                  <div class="modal-name">{{ detailItem.first_name }} {{ detailItem.last_name }}</div>
                  <div class="modal-id-num ltr-number">ת.ז {{ detailItem.id_number }}</div>
                </div>
                <span class="modal-status-chip" :class="detailItem.found_in_production ? 'chip-found' : 'chip-missing'">
                  {{ detailItem.found_in_production ? 'נמצא בפרודוקציה' : 'לא נמצא' }}
                </span>
              </div>
            </div>

            <!-- Recruit file data -->
            <div class="modal-section">
              <div class="section-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                נתוני קובץ גיוס
              </div>
              <div class="info-grid">
                <div class="info-cell" v-if="detailItem.company">
                  <span class="info-lbl">חברה</span>
                  <span class="info-val">{{ detailItem.company }}</span>
                </div>
                <div class="info-cell" v-if="detailItem.product">
                  <span class="info-lbl">מוצר</span>
                  <span class="info-val">{{ detailItem.product }}</span>
                </div>
                <div class="info-cell" v-if="detailItem.amount > 0">
                  <span class="info-lbl">סכום</span>
                  <span class="info-val ltr-number">₪{{ fmtNum(detailItem.amount) }}</span>
                </div>
              </div>
            </div>

            <!-- Production data -->
            <div class="modal-section" v-if="detailItem.found_in_production && detailItem.production_products.length">
              <div class="section-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                מוצרים בפרודוקציה
                <span class="section-count">{{ detailItem.production_products.length }}</span>
              </div>
              <div class="prod-table-wrap">
                <table class="prod-table">
                  <thead>
                    <tr>
                      <th>מוצר</th>
                      <th>חברה</th>
                      <th>סטטוס</th>
                      <th>פרמיה</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(p, i) in detailItem.production_products" :key="i">
                      <td class="pt-product">{{ p.product || p.product_type || '—' }}</td>
                      <td class="pt-company">{{ shortCompany(p.company) || '—' }}</td>
                      <td>
                        <span class="status-tag" :class="statusClass(p.status)">{{ statusLabel(p.status) }}</span>
                      </td>
                      <td class="pt-premium ltr-number">
                        <template v-if="p.premium > 0">₪{{ fmtNum(p.premium) }}</template>
                        <template v-else>—</template>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Total premium -->
              <div class="modal-total" v-if="detailItem.production_premium > 0">
                <span>סה"כ פרמיה חודשית</span>
                <strong class="ltr-number">₪{{ fmtNum(detailItem.production_premium) }}</strong>
              </div>
            </div>

            <!-- Not found message -->
            <div class="modal-section modal-empty" v-if="!detailItem.found_in_production">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <p>לקוח זה לא נמצא בקובץ הפרודוקציה</p>
              <span>יש לוודא שהלקוח קיים במערכת או שת.ז תקין</span>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRecruitsStore } from '../../stores/recruits.js'

const props = defineProps({
  result: { type: Object, required: true },
})

const recruitsStore = useRecruitsStore()
const activeFilter = ref('all')
const currentPage = ref(1)
const pageSize = 50
const chartReady = ref(false)
const detailItem = ref(null)

onMounted(() => { nextTick(() => { chartReady.value = true }) })

const foundPct = computed(() => props.result.total > 0 ? Math.round((props.result.found / props.result.total) * 100) : 0)
const missingPct = computed(() => props.result.total > 0 ? Math.round((props.result.not_found / props.result.total) * 100) : 0)

const filteredResults = computed(() => {
  if (activeFilter.value === 'found') return props.result.results.filter(r => r.found_in_production)
  if (activeFilter.value === 'not_found') return props.result.results.filter(r => !r.found_in_production)
  return props.result.results
})

const totalPages = computed(() => Math.ceil(filteredResults.value.length / pageSize))

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredResults.value.slice(start, start + pageSize)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const cur = currentPage.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = []
  pages.push(1)
  if (cur > 3) pages.push('...')
  const windowStart = Math.max(2, cur - 1)
  const windowEnd = Math.min(total - 1, Math.max(cur + 1, 4))
  for (let i = windowStart; i <= windowEnd; i++) pages.push(i)
  if (cur < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

watch(activeFilter, () => { currentPage.value = 1 })

function openDetail(item) { detailItem.value = item }

function fmtNum(val) {
  if (val == null || val === 0) return '0'
  return Number(val).toLocaleString('he-IL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function shortCompany(name) {
  if (!name) return ''
  const words = name.split(/\s+/)
  return words.length <= 2 ? name : words.slice(0, 2).join(' ')
}

function statusLabel(s) {
  if (!s) return '—'
  if (s === 'פעיל' || s.includes('active') || s.includes('פעיל')) return 'פעיל'
  if (s === 'מוקפא' || s.includes('frozen')) return 'מוקפא'
  if (s.includes('מבוטל') || s.includes('cancel')) return 'מבוטל'
  return s
}

function statusClass(s) {
  const label = statusLabel(s)
  if (label === 'פעיל') return 'st-active'
  if (label === 'מוקפא') return 'st-frozen'
  if (label === 'מבוטל') return 'st-cancelled'
  return ''
}

const chartSeries = computed(() => [props.result.found, props.result.not_found])

const chartOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif' },
  labels: ['נמצאו בפרודוקציה', 'לא נמצאו'],
  colors: ['#2E844A', '#E8720A'],
  legend: { show: false },
  dataLabels: {
    enabled: true,
    formatter: (val) => val.toFixed(0) + '%',
    style: { fontFamily: 'Heebo, sans-serif', fontWeight: 700, fontSize: '13px' },
    dropShadow: { enabled: false },
  },
  plotOptions: {
    pie: {
      donut: {
        size: '65%',
        labels: {
          show: true,
          total: {
            show: true,
            label: 'סה"כ',
            fontFamily: 'Heebo, sans-serif',
            fontSize: '13px',
            fontWeight: 700,
            color: 'var(--text-muted)',
            formatter: () => props.result.total,
          },
          value: {
            fontFamily: 'Heebo, sans-serif',
            fontSize: '22px',
            fontWeight: 800,
          },
        },
      },
    },
  },
  stroke: { width: 2, colors: ['var(--card-bg)'] },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif' },
    y: { formatter: (val) => val + ' לקוחות' },
  },
}))
</script>

<style scoped>
.comparison-results {
  padding: 24px;
  animation: slideUp 0.5s var(--transition);
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--primary);
}

.header-title h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}

.btn-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-muted);
  transition: all 0.25s var(--transition);
}
.btn-close:hover { background: var(--bg-surface); color: var(--text); }

/* ── Dashboard row ── */
.dashboard-row {
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 20px;
}

.chart-box { flex: 0 0 220px; }

.kpi-row {
  flex: 1;
  display: flex;
  gap: 10px;
}

.kpi {
  flex: 1;
  text-align: center;
  padding: 16px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.25s var(--transition);
}
.kpi:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.06); }

.kpi-num {
  display: block;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -1px;
  line-height: 1.1;
}

.kpi-lbl {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-top: 4px;
}

.kpi-pct {
  display: block;
  font-size: 11px;
  font-weight: 700;
  margin-top: 2px;
}

.found-kpi { background: var(--green-light); border-color: var(--green-light); }
.found-kpi .kpi-num { color: var(--accent-emerald); }
.found-kpi .kpi-pct { color: var(--accent-emerald); }

.missing-kpi { background: rgba(232,114,10,0.06); border-color: rgba(232,114,10,0.1); }
.missing-kpi .kpi-num { color: #E8720A; }
.missing-kpi .kpi-pct { color: #E8720A; }

.total-kpi { background: var(--border-subtle); }
.total-kpi .kpi-num { color: var(--text); }

/* ── Segmented filter ── */
.seg-filter {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 16px;
}

.seg-filter button {
  padding: 8px 18px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s var(--transition);
  border-left: 1px solid var(--border);
  white-space: nowrap;
}
.seg-filter button:first-child { border-left: none; }
.seg-filter button b { font-weight: 800; margin-right: 3px; }
.seg-filter button:hover { background: var(--border-subtle); }
.seg-filter button.active {
  background: var(--primary);
  color: #fff;
}

/* ── Table ── */
.tbl-wrap { overflow-x: auto; }

.tbl {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.tbl thead th {
  padding: 10px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-align: right;
  letter-spacing: 0.3px;
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
}
.th-status { width: 28px; }

.tbl-row {
  cursor: pointer;
  transition: all 0.15s var(--transition);
}
.tbl-row:hover { background: var(--border-subtle); }
.tbl-row td {
  padding: 10px 10px;
  font-size: 13px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.row-found { border-right: 3px solid var(--accent-emerald); }
.row-missing { border-right: 3px solid #E8720A; }

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot-found { background: var(--accent-emerald); box-shadow: 0 0 6px var(--green-light); }
.dot-missing { background: #E8720A; box-shadow: 0 0 6px rgba(232,114,10,0.2); }

.td-name { font-weight: 600; white-space: nowrap; }
.td-id { font-size: 12px; color: var(--text-muted); font-family: monospace; }
.td-company, .td-product { font-size: 12px; color: var(--text-secondary); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.prod-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  background: var(--green-light);
  color: var(--accent-emerald);
}
.prod-badge-zero { background: rgba(232,114,10,0.08); color: #E8720A; }

.td-premium { font-weight: 700; font-size: 12px; color: var(--primary); white-space: nowrap; }

/* ── Pagination ── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.pg {
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
}
.pg:hover:not(:disabled) { background: var(--border-subtle); }
.pg.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.pg:disabled { opacity: 0.3; cursor: not-allowed; }
.pg-dots { color: var(--text-muted); font-size: 12px; padding: 0 4px; }
.pg-info { font-size: 11px; color: var(--text-muted); margin-right: 8px; }

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  width: 100%;
  max-width: 580px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.18);
}

.modal-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: #F7F8FA;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
}

.modal-x {
  position: absolute;
  top: 12px;
  left: 12px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 28px;
  height: 28px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.modal-x:hover { background: var(--border-subtle); color: var(--text); }

.modal-id-row {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-name { font-size: 16px; font-weight: 700; color: var(--text); }
.modal-id-num { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.modal-status-chip {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}
.chip-found { background: var(--green-light); color: var(--accent-emerald); }
.chip-missing { background: rgba(232,114,10,0.08); color: #E8720A; }

/* Modal sections */
.modal-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}

.section-count {
  background: var(--primary-glow);
  color: var(--primary);
  padding: 1px 7px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
}

/* Info grid (recruit data) */
.info-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.info-cell {
  flex: 1;
  min-width: 100px;
  padding: 10px 14px;
  background: var(--border-subtle);
  border-radius: 8px;
}

.info-lbl {
  display: block;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.info-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

/* Product table in modal */
.prod-table-wrap {
  overflow-x: auto;
}

.prod-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.prod-table thead th {
  padding: 8px 10px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-align: right;
  border-bottom: 1px solid var(--border-subtle);
  letter-spacing: 0.3px;
}

.prod-table tbody tr {
  transition: background 0.12s;
}
.prod-table tbody tr:hover { background: var(--border-subtle); }

.prod-table tbody td {
  padding: 9px 10px;
  font-size: 12px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.pt-product { font-weight: 600; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pt-company { color: var(--text-secondary); font-size: 11px; }
.pt-premium { font-weight: 700; color: var(--primary); white-space: nowrap; }

.status-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
}
.st-active { background: var(--green-light); color: var(--accent-emerald); }
.st-frozen { background: rgba(1,118,211,0.06); color: var(--primary); }
.st-cancelled { background: var(--red-light, rgba(234,67,53,0.06)); color: var(--red, #EA4335); }

.modal-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
  font-size: 13px;
  color: var(--text-secondary);
}
.modal-total strong { font-size: 16px; font-weight: 800; color: var(--primary); }

.modal-empty {
  text-align: center;
  padding: 32px 20px;
  color: var(--text-muted);
}
.modal-empty svg { margin-bottom: 12px; opacity: 0.4; }
.modal-empty p { font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.modal-empty span { font-size: 12px; }

/* Modal transition */
.modal-enter-active { animation: modalIn 0.2s ease-out; }
.modal-leave-active { animation: modalIn 0.15s ease reverse; }
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 700px) {
  .dashboard-row { flex-direction: column; }
  .chart-box { flex: none; width: 100%; }
  .kpi-row { width: 100%; }
  .seg-filter { width: 100%; display: flex; }
  .seg-filter button { flex: 1; }
}
</style>
