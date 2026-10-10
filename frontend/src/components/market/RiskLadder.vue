<template>
  <ol class="rl" :class="{ 'rl--in': shown }" :style="{ '--rl-accent': accent, '--rl-ink': ink }">
  <!-- One risk-level group, in rank order. Bars grow in a cascade (top first), the leader is marked,
       and the customer's track ("is_this") lights up with a dot that rides up to its place. -->
    <li v-for="(t, i) in rows" :key="t.fund_id || t.fund" class="rl-row"
        :class="{ 'rl-row--me': t.is_this, 'rl-row--lead': t.rank === 1 }" :style="{ '--i': i }">
      <span class="rl-rank ltr-number">#{{ t.rank }}</span>
      <span class="rl-name" :title="t.fund">
        {{ label(t) }}
        <b v-if="t.rank === 1" class="rl-tag">מוביל</b>
        <b v-if="t.is_this" class="rl-tag rl-tag--me">המסלול של הלקוח</b>
      </span>
      <span class="rl-bar"><i :style="{ width: pct(t) + '%' }"><em v-if="t.is_this" class="rl-dot"></em></i></span>
      <span class="rl-val"><span v-if="t.avg_yield_3y != null" class="ltr-number">{{ t.avg_yield_3y.toFixed(2) }}%</span></span>
      <button v-if="t.customers && t.customers.length" type="button" class="rl-cust"
              @click="$emit('customers', t, $event.currentTarget)">
        <span class="ltr-number">{{ t.customers.length }}</span> לקוחות שלך
      </button>
    </li>
  </ol>
  <p v-if="caption && rows.length" class="rl-cap">הדירוג — לפי ציון משולב (תשואה 12 חודשים, 3 ו-5 שנים, שארפ, דמי ניהול). הבר — תשואה שנתית ממוצעת 3 שנים.</p>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  tracks: { type: Array, default: () => [] },
  max: { type: Number, default: 14 },        // long groups: the top rows + the customer's row
  accent: { type: String, default: 'var(--tab-market)' },
  ink: { type: String, default: 'var(--tab-market-ink)' },
  caption: { type: Boolean, default: true },
})
defineEmits(['customers'])

const rows = computed(() => {
  const all = props.tracks || []
  if (all.length <= props.max) return all
  const head = all.slice(0, props.max - 1)
  const me = all.find((t) => t.is_this && !head.includes(t))
  return me ? [...head, me] : all.slice(0, props.max)
})
const top = computed(() => Math.max(1, ...rows.value.map((t) => t.avg_yield_3y || 0)))
const pct = (t) => Math.max(3, Math.round(((t.avg_yield_3y || 0) / top.value) * 100))
const label = (t) => (t.fund || '').replace(/\s*-\s*/g, ' ').replace(/קופת גמל לחיסכון,.*?-\s*/, '')
const shown = ref(false)
onMounted(() => requestAnimationFrame(() => { shown.value = true }))
</script>

<style scoped>
.rl { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rl-row {
  display: grid; grid-template-columns: 44px minmax(0, 1.4fr) minmax(80px, 1fr) 64px 112px; align-items: center; gap: 10px;
  padding: 7px 10px; border-radius: 10px; font-size: 13.5px; color: var(--text-primary, #181818);
  opacity: 0; transform: translateY(10px);
  transition: opacity 0.5s ease calc(var(--i) * 55ms), transform 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) calc(var(--i) * 55ms);
}
.rl--in .rl-row { opacity: 1; transform: none; }
.rl-row--me { background: var(--tab-market-wash); box-shadow: inset 0 0 0 1.5px var(--rl-accent); font-weight: 700; }
.rl-rank { color: var(--text-secondary, #5C5C5C); font-weight: 700; }
.rl-row--lead .rl-rank, .rl-row--me .rl-rank { color: var(--rl-ink); }
.rl-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rl-tag {
  margin-inline-start: 6px; padding: 1px 7px; border-radius: 999px; font-size: 11px; font-weight: 800;
  color: var(--rl-ink); background: var(--tab-market-wash);
}
.rl-tag--me { color: #fff; background: var(--rl-ink); }
.rl-bar { height: 10px; border-radius: 999px; background: var(--bg, #F3F3F3); overflow: visible; direction: ltr; }
.rl-bar i {
  position: relative; display: block; height: 100%; border-radius: 999px; background: var(--rl-accent); opacity: 0.35;
  transform-origin: left center; transform: scaleX(0);
  transition: transform 0.9s cubic-bezier(0.2, 0.8, 0.2, 1) calc(var(--i) * 55ms + 120ms);
}
.rl--in .rl-bar i { transform: scaleX(1); }
.rl-row--me .rl-bar i, .rl-row--lead .rl-bar i { opacity: 0.85; }
.rl-dot {
  position: absolute; right: -7px; top: 50%; width: 14px; height: 14px; margin-top: -7px; border-radius: 50%;
  background: var(--rl-ink); box-shadow: 0 0 0 3px #fff, 0 0 0 5px var(--rl-accent);
  animation: rlPulse 2.2s ease-in-out infinite 1.4s;
}
@keyframes rlPulse { 50% { box-shadow: 0 0 0 3px #fff, 0 0 0 9px rgba(122, 127, 42, 0.25); } }
.rl-val { text-align: center; font-weight: 700; }
.rl-cust {
  justify-self: start; border: none; cursor: pointer; padding: 3px 10px; border-radius: 999px; font: inherit; font-size: 12px; font-weight: 700;
  color: var(--rl-ink); background: var(--tab-market-wash);
}
.rl-cap { margin: 6px 0 0; font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.rl-cust:hover { background: var(--rl-accent); color: #fff; }
@media (max-width: 640px) {
  .rl-row { grid-template-columns: 36px minmax(0, 1fr) 58px; }
  .rl-name { white-space: normal; }   /* phones: wrap, so the מוביל / המסלול של הלקוח tag stays visible */
  .rl-bar, .rl-cust { grid-column: 1 / -1; }
}
@media (prefers-reduced-motion: reduce) {
  .rl-row, .rl-bar i { transition: none; opacity: 1; transform: none; }
  .rl-dot { animation: none; }
}
</style>
