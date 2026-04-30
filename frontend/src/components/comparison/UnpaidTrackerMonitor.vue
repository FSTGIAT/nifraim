<template>
  <section class="unpaid-monitor" :data-empty="!loading && rows.length === 0">
    <!-- Decorative orange accent bar -->
    <div class="um-accent-bar"></div>

    <header class="um-header">
      <div class="um-header-meta">
        <div class="um-eyebrow-row">
          <span class="um-pulse"></span>
          <span class="um-eyebrow">מעקב לא-שולם · לפי חברה</span>
        </div>
        <h3 class="um-title">סיכום עמלות לא משולמות</h3>
        <p class="um-subtitle">מצטבר על פני כל החברות והחודשים שהעלית. עדכון אוטומטי בכל העלאת נפרעים.</p>
      </div>
      <div class="um-header-actions">
        <div class="um-search" v-if="rows.length > 4">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input v-model="search" type="text" placeholder="חפש חברה" />
        </div>
        <button class="um-refresh" :disabled="loading" @click="refresh" title="רענון">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ spin: loading }"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
        </button>
      </div>
    </header>

    <!-- Loading skeleton -->
    <div v-if="loading && rows.length === 0" class="um-loading">
      <div class="um-skel-kpis">
        <div class="um-skel um-skel-kpi" v-for="i in 4" :key="i"></div>
      </div>
      <div class="um-skel um-skel-chart"></div>
      <div class="um-skel um-skel-row" v-for="i in 3" :key="i"></div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && rows.length === 0" class="um-empty">
      <div class="um-empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3h18v6H3z"/><path d="M3 13h18v8H3z"/><path d="M8 9v4M16 9v4"/></svg>
      </div>
      <div class="um-empty-text">
        <strong>אין עדיין נתוני לא-שולם</strong>
        <span>העלה קובץ נפרעים כדי להתחיל מעקב חודשי לפי חברה. הסיכום יציג את החברות שלא שילמו, היקפי הפרמיה והמגמה לאורך הזמן.</span>
      </div>
    </div>

    <!-- Content -->
    <div v-else class="um-body">
      <!-- KPI tiles -->
      <div class="um-kpis">
        <div class="um-kpi um-kpi--total">
          <div class="um-kpi-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <div class="um-kpi-data">
            <div class="um-kpi-num">{{ totalUnpaid.toLocaleString('he-IL') }}</div>
            <div class="um-kpi-label">לקוחות לא שולמו</div>
          </div>
        </div>

        <div class="um-kpi um-kpi--amount">
          <div class="um-kpi-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
          </div>
          <div class="um-kpi-data">
            <div class="um-kpi-num ltr-number">{{ formatCurrency(totalAmount) }}</div>
            <div class="um-kpi-label">עמלה לא שולמה</div>
          </div>
        </div>

        <div class="um-kpi um-kpi--companies">
          <div class="um-kpi-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18"/><path d="M5 21V7l8-4v18"/><path d="M19 21V11l-6-4"/></svg>
          </div>
          <div class="um-kpi-data">
            <div class="um-kpi-num">{{ rows.length }}</div>
            <div class="um-kpi-label">חברות במעקב</div>
          </div>
        </div>

        <div class="um-kpi um-kpi--sent">
          <div class="um-kpi-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </div>
          <div class="um-kpi-data">
            <div class="um-kpi-num">{{ sentCount }}<span class="um-kpi-frac">/{{ rows.length }}</span></div>
            <div class="um-kpi-label">נשלחו פניות</div>
          </div>
        </div>
      </div>

      <!-- Cinematic MoM trend (Remotion) — auto-sizes to its parent width -->
      <div v-if="cinematicSeries.length > 0" class="um-chart um-chart--cinema">
        <UnpaidTrendCinematic
          :periods="cinematicPeriods"
          :series="cinematicSeries"
          :title="cinematicTitle"
          :insight="cinematicInsight"
        />
      </div>

      <!-- Per-company strip -->
      <div class="um-rows">
        <div
          v-for="row in filteredRows"
          :key="row.snapshot_id"
          class="um-row"
          :class="{ 'um-row--expanded': expandedId === row.snapshot_id }"
        >
          <div class="um-row-main">
            <div class="um-row-company">
              <span class="um-row-name">{{ row.company }}</span>
              <span class="um-row-period">{{ row.period }}</span>
              <span v-if="row.email_sent_at" class="um-chip um-chip-sent" :title="`נשלח אל ${row.email_sent_to}`">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                נשלח {{ formatShortDate(row.email_sent_at) }}
              </span>
            </div>

            <div class="um-row-metric">
              <span class="um-metric-num">{{ row.count }}</span>
              <span class="um-metric-suffix">לקוחות</span>
            </div>

            <div class="um-row-amount ltr-number">{{ formatCurrency(row.amount) }}</div>

            <div class="um-row-spark">
              <apexchart
                v-if="sparklineSeries(row.company).length"
                type="line"
                height="32"
                width="86"
                :options="sparkOptions"
                :series="[{ name: row.company, data: sparklineSeries(row.company) }]"
              />
            </div>

            <div class="um-row-actions">
              <button
                class="um-btn um-btn-mail"
                :disabled="sendingId === row.snapshot_id"
                :title="row.email_sent_at ? 'שלח שוב' : 'שלח מייל ל-' + row.company"
                @click="confirmSend(row)"
              >
                <svg v-if="sendingId !== row.snapshot_id" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>
                <svg v-else class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>
              </button>
              <button class="um-btn um-btn-excel" title="הורדת Excel" @click="downloadExcel(row)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><polyline points="9 15 12 18 15 15"/></svg>
              </button>
              <button class="um-btn um-btn-trash" :title="`הסר את כל ${row.count} הלקוחות של ${row.company}`" @click="confirmDismissCompany(row)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a2 2 0 012-2h2a2 2 0 012 2v2"/></svg>
              </button>
              <button class="um-btn um-btn-toggle" :class="{ 'is-open': expandedId === row.snapshot_id }" :title="expandedId === row.snapshot_id ? 'סגור' : 'פתח רשימה'" @click="toggleExpand(row)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
            </div>
          </div>

          <Transition name="um-expand">
            <div v-if="expandedId === row.snapshot_id" class="um-row-detail">
              <div v-if="loadingCustomers" class="um-detail-loading">טוען...</div>
              <div v-else-if="!expandedCustomers.length" class="um-detail-empty">אין לקוחות להצגה</div>
              <table v-else class="um-detail-table">
                <thead>
                  <tr>
                    <th>שם</th>
                    <th>ת.ז</th>
                    <th>מוצרים</th>
                    <th class="num">פרמיה</th>
                    <th class="actions"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(c, i) in expandedCustomers" :key="(c.id_number || '') + i">
                    <td>{{ c.name || '—' }}</td>
                    <td><span class="ltr-number">{{ c.id_number }}</span></td>
                    <td class="um-cell-products">
                      <span v-for="(p, pi) in (c.products || []).slice(0, 3)" :key="pi" class="um-product-pill">{{ p.product }}</span>
                      <span v-if="(c.products || []).length > 3" class="um-product-more">+{{ c.products.length - 3 }}</span>
                    </td>
                    <td class="num"><span class="ltr-number">{{ formatCurrency(c.premium) }}</span></td>
                    <td class="actions">
                      <button
                        class="um-row-x"
                        :disabled="dismissingCustomerId === c.id_number"
                        title="הסר מרשימת לא-שולם"
                        @click="dismissCustomer(row, c)"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- Confirm-send modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="confirmRow" class="um-overlay" @click.self="confirmRow = null">
          <div class="um-modal">
            <h4 class="um-modal-title">שליחת מייל ל-{{ confirmRow.company }}</h4>
            <p class="um-modal-body">
              הקובץ יכלול <strong>{{ confirmRow.count }}</strong> לקוחות לא משולמים על סך
              <strong class="ltr-number">{{ formatCurrency(confirmRow.amount) }}</strong>.
              <br>
              <span class="um-modal-period">תקופה: {{ confirmRow.period }}</span>
            </p>
            <div class="um-modal-actions">
              <button class="um-modal-cancel" @click="confirmRow = null">ביטול</button>
              <button class="um-modal-confirm" :disabled="sendingId === confirmRow.snapshot_id" @click="doSend">
                <svg v-if="sendingId === confirmRow.snapshot_id" class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>
                שלח עכשיו
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Confirm-dismiss-company modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="dismissCompanyRow" class="um-overlay" @click.self="dismissCompanyRow = null">
          <div class="um-modal">
            <h4 class="um-modal-title">הסרת כל הלקוחות של {{ dismissCompanyRow.company }}?</h4>
            <p class="um-modal-body">
              כל <strong>{{ dismissCompanyRow.count }}</strong> הלקוחות יוסתרו מסיכום הלא-שולם
              (היסטוריית המגמה תישמר).
              <br>
              <span class="um-modal-period">תוכל לשחזר בכל עת בלחיצה על "שחזר את {{ dismissCompanyRow.company }}".</span>
            </p>
            <div class="um-modal-actions">
              <button class="um-modal-cancel" @click="dismissCompanyRow = null">ביטול</button>
              <button class="um-modal-confirm um-modal-danger" :disabled="dismissingCompany" @click="doDismissCompany">
                הסר את כולם
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Toast -->
    <Transition name="um-toast">
      <div v-if="toast" class="um-toast" :class="`um-toast--${toast.kind}`">
        <span>{{ toast.message }}</span>
      </div>
    </Transition>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api/client'
import * as XLSX from 'xlsx'
import UnpaidTrendCinematic from './UnpaidTrendCinematic.vue'

const props = defineProps({
  refreshKey: { type: [Number, String], default: 0 },
})

const rows = ref([])
const trend = ref([])
const loading = ref(false)
const search = ref('')
const expandedId = ref(null)
const expandedCustomers = ref([])
const loadingCustomers = ref(false)
const sendingId = ref(null)
const confirmRow = ref(null)
const dismissCompanyRow = ref(null)
const dismissingCompany = ref(false)
const dismissingCustomerId = ref(null)
const toast = ref(null)

const filteredRows = computed(() => {
  const q = search.value.trim()
  if (!q) return rows.value
  return rows.value.filter(r => r.company.includes(q))
})

// Aggregate KPIs across all tracked companies
const totalUnpaid = computed(() => rows.value.reduce((s, r) => s + (r.count || 0), 0))
const totalAmount = computed(() => rows.value.reduce((s, r) => s + (r.amount || 0), 0))
const sentCount = computed(() => rows.value.filter(r => r.email_sent_at).length)

const chartPeriodRange = computed(() => {
  const periods = [...new Set(trend.value.map(t => t.period))].sort()
  if (!periods.length) return ''
  if (periods.length === 1) return periods[0]
  return `${periods[0]} → ${periods[periods.length - 1]}`
})

// Periods + series in the shape Remotion expects: ascending periods, top-5
// companies by current amount, count per period (zero-filled where missing).
const cinematicPeriods = computed(() =>
  [...new Set(trend.value.map(t => t.period))].sort()
)
const cinematicSeries = computed(() => {
  const periods = cinematicPeriods.value
  if (!periods.length) return []
  const top = rows.value.slice(0, 5).map(r => r.company)
  return top.map(company => ({
    company,
    data: periods.map(p => {
      const point = trend.value.find(t => t.period === p && t.company === company)
      return point ? point.count : 0
    }),
  }))
})
const cinematicTitle = computed(() => {
  const n = cinematicSeries.value.length
  if (!n) return 'מגמת לא-שולם לפי חברה'
  return `${n} חברות במעקב — ${totalUnpaid.value.toLocaleString('he-IL')} לקוחות`
})
const cinematicInsight = computed(() => {
  if (!cinematicSeries.value.length) return ''
  // Highlight the top company by latest count
  const top = [...cinematicSeries.value].sort((a, b) => {
    const al = a.data[a.data.length - 1] || 0
    const bl = b.data[b.data.length - 1] || 0
    return bl - al
  })[0]
  if (!top) return ''
  const latest = top.data[top.data.length - 1] || 0
  return `${top.company} מובילה — ${latest} לא שולמו`
})


const sparkOptions = {
  chart: {
    sparkline: { enabled: true },
    animations: { enabled: false },
  },
  stroke: { curve: 'smooth', width: 2 },
  colors: ['#E8720A'],
  tooltip: { enabled: false },
  markers: { size: 0 },
}

function sparklineSeries(company) {
  const points = trend.value.filter(t => t.company === company)
  points.sort((a, b) => a.period.localeCompare(b.period))
  return points.map(p => p.count)
}

function formatCurrency(v) {
  if (!v && v !== 0) return ''
  return '₪' + Number(v).toLocaleString('he-IL', { maximumFractionDigits: 0 })
}

function formatShortDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit' })
}

async function refresh() {
  loading.value = true
  try {
    const [byCompany, trendRes] = await Promise.all([
      api.get('/unpaid-tracker/by-company'),
      api.get('/unpaid-tracker/trend', { params: { months: 12 } }),
    ])
    rows.value = byCompany.data?.rows || []
    trend.value = trendRes.data?.rows || []
  } catch (e) {
    showToast('error', 'שגיאה בטעינת נתוני לא-שולם')
  } finally {
    loading.value = false
  }
}

async function toggleExpand(row) {
  if (expandedId.value === row.snapshot_id) {
    expandedId.value = null
    expandedCustomers.value = []
    return
  }
  expandedId.value = row.snapshot_id
  expandedCustomers.value = []
  loadingCustomers.value = true
  try {
    const res = await api.get(`/unpaid-tracker/${row.snapshot_id}/customers`)
    expandedCustomers.value = res.data?.customers || []
  } catch (e) {
    showToast('error', 'שגיאה בטעינת לקוחות')
  } finally {
    loadingCustomers.value = false
  }
}

function downloadExcel(row) {
  // Pull full customer list and build XLSX client-side (mirrors existing
  // downloadUnpaidExcel pattern in ComparisonDashboard.vue)
  api.get(`/unpaid-tracker/${row.snapshot_id}/customers`)
    .then(res => {
      const customers = res.data?.customers || []
      const sheet = customers.map(c => ({
        'ת.ז': c.id_number || '',
        'שם': c.name || '',
        'מוצרים': (c.products || []).map(p => p.product).filter(Boolean).join(' | '),
        'פרמיה': (c.products || []).reduce((s, p) => s + (Number(p.premium) || 0), 0) || (Number(c.premium) || 0),
        'צבירה': (c.products || []).reduce((s, p) => s + (Number(p.accumulation) || 0), 0),
      }))
      const ws = XLSX.utils.json_to_sheet(sheet)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'לא_שולם')
      const safe = (row.company || 'company').replace(/\s+/g, '_')
      XLSX.writeFile(wb, `לא_שולם_${safe}_${row.period}.xlsx`)
    })
    .catch(() => showToast('error', 'שגיאה בהורדה'))
}

function confirmSend(row) {
  confirmRow.value = row
}

async function doSend() {
  if (!confirmRow.value) return
  const row = confirmRow.value
  sendingId.value = row.snapshot_id
  try {
    const res = await api.post(`/unpaid-tracker/${row.snapshot_id}/send-email`)
    const target = rows.value.find(r => r.snapshot_id === row.snapshot_id)
    if (target) {
      target.email_sent_at = res.data.sent_at
      target.email_sent_to = res.data.sent_to
    }
    confirmRow.value = null
    showToast('success', `נשלח ל-${res.data.sent_to}`)
  } catch (e) {
    const detail = e.response?.data?.detail
    if (detail && typeof detail === 'object' && detail.code === 'no_contact') {
      confirmRow.value = null
      showToast('error', detail.message || 'אין מייל מוגדר לחברה זו')
    } else {
      showToast('error', 'שליחה נכשלה')
    }
  } finally {
    sendingId.value = null
  }
}

function showToast(kind, message) {
  toast.value = { kind, message }
  setTimeout(() => { toast.value = null }, 3500)
}

async function dismissCustomer(row, customer) {
  if (!customer?.id_number || dismissingCustomerId.value) return
  dismissingCustomerId.value = customer.id_number
  try {
    await api.post('/unpaid-tracker/dismiss-customer', {
      company: row.company,
      customer_id: customer.id_number,
    })
    // Optimistic local update — remove from expanded list and decrement row
    expandedCustomers.value = expandedCustomers.value.filter(c => c.id_number !== customer.id_number)
    const target = rows.value.find(r => r.snapshot_id === row.snapshot_id)
    if (target) {
      target.count = Math.max(0, target.count - 1)
      target.amount = Math.max(0, target.amount - (Number(customer.expected_commission) || Number(customer.premium) || 0))
    }
    // If the row drops to 0, refresh fully so the row disappears
    if (target && target.count === 0) {
      await refresh()
      expandedId.value = null
    }
    showToast('success', 'הלקוח הוסר')
  } catch (e) {
    showToast('error', 'שגיאה בהסרה')
  } finally {
    dismissingCustomerId.value = null
  }
}

function confirmDismissCompany(row) {
  dismissCompanyRow.value = row
}

async function doDismissCompany() {
  if (!dismissCompanyRow.value) return
  const row = dismissCompanyRow.value
  dismissingCompany.value = true
  try {
    const res = await api.post('/unpaid-tracker/dismiss-company', { company: row.company })
    dismissCompanyRow.value = null
    showToast('success', `הוסרו ${res.data?.dismissed ?? row.count} לקוחות מ-${row.company}`)
    if (expandedId.value === row.snapshot_id) expandedId.value = null
    await refresh()
  } catch (e) {
    showToast('error', 'שגיאה בהסרת החברה')
  } finally {
    dismissingCompany.value = false
  }
}

onMounted(refresh)
watch(() => props.refreshKey, refresh)
</script>

<style scoped>
.unpaid-monitor {
  background: linear-gradient(180deg, #FFFFFF 0%, #FFFBF5 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 18px rgba(245, 124, 0, 0.06), var(--shadow-md);
  padding: 22px 24px 20px;
  margin: 0 0 20px;
  position: relative;
  overflow: hidden;
}
.um-accent-bar {
  position: absolute;
  top: 0; right: 0; left: 0; height: 4px;
  background: linear-gradient(90deg, #E65100 0%, #F57C00 35%, #FB8C00 70%, #FFB74D 100%);
}
.um-accent-bar::after {
  content: '';
  position: absolute;
  top: 0; bottom: 0;
  left: -40%;
  width: 30%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.55), transparent);
  animation: umSweep 5s ease-in-out infinite;
}
@keyframes umSweep {
  0%, 30% { left: -40%; }
  70%, 100% { left: 110%; }
}

.um-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}
.um-eyebrow-row { display: flex; align-items: center; gap: 8px; }
.um-pulse {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 0 0 rgba(245, 124, 0, 0.6);
  animation: umPulse 2s ease-in-out infinite;
}
@keyframes umPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 124, 0, 0.55); }
  50%      { box-shadow: 0 0 0 6px rgba(245, 124, 0, 0); }
}
.um-eyebrow {
  font-size: 10px;
  font-weight: 800;
  color: var(--primary-deep);
  letter-spacing: 0.8px;
  text-transform: uppercase;
}
.um-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin: 6px 0 4px;
  letter-spacing: -0.2px;
}
.um-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
  max-width: 540px;
  line-height: 1.55;
}
.um-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.um-search {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 10px;
  color: var(--text-muted);
}
.um-search input {
  border: 0;
  outline: 0;
  font: inherit;
  font-size: 12px;
  width: 110px;
  background: transparent;
}
.um-refresh {
  width: 30px; height: 30px;
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
  display: flex; align-items: center; justify-content: center;
  transition: background 160ms;
}
.um-refresh:hover:not(:disabled) { background: var(--primary-light); color: var(--primary); }
.um-refresh:disabled { opacity: 0.6; cursor: wait; }

/* Empty state */
.um-empty {
  display: flex;
  align-items: center;
  gap: 18px;
  background: linear-gradient(135deg, #FFF6EC 0%, #FFFAF4 100%);
  border: 1px dashed #F4B679;
  border-radius: 14px;
  padding: 22px 24px;
  position: relative;
}
.um-empty-icon {
  color: var(--primary);
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  background: #fff;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(245, 124, 0, 0.12);
}
.um-empty-text { display: flex; flex-direction: column; gap: 4px; }
.um-empty-text strong { font-size: 15px; color: var(--text); font-weight: 700; }
.um-empty-text span { font-size: 12px; color: var(--text-muted); line-height: 1.55; }

/* Loading */
.um-loading { display: flex; flex-direction: column; gap: 10px; }
.um-skel-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.um-skel {
  background: linear-gradient(90deg, #F4F4F4 0%, #FAFAFA 50%, #F4F4F4 100%);
  background-size: 200% 100%;
  border-radius: 10px;
  animation: shimmer 1.4s infinite;
}
.um-skel-kpi { height: 70px; }
.um-skel-chart { height: 200px; }
.um-skel-row { height: 56px; }
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Body */
.um-body { display: flex; flex-direction: column; gap: 16px; }

/* KPI tiles */
.um-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.um-kpi {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 14px 16px;
  position: relative;
  overflow: hidden;
  transition: transform 200ms, box-shadow 200ms, border-color 200ms;
}
.um-kpi::before {
  content: '';
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--accent), transparent);
}
.um-kpi:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.08);
  border-color: #F4B679;
}
.um-kpi--total      { --accent: #E65100; }
.um-kpi--amount     { --accent: #F57C00; }
.um-kpi--companies  { --accent: #FB8C00; }
.um-kpi--sent       { --accent: #2E844A; }

.um-kpi-icon {
  width: 36px; height: 36px;
  background: var(--primary-light);
  color: var(--accent);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.um-kpi--sent .um-kpi-icon {
  background: var(--green-light);
}
.um-kpi-data { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.um-kpi-num {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.4px;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.um-kpi-frac { font-size: 13px; font-weight: 600; color: var(--text-muted); margin-right: 2px; }
.um-kpi-label { font-size: 11px; color: var(--text-muted); font-weight: 600; }

/* Cinematic chart card */
.um-chart {
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 0;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 14px rgba(245, 124, 0, 0.06);
}
.um-chart--cinema {
  border-color: rgba(245, 124, 0, 0.18);
}

.um-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Per-company row */
.um-row {
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  transition: border-color 160ms, box-shadow 160ms, transform 160ms;
}
.um-row:hover {
  border-color: #F4B679;
  box-shadow: 0 1px 6px rgba(245, 124, 0, 0.08);
}
.um-row--expanded {
  border-color: var(--primary);
  box-shadow: 0 2px 10px rgba(245, 124, 0, 0.14);
}
.um-row-main {
  display: grid;
  grid-template-columns: minmax(200px, 1.8fr) auto auto auto auto;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
}
.um-row-company {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}
.um-row-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
.um-row-period {
  font-size: 11px;
  color: var(--text-muted);
  background: #F7F7F7;
  border-radius: 6px;
  padding: 2px 8px;
  font-variant-numeric: tabular-nums;
}
.um-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 999px;
}
.um-chip-sent {
  background: var(--green-light);
  color: var(--green-deep);
  border: 1px solid #C7E5CB;
}
.um-row-metric {
  display: flex;
  align-items: baseline;
  gap: 4px;
  white-space: nowrap;
}
.um-metric-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.um-metric-suffix { font-size: 11px; color: var(--text-muted); }
.um-row-amount {
  font-size: 14px;
  font-weight: 700;
  color: var(--primary-deep);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  min-width: 90px;
  text-align: left;
}
.um-row-spark {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  min-width: 90px;
}
.um-row-actions { display: flex; gap: 6px; }
.um-btn {
  width: 30px; height: 30px;
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
  display: flex; align-items: center; justify-content: center;
  transition: background 160ms, color 160ms, border-color 160ms;
}
.um-btn:hover:not(:disabled) {
  background: var(--primary-light);
  color: var(--primary-deep);
  border-color: var(--primary);
}
.um-btn:disabled { opacity: 0.6; cursor: wait; }
.um-btn-toggle.is-open { transform: rotate(180deg); background: var(--primary-light); color: var(--primary); border-color: var(--primary); }
.um-btn-trash:hover:not(:disabled) {
  background: var(--red-light);
  color: var(--red-deep);
  border-color: var(--red-deep);
}

/* Expanded detail */
.um-row-detail {
  border-top: 1px solid var(--border-subtle);
  padding: 10px 14px 12px;
  overflow: hidden;
}
.um-detail-loading, .um-detail-empty {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  padding: 12px;
}
.um-detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: fixed;
}
.um-detail-table th {
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  padding: 6px 8px;
}
.um-detail-table th.num, .um-detail-table td.num { text-align: center; width: 100px; }
.um-detail-table th.actions, .um-detail-table td.actions { width: 36px; text-align: center; }
.um-row-x {
  width: 22px;
  height: 22px;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 160ms;
}
.um-row-x:hover:not(:disabled) {
  background: var(--red-light);
  color: var(--red-deep);
  border-color: var(--red-deep);
}
.um-row-x:disabled { opacity: 0.5; cursor: wait; }
.um-detail-table td {
  padding: 6px 8px;
  color: var(--text);
  border-bottom: 1px solid #F5F5F5;
}
.um-detail-table tbody tr:last-child td { border-bottom: 0; }
.um-detail-table tbody tr:hover td { background: #FFFAF2; }
.um-cell-products { display: flex; gap: 4px; flex-wrap: wrap; }
.um-product-pill {
  font-size: 10px;
  background: #FFF3E0;
  color: var(--primary-deep);
  border-radius: 4px;
  padding: 1px 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}
.um-product-more {
  font-size: 10px;
  color: var(--text-muted);
}

.um-expand-enter-active, .um-expand-leave-active {
  transition: max-height 240ms cubic-bezier(0.4, 0, 0.2, 1), opacity 200ms;
  overflow: hidden;
}
.um-expand-enter-from, .um-expand-leave-to {
  max-height: 0;
  opacity: 0;
}
.um-expand-enter-to, .um-expand-leave-from {
  max-height: 360px;
  opacity: 1;
}

.spin { animation: um-spin 0.9s linear infinite; }
@keyframes um-spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

/* Confirm modal */
.um-overlay {
  position: fixed;
  inset: 0;
  background: rgba(20, 20, 20, 0.45);
  z-index: 1020;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.um-modal {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 22px 24px;
  max-width: 420px;
  width: 100%;
}
.um-modal-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 8px;
  color: var(--text);
}
.um-modal-body {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0 0 18px;
}
.um-modal-period { font-size: 11px; color: var(--text-muted); }
.um-modal-actions { display: flex; gap: 10px; justify-content: flex-end; }
.um-modal-cancel, .um-modal-confirm {
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.um-modal-cancel { background: #F5F5F5; color: var(--text); border-color: var(--border); }
.um-modal-cancel:hover { background: #ECECEC; }
.um-modal-confirm {
  background: var(--primary);
  color: #fff;
}
.um-modal-confirm:hover:not(:disabled) { background: var(--primary-deep); }
.um-modal-confirm:disabled { opacity: 0.7; cursor: wait; }
.um-modal-danger { background: var(--red-deep); }
.um-modal-danger:hover:not(:disabled) { background: var(--red); }
.modal-enter-active, .modal-leave-active { transition: opacity 200ms; }
.modal-enter-from, .modal-leave-to { opacity: 0; }

/* Toast */
.um-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: #181818;
  color: #fff;
  border-radius: 10px;
  padding: 12px 18px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: var(--shadow-lg);
  z-index: 1030;
}
.um-toast--success { background: var(--green); }
.um-toast--error { background: var(--red-deep); }
.um-toast-enter-active, .um-toast-leave-active { transition: transform 220ms, opacity 220ms; }
.um-toast-enter-from, .um-toast-leave-to { transform: translateY(20px); opacity: 0; }

@media (max-width: 960px) {
  .um-kpis { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 720px) {
  .um-header { flex-direction: column; align-items: stretch; }
  .um-row-main {
    grid-template-columns: 1fr auto auto;
    grid-template-rows: auto auto;
    row-gap: 6px;
  }
  .um-row-company { grid-column: 1 / -1; }
  .um-row-spark { display: none; }
}
@media (max-width: 520px) {
  .um-kpis { grid-template-columns: 1fr; }
}
</style>
