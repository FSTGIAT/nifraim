<template>
  <!-- One company's products: paid vs the agreement. Redesigned (QA
       2026-09-30): an 8-column table mixed the products that CAN be checked
       with ≈ estimates that cannot, and its "לפי ההסכם" total added a ₪107K
       estimate for pension that is no claim at all. Now: the strip states only
       what was checked, each checked product is a card whose one bar says
       "paid this much of what the agreement says", and the estimates fold away
       with the reason. One colour; red/green only on a real gap. -->
  <div class="pr">
    <!-- מגיע leads: "how much should I have got" is the number the agent
         acts on (QA 2026-09-30). Then what arrived, then the difference. -->
    <div v-if="checked.length" class="pr-stats">
      <div class="pr-stat pr-stat--lead">
        <span class="pr-stat-lbl">מגיע לפי ההסכם</span>
        <span class="pr-stat-val ltr-number">{{ money(checkedTotals.expected) }}</span>
      </div>
      <div class="pr-stat">
        <span class="pr-stat-lbl">התקבל</span>
        <span class="pr-stat-val ltr-number">{{ money(checkedTotals.paid) }}</span>
      </div>
      <div class="pr-stat">
        <span class="pr-stat-lbl">הפרש</span>
        <span class="pr-stat-val ltr-number" :class="gapTone(checkedTotals.paid, checkedTotals.expected)">
          {{ signedMoney(checkedTotals.paid - checkedTotals.expected) }}
        </span>
      </div>
    </div>
    <p class="pr-total-note">
      סה״כ שולם מהחברה <strong class="ltr-number">{{ money(totals.paid) }}</strong>
      <template v-if="unchecked.length && checked.length">
        — כולל <span class="ltr-number">{{ money(uncheckedPaid) }}</span> על מוצרים שלא ניתן לבדוק מול ההסכם
      </template>
    </p>

    <!-- Checked against the agreement -->
    <section v-if="checked.length" class="pr-sec">
      <h5 class="pr-sec-title">נבדקו מול ההסכם <span class="ltr-number">{{ checked.length }}</span></h5>
      <ul class="pr-list">
        <li v-for="(p, i) in checked" :key="p.product" class="pr-card" :style="{ '--d': i * 40 + 'ms' }">
          <!-- Three figures in fixed columns, the same order as the summary,
               so they line up card to card. No bar: a track with a tick had to
               be decoded; three labelled numbers do not. -->
          <div class="pr-row">
            <span class="pr-name" :title="p.product">
              {{ p.product }}
              <small v-if="p.category">{{ p.category }}</small>
            </span>
            <span class="pr-fig pr-fig--lead">
              <small>מגיע</small>
              <span class="ltr-number">{{ money(fExp(p)) }}</span>
            </span>
            <span class="pr-fig">
              <small>התקבל</small>
              <span class="ltr-number">{{ money(fPaid(p)) }}</span>
            </span>
            <span class="pr-fig">
              <small>הפרש</small>
              <span class="ltr-number pr-gap" :class="gapTone(fPaid(p), fExp(p))">{{ signedMoney(fPaid(p) - fExp(p)) }}</span>
            </span>
          </div>
          <div class="pr-rates" :title="formula(p)">
            שיעור בהסכם <span class="ltr-number">{{ rateText(p.rate_firm ?? p.rate) }}</span>
            · שיעור בפועל <span class="ltr-number" :class="gapTone(fPaid(p), fExp(p))">{{ rateText(p.paid_rate_firm ?? p.paid_rate) }}</span>
            <!-- The rows of this product the comparison left out, and their
                 money — said, so the card's figures never look incomplete. -->
            <span v-if="p.estimated" class="pr-partial">
              ≈ <span class="ltr-number">{{ p.estimated }}</span> מתוך <span class="ltr-number">{{ p.records }}</span>
              שורות בלי שיעור מפורש<template v-if="(p.paid || 0) - fPaid(p) > 0.5"> (<span class="ltr-number">{{ money((p.paid || 0) - fPaid(p)) }}</span>) — לא נכללו</template>
            </span>
          </div>
        </li>
      </ul>
    </section>
    <p v-else class="pr-none">לאף מוצר של החברה אין שיעור מפורש בהסכם, ולכן אין מה לבדוק.</p>

    <!-- Cannot be checked -->
    <section v-if="unchecked.length" class="pr-sec">
      <button class="pr-fold-head" :aria-expanded="openUnchecked" @click="openUnchecked = !openUnchecked">
        <span>לא ניתן לבדוק <span class="ltr-number">{{ unchecked.length }}</span></span>
        <small>שולמו <span class="ltr-number">{{ money(sum(unchecked, 'paid')) }}</span> — אין להם שיעור מפורש בהסכם</small>
        <svg :class="{ open: openUnchecked }" width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      <div class="pr-fold" :class="{ open: openUnchecked }">
        <div class="pr-fold-inner">
          <p class="pr-why">
            הסכום שהתקבל מוצג, אבל בלי שיעור בהסכם למוצר הזה אי אפשר לדעת אם הוא נכון —
            ולכן אין כאן טענה על חוב. להוספה: לשונית מדף ההסכמים.
          </p>
          <ul class="pr-quiet">
            <li v-for="p in unchecked" :key="p.product">
              <span class="pr-name">{{ p.product }}<small v-if="p.category">{{ p.category }}</small></span>
              <span class="pr-quiet-rate">
                שיעור בפועל <span class="ltr-number">{{ rateText(p.paid_rate) }}</span>
              </span>
              <span class="pr-quiet-amt ltr-number">{{ money(p.paid) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { money, signedMoney } from '../../utils/chartDefaults'

// Same thresholds as the rest of the agreement panel — a gap is coloured only
// past BOTH (insurers round; a commission can straddle a month boundary).
const GAP_MIN_PCT = 10
const GAP_MIN_SHEKEL = 100

const props = defineProps({ products: { type: Array, default: () => [] } })
const shown = ref(false)
const openUnchecked = ref(false)

/** Every row priced off a fallback rate — no claim. */
const isEstimate = p => (p.estimated || 0) >= (p.records || 0)
// Only the FIRM share of a product is compared — the rows the agreement names.
// That is exactly what the company row's gap is built from, so the drill and
// the row always agree (QA 2026-09-30: מנורה row +₪1,519, drill was +₪2,394,
// because a partly-≈ product brought its estimated rows along).
// `?? p.paid` keeps an older payload (no firm fields) readable.
const fPaid = p => Number(p.paid_firm ?? p.paid) || 0
const fExp = p => Number(p.expected_firm ?? p.expected) || 0
const checked = computed(() => props.products
  .filter(p => fExp(p) > 0)
  .sort((a, b) => ((fPaid(a) - fExp(a)) - (fPaid(b) - fExp(b)))))  // worst first
const unchecked = computed(() => props.products
  .filter(p => !checked.value.includes(p))
  .sort((a, b) => (b.paid || 0) - (a.paid || 0)))

const sum = (rows, k) => rows.reduce((s, p) => s + (Number(p[k]) || 0), 0)
const totals = computed(() => ({ paid: sum(props.products, 'paid') }))
const checkedTotals = computed(() => ({
  paid: checked.value.reduce((s, p) => s + fPaid(p), 0),
  expected: checked.value.reduce((s, p) => s + fExp(p), 0),
}))
// Everything paid that is NOT in the comparison: unchecked products plus the
// ≈ rows inside partly-checked ones.
const uncheckedPaid = computed(() => totals.value.paid - checkedTotals.value.paid)

function gapTone(paid, expected) {
  const diff = (Number(paid) || 0) - (Number(expected) || 0)
  const base = Math.abs(Number(expected) || 0)
  if (Math.abs(diff) < GAP_MIN_SHEKEL) return ''
  if (base && (Math.abs(diff) / base) * 100 < GAP_MIN_PCT) return ''
  return diff < 0 ? 'is-down' : 'is-up'
}

function rateText(rate) {
  if (!rate) return '—'
  const n = Number(rate) * 100
  return (n < 1 ? n.toFixed(3) : n.toFixed(2)) + '%'
}

/** "₪8,513 פרמיה × 19.2% = ₪1,635" — the arithmetic behind the agreed figure. */
function formula(p) {
  const rate = p.rate_firm ?? p.rate
  const base = p.base_firm ?? p.base
  if (!rate || !base) return ''
  const basis = p.basis === 'accumulation' ? 'צבירה' : 'פרמיה'
  const per = p.basis === 'accumulation' ? ' ÷ 12' : ''
  return `${money(base)} ${basis} × ${rateText(rate)}${per} = ${money(fExp(p))}`
}

function play() {
  shown.value = false
  openUnchecked.value = false
  requestAnimationFrame(() => requestAnimationFrame(() => { shown.value = true }))
}
onMounted(play)
watch(() => props.products, play)
</script>

<style scoped>
.pr { display: flex; flex-direction: column; gap: 18px; }

.pr-stats { display: grid; grid-template-columns: 1.25fr 1fr 1fr; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.pr-stat { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 14px 18px; }
.pr-stat + .pr-stat { border-inline-start: 1px solid var(--border-subtle); }
.pr-stat-val { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.pr-stat-lbl { font-size: 12px; color: var(--text-muted); font-weight: 600; }
.pr-stat--lead { }
.pr-stat--lead .pr-stat-val { font-size: 26px; color: var(--tab-production); }
.pr-total-note { font-size: 12px; color: var(--text-muted); margin: -8px 2px 0; }
.pr-total-note strong { color: var(--text); }

.pr-sec { display: flex; flex-direction: column; gap: 8px; }
.pr-sec-title { font-size: 13px; font-weight: 700; color: var(--text); display: flex; gap: 6px; align-items: baseline; }
.pr-sec-title .ltr-number { color: var(--text-muted); font-weight: 500; }

.pr-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.pr-card {
  border: 1px solid var(--border-subtle); border-radius: 12px; padding: 12px 14px;
  display: flex; flex-direction: column; gap: 8px; background: var(--card-bg);
  animation: prIn 0.35s cubic-bezier(0.2, 0, 0.2, 1) both; animation-delay: var(--d);
}
@keyframes prIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.pr-row {
  display: grid; align-items: center; gap: 12px;
  grid-template-columns: minmax(0, 1.4fr) 1.1fr 1fr 1fr;
}
.pr-name { display: flex; flex-direction: column; font-size: 14px; font-weight: 600; color: var(--text); min-width: 0; }
.pr-name small { font-size: 11.5px; font-weight: 400; color: var(--text-muted); }
.pr-fig { display: flex; flex-direction: column; align-items: flex-start; gap: 1px; font-size: 15px; font-weight: 700; color: var(--text); }
.pr-fig small { font-size: 11px; font-weight: 500; color: var(--text-muted); }
.pr-fig--lead { color: var(--tab-production); font-size: 16px; }
.pr-gap { color: var(--text-muted); }
.pr-rates { font-size: 12px; color: var(--text-muted); padding-top: 8px; border-top: 1px solid var(--border-subtle); }
.pr-partial {
  margin-inline-start: 6px; font-size: 11px; padding: 1px 7px; border-radius: 8px;
  background: var(--bg); color: var(--text-muted);
}

.is-down { color: var(--chart-loss) !important; }
.is-up { color: var(--chart-gain) !important; }

.pr-none { font-size: 13px; color: var(--text-muted); text-align: center; padding: 12px; }

.pr-fold-head {
  display: flex; align-items: baseline; gap: 10px; width: 100%;
  border: 1px dashed var(--border-subtle); border-radius: 12px; background: none;
  padding: 11px 14px; font: inherit; color: var(--text); cursor: pointer; text-align: right;
}
.pr-fold-head > span { font-size: 13px; font-weight: 700; }
.pr-fold-head small { font-size: 12px; color: var(--text-muted); }
.pr-fold-head svg { margin-inline-start: auto; align-self: center; color: var(--text-muted); transition: transform 0.25s ease; }
.pr-fold-head svg.open { transform: rotate(180deg); }
.pr-fold-head:hover { border-color: var(--text-muted); }
.pr-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.3s cubic-bezier(0.2, 0, 0.2, 1); }
.pr-fold.open { grid-template-rows: 1fr; }
.pr-fold-inner { overflow: hidden; min-height: 0; }
.pr-why { font-size: 12px; color: var(--text-muted); line-height: 1.7; margin: 10px 2px 6px; }
.pr-quiet { list-style: none; display: flex; flex-direction: column; }
.pr-quiet li {
  display: grid; grid-template-columns: minmax(0, 1fr) auto 100px; align-items: center; gap: 12px;
  padding: 9px 4px; border-bottom: 1px solid var(--border-subtle);
}
.pr-quiet li:last-child { border-bottom: none; }
.pr-quiet .pr-name { font-weight: 500; font-size: 13px; }
.pr-quiet-rate { font-size: 12px; color: var(--text-muted); }
.pr-quiet-amt { font-size: 13px; font-weight: 700; text-align: left; }

@media (max-width: 640px) {
  .pr-stats { grid-template-columns: 1fr 1fr; }
  .pr-stat--lead { grid-column: 1 / -1; }
  .pr-stat + .pr-stat { border-inline-start: none; border-top: 1px solid var(--border-subtle); }
  .pr-stat { padding: 10px 14px; }
  .pr-stat-val { font-size: 19px; }
  .pr-row { grid-template-columns: 1fr 1fr 1fr; }
  .pr-name { grid-column: 1 / -1; }
  .pr-quiet li { grid-template-columns: minmax(0, 1fr) 90px; }
  .pr-quiet-rate { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .pr-card { animation: none; }
  .pr-fold, .pr-fold-head svg { transition: none; }
}
</style>
