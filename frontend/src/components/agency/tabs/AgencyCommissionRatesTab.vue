<template>
  <div class="rates-tab">
    <div v-if="!data" class="loading">טוען שיעורי עמלה…</div>
    <div v-else-if="!data.by_company.length" class="empty">
      אין שיעורי עמלה שהוגדרו ע"י סוכני הסוכנות עדיין.
    </div>
    <div v-else class="card">
      <h3>שיעורי עמלה — לפי חברה</h3>
      <table class="rates-table">
        <thead>
          <tr>
            <th>חברה</th>
            <th class="num">סוכנים שהגדירו</th>
            <th class="num">שיעור ממוצע</th>
            <th class="num">טווח</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in data.by_company" :key="c.company">
            <td class="co">{{ c.company }}</td>
            <td class="num"><strong>{{ c.agent_count_with_rate }}</strong></td>
            <td class="num"><span class="ltr-number">{{ avgRate(c).toFixed(2) }}%</span></td>
            <td class="num muted"><span class="ltr-number">{{ rangeRate(c) }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAgencyStore } from '../../../stores/agency.js'

const agencyStore = useAgencyStore()
const data = computed(() => agencyStore.rates)
onMounted(() => { if (!agencyStore.rates) agencyStore.fetchCommissionRates() })

function avgRate(c) {
  const arr = c.rates || []
  if (!arr.length) return 0
  return (arr.reduce((s, r) => s + (r.rate || 0), 0) / arr.length) * 100
}
function rangeRate(c) {
  const arr = (c.rates || []).map(r => r.rate || 0)
  if (!arr.length) return '—'
  const min = Math.min(...arr) * 100
  const max = Math.max(...arr) * 100
  if (Math.abs(min - max) < 0.01) return `${min.toFixed(2)}%`
  return `${min.toFixed(2)}% – ${max.toFixed(2)}%`
}
</script>

<style scoped>
.rates-tab { position: relative; z-index: 2; }
.loading { padding: 60px; text-align: center; color: var(--text-muted); }
.empty { padding: 60px 20px; text-align: center; color: var(--text-muted); }
.card { background: #FFFFFF; border: 1px solid var(--border); border-radius: 14px; padding: 18px 22px; box-shadow: var(--shadow-sm); }
.card h3 { font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 14px; }
.rates-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.rates-table th { text-align: right; font-size: 11px; color: var(--text-muted); font-weight: 700; padding: 10px 8px; border-bottom: 1px solid var(--border-subtle); }
.rates-table td { padding: 12px 8px; border-bottom: 1px solid var(--border-subtle); }
.rates-table tr:last-child td { border-bottom: none; }
.rates-table .num { text-align: center; }
.rates-table .num strong { color: var(--primary-deep); font-weight: 800; }
.rates-table .co { font-weight: 600; color: var(--text); }
.muted { color: var(--text-muted); font-size: 12px; }
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }
</style>
