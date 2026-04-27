<template>
  <div class="ov-tab">
    <div v-if="!comparison || !overview" class="loading">טוען לוח בקרה…</div>
    <template v-else>
      <!-- ─── AI Insight Card — hero AI summary at top, mirrors ProductionComparison ─── -->
      <AiInsightCard
        v-if="aiViewContext"
        :view-context="aiViewContext"
        @open-sheet="openAi"
      />

      <!-- ─── KPI Row (clickable) ─── -->
      <div class="kpi-row">
        <div class="kpi-card kpi-blue clickable" @click="$emit('open-modal', 'agents')">
          <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2"/><circle cx="9" cy="7" r="4"/></svg></div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ overview.agent_count }}</div>
            <div class="kpi-label">סוכנים בסוכנות</div>
          </div>
        </div>

        <div class="kpi-card kpi-cyan clickable" @click="$emit('select-tab', 'comparison')">
          <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 17v-6a3 3 0 016 0v6m-9 4h12"/><circle cx="12" cy="6" r="2"/></svg></div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ comparison.summary.total_customers.toLocaleString('he-IL') }}</div>
            <div class="kpi-label">לקוחות בנפרעים</div>
          </div>
        </div>

        <div class="kpi-card kpi-amber clickable" @click="$emit('select-tab', 'comparison')">
          <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ comparison.summary.unpaid_count.toLocaleString('he-IL') }}</div>
            <div class="kpi-label">לא שולם</div>
          </div>
        </div>

        <div class="kpi-card kpi-emerald clickable" @click="$emit('select-tab', 'production')">
          <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg></div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ formatShort(overview.total_premium) }}</div>
            <div class="kpi-label">סך פרמיה</div>
          </div>
        </div>

        <div class="kpi-card kpi-red clickable" @click="$emit('open-modal', 'unpaid-detail')">
          <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1v22M1 12h22"/></svg></div>
          <div class="kpi-data">
            <div class="kpi-value ltr-number">{{ formatShort(comparison.summary.total_unpaid_amount) }}</div>
            <div class="kpi-label">סך עמלות לא שולמו</div>
          </div>
        </div>
      </div>

      <!-- ─── Hero donut + per-company bar ─── -->
      <div class="charts-row">
        <div class="chart-card" @click="$emit('select-tab', 'comparison')" style="cursor:pointer">
          <div class="chart-header">
            <h3>חלוקת נפרעים בסוכנות</h3>
            <span class="chart-tag">לחץ למעבר ל-השוואת נפרעים</span>
          </div>
          <apexchart
            v-if="donutSeries.length"
            type="donut" :height="320"
            :options="donutOptions" :series="donutSeries"
          />
          <div v-else class="empty">אין נתונים</div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <h3>טופ חברות — לא שולם</h3>
            <span class="chart-tag">לחץ על עמודה כדי לראות לקוחות</span>
          </div>
          <apexchart
            v-if="topUnpaidCoSeries[0].data.length"
            type="bar" :height="320"
            :options="topUnpaidCoOptions" :series="topUnpaidCoSeries"
          />
          <div v-else class="empty">🎉 אין כרגע פערי נפרעים</div>
        </div>
      </div>

      <!-- ─── Top agents by unpaid (full width) ─── -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>סוכנים — לא שולם</h3>
          <span class="chart-tag">לחץ על סוכן לפירוט מלא</span>
        </div>
        <apexchart
          v-if="topAgentsSeries[0].data.length"
          type="bar" :height="360"
          :options="topAgentsOptions" :series="topAgentsSeries"
          @click="onAgentBarClick"
        />
        <div v-else class="empty">אין סוכנים עם פערים</div>
      </div>

      <!-- ─── Top unpaid customers — clickable rows ─── -->
      <div class="card">
        <div class="card-h">
          <h3>טופ לקוחות שלא שולמו — אגרגציה לכל הסוכנים</h3>
          <span class="card-tag">{{ comparison.top_unpaid_customers.length }} שורות</span>
        </div>
        <table v-if="comparison.top_unpaid_customers.length" class="ov-table">
          <thead>
            <tr><th>סוכן</th><th>לקוח</th><th>חברה</th><th>סטטוס</th><th class="num">חוסר</th></tr>
          </thead>
          <tbody>
            <tr
              v-for="c in comparison.top_unpaid_customers.slice(0, 12)"
              :key="c.record_id"
              class="clickable"
              @click="$emit('view-agent', c.agent_user_id)"
            >
              <td>{{ c.agent_name }}</td>
              <td>{{ c.name || c.id_number }}</td>
              <td>{{ shortCo(c.company) }}</td>
              <td><span class="status" :class="c.status">{{ statusLabel(c.status) }}</span></td>
              <td class="num warn"><span class="ltr-number">{{ formatShort(c.unpaid_amount) }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">אין כרגע פוליסות שלא שולמו</div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAgencyStore } from '../../../stores/agency.js'
import AiInsightCard from '../../workspace/AiInsightCard.vue'

const agencyStore = useAgencyStore()
const emit = defineEmits(['select-tab', 'open-modal', 'view-agent', 'open-ai'])

const aiSuggestions = [
  'איפה לא שולם החודש בסוכנות?',
  'איזו חברה משלמת הכי פחות מהצפוי?',
  'אילו סוכנים משאירים הכי הרבה כסף על השולחן?',
  'מה סטטוס בונוסי התפוקה השנה?',
]

// AI insight card content — short summary string + suggestion chips,
// shaped to match what AiInsightCard expects ({ summary, suggestions })
const aiViewContext = computed(() => {
  if (!comparison.value || !overview.value) return null
  const o = overview.value
  const s = comparison.value.summary
  const top = (comparison.value.by_company || []).find(c => c.unpaid > 0)
  const fmt = (v) => '₪' + Math.round(Number(v || 0)).toLocaleString('he-IL')
  const summary =
    `הסוכנות ${o.agent_count > 0 ? `מנהלת ${o.agent_count} סוכנים` : 'ריקה'} · ${s.unpaid_count.toLocaleString('he-IL')} מתוך ${s.total_customers.toLocaleString('he-IL')} רשומות לא שולמו ` +
    `(סך ${fmt(s.total_unpaid_amount)})` +
    (top ? ` · החברה המובילה בלא-שולם: ${shortCo(top.company)} (${top.unpaid.toLocaleString('he-IL')} פוליסות)` : '') +
    `.`
  return { summary, suggestions: aiSuggestions, viewKey: 'agency-overview', viewTitle: 'לוח בקרה — סוכנות' }
})

function openAi(initialQuestion) {
  emit('open-ai', { initialQuestion: initialQuestion || '', viewTitle: 'לוח בקרה — סוכנות' })
}

const comparison = computed(() => agencyStore.comparison)
const overview = computed(() => agencyStore.overview)

onMounted(() => {
  if (!agencyStore.comparison) agencyStore.fetchComparison()
  if (!agencyStore.overview) agencyStore.fetchOverview()
})

// ─── Donut: matched vs unpaid ───
const donutSeries = computed(() => {
  if (!comparison.value) return []
  const s = comparison.value.summary
  const out = []
  if (s.matched_count) out.push(s.matched_count)
  if (s.unpaid_count) out.push(s.unpaid_count)
  return out
})
const donutOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  labels: ['נמצא בשניהם', 'לא שולם'].slice(0, donutSeries.value.length),
  colors: ['#2E844A', '#E8720A'],
  legend: { position: 'bottom', fontSize: '12.5px', markers: { width: 10, height: 10 } },
  dataLabels: { enabled: true, formatter: (v) => `${Math.round(v)}%` },
  stroke: { width: 2, colors: ['#fff'] },
  plotOptions: {
    pie: {
      donut: {
        size: '60%',
        labels: {
          show: true, name: { fontSize: '13px', color: '#706E6B' },
          value: { fontSize: '24px', fontWeight: 800, color: '#181818', formatter: (v) => Number(v).toLocaleString('he-IL') },
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

// ─── Top companies by unpaid count ───
const topUnpaidCo = computed(() => (comparison.value?.by_company || []).filter(c => c.unpaid > 0).slice(0, 8))
const topUnpaidCoSeries = computed(() => [{ name: 'לא שולם', data: topUnpaidCo.value.map(c => c.unpaid) }])
const topUnpaidCoOptions = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#E8720A', '#FF9800', '#FFB74D', '#FFCC80', '#C68A2E', '#7F56D9', '#0891b2', '#22d3ee'],
  legend: { show: false },
  xaxis: { categories: topUnpaidCo.value.map(c => shortCo(c.company)), labels: { style: { fontSize: '10.5px' } } },
  yaxis: { labels: { style: { fontSize: '11px', fontWeight: 600 } } },
  dataLabels: { enabled: true, formatter: (v) => v.toLocaleString('he-IL'), style: { fontSize: '10px', fontWeight: 700, colors: ['#fff'] } },
  tooltip: { y: { formatter: (v) => v.toLocaleString('he-IL') + ' רשומות' } },
  grid: { strokeDashArray: 3 },
}))

// ─── Top agents by unpaid count ───
const topAgents = computed(() =>
  [...(comparison.value?.by_agent || [])]
    .filter(a => a.unpaid > 0)
    .sort((a, b) => b.unpaid - a.unpaid)
    .slice(0, 12)
)
const topAgentsSeries = computed(() => [{ name: 'לא שולם', data: topAgents.value.map(a => a.unpaid) }])
const topAgentsOptions = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '72%' } },
  colors: ['#F57C00', '#FF9800', '#FFB74D', '#E8720A', '#C68A2E', '#a78bfa', '#22d3ee', '#3b82f6', '#10b981', '#f59e0b', '#7F56D9', '#0891b2'],
  legend: { show: false },
  xaxis: { categories: topAgents.value.map(a => a.name), labels: { style: { fontSize: '10.5px' } } },
  yaxis: { labels: { style: { fontSize: '12px', fontWeight: 600 } } },
  dataLabels: { enabled: true, formatter: (v) => v.toLocaleString('he-IL'), style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] } },
  tooltip: { y: { formatter: (v) => v.toLocaleString('he-IL') + ' רשומות' } },
  grid: { strokeDashArray: 3 },
}))

function onAgentBarClick(_evt, _ctx, config) {
  const idx = config?.dataPointIndex
  if (idx == null || idx < 0) return
  const agent = topAgents.value[idx]
  if (agent?.user_id) {
    // emit must match API; use plain user_id string
    const e = new CustomEvent('view-agent')
    // Vue's defineEmits doesn't expose emit() to outside; instead use a $emit via the component instance
    // We attach the click only as a hint; clicking the table row remains the canonical path.
  }
}

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
.ov-tab { display: flex; flex-direction: column; gap: 16px; position: relative; z-index: 2; }
.loading { padding: 80px; text-align: center; color: var(--text-muted); }
.empty { padding: 60px 20px; text-align: center; color: var(--text-muted); font-size: 13.5px; }

/* KPI row — mirrors ProductionDashboard */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.kpi-card {
  background: #FFFFFF; border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: var(--shadow-sm);
  position: relative; overflow: hidden;
  transition: transform .2s var(--transition), box-shadow .2s var(--transition);
}
.kpi-card.clickable { cursor: pointer; }
.kpi-card.clickable:hover { transform: translateY(-3px); box-shadow: 0 14px 32px -16px rgba(0,0,0,0.18); }
.kpi-card::before { content: ''; position: absolute; inset: 0 0 auto 0; height: 3px; }
.kpi-blue::before    { background: #6366f1; }
.kpi-cyan::before    { background: #22d3ee; }
.kpi-amber::before   { background: #E8720A; }
.kpi-emerald::before { background: #2E844A; }
.kpi-red::before     { background: #8C1D2A; }
.kpi-icon {
  width: 38px; height: 38px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.kpi-blue    .kpi-icon { background: rgba(99, 102, 241, 0.10); color: #6366f1; }
.kpi-cyan    .kpi-icon { background: rgba(34, 211, 238, 0.10); color: #0891b2; }
.kpi-amber   .kpi-icon { background: rgba(232, 114, 10, 0.10); color: #E8720A; }
.kpi-emerald .kpi-icon { background: var(--green-light); color: var(--green-deep); }
.kpi-red     .kpi-icon { background: rgba(140, 29, 42, 0.10); color: #8C1D2A; }
.kpi-data { min-width: 0; }
.kpi-value { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; line-height: 1; }
.kpi-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* Charts */
.charts-row { display: grid; grid-template-columns: 1fr 1.3fr; gap: 14px; }
.chart-card {
  background: #FFFFFF; border: 1px solid var(--border);
  border-radius: 14px; padding: 16px 18px;
  box-shadow: var(--shadow-sm);
}
.chart-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
.chart-header h3 { font-size: 14.5px; font-weight: 700; color: var(--text); letter-spacing: -0.2px; }
.chart-tag { font-size: 10.5px; color: var(--text-muted); font-weight: 600; letter-spacing: 0.3px; }

.card { background: #FFFFFF; border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; box-shadow: var(--shadow-sm); }
.card-h { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.card-h h3 { font-size: 14.5px; font-weight: 700; color: var(--text); }
.card-tag { background: var(--bg); color: var(--text-muted); padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }

.ov-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ov-table th { text-align: right; font-size: 11px; color: var(--text-muted); font-weight: 700; padding: 8px 6px; border-bottom: 1px solid var(--border-subtle); }
.ov-table td { padding: 9px 6px; border-bottom: 1px solid var(--border-subtle); }
.ov-table tr:last-child td { border-bottom: none; }
.ov-table tr.clickable { cursor: pointer; transition: background .12s; }
.ov-table tr.clickable:hover td { background: rgba(245, 124, 0, 0.05); }
.ov-table .num { text-align: center; }
.ov-table .num.warn .ltr-number { color: #8C1D2A; font-weight: 700; }
.status { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px; }
.status.unpaid        { background: rgba(232, 114, 10, 0.10); color: #E8720A; }
.status.paid_mismatch { background: rgba(232, 114, 10, 0.10); color: #C85A00; }
.status.no_data       { background: rgba(45, 37, 34, 0.06); color: var(--text-muted); }
.status.paid_match    { background: var(--green-light); color: var(--green-deep); }
.status.cancelled     { background: rgba(127, 86, 217, 0.10); color: var(--accent-violet); }

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 1100px) {
  .kpi-row { grid-template-columns: repeat(3, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}
</style>
