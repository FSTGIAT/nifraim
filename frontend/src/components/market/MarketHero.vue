<template>
  <section class="mh">
  <!-- "הלקוחות שלך מול השוק": the book's yearly gap vs the risk-level leaders rolls up, then the customers
       with the biggest gaps race in as bars. A row opens that customer's ladder drill. -->
    <div v-if="store.loadingOverview && !ov" class="mh-wait">מחשב את התיק מול השוק…</div>
    <div v-else-if="ov && ov.missing" class="mh-empty">
      <p>{{ ov.missing }}</p>
      <p class="mh-empty-sub">סולם הסיכון, מה זז החודש ודו-קרב החברות כבר עובדים — הם מנתוני השוק הציבוריים.</p>
    </div>
    <template v-else-if="ov">
      <div class="mh-top">
        <div class="mh-count">
          <small>פער שנתי משוער של הלקוחות שלך מול המובילים ברמת הסיכון</small>
          <b class="ltr-number">{{ ils(counter) }}</b>
          <span>{{ ov.customers_to_review }} לקוחות לבחינת מעבר · {{ ov.customers_compared }} לקוחות הושוו · נתוני שוק {{ ov.data_month }}</span>
        </div>
      </div>
      <h3 class="mh-h">הפערים הגדולים</h3>
      <ol class="mh-race" :class="{ 'mh-race--in': raced }">
        <li v-for="(c, i) in ov.customers" :key="c.id_number" :style="{ '--i': i }">
          <button type="button" class="mh-row" @click="$emit('open-customer', c, $event.currentTarget)">
            <span class="mh-name">{{ c.name }}<small v-if="c.top">{{ shortFund(c.top.fund) }}<template v-if="c.top.rank"> · {{ c.top.rank }}</template></small></span>
            <span class="mh-bar"><i :style="{ width: barPct(c) + '%' }"></i></span>
            <span class="mh-gain"><span class="ltr-number">{{ ils(c.annual_gain_ils) }}</span><small>בשנה</small></span>
            <svg class="mh-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 6l-6 6 6 6" /></svg>
          </button>
        </li>
      </ol>
      <p class="mh-rule">{{ ov.rule }}</p>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useMarketStore } from '../../stores/market.js'

defineEmits(['open-customer'])
const store = useMarketStore()
const ov = computed(() => store.overview)
const counter = ref(0)
const raced = ref(false)
const maxGain = computed(() => Math.max(1, ...((ov.value?.customers || []).map((c) => c.annual_gain_ils))))
const barPct = (c) => Math.max(4, Math.round((c.annual_gain_ils / maxGain.value) * 100))
const ils = (v) => '₪' + Math.round(v || 0).toLocaleString('he-IL')
const shortFund = (f) => (f || '').replace(/קופת גמל לחיסכון,.*?-\s*/, '').replace(/\s*-\s*/g, ' ')

function rollUp(target) {
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduce || !target) { counter.value = target || 0; raced.value = true; return }
  const t0 = performance.now(); const dur = 1600
  const step = (now) => {
    const k = Math.min(1, (now - t0) / dur)
    counter.value = target * (1 - Math.pow(1 - k, 3))
    if (k < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
  setTimeout(() => { raced.value = true }, 350)
}
watch(() => ov.value?.total_annual_gain_ils, (v) => { if (v != null) rollUp(v) })
onMounted(async () => {
  await store.loadOverview()
  if (ov.value?.total_annual_gain_ils != null) rollUp(ov.value.total_annual_gain_ils)
})
</script>

<style scoped>
.mh { display: flex; flex-direction: column; gap: 12px; }
.mh-wait, .mh-empty { padding: 28px; text-align: center; color: var(--text-secondary, #5C5C5C); background: #fff; border-radius: 14px; }
.mh-empty p { margin: 0; font-size: 15px; color: var(--text-primary, #181818); }
.mh-empty .mh-empty-sub { margin-top: 8px; font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.mh-top { background: #fff; border-radius: 16px; padding: 18px 22px; border: 1px solid var(--border-subtle, #E5E5E5); }
.mh-count { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
.mh-count small { font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.mh-count b { font-size: clamp(34px, 4.4vw, 52px); font-weight: 900; letter-spacing: -0.03em; color: var(--tab-market-ink); line-height: 1.05; }
.mh-count span { font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.mh-h { margin: 4px 0 0; font-size: 15px; font-weight: 800; }
.mh-race { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.mh-race li {
  opacity: 0; transform: translateX(-18px);
  transition: opacity 0.5s ease calc(var(--i) * 70ms), transform 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) calc(var(--i) * 70ms);
}
.mh-race--in li { opacity: 1; transform: none; }
.mh-row {
  width: 100%; display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(90px, 1fr) 110px 18px; align-items: center; gap: 12px;
  padding: 10px 14px; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 12px; background: #fff;
  font: inherit; text-align: start; cursor: pointer; transition: border-color 0.2s, transform 0.2s;
}
.mh-row:hover { border-color: var(--tab-market); transform: translateY(-1px); }
.mh-name { display: flex; flex-direction: column; font-size: 14px; font-weight: 700; min-width: 0; }
.mh-name small { font-size: 12px; font-weight: 400; color: var(--text-secondary, #5C5C5C); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mh-bar { height: 10px; border-radius: 999px; background: var(--bg, #F3F3F3); direction: ltr; overflow: hidden; }
.mh-bar i {
  display: block; height: 100%; border-radius: 999px; background: var(--tab-market);
  transform-origin: left center; transform: scaleX(0);
  transition: transform 1s cubic-bezier(0.2, 0.8, 0.2, 1) calc(var(--i) * 70ms + 200ms);
}
.mh-race--in .mh-bar i { transform: scaleX(1); }
.mh-gain { display: flex; flex-direction: column; align-items: flex-end; font-weight: 800; color: var(--tab-market-ink); }
.mh-gain small { font-size: 11px; font-weight: 500; color: var(--text-secondary, #5C5C5C); }
.mh-chev { color: var(--text-secondary, #5C5C5C); }
.mh-rule { margin: 0; font-size: 12px; color: var(--text-secondary, #5C5C5C); }
@media (max-width: 640px) {
  .mh-row { grid-template-columns: minmax(0, 1fr) 96px; }
  .mh-bar { grid-column: 1 / -1; grid-row: 2; }
  .mh-chev { display: none; }
}
@media (prefers-reduced-motion: reduce) { .mh-race li, .mh-bar i { transition: none; opacity: 1; transform: none; } }
</style>
