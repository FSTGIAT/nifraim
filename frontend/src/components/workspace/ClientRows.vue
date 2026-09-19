<template>
  <div class="cl">
    <!-- A figure repeated across many clients is a source-file artefact, not a
         book. Saying so beats rendering 76 identical rows as fact. -->
    <p v-if="identical" class="cl-warn">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <span>
        <strong class="ltr-number">{{ identical.clients }}</strong> לקוחות נושאים בדיוק אותו סכום
        (<strong class="ltr-number">{{ money(identical.value) }}</strong>
        {{ identical.field === 'premium' ? 'פרמיה' : 'צבירה' }}) — בדרך כלל סימן שסכום קבוצתי
        נרשם על כל שורה בקובץ המקור, ולא סכום אישי.
      </span>
    </p>

    <div class="cl-row cl-head">
      <span>לקוח</span><span></span><span>פרמיה</span><span>צבירה</span><span>עמלה</span><span>מוצרים</span>
    </div>

    <ul class="cl-list">
      <template v-for="(c, i) in shownRows" :key="c.id_number">
        <li class="cl-row" :class="{ 'cl-row--in': shown, 'cl-row--open': open === c.id_number }"
            :style="{ transitionDelay: Math.min(i, 14) * 25 + 'ms' }"
            @click="open = open === c.id_number ? null : c.id_number">
          <span class="cl-name" :title="c.name || c.id_number">{{ c.name || c.id_number }}</span>
          <span class="cl-track">
            <span class="cl-bar cl-bar--prem" :style="{ width: bar(c.premium, maxPrem) }"></span>
            <span class="cl-bar cl-bar--acc" :style="{ width: bar(c.accumulation, maxAcc) }"></span>
          </span>
          <span class="cl-val ltr-number" :class="{ 'cl-zero': !c.premium }">
            {{ c.premium ? money(c.premium) : '—' }}
          </span>
          <span class="cl-val ltr-number" :class="{ 'cl-zero': !c.accumulation }">
            {{ c.accumulation ? money(c.accumulation) : '—' }}
          </span>
          <span class="cl-val cl-comm ltr-number" :class="{ 'cl-zero': !c.commission }">
            {{ c.commission ? money(c.commission) : '—' }}
          </span>
          <span class="cl-n ltr-number">{{ c.products.length }}</span>
        </li>

        <!-- The client's holdings open UNDER the client, not at the foot of
             the list. Rendered after the </ul> it sat below 25 rows, so on a
             long list the agent clicked a name and nothing appeared to
             happen unless they scrolled. -->
        <li v-if="open === c.id_number" class="cl-detail-li">
          <div class="cl-detail">
            <div class="cl-detail-head">
              <span>{{ c.name || c.id_number }} — כל המוצרים</span>
              <span class="cl-detail-id ltr-number">ת.ז {{ c.id_number }}</span>
            </div>
            <div class="cl-detail-row cl-detail-row--head">
              <span>מוצר</span><span>חברה</span><span>סוג</span>
              <span>מסלול</span><span>דמי ניהול</span>
              <span>פרמיה</span><span>צבירה</span><span>עמלה</span>
            </div>
            <div v-for="(p, pi) in c.products" :key="pi" class="cl-detail-row">
              <span :title="p.raw_product || p.product">{{ p.raw_product || p.product }}</span>
              <span class="cl-detail-co">{{ p.company }}</span>
              <span class="cl-detail-cat">{{ p.category === 'insurance' ? 'ביטוח' : 'פיננסים' }}</span>
              <span class="cl-detail-co">{{ p.track || '—' }}</span>
              <span class="cl-detail-co ltr-number">{{ mgmtFee(p) }}</span>
              <span class="ltr-number">{{ p.premium ? money(p.premium) : '—' }}</span>
              <span class="ltr-number">{{ p.accumulation ? money(p.accumulation) : '—' }}</span>
              <span class="ltr-number" :title="p.rate_percent ? p.rate_percent + '%' : ''">
                {{ p.commission ? money(p.commission) : '—' }}
              </span>
            </div>
            <!-- Empty columns are named, not left as dashes. Measured on the
                 live book: מסלול and דמי ניהול are absent from every row of
                 the merged production file, and no נפרעים row matches these
                 policies either — so "—" here is a missing SOURCE, not a
                 client who pays no fee. -->
            <p v-if="missingCols(c).length" class="cl-detail-note">
              {{ missingCols(c).join(' ו') }} לא מגיעים בקובץ הפרודוקציה של החברות האלה,
              ולכן העמודה ריקה.
            </p>
          </div>
        </li>
      </template>
    </ul>

    <button v-if="hidden && !expanded" class="cl-more" @click="expanded = true">
      הצג עוד {{ hidden }} לקוחות
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { money } from '../../utils/chartDefaults'

const TOP = 25

const props = defineProps({
  rows: { type: Array, default: () => [] },
  identical: { type: Object, default: null },
})

const shown = ref(false)
const expanded = ref(false)
const open = ref(null)

const shownRows = computed(() => (expanded.value ? props.rows : props.rows.slice(0, TOP)))
const hidden = computed(() => Math.max(0, props.rows.length - TOP))
function mgmtFee(p) {
  // A rate (`management_fee`) shows as a percent; a shekel amount
  // (`management_fee_amount`) shows as money. Neither invented when absent.
  if (p.management_fee != null) return Number(p.management_fee).toFixed(2) + '%'
  if (p.management_fee_amount != null) return money(p.management_fee_amount)
  return '—'
}

function missingCols(c) {
  const out = []
  if (!c.products.some(p => p.track)) out.push('מסלול ההשקעה')
  if (!c.products.some(p => p.management_fee != null || p.management_fee_amount != null)) {
    out.push('דמי הניהול')
  }
  return out
}

// Each measure on its own scale: a monthly payment and a balance are different
// quantities, and one scale across both would flatten the smaller to nothing.
const maxPrem = computed(() => Math.max(1, ...props.rows.map(c => Number(c.premium) || 0)))
const maxAcc = computed(() => Math.max(1, ...props.rows.map(c => Number(c.accumulation) || 0)))

function bar(v, max) {
  // `max` arrives already unwrapped from the template.
  const limit = Number(max) || 1
  const n = Math.abs(Number(v) || 0)
  if (!shown.value || !n) return '0%'
  return Math.max(1.5, (n / limit) * 100) + '%'
}

function play() {
  expanded.value = false
  open.value = null
  shown.value = false
  requestAnimationFrame(() => requestAnimationFrame(() => { shown.value = true }))
}
onMounted(play)
watch(() => props.rows, play)
</script>

<style scoped>
.cl-warn {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 10px 12px; margin-bottom: 14px;
  border-radius: var(--radius-sm); background: var(--amber-light);
  color: var(--amber); font-size: 12px; line-height: 1.6;
}
.cl-warn svg { flex-shrink: 0; margin-top: 2px; }

.cl-list { list-style: none; display: flex; flex-direction: column; }
.cl-row {
  display: grid;
  grid-template-columns: minmax(110px, 1.3fr) 1fr 90px 104px 90px 52px;
  align-items: center; gap: 12px;
  padding: 8px; border-bottom: 1px solid var(--border-subtle);
  opacity: 0; transform: translateY(3px);
  transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.2, 0, 0.2, 1);
  cursor: pointer;
}
.cl-row--in { opacity: 1; transform: none; }
.cl-row:hover { background: var(--border-subtle); }
.cl-row--open { background: var(--primary-light); }

.cl-row.cl-head {
  font-size: 11px; color: var(--text-muted); cursor: default;
  opacity: 1; transform: none; transition: none;
}
.cl-row.cl-head:hover { background: none; }
.cl-row.cl-head > span:not(:first-child) { text-align: left; }

.cl-name { font-size: 13px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cl-track { display: flex; flex-direction: column; gap: 3px; direction: ltr; }
.cl-bar { display: block; height: 7px; border-radius: 4px; transition: width 0.5s cubic-bezier(0.2, 0, 0.2, 1); }
.cl-bar--prem { background: var(--chart-9); }
.cl-bar--acc { background: var(--chart-7); }
.cl-val { font-size: 12px; font-weight: 600; color: var(--text); text-align: left; }
.cl-zero { color: var(--text-muted); font-weight: 500; }
.cl-n { font-size: 12px; color: var(--text-muted); text-align: left; }

.cl-detail-li { list-style: none; }
.cl-detail {
  margin: 2px 0 10px; padding: 10px 12px;
  border-radius: var(--radius-sm); background: var(--border-subtle);
}
.cl-detail-head {
  display: flex; align-items: baseline; gap: 10px;
  font-size: 12px; font-weight: 700; color: var(--text); margin-bottom: 6px;
}
.cl-detail-id { margin-right: auto; font-weight: 600; color: var(--text-muted); }
.cl-detail-row {
  display: grid; grid-template-columns: 1.4fr 1fr 62px 1fr 78px 86px 100px 86px;
  gap: 10px; padding: 5px 0; font-size: 12px; color: var(--text);
}
.cl-detail-row > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cl-detail-row > span:nth-child(n+5) { text-align: left; }
.cl-detail-row--head {
  font-size: 11px; color: var(--text-muted); font-weight: 600;
  border-bottom: 1px solid var(--card-bg); padding-bottom: 6px;
}
.cl-detail-note {
  margin-top: 8px; font-size: 11.5px; color: var(--text-muted); line-height: 1.7;
}
.cl-comm { color: var(--chart-3, var(--text)); }
.cl-detail-co, .cl-detail-cat { color: var(--text-muted); }

.cl-more {
  margin-top: 10px; padding: 6px 14px; width: 100%;
  border: 1px dashed var(--border-subtle); border-radius: var(--radius-sm);
  background: none; color: var(--text-muted);
  font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
}
.cl-more:hover { color: var(--text); border-color: var(--text-muted); }

@media (prefers-reduced-motion: reduce) {
  .cl-row { opacity: 1; transform: none; transition: none; }
  .cl-bar { transition: none; }
}
</style>
