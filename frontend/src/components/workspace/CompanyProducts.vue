<template>
  <!-- One company's book — redesigned (QA 2026-10-01): the old table put a
       two-colour bar pair on every row and a dash in every empty cell. Now a
       summary strip, then פיננסים and ביטוח as calm rows: one thin share bar
       in the tab colour, the section's main amount first, the other measure
       small beneath it only when it exists, never a dash. -->
  <div class="cp">
    <p v-if="company.entities && company.entities.length > 1" class="cp-entities">
      כולל {{ company.entities.join(' · ') }}
    </p>

    <div class="cp-stats">
      <div v-if="company.accumulation > 0" class="cp-stat">
        <span class="cp-lbl">צבירה</span>
        <span class="cp-val ltr-number">{{ money(company.accumulation) }}</span>
      </div>
      <div v-if="company.premium > 0" class="cp-stat">
        <span class="cp-lbl">פרמיה חודשית</span>
        <span class="cp-val ltr-number">{{ money(company.premium) }}</span>
      </div>
      <div v-if="company.commission > 0" class="cp-stat">
        <span class="cp-lbl">עמלה צפויה בחודש</span>
        <span class="cp-val ltr-number">{{ money(company.commission) }}</span>
      </div>
      <div class="cp-stat">
        <span class="cp-lbl">לקוחות</span>
        <span class="cp-val ltr-number">{{ (company.clients || 0).toLocaleString() }}</span>
      </div>
    </div>

    <section v-for="sec in sections" :key="sec.key" class="cp-sec">
      <h5 class="cp-sec-title">
        {{ sec.label }} <span class="ltr-number">{{ sec.rows.length }}</span>
        <small>לפי {{ sec.metricLabel }}</small>
      </h5>
      <ul class="cp-list">
        <li v-for="(p, i) in sec.rows" :key="p.product" :style="{ '--d': i * 35 + 'ms' }">
          <button class="cp-row" @click="$emit('drill', { category: sec.key, product: p.product })">
            <span class="cp-name">
              <span class="cp-name-txt" :title="p.label || p.product">{{ p.label || p.product }}</span>
              <span class="cp-share"><i :style="{ width: shown ? share(p, sec) : '0%' }"></i></span>
            </span>
            <span class="cp-fig">
              <span class="ltr-number">{{ money(p[sec.metric]) }}</span>
              <small v-if="p[sec.other] > 0" class="ltr-number">{{ money(p[sec.other]) }} {{ sec.otherLabel }}</small>
            </span>
            <span class="cp-fig cp-fig--small">
              <template v-if="p.commission > 0">
                <span class="ltr-number">{{ money(p.commission) }}</span>
                <small>עמלה</small>
              </template>
            </span>
            <span class="cp-clients">
              <span class="ltr-number">{{ p.clients }}</span>
              <small>לקוחות</small>
            </span>
            <svg class="cp-go" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </li>
      </ul>
    </section>
    <p v-if="!sections.length" class="cp-none">אין מוצרים להצגה</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { money } from '../../utils/chartDefaults'

const props = defineProps({
  company: { type: Object, required: true },
  // Display label per product (the parent's FINANCIAL_LABELS mapping).
  labelFor: { type: Function, default: (_k, p) => p },
})
defineEmits(['drill'])

// Savings first: in most books it is where the money sits.
const sections = computed(() => {
  const out = []
  const mk = (key, label, metric, metricLabel, other, otherLabel) => {
    const rows = [...(props.company.products?.[key] || [])]
      .filter(p => (p[metric] || 0) > 0 || (p[other] || 0) > 0)
      .map(p => ({ ...p, label: props.labelFor(key, p.product) }))
      .sort((a, b) => (b[metric] || 0) - (a[metric] || 0) || (b[other] || 0) - (a[other] || 0))
    if (rows.length) {
      out.push({ key, label, metric, metricLabel, other, otherLabel, rows,
                 max: Math.max(1, ...rows.map(p => p[metric] || 0)) })
    }
  }
  mk('financial', 'פיננסים', 'accumulation', 'צבירה', 'premium', 'פרמיה')
  mk('insurance', 'ביטוח', 'premium', 'פרמיה', 'accumulation', 'צבירה')
  return out
})

function share(p, sec) {
  return Math.max(2, ((p[sec.metric] || 0) / sec.max) * 100) + '%'
}

const shown = ref(false)
function play() {
  shown.value = false
  requestAnimationFrame(() => requestAnimationFrame(() => { shown.value = true }))
}
onMounted(play)
watch(() => props.company, play)
</script>

<style scoped>
.cp { display: flex; flex-direction: column; gap: 16px; }
.cp-entities { font-size: 12px; color: var(--text-muted); margin: 0; }
.cp-stats { display: flex; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.cp-stat { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 14px 18px; }
.cp-stat + .cp-stat { border-inline-start: 1px solid var(--border-subtle); }
.cp-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.cp-val { font-size: 21px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.cp-stat:first-child .cp-val { color: var(--tab-production); }

.cp-sec { display: flex; flex-direction: column; gap: 6px; }
.cp-sec-title { display: flex; align-items: baseline; gap: 6px; font-size: 14px; font-weight: 700; color: var(--text); }
.cp-sec-title .ltr-number { color: var(--text-muted); font-weight: 500; }
.cp-sec-title small { margin-inline-start: auto; font-size: 11.5px; font-weight: 500; color: var(--text-muted); }
.cp-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.cp-list li { animation: cpIn 0.35s cubic-bezier(0.2, 0, 0.2, 1) both; animation-delay: var(--d); }
@keyframes cpIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.cp-row {
  width: 100%; display: grid; align-items: center; gap: 14px;
  grid-template-columns: minmax(130px, 1.5fr) 150px 100px 70px 14px;
  padding: 11px 14px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg);
  font: inherit; color: var(--text); text-align: right; cursor: pointer; transition: border-color 0.2s ease;
}
.cp-row:hover { border-color: var(--tab-production); }
.cp-row:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
.cp-name { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.cp-name-txt { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cp-share { display: block; height: 5px; border-radius: 3px; background: var(--bg); overflow: hidden; }
.cp-share i { display: block; height: 100%; border-radius: 3px; background: var(--tab-production); opacity: 0.8;
  transition: width 0.6s cubic-bezier(0.2, 0, 0.2, 1); }
.cp-fig { display: flex; flex-direction: column; align-items: flex-start; font-size: 15px; font-weight: 800; }
.cp-fig small { font-size: 11px; font-weight: 500; color: var(--text-muted); }
.cp-fig--small { font-size: 13px; font-weight: 700; }
.cp-clients { display: flex; flex-direction: column; align-items: flex-start; font-size: 13px; font-weight: 700; }
.cp-clients small { font-size: 10.5px; font-weight: 500; color: var(--text-muted); }
.cp-go { color: var(--text-muted); }
.cp-none { text-align: center; color: var(--text-muted); font-size: 13px; }

@media (max-width: 640px) {
  .cp-stats { flex-wrap: wrap; }
  .cp-stat { flex: 1 1 45%; padding: 10px 12px; }
  .cp-val { font-size: 17px; }
  .cp-row { grid-template-columns: minmax(0, 1fr) 110px 44px 12px; gap: 8px; padding: 10px; }
  .cp-fig--small { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .cp-list li { animation: none; }
  .cp-share i, .cp-row { transition: none; }
}
</style>
