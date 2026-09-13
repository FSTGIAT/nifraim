<template>
  <div class="cpr">
    <div class="cpr-row cpr-head">
      <span>מוצר</span>
      <span class="cpr-keys">
        <i class="cpr-key cpr-key--prem"></i>פרמיה
        <i class="cpr-key cpr-key--acc"></i>צבירה
      </span>
      <span>פרמיה</span>
      <span>צבירה</span>
      <span>לקוחות</span>
    </div>

    <p v-if="!rows.length" class="cpr-none">אין מוצרים בקטגוריה זו</p>

    <ul v-else class="cpr-list">
      <li v-for="(p, i) in rows" :key="p.product"
          class="cpr-row" :class="{ 'cpr-row--in': shown }"
          :style="{ transitionDelay: Math.min(i, 12) * 30 + 'ms' }"
          @click="$emit('drill', p)">
        <span class="cpr-name" :title="p.product">{{ p.product }}</span>
        <span class="cpr-track">
          <span class="cpr-bar cpr-bar--prem" :style="{ width: bar(p.premium, maxPrem) }"></span>
          <span class="cpr-bar cpr-bar--acc" :style="{ width: bar(p.accumulation, maxAcc) }"></span>
        </span>
        <!-- BOTH measures on every row, whichever side the product sits on.
             A product can carry premium AND accumulation at once, and showing
             only its category's measure made the other one disappear: a company
             card reading ₪1,774,008 צבירה opened onto a breakdown that listed
             premium alone and "אין מוצרים" under פיננסים, with the ₪1.77M
             visible nowhere. -->
        <span class="cpr-val ltr-number" :class="{ 'cpr-zero': !p.premium }">
          {{ p.premium ? money(p.premium) : '—' }}
        </span>
        <span class="cpr-val ltr-number" :class="{ 'cpr-zero': !p.accumulation }">
          {{ p.accumulation ? money(p.accumulation) : '—' }}
        </span>
        <span class="cpr-clients ltr-number">{{ p.clients }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { money } from '../../utils/chartDefaults'

const props = defineProps({ rows: { type: Array, default: () => [] } })
defineEmits(['drill'])
const shown = ref(false)

// Premium and accumulation are different quantities on wildly different scales
// (a monthly payment vs a balance), so each gets its own scale. The bars
// compare a product with the other products on the SAME measure — never
// premium against accumulation.
const maxPrem = computed(
  () => Math.max(1, ...props.rows.map(p => Number(p.premium) || 0)),
)
const maxAcc = computed(
  () => Math.max(1, ...props.rows.map(p => Number(p.accumulation) || 0)),
)

function bar(v, max) {
  // `max` arrives ALREADY UNWRAPPED: Vue unwraps top-level refs in template
  // expressions, so reading `.value` here yielded undefined → NaN% → a 0px bar
  // on every row while the rows themselves rendered fine.
  const limit = Number(max) || 1
  const n = Math.abs(Number(v) || 0)
  if (!shown.value || !n) return '0%'
  return Math.max(1.5, (n / limit) * 100) + '%'
}

function play() {
  shown.value = false
  requestAnimationFrame(() => requestAnimationFrame(() => { shown.value = true }))
}
onMounted(play)
watch(() => props.rows, play)
</script>

<style scoped>
.cpr-list { list-style: none; display: flex; flex-direction: column; }
.cpr-row {
  display: grid;
  grid-template-columns: minmax(96px, 1.2fr) 1.3fr 92px 108px 58px;
  align-items: center; gap: 12px;
  padding: 8px; border-bottom: 1px solid var(--border-subtle);
  opacity: 0; transform: translateY(4px);
  transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.2, 0, 0.2, 1);
  cursor: pointer;
}
.cpr-row--in { opacity: 1; transform: none; }
.cpr-row:last-child { border-bottom: none; }
.cpr-row:hover { background: var(--border-subtle); }

.cpr-row.cpr-head {
  font-size: 11px; color: var(--text-muted); cursor: default;
  opacity: 1; transform: none; transition: none;
  border-bottom: 1px solid var(--border-subtle); padding-bottom: 7px;
}
.cpr-row.cpr-head:hover { background: none; }
.cpr-row.cpr-head > span:not(:first-child):not(.cpr-keys) { text-align: left; }
.cpr-keys { display: flex; align-items: center; gap: 6px; }
.cpr-keys .cpr-key:not(:first-child) { margin-right: 8px; }
.cpr-key { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.cpr-key--prem { background: var(--chart-9); }
.cpr-key--acc { background: var(--chart-7); }

.cpr-name {
  font-size: 13px; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cpr-track { display: flex; flex-direction: column; gap: 3px; direction: ltr; }
.cpr-bar {
  display: block; height: 8px; border-radius: 4px;
  transition: width 0.55s cubic-bezier(0.2, 0, 0.2, 1);
}
.cpr-bar--prem { background: var(--chart-9); }
.cpr-bar--acc { background: var(--chart-7); }

.cpr-val { font-size: 12px; font-weight: 600; color: var(--text); text-align: left; }
.cpr-zero { color: var(--text-muted); font-weight: 500; }
.cpr-clients { font-size: 12px; color: var(--text-muted); text-align: left; }
.cpr-none { font-size: 13px; color: var(--text-muted); padding: 14px 4px; }

@media (prefers-reduced-motion: reduce) {
  .cpr-row { opacity: 1; transform: none; transition: none; }
  .cpr-bar { transition: none; }
}
</style>
