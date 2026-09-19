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
      <!-- Clickable, because the number alone read as a contradiction: "3
           חברות שנבדקו" sat beside a movers chart showing four companies. The
           fourth is one that reported LAST month and not this one. -->
      <button class="pa-tile" :class="{ 'pa-tile--in': mounted }"
              @click="checkedOpen = true" :disabled="!checkedCompanies.length">
        <span class="pa-tile-val ltr-number">
          {{ coveredCompanies.length }}<span v-if="missingCount" class="pa-tile-of">
            / {{ checkedCompanies.length }}</span>
        </span>
        <span class="pa-tile-lbl">
          {{ missingCount ? 'חברות שדיווחו החודש' : 'חברות שנבדקו' }}
        </span>
      </button>
    </div>

    <p v-if="uncheckable.length" class="pa-note">
      לא נבדקו: {{ uncheckable.join(', ') }} — לא התקבל מהן דוח נפרעים החודש, ולכן
      אי אפשר לדעת אם שולם בגין הלקוחות שלהן.
    </p>

    <!-- Rows without money look exactly like a successful download: the file
         exists, the count even goes UP. Live (2026-09-15) הראל landed 1,729
         rows carrying ₪0 because the leg that owns the money returned nothing,
         and the run reported success. -->
    <p v-if="noValueCompanies.length" class="pa-note pa-note--warn">
      הפרודוקציה של {{ noValueCompanies.map(c => c.company).join(', ') }} הגיעה ללא
      נתונים כספיים — יש שורות אבל אין בהן פרמיה ולא צבירה, כך שלא ניתן לחשב מולן
      עמלה צפויה. בדוק את ההורדה האוטומטית של החברה.
    </p>

    <!-- Diverging bars: the question is DIRECTION, so up and down get two hues
         around a zero line, never a rainbow. Rows are ordered by magnitude so
         the biggest movement in either direction sits nearest the axis label. -->
    <!-- Diverging rows rather than a plotted bar chart.
         The encoding is the same — length is magnitude, side is direction —
         but each part gets its own column: the name reads on one line, the
         bars share a zero axis, and the amounts align in a single column
         instead of being stacked under the names in 10px axis text. -->
    <div class="pa-split">
      <section v-if="companyMovers.length">
        <h4>השינויים הגדולים לפי חברה</h4>
        <MoverRows :rows="companyMovers" label-key="company" @pick="moverDetail = $event" />
      </section>
      <section v-if="clientMovers.length">
        <h4>השינויים הגדולים לפי לקוח</h4>
        <MoverRows :rows="clientMovers" label-key="name" @pick="moverDetail = $event" />
      </section>
    </div>

    <DataModal :open="checkedOpen" title="אילו חברות נבדקו החודש" @close="checkedOpen = false">
      <p class="pa-note">
        בדיקת "לקוחות ללא תשלום" יכולה לרוץ רק על חברה ששלחה דוח נפרעים החודש.
        חברה שלא שלחה — לא ידוע אם שילמה, ולכן הלקוחות שלה אינם ברשימה.
      </p>
      <table class="pa-table">
        <thead><tr><th>חברה</th><th>סטטוס</th><th>עמלות החודש</th></tr></thead>
        <tbody>
          <tr v-for="c in checkedCompanies" :key="c.company">
            <td>{{ c.company }}</td>
            <td>
              <span class="pa-badge2" :class="c.reported ? 'pa-badge2--ok' : 'pa-badge2--miss'">
                {{ c.reported ? 'התקבל דוח' : 'לא התקבל דוח' }}
              </span>
            </td>
            <td class="pa-num"><span class="ltr-number">{{ money(c.commission) }}</span></td>
          </tr>
        </tbody>
      </table>
    </DataModal>

    <DataModal :open="unpaidOpen" title="לקוחות שלא התקבל בגינם תשלום"
               :subtitle="`${unpaidTotal} לקוחות`" @close="unpaidOpen = false">
      <p class="pa-note">
        נבדק מול הדוחות שהתקבלו מ{{ coveredCompanies.join(', ') }}.
      </p>
      <p class="pa-note">
        לחיצה על לקוח פותחת את המוצרים שלא שולמה עליהם עמלה — שם המוצר, מספר
        הפוליסה והחברה, כדי שאפשר יהיה לפנות לחברה עם פרטים.
      </p>
      <table class="pa-table pa-table--rows">
        <thead><tr><th></th><th>לקוח</th><th>ת.ז</th><th>חברה</th><th>מוצרים</th><th>פרמיה</th><th>צבירה</th></tr></thead>
        <tbody>
          <template v-for="u in unpaid" :key="u.id_number">
            <tr class="pa-row" :class="{ 'pa-row--open': openClient === u.id_number }"
                @click="toggleClient(u)">
              <td class="pa-caret">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
              </td>
              <td :title="u.name || u.id_number">{{ u.name || u.id_number }}</td>
              <td class="pa-num"><span class="ltr-number">{{ u.id_number }}</span></td>
              <td>{{ u.companies.join(', ') }}</td>
              <td class="pa-num"><span class="ltr-number">{{ u.products }}</span></td>
              <td class="pa-num"><span class="ltr-number">{{ money(u.premium) }}</span></td>
              <td class="pa-num"><span class="ltr-number">{{ money(u.accumulation) }}</span></td>
            </tr>
            <tr v-if="openClient === u.id_number" class="pa-sub">
              <td colspan="7">
                <table class="pa-table pa-subtable">
                  <thead><tr><th>מוצר</th><th>מספר פוליסה</th><th>חברה</th><th>פרמיה</th><th>צבירה</th></tr></thead>
                  <tbody>
                    <tr v-for="(it, i) in (u.items || [])" :key="i">
                      <td :title="it.product || it.product_type">{{ it.product || it.product_type || '—' }}</td>
                      <td class="pa-num"><span class="ltr-number">{{ it.policy_number || '—' }}</span></td>
                      <td>{{ it.company }}</td>
                      <td class="pa-num"><span class="ltr-number">{{ money(it.premium) }}</span></td>
                      <td class="pa-num"><span class="ltr-number">{{ money(it.accumulation) }}</span></td>
                    </tr>
                    <tr v-if="!(u.items || []).length">
                      <td colspan="5" class="pa-empty">אין פירוט מוצרים לרשומה הזו</td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </DataModal>

    <DataModal :open="!!moverDetail" size="sm"
               :title="moverDetail ? moverDetail.label : ''" @close="moverDetail = null">
      <MoverDetail :mover="moverDetail" />
    </DataModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client'
import DataModal from './DataModal.vue'
import MoverRows from './MoverRows.vue'
import MoverDetail from './MoverDetail.vue'
import { money, signedMoney } from '../../utils/chartDefaults'

const unpaid = ref([])
const unpaidTotal = ref(0)
const coveredCompanies = ref([])
const companyMovers = ref([])
const clientMovers = ref([])
const previousPeriod = ref(null)
const unpaidOpen = ref(false)
const checkedOpen = ref(false)
const checkedCompanies = ref([])
const noValueCompanies = ref([])
// Which unpaid client's policy list is open. One at a time.
const openClient = ref(null)
const moverDetail = ref(null)
const mounted = ref(false)

const hasAnything = computed(
  () => unpaidTotal.value || companyMovers.value.length || clientMovers.value.length
    || noValueCompanies.value.length,
)
const net = computed(() => companyMovers.value
  .filter(m => m.reported !== false)
  .reduce((s, m) => s + m.delta, 0))
// Named, not hidden: a company that sent no report is why the unpaid list is
// shorter than it looks.
const missingCount = computed(
  () => checkedCompanies.value.filter(c => !c.reported).length,
)
const uncheckable = computed(
  () => companyMovers.value.filter(m => m.reported === false).map(m => m.company),
)

function toggleClient(u) {
  openClient.value = openClient.value === u.id_number ? null : u.id_number
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
    checkedCompanies.value = res.data.checked_companies || []
    noValueCompanies.value = res.data.no_value_companies || []
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
.pa-tile-of { font-size: 15px; font-weight: 600; color: var(--text-muted); }
.pa-badge2 {
  display: inline-block; padding: 2px 9px; border-radius: 10px;
  font-size: 11px; font-weight: 600;
}
.pa-badge2--ok { background: var(--green-light, #E8F5EC); color: var(--accent-emerald); }
.pa-badge2--miss { background: var(--border-subtle); color: var(--text-muted); }

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
.pa-neg { color: var(--chart-loss); }
.pa-pos { color: var(--chart-gain); }

.pa-note--warn { color: var(--amber); }

/* The unpaid table grew a caret column in front, so the shared
   `th:not(:first-child)` 100px rule would squeeze the client name down to the
   numeric width. Widths are explicit here instead — the name and the product
   are the two columns worth reading in full. */
.pa-table--rows th:nth-child(1) { width: 30px; }
.pa-table--rows th:nth-child(2) { width: auto; text-align: right; }
.pa-table--rows th:nth-child(3) { width: 96px; }
.pa-table--rows th:nth-child(4) { width: 130px; text-align: right; }
.pa-table--rows th:nth-child(5) { width: 74px; }
.pa-table--rows th:nth-child(6),
.pa-table--rows th:nth-child(7) { width: 96px; }
.pa-row { cursor: pointer; }
.pa-row:hover { background: var(--glass-hover); }
.pa-caret { width: 30px; color: var(--text-muted); }
/* RTL: the row opens downward, so the chevron turns down, not sideways. */
.pa-caret svg { transition: transform 0.18s ease; }
.pa-row--open .pa-caret svg { transform: rotate(-90deg); }
.pa-sub > td { padding: 0 0 10px 0; background: var(--bg); }
/* auto layout, not the parent's `fixed`: a product name is the longest string
   in the drill-down and the one the agent quotes to the insurer, so it gets the
   slack rather than an ellipsis at 40px. */
.pa-subtable { margin: 0; table-layout: auto; }
.pa-subtable th { font-size: 10px; }
.pa-subtable td { font-size: 12px; }
.pa-subtable th:nth-child(1) { width: auto; text-align: right; }
.pa-subtable th:nth-child(2) { width: 120px; }
.pa-subtable th:nth-child(3) { width: 110px; text-align: right; }
.pa-subtable th:nth-child(4),
.pa-subtable th:nth-child(5) { width: 96px; }
.pa-subtable td:first-child { white-space: normal; }
.pa-empty { color: var(--text-muted); text-align: center; }

@media (prefers-reduced-motion: reduce) {
  .pa-caret svg { transition: none; }
}

@media (prefers-reduced-motion: reduce) {
  .pa-tile { transition: none; opacity: 1; transform: none; }
}
</style>
