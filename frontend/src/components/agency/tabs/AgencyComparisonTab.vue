<template>
  <div class="comp-tab">
    <div v-if="!data" class="loading">טוען נפרעים…</div>
    <template v-else>
      <!-- KPI strip — same vocabulary as the regular ComparisonDashboard -->
      <div class="kpi-row">
        <div class="kpi kpi-blue">
          <div class="kpi-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/>
            </svg>
          </div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ data.summary.total_customers.toLocaleString('he-IL') }}</div>
            <div class="kpi-label">לקוחות בנפרעים</div>
          </div>
        </div>

        <div class="kpi kpi-amber">
          <div class="kpi-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ data.summary.unpaid_count.toLocaleString('he-IL') }}</div>
            <div class="kpi-label">לא שולם</div>
          </div>
        </div>

        <div class="kpi kpi-green">
          <div class="kpi-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ data.summary.matched_count.toLocaleString('he-IL') }}</div>
            <div class="kpi-label">נמצא בשניהם</div>
          </div>
        </div>

        <div class="kpi kpi-red">
          <div class="kpi-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 1v22M1 12h22"/>
            </svg>
          </div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ formatShort(data.summary.total_unpaid_amount) }}</div>
            <div class="kpi-label">סך עמלות לא שולמו</div>
          </div>
        </div>
      </div>

      <!-- Donut + per-company table -->
      <div class="row-2">
        <div class="card chart-card">
          <h3>חלוקת נפרעים בסוכנות</h3>
          <apexchart
            v-if="donutSeries.length"
            type="donut" height="280"
            :options="donutOptions" :series="donutSeries"
          />
          <div v-else class="empty">אין נתוני נפרעים עדיין</div>
        </div>

        <div class="card list-card">
          <h3>לא שולם — לפי חברה משלמת</h3>
          <table v-if="data.by_company.length" class="comp-table">
            <thead>
              <tr>
                <th>חברה</th>
                <th class="num">לא שולם</th>
                <th class="num">נמצא בשניהם</th>
                <th class="num">סכום</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in data.by_company.slice(0, 10)" :key="c.company">
                <td class="co">{{ shortCo(c.company) }}</td>
                <td class="num warn"><span class="ltr-number">{{ c.unpaid.toLocaleString('he-IL') }}</span></td>
                <td class="num"><span class="ltr-number">{{ c.matched.toLocaleString('he-IL') }}</span></td>
                <td class="num warn"><span class="ltr-number">{{ formatShort(c.unpaid_amount) }}</span></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty">אין נתונים עדיין</div>
        </div>
      </div>

      <!-- Top unpaid customers across the agency -->
      <div class="card">
        <div class="card-h">
          <h3>טופ לקוחות שלא שולמו — אגרגציה לכל הסוכנים</h3>
          <span class="card-tag">{{ data.top_unpaid_customers.length }} שורות</span>
        </div>
        <table v-if="data.top_unpaid_customers.length" class="comp-table">
          <thead>
            <tr>
              <th>סוכן</th>
              <th>לקוח</th>
              <th>חברה</th>
              <th>מוצר</th>
              <th>סטטוס</th>
              <th class="num">חוסר</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in data.top_unpaid_customers.slice(0, 25)"
              :key="c.record_id"
              class="clickable"
              @click="$emit('viewAgent', c.agent_user_id)"
            >
              <td>{{ c.agent_name }}</td>
              <td>{{ c.name || c.id_number }}</td>
              <td>{{ shortCo(c.company) }}</td>
              <td class="muted">{{ c.product || '—' }}</td>
              <td><span class="status" :class="c.status">{{ statusLabel(c.status) }}</span></td>
              <td class="num warn"><span class="ltr-number">{{ formatShort(c.unpaid_amount) }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">🎉 אין כרגע פוליסות שלא שולמו</div>
      </div>

      <!-- Per-agent breakdown -->
      <div class="card">
        <div class="card-h">
          <h3>פירוק לפי סוכן</h3>
          <span class="card-tag">{{ data.by_agent.length }} סוכנים</span>
        </div>
        <table v-if="data.by_agent.length" class="comp-table">
          <thead>
            <tr>
              <th>סוכן</th>
              <th class="num">נמצא בשניהם</th>
              <th class="num">לא שולם</th>
              <th class="num">חוסר ₪</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="a in data.by_agent"
              :key="a.user_id"
              class="clickable"
              @click="$emit('viewAgent', a.user_id)"
            >
              <td>{{ a.name }}</td>
              <td class="num"><span class="ltr-number">{{ a.matched.toLocaleString('he-IL') }}</span></td>
              <td class="num warn"><span class="ltr-number">{{ a.unpaid.toLocaleString('he-IL') }}</span></td>
              <td class="num warn"><span class="ltr-number">{{ formatShort(a.unpaid_amount) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAgencyStore } from '../../../stores/agency.js'

const agencyStore = useAgencyStore()
defineEmits(['viewAgent'])

const data = computed(() => agencyStore.comparison)
onMounted(() => { if (!agencyStore.comparison) agencyStore.fetchComparison() })

const donutSeries = computed(() => {
  if (!data.value) return []
  const s = data.value.summary
  const arr = []
  if (s.matched_count) arr.push(s.matched_count)
  if (s.unpaid_count) arr.push(s.unpaid_count)
  return arr
})
const donutLabels = computed(() => {
  if (!data.value) return []
  const s = data.value.summary
  const labels = []
  if (s.matched_count) labels.push('נמצא בשניהם')
  if (s.unpaid_count) labels.push('לא שולם')
  return labels
})
const donutOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  labels: donutLabels.value,
  colors: ['#2E844A', '#E8720A'],
  legend: { position: 'bottom', fontSize: '12px', markers: { width: 10, height: 10 } },
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
            formatter: () => donutSeries.value.reduce((a, b) => a + b, 0).toLocaleString('he-IL'),
          },
        },
      },
    },
  },
  tooltip: { y: { formatter: (v) => v.toLocaleString('he-IL') + ' רשומות' } },
}))

const STATUS_LABELS = {
  paid_match: 'שולם — תואם',
  paid_mismatch: 'שולם — חריגה',
  unpaid: 'לא שולם',
  no_data: 'אין נתונים',
  cancelled: 'בוטל',
}
function statusLabel(s) { return STATUS_LABELS[s] || s }
function shortCo(s) {
  if (!s) return ''
  return s.replace(/\s*חברה\s*לביטוח/g, '').replace(/\s*בע"מ/g, '').replace(/\s*בע״מ/g, '').replace(/\s*ופנסיה/g, '').trim()
}
function formatShort(v) {
  if (v == null || v === 0) return '₪0'
  const n = Number(v)
  if (n >= 1_000_000) return '₪' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '₪' + Math.round(n / 1_000) + 'K'
  return '₪' + Math.round(n).toLocaleString('he-IL')
}
</script>

<style scoped>
.comp-tab { display: flex; flex-direction: column; gap: 18px; position: relative; z-index: 2; }
.loading { padding: 60px; text-align: center; color: var(--text-muted); }
.empty { padding: 50px 20px; text-align: center; color: var(--text-muted); font-size: 13.5px; }

/* KPI strip — mirrors ComparisonDashboard */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi {
  background: #FFFFFF; border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: var(--shadow-sm);
  position: relative; overflow: hidden;
}
.kpi::before {
  content: ''; position: absolute; inset: 0 0 auto 0; height: 3px;
}
.kpi-blue::before  { background: #22d3ee; }
.kpi-amber::before { background: #E8720A; }
.kpi-green::before { background: #2E844A; }
.kpi-red::before   { background: #8C1D2A; }
.kpi-icon {
  width: 38px; height: 38px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.kpi-blue  .kpi-icon { background: rgba(34, 211, 238, 0.10); color: #0891b2; }
.kpi-amber .kpi-icon { background: rgba(232, 114, 10, 0.10); color: #E8720A; }
.kpi-green .kpi-icon { background: var(--green-light); color: var(--green-deep); }
.kpi-red   .kpi-icon { background: rgba(140, 29, 42, 0.10); color: #8C1D2A; }
.kpi-data { min-width: 0; }
.kpi-value { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; line-height: 1; }
.kpi-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.row-2 { display: grid; grid-template-columns: 1fr 1.2fr; gap: 14px; }
.card {
  background: #FFFFFF; border: 1px solid var(--border);
  border-radius: 14px; padding: 16px 18px;
  box-shadow: var(--shadow-sm);
}
.card h3 { font-size: 14.5px; font-weight: 700; color: var(--text); margin-bottom: 10px; letter-spacing: -0.2px; }
.card-h { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.card-tag {
  background: var(--bg); color: var(--text-muted);
  padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600;
}

.comp-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.comp-table th { text-align: right; font-size: 11px; color: var(--text-muted); font-weight: 700; padding: 8px 6px; border-bottom: 1px solid var(--border-subtle); }
.comp-table td { padding: 9px 6px; border-bottom: 1px solid var(--border-subtle); }
.comp-table tr:last-child td { border-bottom: none; }
.comp-table tr.clickable { cursor: pointer; transition: background .12s; }
.comp-table tr.clickable:hover td { background: rgba(245, 124, 0, 0.05); }
.comp-table .num { text-align: center; }
.comp-table .num.warn .ltr-number { color: #8C1D2A; font-weight: 700; }
.comp-table .co { font-weight: 600; color: var(--text); }
.comp-table .muted { color: var(--text-muted); font-size: 12px; }
.status { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px; }
.status.unpaid        { background: rgba(232, 114, 10, 0.10); color: #E8720A; }
.status.paid_mismatch { background: rgba(232, 114, 10, 0.10); color: #C85A00; }
.status.no_data       { background: rgba(45, 37, 34, 0.06); color: var(--text-muted); }
.status.paid_match    { background: var(--green-light); color: var(--green-deep); }
.status.cancelled     { background: rgba(127, 86, 217, 0.10); color: var(--accent-violet); }

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 1100px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .row-2 { grid-template-columns: 1fr; }
}
</style>
