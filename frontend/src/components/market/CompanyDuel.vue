<template>
  <section class="cd2">
  <!-- דו-קרב חברות — two companies, track type against track type (compare_companies). A classic scoreboard
       (not a game): the two names, digits that roll to the score, the verdict line; then the pairs, winner solid.
       Companies are picked as chips: tap a slot (A/B), then a company; ⇄ swaps them. -->
    <nav class="cd2-cats">
      <button v-for="c in MARKET_CATEGORIES" :key="c.id" type="button" :class="{ on: cat === c.id }" @click="cat = c.id">{{ c.label }}</button>
    </nav>

    <div class="cd2-pick">
      <button type="button" class="cd2-slot" :class="{ on: slot === 'a' }" @click="slot = slot === 'a' ? null : 'a'">
        <small>חברה ראשונה</small><b>{{ a }}</b>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      <button type="button" class="cd2-swap" aria-label="החלפת צדדים" title="החלפת צדדים" @click="swap">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 7h11l-3-3M17 17H6l3 3" /></svg>
      </button>
      <button type="button" class="cd2-slot" :class="{ on: slot === 'b' }" @click="slot = slot === 'b' ? null : 'b'">
        <small>חברה שנייה</small><b>{{ b }}</b>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6" /></svg>
      </button>
    </div>
    <div class="cd2-chips" :class="{ open: !!slot }">
      <div class="cd2-chips-in">
        <p>בחרו את ה{{ slot === 'b' ? 'חברה השנייה' : 'חברה הראשונה' }}:</p>
        <div>
          <button v-for="c in MARKET_COMPANIES" :key="c" type="button" :disabled="c === (slot === 'a' ? b : a)"
                  :class="{ on: c === (slot === 'a' ? a : b) }" @click="pick(c)">{{ c }}</button>
        </div>
      </div>
    </div>

    <div v-if="loading && !data" class="cd2-wait">משווה…</div>
    <template v-if="data">
      <p v-if="data.found === false" class="cd2-note cd2-note--box">{{ data.note }}</p>
      <template v-else>
        <div class="cd2-board" :class="{ 'cd2-board--busy': loading }">
          <div class="cd2-team" :class="{ lead: score(A) > score(B) }">
            <span class="cd2-name">{{ A }}</span>
            <span class="cd2-digits ltr-number" :aria-label="String(score(A))">
              <span v-for="(d, i) in digits(score(A))" :key="'a' + i" class="cd2-reel"><span :style="{ transform: `translateY(-${d * 10}%)` }"><i v-for="n in 10" :key="n">{{ n - 1 }}</i></span></span>
            </span>
          </div>
          <div class="cd2-mid">
            <span class="cd2-colon">:</span>
            <small>מתוך <span class="ltr-number">{{ (data.pairs || []).length }}</span> זוגות</small>
          </div>
          <div class="cd2-team" :class="{ lead: score(B) > score(A) }">
            <span class="cd2-name">{{ B }}</span>
            <span class="cd2-digits ltr-number" :aria-label="String(score(B))">
              <span v-for="(d, i) in digits(score(B))" :key="'b' + i" class="cd2-reel"><span :style="{ transform: `translateY(-${d * 10}%)` }"><i v-for="n in 10" :key="n">{{ n - 1 }}</i></span></span>
            </span>
          </div>
        </div>
        <p class="cd2-verdict">{{ data.verdict }}</p>

        <ul class="cd2-pairs" :key="cat + A + B">
          <li class="cd2-head"><span>{{ A }}</span><span>סוג מסלול</span><span>{{ B }}</span></li>
          <li v-for="(p, i) in data.pairs" :key="p.track_type" :style="{ '--i': i }">
            <span class="cd2-side cd2-side--a" :class="{ win: p.winner_3y === A }">
              <b class="ltr-number">{{ fmt(p[A].avg_yield_3y) }}</b>
              <span class="cd2-bar"><i :style="{ width: pct(p[A].avg_yield_3y) + '%' }"></i></span>
            </span>
            <span class="cd2-type">
              <svg v-if="p.winner_3y === A" class="cd2-win" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12l4 4 10-10" /></svg>
              {{ typeLabel(p.track_type) }}
              <svg v-if="p.winner_3y === B" class="cd2-win" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12l4 4 10-10" /></svg>
            </span>
            <span class="cd2-side cd2-side--b" :class="{ win: p.winner_3y === B }">
              <span class="cd2-bar"><i :style="{ width: pct(p[B].avg_yield_3y) + '%' }"></i></span>
              <b class="ltr-number">{{ fmt(p[B].avg_yield_3y) }}</b>
            </span>
          </li>
        </ul>
        <p v-if="onlyIn" class="cd2-note">{{ onlyIn }}</p>
        <p class="cd2-note">תשואה שנתית ממוצעת 3 שנים · המסלול הגדול של כל חברה מכל סוג · נתוני {{ data.data_month }} · {{ data.disclaimer }}</p>
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
const slot = ref(null)
const data = ref(null)
const loading = ref(false)
const A = computed(() => data.value?.companies?.[0] || a.value)
const B = computed(() => data.value?.companies?.[1] || b.value)
const shown = ref({})

function pick(c) {
  if (slot.value === 'a') a.value = c
  else if (slot.value === 'b') b.value = c
  slot.value = null
}
function swap() { const t = a.value; a.value = b.value; b.value = t }

async function load() {
  loading.value = true
  try { data.value = await store.loadDuel(cat.value, a.value, b.value) } finally { loading.value = false }
  roll()
}
watch([cat, a, b], load)
onMounted(load)

const score = (co) => shown.value[co] ?? 0
const digits = (n) => String(Math.max(0, Math.round(n))).padStart(2, '0').split('').map(Number)
// the reels roll from 0 to the score (a short visible turn, not a casino spin)
function roll() {
  const w = data.value?.wins_3y || {}
  const target = { [A.value]: w[A.value] || 0, [B.value]: w[B.value] || 0 }
  shown.value = { [A.value]: 0, [B.value]: 0 }
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { shown.value = target; return }
  requestAnimationFrame(() => setTimeout(() => { shown.value = target }, 120))
}

const top = computed(() => Math.max(1, ...((data.value?.pairs || []).flatMap((p) => [p[A.value]?.avg_yield_3y || 0, p[B.value]?.avg_yield_3y || 0]))))
const pct = (v) => Math.max(4, Math.round(((v || 0) / top.value) * 100))
const fmt = (v) => (v == null ? '' : v.toFixed(2) + '%')
const typeLabel = (t) => (t || '').split(' ').slice(1).join(' ') || t
const onlyIn = computed(() => {
  const o = data.value?.only_in || {}
  const parts = Object.entries(o).filter(([, v]) => v && v.length).map(([co, v]) => `רק ב${co}: ${v.slice(0, 4).map(typeLabel).join(', ')}`)
  return parts.length ? parts.join(' · ') : ''
})
</script>

<style scoped>
.cd2 { display: flex; flex-direction: column; gap: 14px; }
.cd2-cats { display: flex; gap: 18px; border-bottom: 1px solid var(--border-subtle, #E5E5E5); }
.cd2-cats button {
  border: none; background: none; padding: 8px 2px; font: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  color: var(--text-secondary, #5C5C5C); border-bottom: 2.5px solid transparent; margin-bottom: -1px; transition: color 0.2s;
}
.cd2-cats button:hover { color: var(--tab-market-ink); }
.cd2-cats button.on { color: var(--tab-market-ink); border-bottom-color: var(--tab-market); }

.cd2-pick { display: grid; grid-template-columns: 1fr auto 1fr; gap: 10px; align-items: center; }
.cd2-slot {
  display: grid; grid-template-columns: 1fr auto; grid-template-rows: auto auto; align-items: center; column-gap: 8px; text-align: start;
  padding: 10px 14px; border-radius: 14px; border: 1.5px solid var(--border-subtle, #E5E5E5); background: #fff; cursor: pointer; font: inherit;
  transition: border-color 0.2s, background-color 0.25s;
}
.cd2-slot small { grid-column: 1; font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.cd2-slot b { grid-column: 1; font-size: 18px; font-weight: 900; }
.cd2-slot svg { grid-column: 2; grid-row: 1 / 3; color: var(--text-secondary, #5C5C5C); transition: transform 0.25s; }
.cd2-slot:hover { border-color: var(--tab-market); background: var(--tab-market-wash); }
.cd2-slot.on { border-color: var(--tab-market-ink); background: var(--tab-market-wash); }
.cd2-slot.on svg { transform: rotate(180deg); color: var(--tab-market-ink); }
.cd2-swap {
  width: 42px; height: 42px; border-radius: 50%; border: 1.5px solid var(--border-subtle, #E5E5E5); background: #fff; cursor: pointer;
  display: grid; place-items: center; color: var(--tab-market-ink); transition: transform 0.4s cubic-bezier(0.34, 1.4, 0.5, 1), background-color 0.2s;
}
.cd2-swap:hover { background: var(--tab-market-wash); transform: rotate(180deg); }
.cd2-chips { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.45s cubic-bezier(0.2, 0.8, 0.2, 1); }
.cd2-chips.open { grid-template-rows: 1fr; }
.cd2-chips-in { overflow: hidden; min-height: 0; }
.cd2-chips p { margin: 0 0 8px; font-size: 13px; font-weight: 700; color: var(--text-secondary, #5C5C5C); }
.cd2-chips-in > div { display: flex; flex-wrap: wrap; gap: 6px; padding-bottom: 2px; }
.cd2-chips button {
  padding: 7px 14px; border-radius: 999px; border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; cursor: pointer;
  font: inherit; font-size: 13.5px; font-weight: 700; transition: all 0.2s;
}
.cd2-chips button:hover:not(:disabled) { border-color: var(--tab-market); background: var(--tab-market-wash); color: var(--tab-market-ink); }
.cd2-chips button.on { background: var(--tab-market-ink); border-color: var(--tab-market-ink); color: #fff; }
.cd2-chips button:disabled { opacity: 0.35; cursor: default; }

.cd2-wait { padding: 24px; text-align: center; color: var(--text-secondary, #5C5C5C); }
/* the scoreboard — calm, classic: ink panel, two names, rolling digits */
.cd2-board {
  display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; padding: 18px 22px; border-radius: 18px;
  background: linear-gradient(180deg, #1B365D 0%, #12253F 100%); color: #F4F4EE;
  box-shadow: 0 14px 34px rgba(30, 32, 16, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.06); transition: opacity 0.2s;
}
.cd2-board--busy { opacity: 0.6; }
.cd2-team { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.cd2-name { font-size: 15px; font-weight: 800; letter-spacing: 0.02em; color: rgba(244, 244, 238, 0.75); }
.cd2-team.lead .cd2-name { color: #C9DBF3; }
.cd2-digits { display: flex; gap: 6px; }
.cd2-reel {
  position: relative; width: 46px; height: 64px; overflow: hidden; border-radius: 10px;
  background: linear-gradient(180deg, #24406A 0%, #1B365D 50%, #24406A 100%); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.07);
}
.cd2-reel::after { content: ''; position: absolute; left: 0; right: 0; top: 50%; height: 1px; background: rgba(0, 0, 0, 0.35); }
.cd2-reel > span { display: flex; flex-direction: column; transition: transform 1.2s cubic-bezier(0.2, 0.8, 0.2, 1); }
.cd2-reel i { height: 64px; flex-shrink: 0; display: grid; place-items: center; font-style: normal; font-size: 40px; font-weight: 900; color: #F4F4EE; }
.cd2-team.lead .cd2-reel i { color: #C9DBF3; }
.cd2-mid { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.cd2-colon { font-size: 36px; font-weight: 900; color: rgba(244, 244, 238, 0.45); line-height: 1; }
.cd2-mid small { font-size: 12px; color: rgba(244, 244, 238, 0.6); }
.cd2-verdict { margin: 0; text-align: center; font-size: 14px; font-weight: 700; }

.cd2-pairs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.cd2-pairs li {
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(110px, 150px) minmax(0, 1fr); align-items: center; gap: 12px;
  padding: 9px 14px; border-radius: 12px; background: #fff; border: 1px solid var(--border-subtle, #E5E5E5);
  animation: cdIn 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 80ms); transition: background-color 0.25s, border-color 0.2s;
}
.cd2-pairs li:not(.cd2-head):hover { background: var(--tab-market-wash); border-color: var(--tab-market); }
.cd2-pairs li.cd2-head { background: none; border: none; padding: 0 14px; font-size: 12px; font-weight: 700; color: var(--text-secondary, #5C5C5C); animation: none; }
.cd2-head span:nth-child(2) { text-align: center; }
.cd2-head span:nth-child(3) { text-align: end; }
.cd2-side { display: flex; align-items: center; gap: 10px; }
.cd2-side b { font-size: 13.5px; font-weight: 600; color: var(--text-secondary, #5C5C5C); min-width: 56px; }
.cd2-side--a b { text-align: start; }
.cd2-side--b b { text-align: end; }
.cd2-side.win b { color: var(--tab-market-ink); font-weight: 900; }
.cd2-bar { flex: 1; height: 12px; border-radius: 999px; background: var(--bg, #F3F3F3); overflow: hidden; display: flex; }
/* RTL row: both bars are anchored at the middle column */
.cd2-side--a .cd2-bar { justify-content: flex-end; }
.cd2-side--b .cd2-bar { justify-content: flex-start; }
.cd2-bar i { display: block; height: 100%; border-radius: 999px; background: var(--tab-market); opacity: 0.32; animation: cdGrow 1s cubic-bezier(0.2, 0.8, 0.2, 1) both; animation-delay: calc(var(--i) * 80ms + 200ms); }
.cd2-side--a .cd2-bar i { transform-origin: left; }
.cd2-side--b .cd2-bar i { transform-origin: right; }
.cd2-side.win .cd2-bar i { opacity: 1; }
.cd2-type { display: flex; align-items: center; justify-content: center; gap: 6px; text-align: center; font-size: 13.5px; font-weight: 800; }
.cd2-win { color: var(--tab-market-ink); flex-shrink: 0; }
.cd2-note { margin: 0; font-size: 12.5px; color: var(--text-secondary, #5C5C5C); }
.cd2-note--box { padding: 14px; border-radius: 12px; background: #fff; }
@keyframes cdIn { from { opacity: 0; transform: translateY(8px); } }
@keyframes cdGrow { from { transform: scaleX(0); } }
@media (max-width: 640px) {
  .cd2-reel { width: 34px; height: 48px; } .cd2-reel i { height: 48px; font-size: 30px; }
  .cd2-pairs li { grid-template-columns: minmax(0, 1fr) 84px minmax(0, 1fr); gap: 6px; padding: 8px; }
  .cd2-side b { min-width: 46px; font-size: 12.5px; }
  .cd2-slot b { font-size: 16px; }
}
@media (prefers-reduced-motion: reduce) { .cd2-pairs li, .cd2-bar i { animation: none; } .cd2-reel > span { transition: none; } }
</style>
