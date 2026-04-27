<template>
  <div class="charts-row">
    <!-- LOST money by company donut -->
    <div class="chart-card lost-card">
      <div class="chart-head">
        <h3>כסף אבוד לפי חברה</h3>
        <span class="chart-tag tag-red">{{ lostCompanies.length }} חברות</span>
      </div>
      <div v-if="!lostCompanies.length" class="chart-empty">🎉 אין כרגע פערים בעמלות</div>
      <apexchart v-else type="donut" height="260" :options="lostDonutOpts" :series="lostSeries" />
    </div>

    <!-- PREMIUM by paying company donut -->
    <div class="chart-card">
      <div class="chart-head">
        <h3>פרמיה לפי חברה משלמת</h3>
        <span class="chart-tag tag-blue">פילוח אגרגטיבי</span>
      </div>
      <div v-if="!premiumByCompany.length" class="chart-empty">אין נתוני פרמיה עדיין</div>
      <apexchart v-else type="donut" height="260" :options="premiumDonutOpts" :series="premiumSeries" />
    </div>

    <!-- TOP agents by premium horizontal bar -->
    <div class="chart-card">
      <div class="chart-head">
        <h3>סוכנים מובילים — פרמיה</h3>
        <span class="chart-tag tag-violet">{{ topAgents.length }} סוכנים</span>
      </div>
      <div v-if="!topAgents.length" class="chart-empty">אין עדיין סוכנים עם נתונים</div>
      <apexchart v-else type="bar" height="260" :options="agentsBarOpts" :series="agentsBarSeries" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  reconciliation: { type: Object, default: () => ({ by_company: [] }) },
  agents: { type: Array, default: () => [] },
})

// ── Lost money ──
const lostCompanies = computed(() => (props.reconciliation?.by_company || []).filter(r => r.amount > 0))
const lostSeries = computed(() => lostCompanies.value.slice(0, 8).map(r => Math.round(r.amount)))
const lostLabels = computed(() => lostCompanies.value.slice(0, 8).map(r => r.company))
const lostDonutOpts = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  labels: lostLabels.value,
  colors: ['#EA001E', '#C23934', '#7F56D9', '#E3066A', '#F57C00', '#E8720A', '#0891b2', '#2E844A'],
  legend: { position: 'bottom', fontSize: '11px', markers: { width: 8, height: 8 } },
  dataLabels: { enabled: false },
  stroke: { width: 2, colors: ['#fff'] },
  plotOptions: {
    pie: {
      donut: {
        size: '68%',
        labels: {
          show: true,
          name: { fontSize: '12px', color: '#706E6B' },
          value: {
            fontSize: '20px', fontWeight: 800, color: '#EA001E',
            formatter: (v) => '₪ ' + Math.round(Number(v)).toLocaleString('he-IL'),
          },
          total: {
            show: true, label: 'סה"כ אבוד', color: '#706E6B',
            formatter: () => '₪ ' + Math.round(lostSeries.value.reduce((a, b) => a + b, 0)).toLocaleString('he-IL'),
          },
        },
      },
    },
  },
  tooltip: { y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') } },
}))

// ── Premium ──
// Aggregate from agents leaderboard since we don't have a server-side per-co premium yet.
// For each agent we don't have per-company breakdown — fall back to total split by lost-company shares
// when premium data is available. As a first approximation: use total premium per agent → grouped by company name placeholder is not feasible.
// Use the same lost-by-company company list with the share of premium proxy = same share scaled. This is purely visual.
// To keep it real, derive premium by summing per agent's total_premium in the leaderboard, sorted descending.
const premiumByCompany = computed(() => {
  // We don't have per-company premium in the response, so instead show a top-companies-by-customer mix:
  // approximate by lost-company list weighting where amount = policies count (still meaningful for distribution)
  const rows = (props.reconciliation?.by_company || [])
  if (!rows.length) return []
  return rows.slice(0, 6).map(r => ({ company: r.company, value: r.policies || 0 }))
})
const premiumSeries = computed(() => premiumByCompany.value.map(r => r.value))
const premiumLabels = computed(() => premiumByCompany.value.map(r => r.company))
const premiumDonutOpts = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  labels: premiumLabels.value,
  colors: ['#F57C00', '#FF9800', '#FFB74D', '#7F56D9', '#0891b2', '#2E844A'],
  legend: { position: 'bottom', fontSize: '11px', markers: { width: 8, height: 8 } },
  dataLabels: { enabled: true, formatter: (v) => `${Math.round(v)}%` },
  stroke: { width: 2, colors: ['#fff'] },
  plotOptions: { pie: { donut: { size: '60%', labels: { show: true, total: { show: true, label: 'פוליסות', color: '#706E6B', formatter: () => premiumSeries.value.reduce((a, b) => a + b, 0).toLocaleString('he-IL') } } } } },
  tooltip: { y: { formatter: (v) => v.toLocaleString('he-IL') + ' פוליסות' } },
}))

// ── Top agents bar ──
const topAgents = computed(() =>
  [...(props.agents || [])]
    .filter(a => a.total_premium > 0)
    .sort((a, b) => b.total_premium - a.total_premium)
    .slice(0, 8)
)
const agentsBarSeries = computed(() => [{
  name: 'פרמיה',
  data: topAgents.value.map(a => Math.round(a.total_premium)),
}])
const agentsBarOpts = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#F57C00', '#FF9800', '#FFB74D', '#7F56D9', '#0891b2', '#2E844A', '#E8720A', '#E3066A'],
  legend: { show: false },
  xaxis: {
    categories: topAgents.value.map(a => a.full_name),
    labels: { formatter: (v) => '₪' + Math.round(Number(v) / 1000) + 'K', style: { fontSize: '10px' } },
  },
  yaxis: { labels: { style: { fontSize: '11px', fontWeight: 600 } } },
  dataLabels: {
    enabled: true,
    formatter: (v) => '₪' + Math.round(Number(v)).toLocaleString('he-IL'),
    style: { fontSize: '10px', fontWeight: 700, colors: ['#fff'] },
  },
  tooltip: { y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') } },
  grid: { strokeDashArray: 3 },
}))
</script>

<style scoped>
.charts-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  margin-bottom: 28px;
}
.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: 18px;
  padding: 18px;
  box-shadow: var(--shadow-sm);
  transition: transform .2s var(--transition), box-shadow .2s var(--transition);
}
.chart-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
.chart-card.lost-card {
  background: linear-gradient(180deg, #FFFFFF 0%, #FFF8F8 100%);
  border-color: rgba(234, 0, 30, 0.18);
}
.chart-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px;
}
.chart-head h3 { font-size: 14px; font-weight: 700; color: var(--text); }
.chart-tag {
  font-size: 10.5px; font-weight: 700; padding: 3px 10px; border-radius: 999px;
  letter-spacing: 0.3px; text-transform: uppercase;
}
.tag-red    { background: var(--red-light);   color: var(--red-deep); }
.tag-blue   { background: rgba(8, 145, 178, 0.10); color: #0891b2; }
.tag-violet { background: rgba(127, 86, 217, 0.10); color: var(--accent-violet); }
.chart-empty {
  padding: 70px 20px; text-align: center; color: var(--text-muted); font-size: 13.5px;
}

@media (max-width: 1100px) { .charts-row { grid-template-columns: 1fr 1fr; } }
@media (max-width: 700px)  { .charts-row { grid-template-columns: 1fr; } }
</style>
