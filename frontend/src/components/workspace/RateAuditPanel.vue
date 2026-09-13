<template>
  <div v-if="companies.length" class="ra-card">
    <div class="ra-head">
      <h3>עמלות בפועל מול ההסכמים</h3>
      <span v-if="period" class="ra-period ltr-number">{{ period }}</span>
    </div>
    <p class="ra-sub">מה שכל חברה שילמה בפועל, מול מה שאמורה הייתה לשלם לפי אחוזי ההסכם.</p>

    <!-- Anything needing action is stated before the chart. A panel that opens
         with a plot makes the reader hunt for the problem. -->
    <ul v-if="alerts.length" class="ra-alerts">
      <li v-for="a in alerts" :key="a.key" class="ra-alert" :class="'ra-alert--' + a.level">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span>{{ a.text }}</span>
      </li>
    </ul>

    <!-- Two bars per company on ONE axis — both are shekels, so they compare
         directly. Only companies whose rows carry a product-level rate appear:
         a fallback rate is not a claim about what anyone owes. -->
    <p class="ra-hint">בחר חברה בגרף כדי לראות את הפירוט לפי מוצר</p>
    <apexchart v-if="comparable.length" type="bar" :height="chartHeight"
               :options="chartOptions" :series="chartSeries" />
    <p v-else class="ra-none">אין חברה עם שיעור עמלה מפורש בהסכם — אין מה להשוות.</p>

    <!-- Companies that can't be compared are listed, never dropped: each line
         names the action that would make them comparable. -->
    <ul v-if="notComparable.length" class="ra-excluded">
      <li v-for="c in notComparable" :key="c.company">
        <span class="ra-ex-name">{{ c.company }}</span>
        <span class="ra-ex-paid ltr-number">{{ money(c.paid) }}</span>
        <span class="ra-tag">{{ c.no_agreement ? 'אין הסכם עמלות' : 'אין שיעור למוצרים שלה' }}</span>
      </li>
    </ul>

    <button class="ra-all" @click="tableOpen = true">הצג את כל הנתונים</button>

    <DataModal :open="!!openCompany" :title="openCompany ? openCompany.company + ' — לפי מוצר' : ''"
               @close="openCompany = null">
      <template v-if="openCompany">
        <table class="ra-table">
          <thead><tr><th>מוצר</th><th>שולם</th><th>לפי ההסכם</th><th>הפרש</th><th>שורות</th></tr></thead>
          <tbody>
            <tr v-for="p in openCompany.products" :key="p.product">
              <td>
                {{ p.product }}
                <span v-if="p.estimated" class="ra-tag ltr-number">{{ p.estimated }} ללא שיעור מדויק</span>
              </td>
              <td class="ra-num"><span class="ltr-number">{{ money(p.paid) }}</span></td>
              <td class="ra-num"><span class="ltr-number">{{ money(p.expected) }}</span></td>
              <td class="ra-num">
                <span class="ltr-number" :class="p.estimated ? '' : deltaClass(p.paid - p.expected)">
                  {{ signedMoney(p.paid - p.expected) }}
                </span>
              </td>
              <td class="ra-num"><span class="ltr-number">{{ p.records }}</span></td>
            </tr>
          </tbody>
        </table>
      </template>
    </DataModal>

    <DataModal :open="tableOpen" title="עמלות בפועל מול ההסכמים — כל הנתונים" @close="tableOpen = false">
      <table class="ra-table">
        <thead>
          <tr>
            <th>חברה</th><th>סך שולם</th><th>מתוכו להשוואה</th>
            <th>לפי ההסכם</th><th>הפרש</th><th>אחוז בפועל</th><th>אחוז בהסכם</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in companies" :key="c.company">
            <td>
              {{ c.company }}
              <span v-if="c.no_agreement" class="ra-tag">אין הסכם</span>
              <span v-else-if="!c.comparable" class="ra-tag">אין שיעור למוצרים</span>
              <span v-else-if="c.rows_estimated" class="ra-tag ltr-number">
                {{ c.rows_estimated }} ללא שיעור מדויק
              </span>
              <span v-if="!c.vat_verified && c.paid > 0" class="ra-tag" :title="c.vat_reason">
                מע"מ לא מאומת
              </span>
            </td>
            <td class="ra-num"><span class="ltr-number">{{ money(c.paid) }}</span></td>
            <!-- Same rows on both sides, or the pair invites a wrong read:
                 מור paid ₪18,738 overall but only ₪2,030 sits on rows with a
                 product-level rate, where the real gap is −0.6%. -->
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ money(c.paid_firm) }}</span><span v-else class="ra-dash">—</span></td>
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ money(c.expected_firm) }}</span><span v-else class="ra-dash">—</span></td>
            <td class="ra-num">
              <span v-if="c.comparable" class="ltr-number" :class="gapClass(c)">{{ signedMoney(c.gap) }}</span>
              <span v-else class="ra-dash">—</span>
            </td>
            <td class="ra-num"><span class="ltr-number">{{ pct(c.comparable ? c.implied_rate : c.implied_rate_all) }}</span></td>
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ pct(c.effective_agreed_rate) }}</span><span v-else class="ra-dash">—</span></td>
          </tr>
        </tbody>
      </table>
      <p class="ra-foot">
        ההשוואה נעשית רק על שורות שיש להן שיעור עמלה מפורש בהסכם. שיעור שנגזר מברירת מחדל
        או מחציון אינו טענה על חוב, ולכן אינו נכלל בהפרש.
      </p>
    </DataModal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../api/client'
import DataModal from './DataModal.vue'
import { money, signedMoney, pct, axisMoney, BASE_CHART } from '../../utils/chartDefaults'

// A gap is worth naming only past BOTH thresholds — insurers round, and a
// commission can straddle a month boundary. Mirrors the comparison engine.
const GAP_MIN_PCT = 10
const GAP_MIN_SHEKEL = 100

// Status colours, reserved: never reused as a categorical series hue.
const PAID = '#2F73C4'
const AGREED = '#9AA5B1'

const companies = ref([])
const period = ref(null)
const openCompany = ref(null)
const tableOpen = ref(false)

const comparable = computed(() => companies.value.filter(c => c.comparable))
const notComparable = computed(() => companies.value.filter(c => !c.comparable && c.paid > 0))
const chartHeight = computed(() => Math.max(200, comparable.value.length * 58 + 70))

const chartSeries = computed(() => [
  { name: 'שולם בפועל', data: comparable.value.map(c => c.paid_firm) },
  { name: 'לפי ההסכם', data: comparable.value.map(c => c.expected_firm) },
])

const chartOptions = computed(() => ({
  ...BASE_CHART,
  chart: {
    ...BASE_CHART.chart,
    type: 'bar',
    events: {
      dataPointSelection: (_e, _ctx, cfg) => {
        const c = comparable.value[cfg.dataPointIndex]
        if (c) openCompany.value = c
      },
    },
  },
  colors: [PAID, AGREED],
  plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '74%', columnWidth: '74%' } },
  // A 2px surface gap so the two bars never fuse into one block.
  stroke: { show: true, width: 2, colors: ['#fff'] },
  dataLabels: { enabled: false },
  legend: {
    show: true, position: 'top', horizontalAlign: 'right',
    fontFamily: 'Heebo, sans-serif', fontSize: '12px',
    markers: { width: 10, height: 10, radius: 3 },
    labels: { colors: '#706E6B' },
  },
  xaxis: {
    categories: comparable.value.map(c => c.company),
    labels: { formatter: axisMoney, style: { fontFamily: 'Heebo, sans-serif', colors: '#706E6B' } },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', colors: '#706E6B', fontSize: '13px' } } },
  tooltip: { ...BASE_CHART.tooltip, shared: true, intersect: false, y: { formatter: money } },
}))

function gapClass(c) {
  if (!c.comparable || c.gap_pct === null) return ''
  if (Math.abs(c.gap_pct) < GAP_MIN_PCT || Math.abs(c.gap) < GAP_MIN_SHEKEL) return ''
  return c.gap < 0 ? 'ra-neg' : 'ra-pos'
}
function deltaClass(d) { return d < 0 ? 'ra-neg' : 'ra-pos' }

const alerts = computed(() => {
  const out = []
  const noAgreement = companies.value.filter(c => c.no_agreement && c.paid > 0)
  for (const c of companies.value) {
    if (c.no_agreement || !c.comparable) continue
    if (Math.abs(c.gap_pct) >= GAP_MIN_PCT && Math.abs(c.gap) >= GAP_MIN_SHEKEL) {
      const dir = c.gap < 0 ? 'פחות' : 'יותר'
      // Name the product driving it — "Phoenix is 33% off" sends the agent
      // through 750 rows; naming the product does not.
      const worst = (c.products || [])
        .filter(p => p.estimated === 0 && p.expected > 0)
        .sort((a, b) => Math.abs(b.paid - b.expected) - Math.abs(a.paid - a.expected))[0]
      out.push({
        key: 'gap-' + c.company,
        level: c.gap < 0 ? 'warn' : 'info',
        text: `${c.company}: שולם ${money(Math.abs(c.gap))} ${dir} מהצפוי לפי ההסכם `
          + `(${c.gap_pct > 0 ? '+' : ''}${c.gap_pct}%)${worst ? ` בעיקר ב"${worst.product}"` : ''}.`,
      })
    }
  }
  if (noAgreement.length) {
    const total = noAgreement.reduce((s, c) => s + c.paid, 0)
    out.push({
      key: 'noagr', level: 'info',
      text: `${noAgreement.map(c => c.company).join(', ')}: התקבלו ${money(total)} `
        + `ואין הסכם עמלות במערכת — העלה את ההסכמים כדי שנוכל לבדוק אותם.`,
    })
  }
  return out
})

api.get('/production/rate-audit')
  .then((res) => { companies.value = res.data.companies || []; period.value = res.data.period })
  .catch(() => { companies.value = [] })
</script>

<style scoped>
.ra-card {
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 20px;
}
.ra-head { display: flex; align-items: baseline; gap: 10px; }
.ra-head h3 { font-size: 15px; font-weight: 700; color: var(--text); }
.ra-period { font-size: 12px; color: var(--text-muted); }
.ra-sub { font-size: 12px; color: var(--text-muted); margin: 4px 0 14px; }
.ra-hint { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.ra-none { font-size: 13px; color: var(--text-muted); padding: 10px 0; }

.ra-alerts { list-style: none; display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.ra-alert {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 9px 12px; border-radius: var(--radius-sm); font-size: 13px; line-height: 1.5;
}
.ra-alert svg { flex-shrink: 0; margin-top: 2px; }
.ra-alert--warn { background: var(--amber-light); color: var(--amber); }
.ra-alert--info { background: var(--primary-light); color: var(--primary); }

.ra-excluded { list-style: none; margin-top: 12px; display: flex; flex-direction: column; gap: 2px; }
.ra-excluded li {
  display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 10px;
  padding: 7px 8px; border-top: 1px solid var(--border-subtle);
}
.ra-ex-name { font-size: 13px; color: var(--text); }
.ra-ex-paid { font-size: 13px; font-weight: 600; color: var(--text); }

.ra-all {
  margin-top: 14px; padding: 6px 14px; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); background: none; color: var(--text-muted);
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.ra-all:hover { color: var(--text); }

.ra-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.ra-table th {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border-subtle);
}
.ra-table td {
  font-size: 13px; color: var(--text); padding: 9px 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.ra-table th:not(:first-child), .ra-table td.ra-num { text-align: center; width: 100px; }
.ra-tag {
  display: inline-block; margin-right: 6px; padding: 1px 7px; border-radius: 10px;
  background: var(--border-subtle); color: var(--text-muted); font-size: 10px; font-weight: 600;
}
.ra-neg { color: var(--chart-loss); font-weight: 700; }
.ra-pos { color: var(--chart-gain); font-weight: 700; }
.ra-dash { color: var(--text-muted); }
.ra-foot { font-size: 11px; color: var(--text-muted); margin-top: 12px; line-height: 1.6; }
</style>
