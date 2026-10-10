<template>
  <section class="mm">
  <!-- מה זז החודש — tracks that climbed / fell in their peer group this month (arrows slide from the old
       place to the new), where the money went, and which of your customers sit in a faller. -->
    <nav class="mm-cats">
      <button v-for="c in MARKET_CATEGORIES" :key="c.id" type="button" :class="{ on: cat === c.id }" @click="cat = c.id">{{ c.label }}</button>
    </nav>
    <div v-if="loading" class="mm-wait">טוען…</div>
    <template v-else-if="data">
      <p class="mm-sub">{{ data.month }} מול {{ data.compared_with }} · דירוג = מקום בתשואה מתחילת השנה בקבוצת השווים</p>
      <div class="mm-grid" :key="cat">
        <div class="mm-card">
          <h4>עלו בדירוג</h4>
          <ul class="mm-list">
            <li v-for="(r, i) in (data.rank_climbers || []).slice(0, 6)" :key="r.fund" :style="{ '--i': i }">
              <span class="mm-fund">{{ r.fund }}</span>
              <span class="mm-move mm-move--up ltr-number">{{ r.rank_before }} → {{ r.rank_now }}<small>/{{ r.group_size }}</small></span>
            </li>
          </ul>
        </div>
        <div class="mm-card">
          <h4>ירדו בדירוג</h4>
          <ul class="mm-list">
            <li v-for="(r, i) in (data.rank_fallers || []).slice(0, 6)" :key="r.fund" :style="{ '--i': i }">
              <span class="mm-fund">{{ r.fund }}</span>
              <span class="mm-move ltr-number">{{ r.rank_before }} → {{ r.rank_now }}<small>/{{ r.group_size }}</small></span>
            </li>
          </ul>
        </div>
        <div class="mm-card mm-card--wide">
          <h4>לאן זרם הכסף (צבירה נטו בחודש, מיליוני ₪)</h4>
          <ul class="mm-flows">
            <li v-for="(r, i) in flows" :key="r.fund" :style="{ '--i': i }">
              <span class="mm-fund">{{ r.fund }}</span>
              <span class="mm-fbar" :class="{ neg: r.net_inflow_m < 0 }"><i :style="{ width: flowPct(r) + '%' }"></i></span>
              <span class="mm-fval ltr-number">{{ r.net_inflow_m > 0 ? '+' : '' }}{{ Math.round(r.net_inflow_m).toLocaleString('he-IL') }}</span>
            </li>
          </ul>
        </div>
        <div v-if="(data.my_customers_in_fallers || []).length" class="mm-card mm-card--wide">
          <h4>הלקוחות שלך במסלולים שירדו</h4>
          <ul class="mm-cust">
            <li v-for="c in data.my_customers_in_fallers" :key="c.id_number">
              <button type="button" @click="$emit('open-customer', c, $event.currentTarget)">
                <span>{{ c.name }}<small v-if="c.products && c.products[0]">{{ c.products[0].track }} · {{ c.products[0].rank_before }} → {{ c.products[0].rank_now }}</small></span>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 6l-6 6 6 6" /></svg>
              </button>
            </li>
          </ul>
          <p class="mm-note">ירידה בדירוג בחודש אחד אינה סיבה לניוד — נקודה לבדיקה.</p>
        </div>
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
const data = ref(null)
const loading = ref(false)
watch(cat, async () => {
  loading.value = true
  try { data.value = await store.loadMoves(cat.value) } finally { loading.value = false }
}, { immediate: true })
const flows = computed(() => [...(data.value?.top_inflows || []).slice(0, 4), ...(data.value?.top_outflows || []).slice(0, 3)])
const maxFlow = computed(() => Math.max(1, ...flows.value.map((r) => Math.abs(r.net_inflow_m || 0))))
const flowPct = (r) => Math.max(3, Math.round((Math.abs(r.net_inflow_m || 0) / maxFlow.value) * 100))
</script>

<style scoped>
.mm { display: flex; flex-direction: column; gap: 12px; }
.mm-cats { display: flex; gap: 18px; border-bottom: 1px solid var(--border-subtle, #E5E5E5); }
.mm-cats button {
  border: none; background: none; padding: 8px 2px; font: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  color: var(--text-secondary, #5C5C5C); border-bottom: 2.5px solid transparent; margin-bottom: -1px;
}
.mm-cats button.on { color: var(--tab-market-ink); border-bottom-color: var(--tab-market); }
.mm-sub, .mm-note { margin: 0; font-size: 12.5px; color: var(--text-secondary, #5C5C5C); }
.mm-wait { padding: 24px; text-align: center; color: var(--text-secondary, #5C5C5C); }
.mm-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.mm-card { background: #fff; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 14px; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.mm-card--wide { grid-column: 1 / -1; }
.mm-card h4 { margin: 0; font-size: 14px; font-weight: 800; }
.mm-list, .mm-flows, .mm-cust { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.mm-list li, .mm-flows li {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 10px; font-size: 13px;
  animation: mmIn 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 70ms);
}
.mm-flows li { grid-template-columns: minmax(0, 1.2fr) minmax(70px, 1fr) 64px; }
.mm-fund { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mm-move { font-weight: 800; color: var(--text-primary, #181818); }
.mm-move::before { content: '▼ '; font-size: 10px; }
.mm-move--up { color: var(--tab-market-ink); }
.mm-move--up::before { content: '▲ '; }
.mm-move small { font-weight: 500; color: var(--text-secondary, #5C5C5C); }
.mm-fbar { height: 9px; border-radius: 999px; background: var(--bg, #F3F3F3); direction: ltr; overflow: hidden; }
.mm-fbar i { display: block; height: 100%; border-radius: 999px; background: var(--tab-market); animation: mmGrow 1s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 70ms + 150ms); transform-origin: left; }
.mm-fbar.neg i { background: var(--text-secondary, #8A8A8A); opacity: 0.55; }
.mm-fval { text-align: end; font-weight: 700; }
.mm-cust button {
  width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 8px 12px;
  border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 10px; background: #fff; font: inherit; text-align: start; cursor: pointer;
}
.mm-cust button:hover { border-color: var(--tab-market); }
.mm-cust span { display: flex; flex-direction: column; font-size: 13.5px; font-weight: 700; min-width: 0; }
.mm-cust small { font-size: 12px; font-weight: 400; color: var(--text-secondary, #5C5C5C); }
@keyframes mmIn { from { opacity: 0; transform: translateY(8px); } }
@keyframes mmGrow { from { transform: scaleX(0); } }
@media (max-width: 720px) { .mm-grid { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .mm-list li, .mm-flows li, .mm-fbar i { animation: none; } }
</style>
