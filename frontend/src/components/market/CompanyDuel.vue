<template>
  <section class="cd2">
  <!-- דו-קרב חברות — two companies, track type against track type (compare_companies). The pairs grow out
       from the middle, the winner of each pair is solid, and the tally counts up. -->
    <div class="cd2-pick">
      <select v-model="cat" aria-label="קטגוריה">
        <option v-for="c in MARKET_CATEGORIES" :key="c.id" :value="c.id">{{ c.label }}</option>
      </select>
      <select v-model="a" aria-label="חברה ראשונה"><option v-for="c in MARKET_COMPANIES" :key="c" :value="c" :disabled="c === b">{{ c }}</option></select>
      <span class="cd2-vs">מול</span>
      <select v-model="b" aria-label="חברה שנייה"><option v-for="c in MARKET_COMPANIES" :key="c" :value="c" :disabled="c === a">{{ c }}</option></select>
    </div>
    <div v-if="loading" class="cd2-wait">משווה…</div>
    <template v-else-if="data">
      <p v-if="data.found === false" class="cd2-note">{{ data.note }}</p>
      <template v-else>
        <div class="cd2-score">
          <div><b class="ltr-number">{{ tally(A) }}</b><span>{{ A }}</span></div>
          <p>{{ data.verdict }}</p>
          <div><b class="ltr-number">{{ tally(B) }}</b><span>{{ B }}</span></div>
        </div>
        <ul class="cd2-pairs" :key="cat + A + B">
          <li v-for="(p, i) in data.pairs" :key="p.track_type" :style="{ '--i': i }">
            <span class="cd2-val ltr-number" :class="{ win: p.winner_3y === A }">{{ fmt(p[A].avg_yield_3y) }}</span>
            <span class="cd2-bar cd2-bar--a"><i :class="{ win: p.winner_3y === A }" :style="{ width: pct(p[A].avg_yield_3y) + '%' }"></i></span>
            <span class="cd2-type">{{ typeLabel(p.track_type) }}</span>
            <span class="cd2-bar cd2-bar--b"><i :class="{ win: p.winner_3y === B }" :style="{ width: pct(p[B].avg_yield_3y) + '%' }"></i></span>
            <span class="cd2-val ltr-number" :class="{ win: p.winner_3y === B }">{{ fmt(p[B].avg_yield_3y) }}</span>
          </li>
        </ul>
        <p class="cd2-note">תשואה שנתית ממוצעת 3 שנים, המסלול הגדול של כל חברה מכל סוג · נתוני {{ data.data_month }} · {{ data.disclaimer }}</p>
      </template>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { MARKET_CATEGORIES, MARKET_COMPANIES, useMarketStore } from '../../stores/market.js'

const store = useMarketStore()
const cat = ref('pension')
const a = ref('כלל')
const b = ref('אלטשולר')
const data = ref(null)
const loading = ref(false)
const A = computed(() => data.value?.companies?.[0] || a.value)
const B = computed(() => data.value?.companies?.[1] || b.value)
const shownTally = ref({})
async function load() {
  loading.value = true
  try { data.value = await store.loadDuel(cat.value, a.value, b.value) } finally { loading.value = false }
  countUp()
}
watch([cat, a, b], load)
onMounted(load)
const top = computed(() => Math.max(1, ...((data.value?.pairs || []).flatMap((p) => [p[A.value]?.avg_yield_3y || 0, p[B.value]?.avg_yield_3y || 0]))))
const pct = (v) => Math.max(3, Math.round(((v || 0) / top.value) * 100))
const fmt = (v) => (v == null ? '' : v.toFixed(2) + '%')
const typeLabel = (t) => (t || '').split(' ').slice(1).join(' ') || t
const tally = (co) => shownTally.value[co] ?? 0
function countUp() {
  const w = data.value?.wins_3y || {}
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const target = { [A.value]: w[A.value] || 0, [B.value]: w[B.value] || 0 }
  if (reduce) { shownTally.value = target; return }
  shownTally.value = { [A.value]: 0, [B.value]: 0 }
  const t0 = performance.now(); const dur = 900
  const step = (now) => {
    const k = Math.min(1, (now - t0) / dur)
    shownTally.value = { [A.value]: Math.round(target[A.value] * k), [B.value]: Math.round(target[B.value] * k) }
    if (k < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}
</script>

<style scoped>
.cd2 { display: flex; flex-direction: column; gap: 12px; }
.cd2-pick { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.cd2-pick select { padding: 7px 12px; border-radius: 10px; border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; font: inherit; font-size: 14px; }
.cd2-vs { font-weight: 800; color: var(--text-secondary, #5C5C5C); }
.cd2-wait { padding: 24px; text-align: center; color: var(--text-secondary, #5C5C5C); }
.cd2-score { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; background: #fff; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 14px; padding: 14px 18px; }
.cd2-score > div { display: flex; flex-direction: column; align-items: center; }
.cd2-score b { font-size: 34px; font-weight: 900; color: var(--tab-market-ink); line-height: 1; }
.cd2-score span { font-size: 14px; font-weight: 800; }
.cd2-score p { margin: 0; max-width: 340px; text-align: center; font-size: 13.5px; font-weight: 600; }
.cd2-pairs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.cd2-pairs li {
  display: grid; grid-template-columns: 60px minmax(40px, 1fr) minmax(90px, 140px) minmax(40px, 1fr) 60px; align-items: center; gap: 8px;
  background: #fff; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 12px; padding: 8px 12px;
  animation: cdIn 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 80ms);
}
.cd2-type { text-align: center; font-size: 13px; font-weight: 700; }
.cd2-val { font-size: 13px; font-weight: 600; text-align: center; color: var(--text-secondary, #5C5C5C); }
.cd2-val.win { color: var(--tab-market-ink); font-weight: 900; }
.cd2-bar { height: 12px; border-radius: 999px; background: var(--bg, #F3F3F3); overflow: hidden; display: flex; }
/* RTL row: A sits right of the type label, B left of it — both bars are anchored at the middle */
.cd2-bar--a { justify-content: flex-end; }
.cd2-bar--b { justify-content: flex-start; }
.cd2-bar i { display: block; height: 100%; border-radius: 999px; background: var(--tab-market); opacity: 0.35; animation: cdGrow 1s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 80ms + 200ms); }
.cd2-bar--a i { transform-origin: left; }
.cd2-bar--b i { transform-origin: right; }
.cd2-bar i.win { opacity: 1; }
.cd2-note { margin: 0; font-size: 12px; color: var(--text-secondary, #5C5C5C); }
@keyframes cdIn { from { opacity: 0; transform: translateY(8px); } }
@keyframes cdGrow { from { transform: scaleX(0); } }
@media (max-width: 640px) { .cd2-pairs li { grid-template-columns: 52px minmax(20px, 1fr) 84px minmax(20px, 1fr) 52px; padding: 8px; } .cd2-score b { font-size: 26px; } }
@media (prefers-reduced-motion: reduce) { .cd2-pairs li, .cd2-bar i { animation: none; } }
</style>
