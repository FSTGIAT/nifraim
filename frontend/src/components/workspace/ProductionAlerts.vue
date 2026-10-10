<template>
  <!-- The unpaid / not-reported counts moved up to the "דורש טיפול" band
       (ProductionActions), which opens this component's drills through
       `defineExpose`. What stays here is the month-over-month story, so the
       card is named for it instead of the generic "התראות" (QA 2026-09-30). -->
  <div class="pa-root">
  <!-- Month over month — redesigned (QA 2026-10-01): diverging green/red bars
       read as alarm and the numbers were not comparable (the previous month
       was ONE file, so a company missing from it "grew" by everything). Now:
       whole months on both sides, only companies that reported in both, one
       colour, arrows instead of colour, risers and fallers apart. -->
  <div v-if="comparableCos.length || otherCos.length" class="pa-card mm">
    <header class="mm-head">
      <h3>שינויים מול החודש הקודם</h3>
      <span v-if="previousPeriod" class="mm-period ltr-number">{{ previousPeriod }} ← {{ currentPeriod }}</span>
    </header>

    <!-- Nothing to compare: no insurer reported in BOTH months. Say that in
         one sentence instead of a strip of dashes and ₪0 (QA 2026-10-01). -->
    <p v-if="!comparableCos.length" class="mm-none">
      אין חברה ששלחה דוח נפרעים גם ב-<span class="ltr-number">{{ previousPeriod }}</span>
      וגם ב-<span class="ltr-number">{{ currentPeriod }}</span>, ולכן אין מה להשוות.
      ההשוואה תופיע כשאותה חברה תשלח דוח בשני חודשים.
    </p>

    <div v-if="comparableCos.length" class="mm-stats">
      <div class="mm-stat">
        <span class="mm-lbl">בחודש הקודם</span>
        <span class="mm-val ltr-number">{{ money(totPrev) }}</span>
      </div>
      <div class="mm-stat">
        <span class="mm-lbl">החודש</span>
        <span class="mm-val ltr-number">{{ money(totNow) }}</span>
      </div>
      <div class="mm-stat">
        <span class="mm-lbl">שינוי</span>
        <span class="mm-val mm-delta">
          <span class="mm-arrow" aria-hidden="true">{{ net > 0 ? '▲' : net < 0 ? '▼' : '' }}</span>
          <span class="ltr-number">{{ signedMoney(net) }}</span>
          <small v-if="totPrev" class="ltr-number">{{ pctChange(totNow, totPrev) }}</small>
        </span>
      </div>
    </div>
    <p v-if="comparableCos.length" class="mm-note">
      השוואה של חברות ששלחו דוח נפרעים בשני החודשים<template v-if="otherCos.length"> · שאר החברות מופיעות למטה</template>.
      בחר שורה לפירוט.
    </p>

    <section v-if="comparableCos.length" class="mm-sec">
      <h4>לפי חברה</h4>
      <ul class="mm-cos">
        <li v-for="m in comparableCos" :key="m.company">
          <button class="mm-co" @click="moverDetail = { ...m, label: m.company }">
            <span class="mm-co-name">{{ m.company }}</span>
            <span class="mm-bars" aria-hidden="true">
              <i class="mm-bar mm-bar--prev" :style="{ width: barW(m.previous) }"></i>
              <i class="mm-bar mm-bar--now" :style="{ width: barW(m.now) }"></i>
            </span>
            <span class="mm-co-vals">
              <small class="ltr-number">{{ money(m.previous) }} ← {{ money(m.now) }}</small>
              <strong class="ltr-number">
                <span class="mm-arrow" aria-hidden="true">{{ m.delta > 0 ? '▲' : '▼' }}</span>{{ signedMoney(m.delta) }}
              </strong>
            </span>
            <span class="mm-pct ltr-number">{{ m.delta_pct != null ? (m.delta_pct > 0 ? '+' : '') + m.delta_pct + '%' : '' }}</span>
          </button>
        </li>
      </ul>
    </section>

    <!-- Always listed, with the reason — including when nothing compares. -->
    <section v-if="otherCos.length" class="mm-sec">
      <h4>{{ comparableCos.length ? 'לא נכללו בהשוואה' : 'החברות בכל חודש' }}</h4>
      <ul class="mm-other-list">
        <li v-for="m in otherCos" :key="m.company">
          <span class="mm-o-name">{{ m.company }}</span>
          <span class="mm-o-why">
            {{ m.reported === false
              ? `דוח רק ב-${previousPeriod}`
              : `דוח רק ב-${currentPeriod}` }}
          </span>
          <span v-if="(m.reported === false ? m.previous : m.now) > 0" class="mm-o-amt ltr-number">
            {{ money(m.reported === false ? m.previous : m.now) }}
          </span>
        </li>
      </ul>
    </section>

    <!-- By client: a diverging chart around a zero line — risers on one side
         (solid), fallers on the other (light), same blue; bars grow out from
         the centre when the card scrolls into view (QA 2026-10-01). -->
    <section v-if="clientChart.length" ref="clientSec" class="mm-sec">
      <h4>לפי לקוח</h4>
      <div class="dv-legend">
        <span><i class="dv-key dv-key--up"></i>עלו <span class="ltr-number">{{ risers.length }}</span></span>
        <span><i class="dv-key dv-key--down"></i>ירדו <span class="ltr-number">{{ fallers.length }}</span></span>
      </div>
      <ul class="dv" :class="{ 'dv--in': clientsIn }">
        <li v-for="(m, i) in clientChart" :key="m.id_number" :style="{ '--i': i }">
          <button class="dv-row" @click="moverDetail = { ...m, label: m.name || m.id_number }">
            <span class="dv-name">{{ m.name || m.id_number }}</span>
            <span class="dv-track">
              <span class="dv-half dv-half--down">
                <i v-if="m.delta < 0" class="dv-bar dv-bar--down" :style="{ '--w': dvW(m.delta) }"></i>
              </span>
              <span class="dv-zero" aria-hidden="true"></span>
              <span class="dv-half dv-half--up">
                <i v-if="m.delta > 0" class="dv-bar dv-bar--up" :style="{ '--w': dvW(m.delta) }"></i>
              </span>
            </span>
            <span class="dv-val ltr-number" :class="m.delta < 0 ? 'dv-val--down' : ''">{{ signedMoney(m.delta) }}</span>
          </button>
        </li>
      </ul>
    </section>
  </div>

    <DataModal :open="checkedOpen" :origin="drillOrigin" title="אילו חברות נבדקו החודש" @close="checkedOpen = false">
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

    <DataModal :open="unpaidOpen" :origin="drillOrigin" :title="unpaidTitle"
               @close="unpaidOpen = false">
      <UnpaidClientsDrill :rows="unpaidShown" :covered="coveredCompanies" :mode="unpaidFilter" />
    </DataModal>

    <DataModal :open="!!moverDetail" size="sm"
               :title="moverDetail ? moverDetail.label : ''" @close="moverDetail = null">
      <MoverDetail :mover="moverDetail" />
    </DataModal>
  </div>

</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { cachedGet } from '../../utils/cachedGet'
import DataModal from './DataModal.vue'
import MoverRows from './MoverRows.vue'
import MoverDetail from './MoverDetail.vue'
import UnpaidClientsDrill from './UnpaidClientsDrill.vue'
import { money, signedMoney } from '../../utils/chartDefaults'

const unpaid = ref([])
const unpaidTotal = ref(0)
const coveredCompanies = ref([])
const companyMovers = ref([])
const clientMovers = ref([])
const previousPeriod = ref(null)
const unpaidOpen = ref(false)
// Which list the band row asked for: 'full' (nothing paid) · 'partial' · null (all).
const unpaidFilter = ref(null)
const unpaidShown = computed(() =>
  unpaidFilter.value === 'full' ? unpaid.value.filter(u => !u.partially_paid)
    : unpaidFilter.value === 'partial' ? unpaid.value.filter(u => u.partially_paid)
      : unpaid.value)
const unpaidTitle = computed(() =>
  unpaidFilter.value === 'full' ? 'לא שולם — לא התקבלה עמלה על אף מוצר'
    : unpaidFilter.value === 'partial' ? 'שולם חלקית — התקבלה עמלה על חלק מהמוצרים'
      : 'לקוחות שלא התקבל בגינם תשלום')
const checkedOpen = ref(false)
const checkedCompanies = ref([])
const noValueCompanies = ref([])
// Which unpaid client's policy list is open. One at a time.
const openClient = ref(null)
const moverDetail = ref(null)
const mounted = ref(false)

// Only companies that reported in BOTH months are a change (backend flag;
// older payloads without it fall back to "reported this month").
const isComparable = m => (m.comparable ?? (m.reported !== false))
const comparableCos = computed(() => companyMovers.value.filter(isComparable))
const otherCos = computed(() => companyMovers.value.filter(m => !isComparable(m)))
const net = computed(() => comparableCos.value.reduce((s, m) => s + m.delta, 0))
const totNow = computed(() => comparableCos.value.reduce((s, m) => s + (m.now || 0), 0))
const totPrev = computed(() => comparableCos.value.reduce((s, m) => s + (m.previous || 0), 0))
const barMax = computed(() => Math.max(1, ...comparableCos.value.flatMap(m => [m.now || 0, m.previous || 0])))
const barW = v => Math.max(1.5, ((Number(v) || 0) / barMax.value) * 100) + '%'
const risers = computed(() => clientMovers.value.filter(m => m.delta > 0)
  .sort((a, b) => b.delta - a.delta).slice(0, 6))
const fallers = computed(() => clientMovers.value.filter(m => m.delta < 0)
  .sort((a, b) => a.delta - b.delta).slice(0, 6))
// Risers (largest first) then fallers (largest drop first), one scale.
const clientChart = computed(() => [...risers.value, ...fallers.value])
const dvMax = computed(() => Math.max(1, ...clientChart.value.map(m => Math.abs(m.delta))))
const dvW = d => Math.max(4, (Math.abs(d) / dvMax.value) * 100) + '%'
// Grow the bars when the section scrolls into view (once).
const clientSec = ref(null)
const clientsIn = ref(false)
let dvIO = null
watch(clientSec, (el) => {
  dvIO?.disconnect()
  if (!el) return
  if (typeof IntersectionObserver === 'undefined') { clientsIn.value = true; return }
  dvIO = new IntersectionObserver(([e]) => {
    if (e.isIntersecting) { clientsIn.value = true; dvIO.disconnect() }
  }, { threshold: 0.2 })
  dvIO.observe(el)
})
onBeforeUnmount(() => dvIO?.disconnect())
const currentPeriod = ref(null)
function pctChange(now, prev) {
  if (!prev) return ''
  const v = ((now - prev) / prev) * 100
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}%`
}
// Named, not hidden: a company that sent no report is why the unpaid list is
// shorter than it looks.
const missingCount = computed(
  () => checkedCompanies.value.filter(c => !c.reported).length,
)
const uncheckable = computed(
  () => companyMovers.value.filter(m => m.reported === false).map(m => m.company),
)

// The tile that was pressed — the drill grows out of it (DataModal `origin`).
const drillOrigin = ref(null)
function openFrom(e, which) {
  drillOrigin.value = e?.currentTarget || null
  if (which === 'unpaid') unpaidOpen.value = true
  else checkedOpen.value = true
}
// Opened from the "דורש טיפול" band, growing out of the row pressed there.
defineExpose({
  openUnpaid: (el, filter = null) => { unpaidFilter.value = filter; openFrom({ currentTarget: el }, 'unpaid') },
  openChecked: (el) => openFrom({ currentTarget: el }, 'checked'),
})

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
    const res = await cachedGet('/production/alerts')
    unpaid.value = res.data.unpaid || []
    unpaidTotal.value = res.data.unpaid_total || 0
    coveredCompanies.value = res.data.covered_companies || []
    checkedCompanies.value = res.data.checked_companies || []
    noValueCompanies.value = res.data.no_value_companies || []
    companyMovers.value = res.data.company_movers || []
    clientMovers.value = res.data.client_movers || []
    previousPeriod.value = res.data.previous_period
    currentPeriod.value = res.data.current_period
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

.pa-cuts { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.pa-cut-row { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.pa-cut-lbl { font-size: 11px; font-weight: 600; color: var(--text-muted); min-width: 56px; }
.pa-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 11px; border-radius: 999px; border: 1px solid var(--border-subtle);
  background: var(--card-bg); color: var(--text); font: inherit; font-size: 12px;
  cursor: pointer; transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.pa-chip .ltr-number { font-size: 11px; color: var(--text-muted); }
.pa-chip:hover { border-color: var(--tab-production); }
.pa-chip--on { background: var(--tab-production); border-color: var(--tab-production); color: #fff; }
.pa-chip--on .ltr-number { color: rgba(255, 255, 255, 0.85); }
.pa-chip:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
.pa-cut-row--tools { justify-content: space-between; gap: 12px; }
.pa-search {
  flex: 0 1 240px; padding: 6px 10px; border: 1px solid var(--border-subtle);
  border-radius: 10px; background: var(--bg); font: inherit; font-size: 12px; color: var(--text);
}
.pa-search:focus { outline: none; border-color: var(--tab-production); }
.pa-cut-sum { font-size: 12px; color: var(--text-secondary, var(--text-muted)); }
.pa-sortable { cursor: pointer; user-select: none; }
.pa-sortable:hover { color: var(--text); }
.pa-sorted { color: var(--tab-production) !important; }

@media (prefers-reduced-motion: reduce) {
  .pa-caret svg { transition: none; }
}

@media (prefers-reduced-motion: reduce) {
  .pa-tile { transition: none; opacity: 1; transform: none; }
}
.pa-net { margin-inline-start: auto; font-size: 12px; color: var(--text-muted); display: inline-flex; gap: 6px; align-items: baseline; }
.pa-net .ltr-number { font-size: 15px; font-weight: 700; }
.pa-lead { font-size: 12px; color: var(--text-muted); margin: -8px 0 4px; }
/* ── month over month (redesign) ── */
.mm { display: flex; flex-direction: column; gap: 14px; }
.mm-head { display: flex; align-items: baseline; gap: 10px; }
.mm-head h3 { font-size: 16px; font-weight: 700; color: var(--text); }
.mm-period { font-size: 12px; color: var(--text-muted); padding: 2px 9px; border-radius: 8px; background: var(--bg); }
.mm-stats { display: grid; grid-template-columns: 1fr 1fr 1.2fr; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.mm-stat { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 14px 18px; }
.mm-stat + .mm-stat { border-inline-start: 1px solid var(--border-subtle); }
.mm-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.mm-val { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.mm-delta { display: flex; align-items: baseline; gap: 6px; color: var(--tab-production); }
.mm-delta small { font-size: 13px; font-weight: 600; color: var(--text-muted); }
.mm-arrow { font-size: 0.7em; margin-inline-end: 3px; }
.mm-note { font-size: 12px; color: var(--text-muted); margin: -4px 0 0; }
.mm-sec { display: flex; flex-direction: column; gap: 8px; }
.mm-sec h4 { font-size: 13px; font-weight: 700; color: var(--text); }
.mm-cos { list-style: none; display: flex; flex-direction: column; }
.mm-co {
  width: 100%; display: grid; align-items: center; gap: 14px;
  grid-template-columns: minmax(80px, 140px) minmax(80px, 1fr) 170px 60px;
  padding: 10px 6px; border: none; border-bottom: 1px solid var(--border-subtle); background: none;
  font: inherit; color: var(--text); text-align: right; cursor: pointer; border-radius: 8px;
}
.mm-cos li:last-child .mm-co { border-bottom: none; }
.mm-co:hover { background: var(--bg); }
.mm-co:focus-visible { outline: 2px solid var(--tab-production); outline-offset: -2px; }
.mm-co-name { font-size: 14px; font-weight: 600; }
.mm-bars { display: flex; flex-direction: column; gap: 3px; }
.mm-bar { display: block; height: 7px; border-radius: 4px; }
.mm-bar--prev { background: color-mix(in srgb, var(--tab-production) 28%, var(--card-bg)); }
.mm-bar--now { background: var(--tab-production); }
.mm-co-vals { display: flex; flex-direction: column; align-items: flex-start; }
.mm-co-vals small { font-size: 11.5px; color: var(--text-muted); }
.mm-co-vals strong { font-size: 15px; font-weight: 800; color: var(--text); }
.mm-pct { font-size: 12.5px; font-weight: 600; color: var(--text-muted); }
.mm-others { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 12px; color: var(--text-muted); margin: 2px 6px 0; }
.mm-other strong { color: var(--text); font-weight: 600; margin-inline-end: 4px; }
.mm-clients { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.mm-col { display: flex; flex-direction: column; gap: 2px; }
.mm-col-title { font-size: 12.5px; font-weight: 700; color: var(--text-muted); padding: 0 6px 6px; border-bottom: 1px solid var(--border-subtle); }
.mm-col-title .ltr-number { font-weight: 500; margin-inline-start: 4px; }
.mm-empty { font-size: 12px; color: var(--text-muted); padding: 8px 6px; margin: 0; }
.mm-client {
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
  padding: 8px 6px; border: none; background: none; font: inherit; color: var(--text); cursor: pointer; border-radius: 8px; text-align: right;
}
.mm-client:hover { background: var(--bg); }
.mm-cl-name { font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mm-cl-delta { font-size: 13.5px; font-weight: 700; }
@media (max-width: 700px) {
  .mm-stats { grid-template-columns: 1fr 1fr; }
  .mm-stat:last-child { grid-column: 1 / -1; border-inline-start: none; border-top: 1px solid var(--border-subtle); }
  .mm-co { grid-template-columns: minmax(0, 1fr) 130px 50px; }
  .mm-bars { display: none; }
  .mm-clients { grid-template-columns: 1fr; }
}
/* ── by-client diverging chart ── */
.dv-legend { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); }
.dv-legend .ltr-number { margin-inline-start: 3px; }
.dv-key { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-inline-end: 6px; vertical-align: -1px; }
.dv-key--up, .dv-bar--up { background: var(--tab-production); }
.dv-key--down, .dv-bar--down { background: color-mix(in srgb, var(--tab-production) 32%, var(--card-bg)); }
.dv { list-style: none; display: flex; flex-direction: column; }
.dv-row {
  width: 100%; display: grid; align-items: center; gap: 12px;
  grid-template-columns: minmax(90px, 180px) minmax(120px, 1fr) 90px;
  padding: 6px 6px; border: none; background: none; font: inherit; color: var(--text);
  text-align: right; cursor: pointer; border-radius: 8px;
}
.dv-row:hover { background: var(--bg); }
.dv-row:focus-visible { outline: 2px solid var(--tab-production); outline-offset: -2px; }
.dv-name { font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dv-track { display: grid; grid-template-columns: 1fr 2px 1fr; align-items: center; height: 18px; }
.dv-zero { height: 26px; background: var(--border-subtle); }
.dv-half { display: flex; height: 12px; }
/* RTL: the "up" half is on the inline-END side of the zero line, the "down"
   half on the inline-start side; each bar grows out FROM the zero line. */
.dv-half--up { justify-content: flex-start; }
.dv-half--down { justify-content: flex-end; }
.dv-bar {
  display: block; height: 100%; border-radius: 4px; width: 0;
  transition: width 0.7s cubic-bezier(0.32, 0.72, 0, 1);
  transition-delay: calc(var(--i, 0) * 70ms);
}
.dv li { --i: 0; }
.dv--in .dv-bar { width: var(--w); }
.dv-val { font-size: 13.5px; font-weight: 700; text-align: left; }
.dv-val--down { color: var(--text-muted); }
@media (max-width: 700px) { .dv-row { grid-template-columns: minmax(0, 1fr) minmax(90px, 1.2fr) 74px; } }
@media (prefers-reduced-motion: reduce) { .dv-bar { transition: none; } }
.mm-none {
  margin: 0; padding: 14px 16px; border-radius: 12px; background: var(--bg);
  font-size: 13.5px; line-height: 1.7; color: var(--text);
}
.mm-other-list { list-style: none; display: flex; flex-direction: column; }
.mm-other-list li {
  display: grid; grid-template-columns: minmax(80px, 160px) 1fr auto; align-items: center; gap: 12px;
  padding: 9px 6px; border-bottom: 1px solid var(--border-subtle);
}
.mm-other-list li:last-child { border-bottom: none; }
.mm-o-name { font-size: 14px; font-weight: 600; color: var(--text); }
.mm-o-why { font-size: 12.5px; color: var(--text-muted); }
.mm-o-amt { font-size: 13.5px; font-weight: 700; color: var(--text); }
</style>
