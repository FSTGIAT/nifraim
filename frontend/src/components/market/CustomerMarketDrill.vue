<template>
  <!-- One customer against the market: each savings product in the ladder of its risk level, the action,
       the yearly ₪ gap, and the same-name view (labelled as such). Grows out of the tapped row. -->
  <DataModal :open="!!customerId" :origin="origin" :title="name" :subtitle="customerId ? 'ת.ז ' + customerId : ''"
             :period="fit && fit.data_month ? 'נתוני שוק ' + fit.data_month : ''" accent="var(--tab-market)"
             :layer="1040" @close="$emit('close')">
    <div v-if="loading" class="cmd-wait">טוען את הקופות של הלקוח…</div>
    <div v-else-if="fit && !(fit.products || []).length" class="cmd-wait">{{ fit.note || 'אין ללקוח מוצרי חיסכון שאפשר להשוות לשוק.' }}</div>
    <div v-else-if="fit" class="cmd">
      <div v-if="totalGain >= 0.5" class="cmd-strip">
        <div><small>פער שנתי משוער מול המובילים</small><b class="ltr-number">{{ ils(totalGain) }}</b></div>
        <div><small>מוצרים לבחינת מעבר</small><b class="ltr-number">{{ toMove }}</b></div>
        <div><small>מוצרים שהושוו</small><b class="ltr-number">{{ ranked.length }}</b></div>
      </div>
      <section v-for="(p, i) in products" :key="i" class="cmd-prod" :class="{ 'cmd-prod--open': isOpen(i) }">
        <!-- With more than one product each card starts folded; the header opens it (user 2026-10-10). -->
        <button type="button" class="cmd-head" :aria-expanded="isOpen(i)" @click="toggle(i)">
          <div>
            <h4>{{ p.official_fund || p.track }}</h4>
            <p>
              {{ p.category }}
              <template v-if="p.accumulation >= 0.5"> · צבירה <span class="ltr-number">{{ ils(p.accumulation) }}</span></template>
              <template v-if="p.risk_level_view && p.risk_level_view.risk_level"> · רמת סיכון {{ p.risk_level_view.risk_level }}</template>
            </p>
          </div>
          <div class="cmd-act" :class="{ 'cmd-act--move': p.action && p.action.annual_gain_ils }">
            <span v-if="p.risk_level_view && p.risk_level_view.rank" class="cmd-rank ltr-number">{{ p.risk_level_view.rank }}</span>
            <span v-if="p.action && p.action.annual_gain_ils" class="cmd-gain"><span class="ltr-number">{{ ils(p.action.annual_gain_ils) }}</span> בשנה</span>
          </div>
          <svg v-if="products.length > 1" class="cmd-chev" width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
        </button>
        <div class="cmd-fold" :class="{ 'cmd-fold--open': isOpen(i) }"><div class="cmd-fold-inner">
        <p v-if="p.action" class="cmd-verdict">{{ p.action.action }}<template v-if="p.action.leader && !p.action.action.includes(p.action.leader)"> · המוביל: {{ p.action.leader }}</template></p>
        <p v-if="howLine(p)" class="cmd-how">
          איך: המסלול שלו הניב <span class="ltr-number">{{ howLine(p).me.toFixed(2) }}%</span> בשנה, המוביל
          <span class="ltr-number">{{ howLine(p).lead.toFixed(2) }}%</span> — הפרש <span class="ltr-number">{{ howLine(p).diff.toFixed(2) }}%</span>
          × צבירה <span class="ltr-number">{{ ils(p.accumulation) }}</span> = <b class="ltr-number">{{ ils(p.action.annual_gain_ils) }}</b> בשנה
          <small>(ממוצע שנתי של 3 שנים)</small>
        </p>
        <RiskLadder v-if="p.ladder" :tracks="p.ladder.tracks" />
        <p v-if="p.same_name_rank" class="cmd-same">
          מול מסלולים באותו שם: {{ p.same_name_rank.replace(' (מול מסלולים באותו שם)', '') }}
          <template v-if="p.same_name_gap_ils >= 0.5"> · פער <span class="ltr-number">{{ ils(p.same_name_gap_ils) }}</span> בשנה</template>
        </p>
        </div></div>
      </section>
      <p class="cmd-note">אומדן מתשואות עבר (3 שנים) — תשואות עבר אינן מבטיחות תשואות עתידיות.</p>
    </div>
  </DataModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import DataModal from '../workspace/DataModal.vue'
import RiskLadder from './RiskLadder.vue'
import { useMarketStore } from '../../stores/market.js'

const props = defineProps({
  customerId: { type: String, default: null },
  customerName: { type: String, default: '' },
  origin: { type: null, default: null },
})
defineEmits(['close'])
const store = useMarketStore()
const fit = ref(null)
const loading = ref(false)
// Which product cards are open. One product → open; more → all folded.
const opened = ref(new Set())
const isOpen = (i) => products.value.length <= 1 || opened.value.has(i)
function toggle(i) {
  const next = new Set(opened.value)
  next.has(i) ? next.delete(i) : next.add(i)
  opened.value = next
}
watch(() => props.customerId, async (id) => {
  fit.value = null
  opened.value = new Set()
  if (!id) return
  loading.value = true
  try { fit.value = await store.loadCustomer(id) } finally { loading.value = false }
}, { immediate: true })

const name = computed(() => props.customerName || fit.value?.name || '')
const actions = computed(() => fit.value?.recommended_actions_by_risk_level || [])
const products = computed(() => (fit.value?.products || []).filter((p) => p.official_fund)
  .map((p) => ({ ...p, action: actions.value.find((a) => a.track === p.official_fund) }))
  .sort((a, b) => (b.action?.annual_gain_ils || 0) - (a.action?.annual_gain_ils || 0)))
const ranked = computed(() => products.value.filter((p) => p.risk_level_view?.rank))
const toMove = computed(() => products.value.filter((p) => p.action?.annual_gain_ils).length)
const totalGain = computed(() => products.value.reduce((s, p) => s + (p.action?.annual_gain_ils || 0), 0))
const ils = (v) => '₪' + Math.round(v).toLocaleString('he-IL')
// the worked example for one product — the two rows of its own ladder, the gain the card already states
function howLine(p) {
  const t = p.ladder?.tracks || []
  const me = t.find((x) => x.is_this)
  const lead = t.find((x) => x.rank === 1)
  if (!p.action?.annual_gain_ils || !me || !lead || me.avg_yield_3y == null || lead.avg_yield_3y == null) return null
  return { me: me.avg_yield_3y, lead: lead.avg_yield_3y, diff: lead.avg_yield_3y - me.avg_yield_3y }
}
</script>

<style scoped>
.cmd { display: flex; flex-direction: column; gap: 14px; }
.cmd-wait { padding: 30px; text-align: center; color: var(--text-secondary, #5C5C5C); }
.cmd-strip {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: 14px; overflow: hidden; background: #fff;
}
.cmd-strip > div { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 12px 16px; }
.cmd-strip > div + div { border-inline-start: 1px solid var(--border-subtle, #E5E5E5); }
.cmd-strip small { font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.cmd-strip b { font-size: 21px; font-weight: 800; }
.cmd-strip > div:first-child b { color: var(--tab-market-ink); }
.cmd-prod { background: #fff; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 14px; padding: 14px 16px; display: flex; flex-direction: column; gap: 0;
  transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease; }
.cmd-prod--open { border-color: color-mix(in srgb, var(--tab-market) 40%, transparent); }
.cmd-prod:hover { background: rgba(91, 141, 214, 0.09); box-shadow: inset 0 0 0 1px rgba(91, 141, 214, 0.32); }
.cmd-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
  width: 100%; padding: 0; border: none; background: none; font: inherit; color: inherit; text-align: start; cursor: pointer; }
.cmd-head:focus-visible { outline: 2px solid var(--tab-market); outline-offset: 4px; border-radius: 8px; }
.cmd-chev { flex-shrink: 0; align-self: center; color: var(--text-muted); transition: transform 0.3s ease; }
.cmd-prod--open .cmd-chev { transform: rotate(180deg); }
/* the fold: grid rows 0fr → 1fr, the app's open-in-place pattern */
.cmd-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.35s cubic-bezier(0.2, 0, 0.2, 1); }
.cmd-fold--open { grid-template-rows: 1fr; }
.cmd-fold-inner { overflow: hidden; min-height: 0; display: flex; flex-direction: column; gap: 10px; }
.cmd-fold--open .cmd-fold-inner { padding-top: 10px; }
@media (prefers-reduced-motion: reduce) { .cmd-fold, .cmd-chev { transition: none; } }
.cmd-head h4 { margin: 0; font-size: 15px; font-weight: 800; }
.cmd-head p { margin: 2px 0 0; font-size: 12.5px; color: var(--text-secondary, #5C5C5C); }
.cmd-act { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
.cmd-rank { font-size: 18px; font-weight: 800; }
.cmd-act--move .cmd-rank, .cmd-gain { color: var(--tab-market-ink); }
.cmd-gain { font-size: 13px; font-weight: 800; }
.cmd-verdict { margin: 0; font-size: 13px; font-weight: 600; }
.cmd-how { margin: 0; padding: 8px 12px; border-radius: 10px; background: var(--tab-market-wash); font-size: 13px; line-height: 1.6; }
.cmd-how b { color: var(--tab-market-ink); }
.cmd-how small { color: var(--text-secondary, #5C5C5C); }
.cmd-same { margin: 0; font-size: 12.5px; color: var(--text-secondary, #5C5C5C); }
.cmd-note { margin: 0; font-size: 12px; color: var(--text-secondary, #5C5C5C); }
@media (max-width: 640px) { .cmd-strip { grid-template-columns: 1fr; } .cmd-strip > div + div { border-inline-start: none; border-top: 1px solid var(--border-subtle, #E5E5E5); } }
</style>
