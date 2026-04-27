<template>
  <Teleport to="body">
    <Transition name="ag-modal">
      <div v-if="open" class="ad-overlay" @click.self="$emit('close')">
        <div class="ad-card" v-if="data">
          <header class="ad-head">
            <button class="ad-close" @click="$emit('close')" aria-label="סגור">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
            <div class="ad-avatar">{{ initials(data.user.full_name) }}</div>
            <div class="ad-head-text">
              <p class="ad-eyebrow">פירוט סוכן · ד.נ.ר</p>
              <h2 class="ad-title">{{ data.user.full_name }}</h2>
              <div class="ad-contact">
                <span>{{ data.user.email }}</span>
                <span v-if="data.user.phone">· {{ data.user.phone }}</span>
              </div>
            </div>
            <button class="ad-upload-as" @click="$emit('uploadAs', data.user)" title="העלה קובץ עבור סוכן זה">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              העלה לסוכן זה
            </button>
          </header>

          <div class="ad-body">
            <!-- KPI strip -->
            <div class="kpi-row">
              <div class="kpi">
                <span class="kpi-label">פרמיה</span>
                <span class="kpi-val ltr-number">{{ formatCurrency(data.kpi.total_premium) }}</span>
              </div>
              <div class="kpi">
                <span class="kpi-label">צבירה</span>
                <span class="kpi-val ltr-number">{{ formatShort(data.kpi.total_accumulation) }}</span>
              </div>
              <div class="kpi">
                <span class="kpi-label">לקוחות</span>
                <span class="kpi-val ltr-number">{{ (data.kpi.unique_clients || 0).toLocaleString('he-IL') }}</span>
              </div>
              <div class="kpi warn">
                <span class="kpi-label">עמלות לא שולמו</span>
                <span class="kpi-val ltr-number">{{ formatCurrency(data.kpi.lost_money_amount) }}</span>
                <span class="kpi-sub">{{ data.kpi.lost_money_policy_count }} פוליסות</span>
              </div>
            </div>

            <!-- Charts row -->
            <div class="charts-row">
              <!-- Reconciliation status donut -->
              <div class="chart-card">
                <div class="chart-h">
                  <h3>חלוקת מצב פיוס</h3>
                  <span class="chart-tag">{{ totalRecords.toLocaleString('he-IL') }} רשומות</span>
                </div>
                <apexchart
                  v-if="statusSeries.length"
                  type="donut"
                  height="220"
                  :options="statusOpts"
                  :series="statusSeries"
                />
                <div v-else class="empty">אין נתונים</div>
              </div>

              <!-- Top companies by premium bar -->
              <div class="chart-card">
                <div class="chart-h">
                  <h3>פרמיה לפי חברה</h3>
                  <span class="chart-tag tag-orange">{{ data.by_company_premium.length }} חברות</span>
                </div>
                <apexchart
                  v-if="data.by_company_premium.length"
                  type="bar"
                  height="220"
                  :options="premiumBarOpts"
                  :series="premiumBarSeries"
                />
                <div v-else class="empty">אין פרודוקציה פעילה</div>
              </div>

              <!-- Lost by company bar -->
              <div class="chart-card">
                <div class="chart-h">
                  <h3>עמלות לא שולמו לפי חברה</h3>
                  <span class="chart-tag tag-red">{{ data.by_company_lost.length }} חברות</span>
                </div>
                <apexchart
                  v-if="data.by_company_lost.length && hasLost"
                  type="bar"
                  height="220"
                  :options="lostBarOpts"
                  :series="lostBarSeries"
                />
                <div v-else class="empty">🎉 אין פערי עמלה</div>
              </div>
            </div>

            <!-- Top customers + recent uploads side-by-side -->
            <div class="bottom-row">
              <div class="card">
                <div class="card-h">
                  <h3>לקוחות מובילים</h3>
                  <span class="card-tag">לפי פרמיה</span>
                </div>
                <table v-if="data.top_customers.length" class="cust-table">
                  <thead>
                    <tr>
                      <th>שם</th>
                      <th>ת.ז</th>
                      <th class="num">מוצרים</th>
                      <th class="num">פרמיה</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="c in data.top_customers" :key="c.id_number">
                      <td>{{ c.name || '—' }}</td>
                      <td class="muted ltr-number">{{ c.id_number }}</td>
                      <td class="num">{{ c.products }}</td>
                      <td class="num"><span class="ltr-number">{{ formatCurrency(c.premium) }}</span></td>
                    </tr>
                  </tbody>
                </table>
                <div v-else class="empty">אין פרודוקציה פעילה</div>
              </div>

              <div class="card">
                <div class="card-h">
                  <h3>העלאות אחרונות</h3>
                </div>
                <ul v-if="data.recent_uploads.length" class="up-list">
                  <li v-for="u in data.recent_uploads" :key="u.id">
                    <div class="up-icon" :class="{ active: u.is_production }">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                      </svg>
                    </div>
                    <div class="up-info">
                      <div class="up-name">{{ u.filename }}</div>
                      <div class="up-meta">
                        <strong>{{ (u.record_count || 0).toLocaleString('he-IL') }}</strong> רשומות
                        · {{ formatDate(u.uploaded_at) }}
                        <span v-if="u.is_production" class="up-badge">פעיל</span>
                      </div>
                    </div>
                  </li>
                </ul>
                <div v-else class="empty">אין העלאות</div>
              </div>
            </div>
          </div>
        </div>

        <div class="ad-card" v-else>
          <div class="ad-loading">
            <div class="spinner"></div>
            <span>טוען פירוט סוכן…</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  data: { type: Object, default: null },
})
defineEmits(['close', 'uploadAs'])

// ─── Status donut ───
const STATUS_LABELS = {
  paid_match: 'שולם — תואם',
  paid_mismatch: 'שולם — חריגה',
  unpaid: 'לא שולם',
  no_data: 'אין נתונים',
  cancelled: 'בוטל',
  unknown: 'לא ידוע',
}
const STATUS_COLORS = {
  paid_match: '#2E844A',
  paid_mismatch: '#E8720A',
  unpaid: '#8C1D2A',
  no_data: '#A0A0A0',
  cancelled: '#7F56D9',
  unknown: '#999',
}

const statusList = computed(() => (props.data?.status_distribution || []).filter(s => s.count > 0))
const statusSeries = computed(() => statusList.value.map(s => s.count))
const statusOpts = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif' },
  labels: statusList.value.map(s => STATUS_LABELS[s.status] || s.status),
  colors: statusList.value.map(s => STATUS_COLORS[s.status] || '#888'),
  legend: { position: 'bottom', fontSize: '11px', markers: { width: 8, height: 8 } },
  dataLabels: { enabled: true, formatter: (v) => `${Math.round(v)}%` },
  stroke: { width: 2, colors: ['#fff'] },
  plotOptions: {
    pie: {
      donut: {
        size: '60%',
        labels: {
          show: true,
          total: {
            show: true, label: 'סה"כ', color: '#706E6B',
            formatter: () => statusSeries.value.reduce((a, b) => a + b, 0).toLocaleString('he-IL'),
          },
        },
      },
    },
  },
  tooltip: { y: { formatter: (v) => v.toLocaleString('he-IL') + ' רשומות' } },
}))

const totalRecords = computed(() => statusSeries.value.reduce((a, b) => a + b, 0))

// ─── Premium by company bar ───
const premiumBarSeries = computed(() => [{
  name: 'פרמיה',
  data: props.data.by_company_premium.map(c => Math.round(c.premium)),
}])
const premiumBarOpts = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#F57C00', '#FF9800', '#FFB74D', '#FFCC80', '#FFD180', '#E8720A', '#C68A2E', '#FFA726'],
  legend: { show: false },
  xaxis: {
    categories: props.data.by_company_premium.map(c => shortName(c.company)),
    labels: { formatter: (v) => '₪' + Math.round(Number(v) / 1000) + 'K', style: { fontSize: '10px' } },
  },
  yaxis: { labels: { style: { fontSize: '10.5px', fontWeight: 600 } } },
  dataLabels: { enabled: false },
  tooltip: { y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') } },
  grid: { strokeDashArray: 3 },
}))

// ─── Lost by company bar ───
const hasLost = computed(() => props.data.by_company_lost.some(c => c.amount > 0))
const lostBarSeries = computed(() => [{
  name: 'אבוד',
  data: props.data.by_company_lost.map(c => Math.round(c.amount)),
}])
const lostBarOpts = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#8C1D2A', '#A1313F', '#B6485C', '#C66072', '#D67890', '#E8720A', '#C68A2E', '#FFA726'],
  legend: { show: false },
  xaxis: {
    categories: props.data.by_company_lost.map(c => shortName(c.company)),
    labels: { formatter: (v) => '₪' + Math.round(Number(v)).toLocaleString('he-IL'), style: { fontSize: '10px' } },
  },
  yaxis: { labels: { style: { fontSize: '10.5px', fontWeight: 600 } } },
  dataLabels: { enabled: false },
  tooltip: { y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') } },
  grid: { strokeDashArray: 3 },
}))

// ─── helpers ───
function initials(name) {
  if (!name) return '?'
  return name.split(/\s+/).slice(0, 2).map(p => (p || '')[0] || '').join('').toUpperCase()
}
function shortName(s) {
  if (!s) return ''
  return s.replace(/\s*חברה\s*לביטוח/g, '').replace(/\s*בע"מ/g, '').replace(/\s*בע״מ/g, '').trim()
}
function formatCurrency(v) {
  if (v == null) return '—'
  return '₪ ' + Math.round(Number(v)).toLocaleString('he-IL')
}
function formatShort(v) {
  if (v == null || v === 0) return '₪0'
  const n = Number(v)
  if (n >= 1_000_000) return '₪' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '₪' + Math.round(n / 1_000) + 'K'
  return '₪' + Math.round(n).toLocaleString('he-IL')
}
function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('he-IL', { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.ad-overlay {
  position: fixed; inset: 0; z-index: 1020;
  background: rgba(45, 37, 34, 0.5);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
  font-family: 'Heebo', sans-serif;
}
.ad-card {
  width: 100%;
  max-width: 1200px;
  max-height: 92vh;
  background: #FFFFFF;
  border-radius: 22px;
  box-shadow: 0 30px 80px -20px rgba(45, 37, 34, 0.5);
  overflow: hidden;
  display: flex; flex-direction: column;
  border: 1px solid rgba(45, 37, 34, 0.08);
}
.ad-loading { padding: 80px; text-align: center; color: var(--text-muted); }
.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin .8s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Header ── */
.ad-head {
  display: flex; align-items: center; gap: 16px;
  padding: 20px 24px;
  background: linear-gradient(180deg, #FFF8F0 0%, #FAF6F2 100%);
  border-bottom: 1px solid rgba(45, 37, 34, 0.08);
  position: relative;
}
.ad-close {
  background: rgba(45, 37, 34, 0.06);
  border: none; color: rgba(45, 37, 34, 0.7);
  width: 30px; height: 30px;
  border-radius: 8px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s;
}
.ad-close:hover { background: #2D2522; color: #fff; }
.ad-avatar {
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, #E8660A 0%, #FFB74D 100%);
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 20px;
  box-shadow: 0 6px 14px rgba(232, 102, 10, 0.4);
}
.ad-head-text { flex: 1; min-width: 0; }
.ad-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase; color: #C85A00; }
.ad-title { font-size: 22px; font-weight: 800; color: #2D2522; letter-spacing: -0.4px; margin-top: 2px; }
.ad-contact { font-size: 12.5px; color: rgba(45, 37, 34, 0.55); margin-top: 2px; }
.ad-upload-as {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--primary); color: #fff; border: none; border-radius: 9px;
  padding: 8px 14px; font-size: 13px; font-weight: 700; cursor: pointer;
  font-family: inherit; transition: background .15s;
}
.ad-upload-as:hover { background: var(--primary-deep); }

/* ── Body ── */
.ad-body {
  flex: 1; overflow-y: auto;
  padding: 22px 24px;
  background: #F9F6F2;
  display: flex; flex-direction: column; gap: 18px;
}

/* KPI row */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi {
  background: #FFFFFF;
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 12px;
  padding: 14px 16px;
}
.kpi-label { font-size: 11px; font-weight: 700; color: rgba(45, 37, 34, 0.55); letter-spacing: 0.4px; text-transform: uppercase; display: block; }
.kpi-val { font-size: 22px; font-weight: 800; color: #2D2522; letter-spacing: -0.4px; display: block; margin-top: 4px; }
.kpi-sub { font-size: 11px; color: rgba(45, 37, 34, 0.55); display: block; margin-top: 2px; }
.kpi.warn .kpi-val { color: #8C1D2A; }
.kpi.warn { background: linear-gradient(180deg, #FFFFFF 0%, #FFF1F0 100%); border-color: rgba(140, 29, 42, 0.18); }

/* Charts row */
.charts-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.chart-card {
  background: #FFFFFF;
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 12px;
  padding: 14px;
  min-height: 280px;
}
.chart-h { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.chart-h h3 { font-size: 13px; font-weight: 700; color: #2D2522; }
.chart-tag {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.3px; text-transform: uppercase;
  background: rgba(45, 37, 34, 0.06); color: rgba(45, 37, 34, 0.65);
  padding: 3px 9px; border-radius: 999px;
}
.chart-tag.tag-orange { background: var(--primary-light); color: var(--primary-deep); }
.chart-tag.tag-red    { background: rgba(140, 29, 42, 0.10); color: #8C1D2A; }
.empty { padding: 60px 20px; text-align: center; color: rgba(45, 37, 34, 0.45); font-size: 13px; }

/* Bottom row */
.bottom-row { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; }
.card {
  background: #FFFFFF;
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 12px;
  padding: 14px;
}
.card-h { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.card-h h3 { font-size: 13px; font-weight: 700; color: #2D2522; }
.card-tag { font-size: 10.5px; color: rgba(45, 37, 34, 0.55); }

.cust-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.cust-table th { text-align: right; font-size: 10.5px; color: rgba(45, 37, 34, 0.55); font-weight: 700; padding: 8px 6px; border-bottom: 1px solid rgba(45, 37, 34, 0.08); }
.cust-table td { padding: 9px 6px; border-bottom: 1px solid rgba(45, 37, 34, 0.05); }
.cust-table tr:last-child td { border-bottom: none; }
.cust-table .num { text-align: center; }
.cust-table .muted { color: rgba(45, 37, 34, 0.55); font-size: 11.5px; }

.up-list { list-style: none; padding: 0; margin: 0; }
.up-list li { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px dashed rgba(45, 37, 34, 0.08); }
.up-list li:last-child { border-bottom: none; }
.up-icon {
  width: 30px; height: 30px; border-radius: 8px;
  background: rgba(45, 37, 34, 0.06); color: rgba(45, 37, 34, 0.55);
  display: flex; align-items: center; justify-content: center;
}
.up-icon.active { background: var(--primary-light); color: var(--primary-deep); }
.up-info { flex: 1; min-width: 0; }
.up-name { font-size: 12.5px; font-weight: 600; color: #2D2522; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up-meta { font-size: 11px; color: rgba(45, 37, 34, 0.55); margin-top: 2px; }
.up-meta strong { color: #2D2522; font-weight: 700; }
.up-badge { background: var(--green-light); color: var(--green-deep); padding: 2px 7px; border-radius: 999px; font-size: 9.5px; font-weight: 800; margin-right: 4px; }

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

/* transitions */
.ag-modal-enter-active, .ag-modal-leave-active { transition: opacity .25s var(--transition); }
.ag-modal-enter-active .ad-card, .ag-modal-leave-active .ad-card { transition: transform .35s var(--transition), opacity .25s var(--transition); }
.ag-modal-enter-from, .ag-modal-leave-to { opacity: 0; }
.ag-modal-enter-from .ad-card { transform: translateY(20px) scale(0.96); opacity: 0; }
.ag-modal-leave-to .ad-card { transform: translateY(10px) scale(0.98); opacity: 0; }

@media (max-width: 1100px) {
  .charts-row { grid-template-columns: 1fr; }
  .bottom-row { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  .ad-overlay { padding: 0; }
  .ad-card { max-height: 100vh; height: 100vh; border-radius: 0; }
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}
</style>
