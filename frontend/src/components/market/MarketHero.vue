<template>
  <section class="mh">
  <!-- "הלקוחות שלך מול השוק": the book's yearly gap vs the risk-level leaders rolls up, then the customers
       with the biggest gaps race in as bars. A row opens that customer's ladder drill. -->
    <div v-if="store.loadingOverview && !ov" class="mh-wait">מחשב את התיק מול השוק…</div>
    <MarketEmptyState v-else-if="ov && ov.missing" title="עוד אין נתונים מהתיק שלך"
                      :text="ov.missing.replace('עוד אין נתונים מהתיק שלך — ', '')" :actions="marketActions" @go="(v) => $emit('go', v)" />
    <MarketEmptyState v-else-if="ov && !ov.customers_compared" title="לא מצאנו בתיק מוצרי חיסכון להשוואה"
                      text="ההשוואה לשוק עובדת על פנסיה, גמל, השתלמות, גמל להשקעה ופוליסות חיסכון — לפי המסלול שבקובץ הפרודוקציה. בקבצים שהועלו אין עדיין מוצרים כאלה עם מסלול מזוהה. בינתיים אפשר לראות את השוק עצמו:"
                      :actions="marketActions" @go="(v) => $emit('go', v)" />
    <MarketEmptyState v-else-if="ov && !ov.total_annual_gain_ils" tone="ok" title="אין כרגע לקוחות לבחינת מעבר"
                      :text="`השווינו ${ov.customers_compared} לקוחות: כל המסלולים שלהם בראש הטבלה או במרכזה ברמת הסיכון שלהם, או שהמוביל לא באמת הרוויח יותר ב-3 השנים האחרונות.`"
                      :actions="marketActions" @go="(v) => $emit('go', v)" />
    <template v-else-if="ov">
      <div class="mh-top">
        <div class="mh-count">
          <small>פער שנתי משוער של הלקוחות שלך מול המובילים ברמת הסיכון</small>
          <b class="ltr-number">{{ ils(counter) }}</b>
          <span>{{ ov.customers_to_review }} לקוחות לבחינת מעבר · {{ ov.customers_compared }} לקוחות הושוו · נתוני שוק {{ ov.data_month }}</span>
        </div>
        <button type="button" class="mh-how-toggle" :aria-expanded="howOpen" @click="howOpen = !howOpen">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></svg>
          {{ howOpen ? 'הסתר את ההסבר' : 'איך חישבנו את הסכום?' }}
        </button>
        <div class="mh-how" :class="{ open: howOpen }">
          <div class="mh-how-in">
            <ol class="mh-steps">
              <li>
                <b>משווים כל מוצר למסלולים באותה רמת סיכון</b>
                <span>מסלולים עם חשיפה דומה למניות — לפי מה שהם מחזיקים בפועל, לא לפי השם שלהם.</span>
              </li>
              <li>
                <b>סופרים רק את מה שכדאי לבחון</b>
                <span>מסלול שנמצא בחצי התחתון של הדירוג, כשהמסלול המוביל באמת הרוויח יותר ב-3 השנים האחרונות.
                  <template v-if="ov.products_to_review"> אצלך: <span class="ltr-number">{{ ov.products_to_review }}</span> מוצרים אצל <span class="ltr-number">{{ ov.customers_to_review }}</span> לקוחות.</template></span>
              </li>
              <li>
                <b>מתרגמים לשקלים</b>
                <span>הכסף של הלקוח × ההפרש בתשואה השנתית בינו לבין המוביל = כמה הוא היה מרוויח יותר בשנה.</span>
              </li>
            </ol>
            <div v-if="example" class="mh-ex">
              <p class="mh-ex-title">לדוגמה — {{ example.name }}</p>
              <div class="mh-ex-bars">
                <div class="mh-ex-row">
                  <span class="mh-ex-lbl">המסלול שלו<small>{{ shortFund(example.fund) }}</small></span>
                  <span class="mh-ex-bar"><i :style="{ width: exPct(example.track_3y) + '%' }"></i></span>
                  <b class="ltr-number">{{ example.track_3y.toFixed(2) }}%</b>
                </div>
                <div class="mh-ex-row mh-ex-row--lead">
                  <span class="mh-ex-lbl">המוביל ברמת הסיכון<small>{{ shortFund(example.leader) }}</small></span>
                  <span class="mh-ex-bar"><i :style="{ width: exPct(example.leader_3y) + '%' }"></i></span>
                  <b class="ltr-number">{{ example.leader_3y.toFixed(2) }}%</b>
                </div>
              </div>
              <p class="mh-ex-eq">
                <span class="ltr-number">{{ ils(example.accumulation) }}</span><small>צבירה</small>
                <em>×</em>
                <span class="ltr-number">{{ example.diff.toFixed(2) }}%</span><small>הפרש בשנה</small>
                <em>=</em>
                <strong class="ltr-number">{{ ils(example.gain) }}</strong><small>בשנה</small>
              </p>
            </div>
            <p class="mh-how-note">תשואה = ממוצע שנתי של 3 השנים האחרונות, מנתוני גמל-נט ופנסיה-נט. זה אומדן לפי העבר — תשואות עבר אינן מבטיחות תשואות עתידיות.</p>
          </div>
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
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useMarketStore } from '../../stores/market.js'
import MarketEmptyState from './MarketEmptyState.vue'

defineEmits(['open-customer', 'go'])
const marketActions = [{ view: 'ladder', label: 'סולם הסיכון' }, { view: 'moves', label: 'מה זז החודש' }, { view: 'duel', label: 'דו-קרב חברות' }]
const store = useMarketStore()
const ov = computed(() => store.overview)
const counter = ref(0)
// open by default on a desktop — the amount needs its explanation; folded on phones, where it would push the
// list a screen down. Not remembered (nifraim-style: a default the user asked for is not stored)
// Closed by default (user 2026-10-10) — "איך חישבנו את הסכום?" opens it.
const howOpen = ref(false)
// the worked example = the agent's own biggest gap, from the same numbers as the rows below
const example = computed(() => {
  const c = (ov.value?.customers || []).find((x) => x.top && x.top.track_3y != null && x.top.leader_3y != null)
  if (!c) return null
  const t = c.top
  return { name: c.name, fund: t.fund, leader: t.leader, track_3y: t.track_3y, leader_3y: t.leader_3y,
           diff: t.leader_3y - t.track_3y, accumulation: t.accumulation, gain: t.annual_gain_ils }
})
const exPct = (v) => Math.max(4, Math.round(((v || 0) / Math.max(example.value?.leader_3y || 1, example.value?.track_3y || 1)) * 100))
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
.mh-how-toggle {
  margin-top: 12px; display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border: none; border-radius: 999px;
  background: var(--tab-market-wash); color: var(--tab-market-ink); font: inherit; font-size: 13px; font-weight: 700; cursor: pointer;
}
.mh-how-toggle:hover { background: rgba(122, 127, 42, 0.18); }
.mh-how { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); }
.mh-how.open { grid-template-rows: 1fr; }
.mh-how-in { overflow: hidden; min-height: 0; }
.mh-steps { list-style: none; counter-reset: st; margin: 14px 0 0; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.mh-steps li { counter-increment: st; position: relative; padding: 12px 14px 12px 14px; padding-inline-start: 48px; border-radius: 12px; background: var(--bg, #F3F3F3); display: flex; flex-direction: column; gap: 4px; }
.mh-steps li::before {
  content: counter(st); position: absolute; inset-inline-start: 12px; top: 12px; width: 26px; height: 26px; border-radius: 50%;
  display: grid; place-items: center; background: var(--tab-market-ink); color: #fff; font-size: 13px; font-weight: 800;
}
.mh-steps b { font-size: 14px; font-weight: 800; }
.mh-steps span { font-size: 13px; line-height: 1.5; color: var(--text-secondary, #5C5C5C); }
.mh-ex { margin-top: 10px; padding: 14px 16px; border-radius: 12px; border: 1.5px dashed rgba(122, 127, 42, 0.45); display: flex; flex-direction: column; gap: 10px; }
.mh-ex-title { margin: 0; font-size: 14px; font-weight: 800; }
.mh-ex-bars { display: flex; flex-direction: column; gap: 8px; }
.mh-ex-row { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(80px, 1fr) 64px; align-items: center; gap: 10px; font-size: 13px; }
.mh-ex-lbl { display: flex; flex-direction: column; font-weight: 700; min-width: 0; }
.mh-ex-lbl small { font-weight: 400; color: var(--text-secondary, #5C5C5C); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mh-ex-bar { height: 12px; border-radius: 999px; background: var(--bg, #F3F3F3); direction: ltr; overflow: hidden; }
.mh-ex-bar i { display: block; height: 100%; border-radius: 999px; background: var(--tab-market); opacity: 0.4; transform-origin: left; animation: mhGrow 1.1s cubic-bezier(0.2, 0.8, 0.2, 1) both 0.3s; }
.mh-ex-row--lead .mh-ex-bar i { opacity: 1; animation-delay: 0.55s; }
.mh-ex-row b { text-align: center; }
.mh-ex-row--lead b { color: var(--tab-market-ink); }
.mh-ex-eq { margin: 0; display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px; font-size: 18px; font-weight: 800; }
.mh-ex-eq small { font-size: 11.5px; font-weight: 500; color: var(--text-secondary, #5C5C5C); margin-inline-end: 4px; }
.mh-ex-eq em { font-style: normal; color: var(--text-secondary, #5C5C5C); }
.mh-ex-eq strong { color: var(--tab-market-ink); font-size: 22px; }
.mh-how-note { margin: 10px 0 0; font-size: 12px; color: var(--text-secondary, #5C5C5C); }
@keyframes mhGrow { from { transform: scaleX(0); } }
@media (max-width: 760px) { .mh-steps { grid-template-columns: 1fr; } }
.mh-h { margin: 4px 0 0; font-size: 15px; font-weight: 800; }
.mh-race { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.mh-race li {
  opacity: 0; transform: translateX(-18px);
  transition: opacity 0.5s ease calc(var(--i) * 70ms), transform 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) calc(var(--i) * 70ms);
}
.mh-race--in li { opacity: 1; transform: none; }
.mh-row {
  transition: border-color 0.2s, background-color 0.25s, transform 0.2s;
  width: 100%; display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(90px, 1fr) 110px 18px; align-items: center; gap: 12px;
  padding: 10px 14px; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 12px; background: #fff;
  font: inherit; text-align: start; cursor: pointer;
}
.mh-row:hover { border-color: var(--tab-market); background: var(--tab-market-wash); transform: translateY(-1px); }
.mh-row:hover .mh-bar { background: rgba(255, 255, 255, 0.85); }
.mh-row:hover .mh-chev { color: var(--tab-market-ink); transform: translateX(-3px); }
.mh-chev { transition: transform 0.2s, color 0.2s; }
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
@media (max-width: 640px) {
  .mh-row { grid-template-columns: minmax(0, 1fr) 96px; }
  .mh-bar { grid-column: 1 / -1; grid-row: 2; }
  .mh-chev { display: none; }
}
@media (prefers-reduced-motion: reduce) { .mh-race li, .mh-bar i { transition: none; opacity: 1; transform: none; } .mh-ex-bar i { animation: none; } .mh-how { transition: none; } }
</style>
