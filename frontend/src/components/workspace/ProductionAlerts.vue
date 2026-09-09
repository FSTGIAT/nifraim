<template>
  <div v-if="hasAnything" class="pa-card">
    <div class="pa-head">
      <h3>התראות</h3>
      <span v-if="previousPeriod" class="pa-period ltr-number">מול {{ previousPeriod }}</span>
    </div>

    <!-- Clients with no payment. Only companies that actually delivered a
         נפרעים report this month can be checked, and saying which ones is what
         stops a short list reading as "almost everyone was paid". -->
    <section v-if="unpaidTotal" class="pa-sec">
      <h4>
        לקוחות שלא התקבל בגינם תשלום
        <span class="pa-badge ltr-number">{{ unpaidTotal }}</span>
      </h4>
      <p class="pa-note">
        נבדק מול הדוחות שהתקבלו מ{{ coveredCompanies.join(', ') }}.
        <template v-if="uncheckable.length">
          לא נבדקו: {{ uncheckable.join(', ') }} — לא התקבל מהן דוח נפרעים החודש.
        </template>
      </p>
      <table class="pa-table">
        <thead>
          <tr><th>לקוח</th><th>חברה</th><th>מוצרים</th><th>פרמיה</th><th>צבירה</th></tr>
        </thead>
        <tbody>
          <tr v-for="u in shownUnpaid" :key="u.id_number">
            <td>{{ u.name || u.id_number }}</td>
            <td>{{ u.companies.join(', ') }}</td>
            <td class="pa-num"><span class="ltr-number">{{ u.products }}</span></td>
            <td class="pa-num"><span class="ltr-number">{{ money(u.premium) }}</span></td>
            <td class="pa-num"><span class="ltr-number">{{ money(u.accumulation) }}</span></td>
          </tr>
        </tbody>
      </table>
      <button v-if="unpaid.length > unpaidLimit" class="pa-more" @click="unpaidLimit += 20">
        הצג עוד
      </button>
    </section>

    <div class="pa-split">
      <section v-if="companyMovers.length" class="pa-sec">
        <h4>השינויים הגדולים לפי חברה</h4>
        <ul class="pa-movers">
          <li v-for="m in companyMovers" :key="m.company">
            <span class="pa-mv-name">{{ m.company }}</span>
            <span class="pa-mv-delta ltr-number" :class="m.reported ? deltaClass(m.delta) : ''">
              {{ money(m.delta, true) }}
            </span>
            <!-- Missing ≠ zero. See the endpoint's `reported` flag. -->
            <span v-if="!m.reported" class="pa-tag">לא התקבל דוח החודש</span>
            <span v-else-if="m.delta_pct !== null" class="pa-mv-pct ltr-number">
              {{ m.delta_pct > 0 ? '+' : '' }}{{ m.delta_pct }}%
            </span>
            <span v-else class="pa-tag">חדש</span>
          </li>
        </ul>
      </section>

      <section v-if="clientMovers.length" class="pa-sec">
        <h4>השינויים הגדולים לפי לקוח</h4>
        <ul class="pa-movers">
          <li v-for="m in clientMovers" :key="m.id_number">
            <span class="pa-mv-name">{{ m.name || m.id_number }}</span>
            <span class="pa-mv-delta ltr-number" :class="deltaClass(m.delta)">
              {{ money(m.delta, true) }}
            </span>
            <span class="pa-mv-pct ltr-number">{{ money(m.previous) }} ← {{ money(m.now) }}</span>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client'

const unpaid = ref([])
const unpaidTotal = ref(0)
const coveredCompanies = ref([])
const companyMovers = ref([])
const clientMovers = ref([])
const previousPeriod = ref(null)
const unpaidLimit = ref(10)

const shownUnpaid = computed(() => unpaid.value.slice(0, unpaidLimit.value))
const hasAnything = computed(
  () => unpaidTotal.value || companyMovers.value.length || clientMovers.value.length,
)
// Companies that appear as movers but sent no report — named so the unpaid
// list can't be mistaken for a complete picture.
const uncheckable = computed(() =>
  companyMovers.value.filter(m => !m.reported).map(m => m.company),
)

function money(v, signed = false) {
  const n = Math.round(Number(v || 0))
  if (!n) return '₪0'
  const s = '₪' + Math.abs(n).toLocaleString('en-US')
  return signed ? (n > 0 ? '+' : '−') + s : s
}

function deltaClass(d) {
  return d < 0 ? 'pa-neg' : 'pa-pos'
}

onMounted(async () => {
  try {
    const res = await api.get('/production/alerts')
    unpaid.value = res.data.unpaid || []
    unpaidTotal.value = res.data.unpaid_total || 0
    coveredCompanies.value = res.data.covered_companies || []
    companyMovers.value = res.data.company_movers || []
    clientMovers.value = res.data.client_movers || []
    previousPeriod.value = res.data.previous_period
  } catch (e) {
    /* panel simply stays hidden */
  }
})
</script>

<style scoped>
.pa-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px;
}
.pa-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 16px; }
.pa-head h3 { font-size: 15px; font-weight: 700; color: var(--text); }
.pa-period { font-size: 12px; color: var(--text-muted); }

.pa-sec + .pa-sec, .pa-split { margin-top: 22px; }
.pa-sec h4 {
  font-size: 13px; font-weight: 700; color: var(--text);
  margin-bottom: 6px; display: flex; align-items: center; gap: 8px;
}
.pa-badge {
  background: var(--amber-light); color: var(--amber);
  border-radius: 10px; padding: 1px 8px; font-size: 11px; font-weight: 700;
}
.pa-note { font-size: 11px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.6; }

.pa-split { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 900px) { .pa-split { grid-template-columns: 1fr; } }

.pa-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.pa-table th {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border-subtle);
}
.pa-table td {
  font-size: 13px; color: var(--text); padding: 8px;
  border-bottom: 1px solid var(--border-subtle);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pa-table th:not(:first-child), .pa-table td.pa-num { text-align: center; width: 100px; }

.pa-movers { list-style: none; display: flex; flex-direction: column; gap: 2px; }
.pa-movers li {
  display: grid; grid-template-columns: 1fr auto auto;
  align-items: center; gap: 10px;
  padding: 7px 8px; border-bottom: 1px solid var(--border-subtle);
}
.pa-mv-name { font-size: 13px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pa-mv-delta { font-size: 13px; font-weight: 700; }
.pa-mv-pct { font-size: 11px; color: var(--text-muted); }
.pa-neg { color: var(--red, #c23934); }
.pa-pos { color: var(--accent-emerald); }
.pa-tag {
  padding: 1px 7px; border-radius: 10px; background: var(--border-subtle);
  color: var(--text-muted); font-size: 10px; font-weight: 600; white-space: nowrap;
}
.pa-more {
  margin-top: 10px; padding: 5px 14px; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); background: none; color: var(--text-muted);
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.pa-more:hover { color: var(--text); }
</style>
