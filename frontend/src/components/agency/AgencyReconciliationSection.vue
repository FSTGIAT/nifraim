<template>
  <div class="recon">
    <div class="recon-grid">
      <div class="card chart-card">
        <h3>כסף אבוד לפי חברה משלמת</h3>
        <div v-if="!byCompany.length" class="empty">אין כרגע עמלות לא משולמות 🎉</div>
        <div v-else>
          <apexchart
            type="donut"
            height="320"
            :options="donutOptions"
            :series="donutSeries"
          />
        </div>
      </div>
      <div class="card list-card">
        <h3>טופ פוליסות עם כסף אבוד</h3>
        <div v-if="!topPolicies.length" class="empty">אין פוליסות לא-משולמות.</div>
        <table v-else class="recon-table">
          <thead>
            <tr>
              <th>סוכן</th>
              <th>חברה</th>
              <th>לקוח</th>
              <th class="num">חוסר</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in topPolicies" :key="p.record_id" @click="$emit('drillAgent', p.agent_user_id, p.agent_name)">
              <td class="agent">{{ p.agent_name }}</td>
              <td>{{ p.company }}</td>
              <td class="muted">{{ p.client_name || p.client_id_number }}</td>
              <td class="num lost"><span class="ltr-number">{{ formatCurrency(p.lost_amount) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  reconciliation: { type: Object, required: true },
})
defineEmits(['drillAgent'])

const byCompany = computed(() => props.reconciliation?.by_company || [])
const topPolicies = computed(() => (props.reconciliation?.top_policies || []).slice(0, 25))

const donutSeries = computed(() => byCompany.value.slice(0, 8).map((r) => Math.round(r.amount)))
const donutOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif' },
  labels: byCompany.value.slice(0, 8).map((r) => r.company),
  colors: ['#E8660A', '#7F56D9', '#C68A2E', '#0E7B86', '#5B4FCB', '#2D2522', '#C85A00', '#8C1D2A'],
  dataLabels: { enabled: true, formatter: (v) => `${Math.round(v)}%` },
  legend: { position: 'bottom', fontSize: '12px' },
  plotOptions: { pie: { donut: { size: '60%', labels: { show: true, total: { show: true, label: 'סה"כ', formatter: () => '₪ ' + Math.round(donutSeries.value.reduce((a, b) => a + b, 0)).toLocaleString('he-IL') } } } } },
  tooltip: { y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') } },
}))

function formatCurrency(v) {
  if (v == null) return '—'
  return '₪ ' + Math.round(Number(v)).toLocaleString('he-IL')
}
</script>

<style scoped>
.recon { margin-bottom: 24px; }
.recon-grid {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 20px;
}
.card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}
.card h3 { font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 14px; }
.empty { padding: 40px; text-align: center; color: var(--text-muted); }
.recon-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.recon-table th {
  text-align: right; font-weight: 600; font-size: 11px;
  color: var(--text-muted); padding: 8px 6px;
  border-bottom: 1px solid var(--border-subtle);
}
.recon-table td {
  padding: 10px 6px;
  border-bottom: 1px solid var(--border-subtle);
}
.recon-table tr { cursor: pointer; transition: background .12s; }
.recon-table tr:hover td { background: var(--primary-glow); }
.agent { font-weight: 600; color: var(--text); }
.muted { color: var(--text-muted); font-size: 12.5px; }
.num { text-align: center; }
td.lost .ltr-number { color: #8C1D2A; font-weight: 700; }
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 1100px) {
  .recon-grid { grid-template-columns: 1fr; }
}
</style>
