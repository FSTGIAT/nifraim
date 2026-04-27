<template>
  <div class="prod-tab">
    <div v-if="!data" class="loading">טוען נתוני פרודוקציה…</div>
    <template v-else>
      <!-- KPI strip -->
      <div class="kpi-row">
        <div class="kpi"><div class="kpi-label">סך פרמיה</div><div class="kpi-val ltr-number">{{ formatShort(data.kpi.total_premium) }}</div></div>
        <div class="kpi"><div class="kpi-label">סך צבירה</div><div class="kpi-val ltr-number">{{ formatShort(data.kpi.total_accumulation) }}</div></div>
        <div class="kpi"><div class="kpi-label">לקוחות ייחודיים</div><div class="kpi-val ltr-number">{{ data.kpi.unique_clients.toLocaleString('he-IL') }}</div></div>
        <div class="kpi"><div class="kpi-label">סוכנים עם פרודוקציה</div><div class="kpi-val ltr-number">{{ data.kpi.agents_with_data }}</div></div>
      </div>

      <!-- Charts row -->
      <div class="row-2">
        <div class="card">
          <h3>פרמיה לפי חברה משלמת</h3>
          <apexchart v-if="byCompanyPremiumSeries.length" type="donut" height="280" :options="donutOptions" :series="byCompanyPremiumSeries"/>
          <div v-else class="empty">אין נתונים עדיין</div>
        </div>
        <div class="card">
          <h3>טופ לקוחות (אגרגציה כל-סוכנים)</h3>
          <table v-if="data.top_clients.length" class="prod-table">
            <thead>
              <tr><th>שם</th><th>סוכן</th><th class="num">מוצרים</th><th class="num">פרמיה</th></tr>
            </thead>
            <tbody>
              <tr v-for="c in data.top_clients" :key="c.id_number + c.agent_user_id" class="clickable" @click="$emit('viewAgent', c.agent_user_id)">
                <td>{{ c.name || c.id_number }}</td>
                <td class="muted">{{ c.agent_name }}</td>
                <td class="num">{{ c.products }}</td>
                <td class="num"><span class="ltr-number">{{ formatShort(c.total_premium) }}</span></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty">אין נתונים</div>
        </div>
      </div>

      <!-- Per-agent contribution bar -->
      <div class="card">
        <h3>תרומה לפי סוכן — פרמיה</h3>
        <apexchart
          v-if="byAgentSeries.length"
          type="bar" height="320"
          :options="agentBarOptions" :series="[{ name: 'פרמיה', data: byAgentSeries }]"
        />
        <div v-else class="empty">אין נתונים</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAgencyStore } from '../../../stores/agency.js'

const agencyStore = useAgencyStore()
defineEmits(['viewAgent'])

const data = computed(() => agencyStore.production)
onMounted(() => { if (!agencyStore.production) agencyStore.fetchProduction() })

const byCompanyPremiumSeries = computed(() => (data.value?.by_company || []).slice(0, 8).map(c => Math.round(c.total_premium)))
const byCompanyPremiumLabels = computed(() => (data.value?.by_company || []).slice(0, 8).map(c => shortCo(c.company)))
const donutOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  labels: byCompanyPremiumLabels.value,
  colors: ['#F57C00', '#FF9800', '#FFB74D', '#FFCC80', '#E8720A', '#C68A2E', '#0891b2', '#7F56D9'],
  legend: { position: 'bottom', fontSize: '11px' },
  dataLabels: { enabled: true, formatter: (v) => `${Math.round(v)}%` },
  stroke: { width: 2, colors: ['#fff'] },
  plotOptions: { pie: { donut: { size: '58%' } } },
  tooltip: { y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') } },
}))

const byAgentSeries = computed(() => (data.value?.by_agent || []).slice(0, 15).map(a => Math.round(a.total_premium)))
const byAgentCategories = computed(() => (data.value?.by_agent || []).slice(0, 15).map(a => a.name))
const agentBarOptions = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#F57C00', '#FF9800', '#FFB74D', '#FFCC80', '#E8720A', '#C68A2E', '#0891b2', '#7F56D9', '#a78bfa', '#22d3ee', '#3b82f6', '#10b981', '#f59e0b', '#E3066A', '#2E844A'],
  legend: { show: false },
  xaxis: {
    categories: byAgentCategories.value,
    labels: { formatter: (v) => '₪' + Math.round(Number(v) / 1000) + 'K', style: { fontSize: '10px' } },
  },
  yaxis: { labels: { style: { fontSize: '11px', fontWeight: 600 } } },
  dataLabels: { enabled: false },
  tooltip: { y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') } },
  grid: { strokeDashArray: 3 },
}))

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
.prod-tab { display: flex; flex-direction: column; gap: 18px; position: relative; z-index: 2; }
.loading { padding: 60px; text-align: center; color: var(--text-muted); }
.empty { padding: 50px 20px; text-align: center; color: var(--text-muted); font-size: 13.5px; }

.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi {
  background: #FFFFFF; border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px;
  box-shadow: var(--shadow-sm); border-top: 3px solid var(--primary);
}
.kpi-label { font-size: 11px; color: var(--text-muted); font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; }
.kpi-val { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; margin-top: 4px; }

.row-2 { display: grid; grid-template-columns: 1fr 1.2fr; gap: 14px; }
.card { background: #FFFFFF; border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; box-shadow: var(--shadow-sm); }
.card h3 { font-size: 14.5px; font-weight: 700; color: var(--text); margin-bottom: 10px; }

.prod-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.prod-table th { text-align: right; font-size: 11px; color: var(--text-muted); font-weight: 700; padding: 8px 6px; border-bottom: 1px solid var(--border-subtle); }
.prod-table td { padding: 9px 6px; border-bottom: 1px solid var(--border-subtle); }
.prod-table tr:last-child td { border-bottom: none; }
.prod-table tr.clickable { cursor: pointer; transition: background .12s; }
.prod-table tr.clickable:hover td { background: rgba(245, 124, 0, 0.05); }
.prod-table .num { text-align: center; }
.prod-table .muted { color: var(--text-muted); font-size: 12px; }
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 1100px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .row-2 { grid-template-columns: 1fr; }
}
</style>
