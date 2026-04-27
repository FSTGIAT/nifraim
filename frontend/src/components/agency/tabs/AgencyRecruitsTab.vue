<template>
  <div class="rec-tab">
    <div v-if="!data" class="loading">טוען תיקי סוכנים…</div>
    <template v-else>
      <div class="kpi-row">
        <div class="kpi"><div class="kpi-label">סך גיוסים</div><div class="kpi-val ltr-number">{{ data.totals.total.toLocaleString('he-IL') }}</div></div>
        <div class="kpi"><div class="kpi-label">חיסכון פיננסי</div><div class="kpi-val ltr-number">{{ (data.totals.by_category.financial || 0).toLocaleString('he-IL') }}</div></div>
        <div class="kpi"><div class="kpi-label">ביטוח</div><div class="kpi-val ltr-number">{{ (data.totals.by_category.insurance || 0).toLocaleString('he-IL') }}</div></div>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>גיוסים לפי חברה</h3>
          <span class="card-tag">{{ data.by_company.length }} חברות</span>
        </div>
        <table v-if="data.by_company.length" class="rec-table">
          <thead>
            <tr><th>חברה</th><th class="num">גיוסים</th><th class="num">סכום</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in data.by_company" :key="c.company">
              <td class="co">{{ c.company }}</td>
              <td class="num"><strong>{{ c.total }}</strong></td>
              <td class="num"><span class="ltr-number">{{ formatShort(c.amount) }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">אין גיוסים עדיין</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAgencyStore } from '../../../stores/agency.js'

const agencyStore = useAgencyStore()
const data = computed(() => agencyStore.recruits)
onMounted(() => { if (!agencyStore.recruits) agencyStore.fetchRecruits() })

function formatShort(v) {
  if (v == null || v === 0) return '₪0'
  const n = Number(v)
  if (n >= 1_000_000) return '₪' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '₪' + Math.round(n / 1_000) + 'K'
  return '₪' + Math.round(n).toLocaleString('he-IL')
}
</script>

<style scoped>
.rec-tab { display: flex; flex-direction: column; gap: 18px; position: relative; z-index: 2; }
.loading { padding: 60px; text-align: center; color: var(--text-muted); }
.empty { padding: 50px 20px; text-align: center; color: var(--text-muted); }

.kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.kpi { background: #FFFFFF; border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; box-shadow: var(--shadow-sm); border-top: 3px solid #a78bfa; }
.kpi-label { font-size: 11px; color: var(--text-muted); font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; }
.kpi-val { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; margin-top: 4px; }

.card { background: #FFFFFF; border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; box-shadow: var(--shadow-sm); }
.card-h { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.card-h h3 { font-size: 14.5px; font-weight: 700; color: var(--text); }
.card-tag { background: var(--bg); color: var(--text-muted); padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }

.rec-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.rec-table th { text-align: right; font-size: 11px; color: var(--text-muted); font-weight: 700; padding: 8px 6px; border-bottom: 1px solid var(--border-subtle); }
.rec-table td { padding: 9px 6px; border-bottom: 1px solid var(--border-subtle); }
.rec-table tr:last-child td { border-bottom: none; }
.rec-table .num { text-align: center; }
.rec-table .num strong { color: var(--primary-deep); font-weight: 800; }
.rec-table .co { font-weight: 600; color: var(--text); }
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }
</style>
