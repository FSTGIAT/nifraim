<template>
  <div class="pr">
    <div class="pr-legend">
      <span><i class="pr-key pr-key--paid"></i>שולם בפועל</span>
      <span><i class="pr-key pr-key--agreed"></i>לפי ההסכם</span>
      <span class="pr-legend-cols">שולם · לפי ההסכם · שיעור · הפרש · שורות</span>
    </div>

    <ul class="pr-list">
      <li v-for="(p, i) in ordered" :key="p.product"
          class="pr-row" :class="{ 'pr-row--in': shown, 'pr-row--soft': isEstimate(p) }"
          :style="{ transitionDelay: Math.min(i, 14) * 30 + 'ms' }">
        <span class="pr-name" :title="p.product">
          {{ p.product }}
          <!-- Own tooltip rather than the browser's: a native `title` rendered
               a black box that covered the row beside it. -->
          <span v-if="p.estimated" class="pr-est" :data-tip="estTip(p)">≈</span>
        </span>

        <span class="pr-track">
          <span class="pr-bar pr-bar--paid" :style="{ width: w(p.paid) }"></span>
          <span class="pr-bar pr-bar--agreed" :style="{ width: w(p.expected) }"></span>
        </span>

        <span class="pr-val ltr-number">{{ money(p.paid) }}</span>
        <!-- The expected figure carries its own derivation: base × rate. The
             question "where does this number come from" should not require
             reading the code. -->
        <span class="pr-val pr-val--muted ltr-number" :title="formula(p)">
          {{ money(p.expected) }}
        </span>
        <span class="pr-rate ltr-number" :class="{ 'pr-rate--soft': !p.firm }"
              :title="p.firm ? 'שיעור מההסכם, למוצר הזה' : 'אין שיעור למוצר הזה בהסכם — חושב לפי ברירת מחדל'">
          {{ p.rate ? pctText(p.rate) : '—' }}
        </span>
        <span class="pr-diff ltr-number" :class="tone(p)">
          {{ isEstimate(p) ? '—' : signedMoney(p.paid - p.expected) }}
        </span>
        <span class="pr-rows ltr-number">{{ p.records }}</span>
      </li>
    </ul>

    <button v-if="hidden && !expanded" class="pr-more" @click="expanded = true">
      הצג עוד {{ hidden }} מוצרים
    </button>

    <p class="pr-foot">
      <span class="pr-est pr-est--static">≈</span>
      מוצר שחלק משורותיו אינן נושאות שיעור עמלה מפורש בהסכם. שיעור שנגזר מברירת מחדל
      אינו טענה על חוב — כשכל השורות כאלה, ההפרש אינו מוצג כלל.
    </p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { money, signedMoney } from '../../utils/chartDefaults'

const GAP_MIN_PCT = 10
const GAP_MIN_SHEKEL = 100

const props = defineProps({ products: { type: Array, default: () => [] } })
const shown = ref(false)

const TOP = 12

const sorted = computed(
  () => [...props.products].sort((a, b) => (b.paid || 0) - (a.paid || 0)),
)
const expanded = ref(false)
const ordered = computed(
  () => (expanded.value ? sorted.value : sorted.value.slice(0, TOP)),
)
const hidden = computed(() => Math.max(0, sorted.value.length - TOP))

// One scale across the visible rows — but a WHOLLY-ESTIMATED expected is not a
// real figure, and letting it set the scale destroys the chart. מנורה's
// "מבטחים יותר" carries a fallback expected of ₪12,001 against ₪361 paid; with
// it in the scale, all 62 other products rendered as 1px slivers. Those bars
// are clamped instead, and the row already reads "—" with a ≈.
const max = computed(() => Math.max(
  1,
  ...ordered.value.map(p => Number(p.paid) || 0),
  ...ordered.value.filter(p => !isEstimate(p)).map(p => Number(p.expected) || 0),
))

function w(v) {
  if (!shown.value) return '0%'
  const pct = (Math.abs(Number(v) || 0) / max.value) * 100
  return Math.min(100, Math.max(1.5, pct)) + '%'
}

/** Every row priced off a fallback rate — there is no claim here. */
function isEstimate(p) {
  return (p.estimated || 0) >= (p.records || 0)
}

function tone(p) {
  if (isEstimate(p) || p.estimated) return 'is-none'
  const diff = (p.paid || 0) - (p.expected || 0)
  const base = Math.abs(Number(p.expected) || 0)
  if (Math.abs(diff) < GAP_MIN_SHEKEL) return 'is-none'
  if (base && (Math.abs(diff) / base) * 100 < GAP_MIN_PCT) return 'is-none'
  return diff < 0 ? 'is-down' : 'is-up'
}

function estTip(p) {
  return `${p.estimated} מתוך ${p.records} שורות ללא שיעור עמלה מפורש בהסכם`
}

function pctText(rate) {
  const n = Number(rate) * 100
  return (n < 1 ? n.toFixed(3) : n.toFixed(2)) + '%'
}

/** "₪8,513 פרמיה × 19.2% = ₪1,635" — the arithmetic behind the expected cell. */
function formula(p) {
  if (!p.rate || !p.base) return ''
  const basis = p.basis === 'accumulation' ? 'צבירה' : 'פרמיה'
  const per = p.basis === 'accumulation' ? ' ÷ 12' : ''
  return `${money(p.base)} ${basis} × ${pctText(p.rate)}${per} = ${money(p.expected)}`
}

function play() {
  expanded.value = false
  shown.value = false
  requestAnimationFrame(() => requestAnimationFrame(() => { shown.value = true }))
}
onMounted(play)
watch(() => props.products, play)
</script>

<style scoped>
.pr-legend {
  display: flex; gap: 16px; align-items: center;
  font-size: 11px; color: var(--text-muted); margin-bottom: 10px;
}
.pr-legend span { display: flex; align-items: center; gap: 6px; }
.pr-key { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.pr-key--paid { background: var(--chart-9); }
.pr-key--agreed { background: var(--text-muted); opacity: 0.38; }

.pr-list { list-style: none; display: flex; flex-direction: column; }
.pr-row {
  display: grid;
  grid-template-columns: minmax(110px, 1.3fr) 1.4fr 70px 70px 58px 70px 40px;
  align-items: center; gap: 12px;
  padding: 8px; border-bottom: 1px solid var(--border-subtle);
  opacity: 0; transform: translateY(4px);
  transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.2, 0, 0.2, 1);
}
.pr-row--in { opacity: 1; transform: none; }
.pr-row:last-child { border-bottom: none; }
.pr-row:hover { background: var(--border-subtle); }
/* A wholly-estimated row is context, not a finding — it recedes. */
.pr-row--soft .pr-name, .pr-row--soft .pr-val { opacity: 0.72; }

.pr-name {
  font-size: 13px; color: var(--text); display: flex; align-items: center; gap: 6px;
  overflow: hidden;
}
.pr-name > :first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.pr-track { display: flex; flex-direction: column; gap: 3px; direction: ltr; }
.pr-bar {
  display: block; height: 8px; border-radius: 4px;
  transition: width 0.6s cubic-bezier(0.2, 0, 0.2, 1);
}
.pr-bar--paid { background: var(--chart-9); }
.pr-bar--agreed { background: var(--text-muted); opacity: 0.38; }

.pr-val { font-size: 12px; font-weight: 600; color: var(--text); text-align: left; }
.pr-val--muted { color: var(--text-muted); font-weight: 500; }
.pr-diff { font-size: 12px; font-weight: 700; text-align: left; }
.pr-diff.is-up { color: var(--chart-gain); }
.pr-diff.is-down { color: var(--chart-loss); }
.pr-diff.is-none { color: var(--text-muted); font-weight: 500; }
.pr-rate { font-size: 12px; font-weight: 600; color: var(--text); text-align: left; cursor: help; }
/* A rate that came from a default is context, not the agreement's word. */
.pr-rate--soft { color: var(--text-muted); font-weight: 500; font-style: italic; }
.pr-legend-cols { margin-right: auto; }
.pr-rows { font-size: 11px; color: var(--text-muted); text-align: left; }

.pr-est {
  position: relative; flex-shrink: 0;
  width: 16px; height: 16px; line-height: 15px; text-align: center;
  border-radius: 50%; background: var(--border-subtle); color: var(--text-muted);
  font-size: 11px; font-weight: 700; cursor: help;
}
.pr-est--static { display: inline-block; cursor: default; vertical-align: -3px; }
.pr-est[data-tip]:hover::after {
  content: attr(data-tip);
  position: absolute; bottom: calc(100% + 6px); right: 0;
  white-space: nowrap; z-index: 5;
  background: var(--text); color: #fff;
  padding: 5px 9px; border-radius: var(--radius-sm);
  font-size: 11px; font-weight: 500;
}
.pr-more {
  margin-top: 10px; padding: 6px 14px; width: 100%;
  border: 1px dashed var(--border-subtle); border-radius: var(--radius-sm);
  background: none; color: var(--text-muted);
  font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
}
.pr-more:hover { color: var(--text); border-color: var(--text-muted); }
.pr-foot { font-size: 11px; color: var(--text-muted); margin-top: 14px; line-height: 1.7; }

@media (prefers-reduced-motion: reduce) {
  .pr-row { opacity: 1; transform: none; transition: none; }
  .pr-bar { transition: none; }
}
</style>
