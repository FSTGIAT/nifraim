<template>
  <!-- One recruit per card — the drills' row pattern (name + ID, muted context,
       the figure the agent acts on, a chevron). Shared by the found / missing /
       company / product drills so their numbers come from the same fields. -->
  <ul class="rcd">
    <li v-for="(r, i) in items" :key="r.recruit_id" class="rcd-card"
        :class="{ 'rcd-card--on': selectable && selected.has(r.recruit_id) }"
        :style="{ '--d': Math.min(i, 12) * 30 + 'ms' }"
        role="button" tabindex="0"
        @click="emit('pick', r, $event.currentTarget)"
        @keydown.enter.prevent="emit('pick', r, $event.currentTarget)">
      <label v-if="selectable" class="rcd-check" @click.stop @keydown.stop>
        <input type="checkbox" :checked="selected.has(r.recruit_id)" @change="emit('toggle', r.recruit_id)" />
      </label>
      <span class="rcd-who">
        <strong>{{ fullName(r) || 'ללא שם' }}</strong>
        <small class="ltr-number">{{ r.id_number }}</small>
        <small v-if="r.company || r.product" class="rcd-ctx">{{ [r.company, r.product].filter(Boolean).join(' · ') }}</small>
      </span>
      <span v-if="r.found_in_production" class="rcd-pill">
        <span class="ltr-number">{{ r.production_products.length }}</span> מוצרים
      </span>
      <span v-else class="rcd-pill rcd-pill--miss">לא נמצא</span>
      <span class="rcd-fig">
        <template v-if="r.found_in_production && r.production_premium >= 0.5">
          <span class="ltr-number">{{ money(r.production_premium) }}</span><small>פרמיה</small>
        </template>
        <template v-else-if="!r.found_in_production && r.amount >= 0.5">
          <span class="ltr-number">{{ money(r.amount) }}</span><small>העברה</small>
        </template>
      </span>
      <span v-if="$slots.status && !r.found_in_production" class="rcd-status" @click.stop @keydown.stop>
        <slot name="status" :item="r" />
      </span>
      <svg class="rcd-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
    </li>
  </ul>
</template>

<script setup>
const props = defineProps({
  items: { type: Array, default: () => [] },
  selectable: { type: Boolean, default: false },
  selected: { type: Set, default: () => new Set() },
})
const emit = defineEmits(['pick', 'toggle'])

const fullName = (r) => `${r.first_name || ''} ${r.last_name || ''}`.trim()
const money = (v) => '₪' + Math.round(Number(v) || 0).toLocaleString('he-IL')
</script>

<style scoped>
.rcd { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.rcd-card {
  display: grid; align-items: center; gap: 12px;
  grid-template-columns: auto minmax(0, 1fr) auto 110px auto auto;
  grid-template-areas: "check who pill fig status chev";
  padding: 11px 14px; border: 1px solid var(--border-subtle); border-radius: 12px;
  background: var(--card-bg); cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease, background 0.15s ease;
  animation: rcdIn 0.35s cubic-bezier(0.2, 0, 0.2, 1) both; animation-delay: var(--d);
}
@keyframes rcdIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.rcd-card:hover { border-color: var(--tab-recruits); transform: translateY(-1px); }
.rcd-card:focus-visible { outline: 2px solid var(--tab-recruits-ink); outline-offset: 2px; }
.rcd-card--on { background: var(--tab-recruits-wash); border-color: var(--tab-recruits); }
.rcd-check { grid-area: check; display: flex; }
.rcd-check input { width: 16px; height: 16px; accent-color: var(--tab-recruits-ink); cursor: pointer; }
.rcd-who { grid-area: who; display: flex; flex-direction: column; min-width: 0; }
.rcd-who strong { font-size: 14px; font-weight: 700; color: var(--text); }
.rcd-who small { font-size: 12px; color: var(--text-muted); align-self: flex-start; max-width: 100%; }
.rcd-ctx { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rcd-pill {
  grid-area: pill; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px;
  background: var(--tab-recruits-wash); color: var(--tab-recruits-ink); white-space: nowrap;
}
.rcd-pill--miss { background: var(--bg); color: var(--text-secondary); }
.rcd-fig { grid-area: fig; display: flex; flex-direction: column; align-items: flex-start; font-size: 15px; font-weight: 800; color: var(--text); }
.rcd-fig small { font-size: 11px; font-weight: 500; color: var(--text-muted); }
.rcd-status { grid-area: status; }
.rcd-chev { grid-area: chev; color: var(--text-muted); }
.rcd-card:not(:has(.rcd-check)) { grid-template-columns: minmax(0, 1fr) auto 110px auto auto; grid-template-areas: "who pill fig status chev"; }
@media (max-width: 640px) {
  .rcd-card { grid-template-columns: auto minmax(0, 1fr) auto; grid-template-areas: "check who fig" "check pill status"; }
  .rcd-card:not(:has(.rcd-check)) { grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "who fig" "pill status"; }
  .rcd-pill { justify-self: start; }
  .rcd-chev { display: none; }
}
@media (prefers-reduced-motion: reduce) { .rcd-card { animation: none; transition: none; } }
</style>
