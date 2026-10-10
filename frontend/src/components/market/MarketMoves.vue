<template>
  <section class="mm">
  <!-- מה זז — any month against the month before it: who climbed / fell inside its peer group (each drawn as a
       slope from the old place to the new one), where the money went, and your customers in tracks that fell. -->
    <nav class="mm-cats">
      <button v-for="c in MARKET_CATEGORIES" :key="c.id" type="button" :class="{ on: cat === c.id }" @click="cat = c.id">{{ c.label }}</button>
    </nav>

    <div v-if="data && (data.months || []).length" class="mm-months" role="tablist" aria-label="בחירת חודש">
      <span class="mm-months-lbl">חודש</span>
      <button v-for="m in data.months" :key="m.period" type="button" role="tab" :aria-selected="period === m.period"
              :class="{ on: (period || data.period) === m.period }" @click="period = m.period">
        <span class="ltr-number">{{ m.label }}</span>
      </button>
    </div>

    <div v-if="loading" class="mm-wait">טוען…</div>
    <template v-else-if="data">
      <p class="mm-sub"><b class="ltr-number">{{ data.month }}</b> מול <span class="ltr-number">{{ data.compared_with }}</span> — דירוג = המקום בתשואה מתחילת השנה, בתוך קבוצת השווים</p>

      <div v-if="data.summary" class="mm-kpis" :key="'k' + cat + data.period">
        <div><small>קופות שהושוו</small><b class="ltr-number">{{ fmtInt(kpi.funds) }}</b></div>
        <div v-if="data.summary.net_inflow_m_this_month != null"><small>צבירה נטו בחודש</small>
          <b class="ltr-number">{{ kpi.inflow >= 0 ? '+' : '−' }}₪{{ fmtInt(Math.abs(kpi.inflow)) }}M</b></div>
        <div><small>שינויי דמי ניהול</small><b class="ltr-number">{{ fmtInt(kpi.fees) }}</b></div>
      </div>

      <div class="mm-grid" :key="cat + data.period">
        <article class="mm-card">
          <header><span class="mm-ic mm-ic--up"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M7 14l5-5 5 5" /></svg></span><h4>עלו בדירוג</h4></header>
          <ul class="mm-movers">
            <li v-for="(r, i) in (data.rank_climbers || []).slice(0, 6)" :key="r.fund" :style="{ '--i': i }">
              <svg class="mm-slope" viewBox="0 0 44 40" aria-hidden="true">
                <line x1="8" y1="4" x2="8" y2="36" class="mm-axis" /><line x1="36" y1="4" x2="36" y2="36" class="mm-axis" />
                <path :d="slope(r)" class="mm-path mm-path--up" />
                <circle :cx="8" :cy="yOf(r.rank_before, r.group_size)" r="3.2" class="mm-dot-old" />
                <circle :cx="36" :cy="yOf(r.rank_now, r.group_size)" r="4" class="mm-dot-new mm-dot-new--up" />
              </svg>
              <span class="mm-fund">{{ r.fund }}<small>מקום <span class="ltr-number">{{ r.rank_before }} → {{ r.rank_now }}</span> מתוך <span class="ltr-number">{{ r.group_size }}</span></small></span>
              <b class="mm-chip mm-chip--up ltr-number">+{{ r.rank_before - r.rank_now }}</b>
            </li>
          </ul>
          <p v-if="!(data.rank_climbers || []).length" class="mm-none">אין תזוזות גדולות החודש.</p>
        </article>
        <article class="mm-card">
          <header><span class="mm-ic"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M7 10l5 5 5-5" /></svg></span><h4>ירדו בדירוג</h4></header>
          <ul class="mm-movers">
            <li v-for="(r, i) in (data.rank_fallers || []).slice(0, 6)" :key="r.fund" :style="{ '--i': i }">
              <svg class="mm-slope" viewBox="0 0 44 40" aria-hidden="true">
                <line x1="8" y1="4" x2="8" y2="36" class="mm-axis" /><line x1="36" y1="4" x2="36" y2="36" class="mm-axis" />
                <path :d="slope(r)" class="mm-path" />
                <circle :cx="8" :cy="yOf(r.rank_before, r.group_size)" r="3.2" class="mm-dot-old" />
                <circle :cx="36" :cy="yOf(r.rank_now, r.group_size)" r="4" class="mm-dot-new" />
              </svg>
              <span class="mm-fund">{{ r.fund }}<small>מקום <span class="ltr-number">{{ r.rank_before }} → {{ r.rank_now }}</span> מתוך <span class="ltr-number">{{ r.group_size }}</span></small></span>
              <b class="mm-chip ltr-number">−{{ r.rank_now - r.rank_before }}</b>
            </li>
          </ul>
          <p v-if="!(data.rank_fallers || []).length" class="mm-none">אין תזוזות גדולות החודש.</p>
        </article>

        <article class="mm-card">
          <header><h4>נכנס הכי הרבה כסף</h4><small>צבירה נטו בחודש, מיליוני ₪</small></header>
          <ul class="mm-flows">
            <li v-for="(r, i) in inflows" :key="r.fund" :style="{ '--i': i }">
              <span class="mm-fund">{{ r.fund }}</span>
              <span class="mm-fbar"><i :style="{ width: flowPct(r) + '%' }"></i></span>
              <b class="ltr-number">+{{ fmtInt(r.net_inflow_m) }}</b>
            </li>
          </ul>
        </article>
        <article class="mm-card">
          <header><h4>יצא הכי הרבה כסף</h4><small>צבירה נטו בחודש, מיליוני ₪</small></header>
          <ul class="mm-flows">
            <li v-for="(r, i) in outflows" :key="r.fund" :style="{ '--i': i }">
              <span class="mm-fund">{{ r.fund }}</span>
              <span class="mm-fbar mm-fbar--out"><i :style="{ width: flowPct(r) + '%' }"></i></span>
              <b class="ltr-number">−{{ fmtInt(Math.abs(r.net_inflow_m)) }}</b>
            </li>
          </ul>
        </article>

        <article v-if="(data.my_customers_in_fallers || []).length" class="mm-card mm-card--wide">
          <header><h4>הלקוחות שלך במסלולים שירדו</h4><small>ירידה בחודש אחד היא נקודה לבדיקה, לא סיבה לניוד</small></header>
          <ul class="mm-cust">
            <li v-for="c in data.my_customers_in_fallers" :key="c.id_number">
              <button type="button" @click="$emit('open-customer', c, $event.currentTarget)">
                <span>{{ c.name }}<small v-if="c.products && c.products[0]">{{ c.products[0].track }} · מקום <span class="ltr-number">{{ c.products[0].rank_before }} → {{ c.products[0].rank_now }}</span></small></span>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 6l-6 6 6 6" /></svg>
              </button>
            </li>
          </ul>
        </article>
      </div>
      <p class="mm-note">{{ data.disclaimer }}</p>
    </template>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { MARKET_CATEGORIES, useMarketStore } from '../../stores/market.js'

defineEmits(['open-customer'])
const store = useMarketStore()
const cat = ref('pension')
const period = ref(null)
const data = ref(null)
const loading = ref(false)
watch(cat, () => { period.value = null })
watch([cat, period], async () => {
  loading.value = true
  try { data.value = await store.loadMoves(cat.value, period.value) } finally { loading.value = false }
  countUp()
}, { immediate: true })

const inflows = computed(() => (data.value?.top_inflows || []).filter((r) => r.net_inflow_m > 0).slice(0, 5))
const outflows = computed(() => (data.value?.top_outflows || []).filter((r) => r.net_inflow_m < 0).slice(0, 5))
const maxFlow = computed(() => Math.max(1, ...[...inflows.value, ...outflows.value].map((r) => Math.abs(r.net_inflow_m || 0))))
const flowPct = (r) => Math.max(4, Math.round((Math.abs(r.net_inflow_m || 0) / maxFlow.value) * 100))
const fmtInt = (v) => Math.round(v || 0).toLocaleString('he-IL')
// rank 1 at the top of the little axis, the group's last place at the bottom
const yOf = (rank, of) => 6 + ((Math.max(1, rank) - 1) / Math.max(1, (of || 1) - 1)) * 28
const slope = (r) => {
  const y1 = yOf(r.rank_before, r.group_size), y2 = yOf(r.rank_now, r.group_size)
  return `M8 ${y1} C 22 ${y1}, 22 ${y2}, 36 ${y2}`
}

const kpi = ref({ funds: 0, inflow: 0, fees: 0 })
function countUp() {
  const s = data.value?.summary || {}
  const target = { funds: s.funds_compared || 0, inflow: s.net_inflow_m_this_month || 0, fees: s.fee_changes || 0 }
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { kpi.value = target; return }
  const t0 = performance.now(); const dur = 1100
  const step = (now) => {
    const k = Math.min(1, (now - t0) / dur); const e = 1 - Math.pow(1 - k, 3)
    kpi.value = { funds: target.funds * e, inflow: target.inflow * e, fees: target.fees * e }
    if (k < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}
</script>

<style scoped>
.mm { display: flex; flex-direction: column; gap: 14px; }
.mm-cats { display: flex; gap: 18px; border-bottom: 1px solid var(--border-subtle, #E5E5E5); }
.mm-cats button {
  border: none; background: none; padding: 8px 2px; font: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  color: var(--text-secondary, #5C5C5C); border-bottom: 2.5px solid transparent; margin-bottom: -1px; transition: color 0.2s;
}
.mm-cats button:hover { color: var(--tab-market-ink); }
.mm-cats button.on { color: var(--tab-market-ink); border-bottom-color: var(--tab-market); }
.mm-months { display: flex; align-items: center; gap: 6px; overflow-x: auto; padding-bottom: 2px; scrollbar-width: thin; }
.mm-months-lbl { font-size: 12.5px; font-weight: 700; color: var(--text-secondary, #5C5C5C); flex-shrink: 0; }
.mm-months button {
  flex-shrink: 0; padding: 5px 12px; border-radius: 999px; border: 1px solid var(--border-subtle, #E5E5E5); background: #fff;
  font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; color: var(--text-secondary, #5C5C5C); transition: all 0.2s;
}
.mm-months button:hover { border-color: var(--tab-market); color: var(--tab-market-ink); }
.mm-months button.on { background: var(--tab-market-ink); border-color: var(--tab-market-ink); color: #fff; }
.mm-sub, .mm-note { margin: 0; font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.mm-sub b { color: var(--text-primary, #181818); }
.mm-wait { padding: 24px; text-align: center; color: var(--text-secondary, #5C5C5C); }
.mm-kpis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 14px; background: #fff; overflow: hidden; }
.mm-kpis > div { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 12px 16px; }
.mm-kpis > div + div { border-inline-start: 1px solid var(--border-subtle, #E5E5E5); }
.mm-kpis small { font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.mm-kpis b { font-size: 22px; font-weight: 800; }
.mm-kpis > div:first-child b { color: var(--tab-market-ink); }
.mm-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.mm-card { background: #fff; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 16px; padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; min-width: 0;
  transition: background-color 0.2s ease, box-shadow 0.2s ease; }
/* hover fills the card in Market's steel blue, as Nifra Insights does in its teal */
.mm-card:hover { background: rgba(91, 141, 214, 0.09); box-shadow: inset 0 0 0 1px rgba(91, 141, 214, 0.32); }
.mm-card--wide { grid-column: 1 / -1; }
.mm-card header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.mm-card h4 { margin: 0; font-size: 15px; font-weight: 800; }
.mm-card header small { font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.mm-ic { width: 24px; height: 24px; border-radius: 8px; display: grid; place-items: center; background: var(--bg, #F3F3F3); color: var(--text-secondary, #5C5C5C); }
.mm-ic--up { background: var(--tab-market-wash); color: var(--tab-market-ink); }
.mm-movers, .mm-flows, .mm-cust { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.mm-movers li {
  display: grid; grid-template-columns: 44px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 6px 8px; border-radius: 10px;
  animation: mmIn 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 70ms); transition: background-color 0.25s;
}
.mm-movers li:hover, .mm-flows li:hover { background: var(--tab-market-wash); }
.mm-slope { width: 44px; height: 40px; }
.mm-axis { stroke: var(--border-subtle, #E5E5E5); stroke-width: 1.5; }
.mm-path { fill: none; stroke: #9A9A9A; stroke-width: 2; stroke-dasharray: 60; stroke-dashoffset: 60; animation: mmDraw 0.9s ease-out both; animation-delay: calc(var(--i) * 70ms + 200ms); }
.mm-path--up { stroke: var(--tab-market); }
.mm-dot-old { fill: #fff; stroke: #B5B5B5; stroke-width: 1.5; }
.mm-dot-new { fill: #8A8A8A; animation: mmPop 0.45s cubic-bezier(0.34, 1.6, 0.5, 1) both; animation-delay: calc(var(--i) * 70ms + 900ms); transform-box: fill-box; transform-origin: center; }
.mm-dot-new--up { fill: var(--tab-market-ink); }
.mm-fund { display: flex; flex-direction: column; min-width: 0; font-size: 13.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mm-fund small { font-size: 12px; font-weight: 400; color: var(--text-secondary, #5C5C5C); }
.mm-chip { padding: 3px 9px; border-radius: 999px; font-size: 12.5px; font-weight: 800; background: var(--bg, #F3F3F3); color: var(--text-secondary, #5C5C5C); }
.mm-chip--up { background: var(--tab-market-wash); color: var(--tab-market-ink); }
.mm-flows li {
  display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(70px, 1fr) 66px; align-items: center; gap: 10px; padding: 7px 8px; border-radius: 10px;
  font-size: 13px; animation: mmIn 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 70ms); transition: background-color 0.25s;
}
.mm-flows b { text-align: end; font-weight: 800; color: var(--tab-market-ink); }
.mm-fbar { height: 10px; border-radius: 999px; background: var(--bg, #F3F3F3); direction: ltr; overflow: hidden; }
.mm-fbar i { display: block; height: 100%; border-radius: 999px; background: var(--tab-market); transform-origin: left; animation: mmGrow 1s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 70ms + 150ms); }
.mm-fbar--out i { background: #A9A9A9; }
.mm-fbar--out + b { color: var(--text-secondary, #5C5C5C); }
.mm-cust button {
  width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 9px 12px;
  border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 12px; background: #fff; font: inherit; text-align: start; cursor: pointer;
  transition: background-color 0.25s, border-color 0.2s;
}
.mm-cust button:hover { border-color: var(--tab-market); background: var(--tab-market-wash); }
.mm-cust span { display: flex; flex-direction: column; font-size: 13.5px; font-weight: 700; min-width: 0; }
.mm-cust small { font-size: 12px; font-weight: 400; color: var(--text-secondary, #5C5C5C); }
.mm-none { margin: 0; font-size: 13px; color: var(--text-secondary, #5C5C5C); }
@keyframes mmIn { from { opacity: 0; transform: translateY(8px); } }
@keyframes mmGrow { from { transform: scaleX(0); } }
@keyframes mmDraw { to { stroke-dashoffset: 0; } }
@keyframes mmPop { from { transform: scale(0); } }
@media (max-width: 760px) { .mm-grid { grid-template-columns: 1fr; } .mm-kpis b { font-size: 18px; } }
@media (prefers-reduced-motion: reduce) { .mm-movers li, .mm-flows li, .mm-fbar i, .mm-path, .mm-dot-new { animation: none; stroke-dashoffset: 0; } }
</style>
