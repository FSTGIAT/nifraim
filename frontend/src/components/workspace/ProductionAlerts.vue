<template>
  <div v-if="hasAnything" class="pa-card">
    <div class="pa-head">
      <h3>התראות</h3>
      <span v-if="previousPeriod" class="pa-period ltr-number">מול {{ previousPeriod }}</span>
    </div>

    <!-- The headline is a count, not a plot: "how many clients went unpaid" is
         a single number, and a chart of one value is a chart for its own sake.
         The plot below answers the different question — which way did money
         move, and for whom. -->
    <div class="pa-tiles">
      <button class="pa-tile pa-tile--warn" :class="{ 'pa-tile--in': mounted }"
              @click="unpaidOpen = true" :disabled="!unpaidTotal">
        <span class="pa-tile-val ltr-number">{{ unpaidTotal }}</span>
        <span class="pa-tile-lbl">לקוחות ללא תשלום</span>
      </button>
      <div class="pa-tile" :class="{ 'pa-tile--in': mounted }">
        <span class="pa-tile-val ltr-number" :class="net < 0 ? 'pa-neg' : 'pa-pos'">
          {{ signedMoney(net) }}
        </span>
        <span class="pa-tile-lbl">שינוי נטו מול החודש הקודם</span>
      </div>
      <div class="pa-tile" :class="{ 'pa-tile--in': mounted }">
        <span class="pa-tile-val ltr-number">{{ coveredCompanies.length }}</span>
        <span class="pa-tile-lbl">חברות שנבדקו</span>
      </div>
    </div>

    <p v-if="uncheckable.length" class="pa-note">
      לא נבדקו: {{ uncheckable.join(', ') }} — לא התקבל מהן דוח נפרעים החודש, ולכן
      אי אפשר לדעת אם שולם בגין הלקוחות שלהן.
    </p>

    <!-- Diverging bars: the question is DIRECTION, so up and down get two hues
         around a zero line, never a rainbow. Rows are ordered by magnitude so
         the biggest movement in either direction sits nearest the axis label. -->
    <div class="pa-split">
      <section v-if="companyMovers.length">
        <h4>השינויים הגדולים לפי חברה</h4>
        <apexchart type="bar" :height="barHeight(companyMovers)"
                   :options="moverOptions(companyMovers, 'company')"
                   :series="moverSeries(companyMovers)" />
      </section>
      <section v-if="clientMovers.length">
        <h4>השינויים הגדולים לפי לקוח</h4>
        <apexchart type="bar" :height="barHeight(clientMovers)"
                   :options="moverOptions(clientMovers, 'name')"
                   :series="moverSeries(clientMovers)" />
      </section>
    </div>

    <DataModal :open="unpaidOpen" title="לקוחות שלא התקבל בגינם תשלום"
               :subtitle="`${unpaidTotal} לקוחות`" @close="unpaidOpen = false">
      <p class="pa-note">
        נבדק מול הדוחות שהתקבלו מ{{ coveredCompanies.join(', ') }}.
      </p>
      <table class="pa-table">
        <thead><tr><th>לקוח</th><th>חברה</th><th>מוצרים</th><th>פרמיה</th><th>צבירה</th></tr></thead>
        <tbody>
          <tr v-for="u in unpaid" :key="u.id_number">
            <td>{{ u.name || u.id_number }}</td>
            <td>{{ u.companies.join(', ') }}</td>
            <td class="pa-num"><span class="ltr-number">{{ u.products }}</span></td>
            <td class="pa-num"><span class="ltr-number">{{ money(u.premium) }}</span></td>
            <td class="pa-num"><span class="ltr-number">{{ money(u.accumulation) }}</span></td>
          </tr>
        </tbody>
      </table>
    </DataModal>

    <DataModal :open="!!moverDetail" :title="moverDetail ? moverDetail.label : ''"
               @close="moverDetail = null">
      <table v-if="moverDetail" class="pa-table">
        <thead><tr><th>חודש קודם</th><th>החודש</th><th>שינוי</th></tr></thead>
        <tbody>
          <tr>
            <td class="pa-num"><span class="ltr-number">{{ money(moverDetail.previous) }}</span></td>
            <td class="pa-num"><span class="ltr-number">{{ money(moverDetail.now) }}</span></td>
            <td class="pa-num">
              <span class="ltr-number" :class="moverDetail.delta < 0 ? 'pa-neg' : 'pa-pos'">
                {{ signedMoney(moverDetail.delta) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="moverDetail && moverDetail.reported === false" class="pa-note">
        לא התקבל דוח נפרעים מחברה זו החודש — הירידה משקפת הורדה שנכשלה, לא הפסקת תשלום.
      </p>
    </DataModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client'
import DataModal from './DataModal.vue'
import { money, signedMoney, axisMoney, BASE_CHART } from '../../utils/chartDefaults'

// Diverging pair + a neutral for "no report". Status hues, never categorical.
const UP = '#2E7D5B'
const DOWN = '#C23934'
const MISSING = '#9AA5B1'

const unpaid = ref([])
const unpaidTotal = ref(0)
const coveredCompanies = ref([])
const companyMovers = ref([])
const clientMovers = ref([])
const previousPeriod = ref(null)
const unpaidOpen = ref(false)
const moverDetail = ref(null)
const mounted = ref(false)

const hasAnything = computed(
  () => unpaidTotal.value || companyMovers.value.length || clientMovers.value.length,
)
const net = computed(() => companyMovers.value
  .filter(m => m.reported !== false)
  .reduce((s, m) => s + m.delta, 0))
// Named, not hidden: a company that sent no report is why the unpaid list is
// shorter than it looks.
const uncheckable = computed(
  () => companyMovers.value.filter(m => m.reported === false).map(m => m.company),
)

const barHeight = rows => Math.max(160, rows.length * 34 + 60)

function moverSeries(rows) {
  return [{ name: 'שינוי', data: rows.map(m => m.delta) }]
}

/** Indices of the three largest movements — the only bars that get text. */
function labelled(rows) {
  return new Set(
    rows.map((m, i) => [i, Math.abs(m.delta)])
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([i]) => i),
  )
}

function moverOptions(rows, labelKey) {
  return {
    ...BASE_CHART,
    chart: {
      ...BASE_CHART.chart,
      type: 'bar',
      // One orchestrated entrance: the bars grow out of the zero line once,
      // which is what makes the direction legible. No looping, no per-hover
      // re-animation, and the browser's reduced-motion setting turns it off.
      animations: {
        enabled: !prefersReducedMotion(),
        easing: 'easeout', speed: 700,
        animateGradually: { enabled: true, delay: 60 },
      },
      events: {
        dataPointSelection: (_e, _ctx, cfg) => {
          const m = rows[cfg.dataPointIndex]
          if (m) moverDetail.value = { ...m, label: m[labelKey] || m.company || m.name }
        },
      },
    },
    colors: [({ dataPointIndex }) => {
      const m = rows[dataPointIndex]
      if (m && m.reported === false) return MISSING
      return m && m.delta < 0 ? DOWN : UP
    }],
    plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '58%' } },
    // Selective labels, not one per bar. A single `offsetX` pushes every label
    // the same way, so on a diverging chart the negative bars' labels land on
    // top of the zero line; and small movers had their text clipped by the
    // axis. The three biggest movements carry text, the rest rely on bar
    // length plus the hover tooltip.
    dataLabels: {
      enabled: true,
      formatter: (v, o) => (labelled(rows).has(o.dataPointIndex) ? signedMoney(v) : ''),
      style: { fontSize: '11px', fontFamily: 'Heebo, sans-serif', colors: ['#3E3E3C'] },
      offsetX: 0,
      textAnchor: 'middle',
    },
    legend: { show: false },
    xaxis: {
      categories: rows.map(m => m[labelKey] || m.company || m.name || '—'),
      labels: { formatter: axisMoney, style: { fontFamily: 'Heebo, sans-serif', colors: '#706E6B' } },
    },
    yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', colors: '#706E6B', fontSize: '12px' } } },
    tooltip: {
      ...BASE_CHART.tooltip,
      y: {
        formatter: (v, o) => {
          const m = rows[o.dataPointIndex]
          if (m && m.reported === false) return `${signedMoney(v)} — לא התקבל דוח החודש`
          return `${money(m.previous)} ← ${money(m.now)}  (${signedMoney(v)})`
        },
      },
    },
  }
}

function prefersReducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch (_) {
    return false
  }
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
    /* panel stays hidden */
  } finally {
    requestAnimationFrame(() => { mounted.value = true })
  }
})
</script>

<style scoped>
.pa-card {
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 20px;
}
.pa-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 16px; }
.pa-head h3 { font-size: 15px; font-weight: 700; color: var(--text); }
.pa-period { font-size: 12px; color: var(--text-muted); }

.pa-tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
@media (max-width: 700px) { .pa-tiles { grid-template-columns: 1fr; } }
.pa-tile {
  display: flex; flex-direction: column; gap: 3px; align-items: flex-start;
  padding: 14px 16px; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); background: none; font-family: inherit;
  text-align: right;
  opacity: 0; transform: translateY(6px);
  transition: opacity 0.45s ease, transform 0.45s cubic-bezier(0.2, 0, 0.2, 1);
}
.pa-tile:nth-child(2) { transition-delay: 0.07s; }
.pa-tile:nth-child(3) { transition-delay: 0.14s; }
.pa-tile--in { opacity: 1; transform: none; }
button.pa-tile { cursor: pointer; }
button.pa-tile:disabled { cursor: default; }
button.pa-tile:not(:disabled):hover { border-color: var(--text-muted); }
.pa-tile--warn .pa-tile-val { color: var(--amber); }
.pa-tile-val { font-size: 22px; font-weight: 700; color: var(--text); }
.pa-tile-lbl { font-size: 12px; color: var(--text-muted); }

.pa-note { font-size: 11px; color: var(--text-muted); margin-top: 12px; line-height: 1.6; }

.pa-split { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 18px; }
@media (max-width: 900px) { .pa-split { grid-template-columns: 1fr; } }
.pa-split h4 { font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 4px; }

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
.pa-neg { color: var(--red, #c23934); }
.pa-pos { color: var(--accent-emerald); }

@media (prefers-reduced-motion: reduce) {
  .pa-tile { transition: none; opacity: 1; transform: none; }
}
</style>
