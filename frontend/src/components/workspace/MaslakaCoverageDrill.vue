<template>
  <!-- One מסלקה production file split into אצלך (the product matched a row of
       the agent's production) and לא אצלך (GET /maslaka/coverage). Same shell
       and shape as MaslakaDeltaDrill: summary strip → אצלך/לא אצלך pill →
       company text tabs + search → customer cards that fold open to the
       products. A customer opens their full מסלקה picture (emit 'open-customer'). -->
  <DataModal
    :open="open" :origin="origin" title="אצלך / לא אצלך" :badge="side === 'out' ? (s.out_customers || null) : null"
    :period="periodLabel" accent="var(--tab-maslaka)" size="xl" @close="emit('close')"
  >
    <div class="cv">
      <p v-if="loading" class="cv-note">טוען…</p>
      <p v-else-if="error" class="cv-note" role="alert">{{ error }}</p>
      <p v-else-if="!data?.summary" class="cv-note">עוד לא הגיע קובץ מהמסלקה.</p>

      <template v-else>
        <!-- 1. the two sides ARE the selector: one teal pill glides to the chosen one -->
        <div class="cv-kpis cv-mod">
          <div class="cv-pick" role="tablist" aria-label="אצלך או לא אצלך" :style="{ '--i': side === 'in' ? 0 : 1 }">
            <span class="cv-glider" aria-hidden="true"></span>
            <button
              v-for="k in SIDES" :key="k.id" type="button" role="tab" class="cv-kpi"
              :class="{ 'cv-kpi--on': side === k.id }" :aria-selected="side === k.id" @click="pick(k.id)"
            >
              <span class="cv-kpi-label">{{ k.label }}</span>
              <strong class="cv-kpi-n ltr-number">{{ num(k.id === 'in' ? s.in_customers : s.out_customers) }}</strong>
              <span class="cv-kpi-sub">
                לקוחות · <span class="ltr-number">{{ num(k.id === 'in' ? s.in_products : s.out_products) }}</span> מוצרים
              </span>
            </button>
          </div>
          <div v-if="s.out_accumulation >= 0.5" class="cv-kpi cv-kpi--quiet">
            <span class="cv-kpi-label">צבירה שלא אצלך</span>
            <strong class="cv-kpi-n ltr-number">₪{{ money(s.out_accumulation) }}</strong>
          </div>
        </div>

        <!-- 2. company text tabs with counts, then search -->
        <section class="cv-mod cv-listmod">
          <div v-if="companies.length > 1" class="cv-tabs" role="tablist" aria-label="חברה">
            <button
              type="button" role="tab" class="cv-tab" :class="{ 'cv-tab--on': !company }"
              :aria-selected="!company" @click="setCompany('')"
            >הכל <span class="ltr-number">{{ num(countFor('')) }}</span></button>
            <button
              v-for="c in companies" :key="c.name" type="button" role="tab" class="cv-tab"
              :class="{ 'cv-tab--on': company === c.name }" :aria-selected="company === c.name"
              @click="setCompany(c.name)"
            >{{ shortCo(c.name) }} <span class="ltr-number">{{ num(c.n) }}</span></button>
          </div>
          <label class="cv-search">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
            <input v-model="q" placeholder="שם או ת.ז" aria-label="חיפוש" @input="limit = PAGE" />
          </label>

          <p v-if="!shown.length" class="cv-note">
            {{ q ? 'לא נמצא' : (side === 'out' ? 'כל הלקוחות בקובץ הזה כבר אצלך' : 'אין') }}
          </p>
          <Transition :name="slideDir" mode="out-in">
            <TransitionGroup :key="side + '|' + company" tag="ul" name="cv-li" class="cv-list">
              <li
                v-for="(c, i) in shown.slice(0, limit)" :key="c.id_number" class="cv-card"
                :class="{ 'cv-card--open': openKey === c.id_number }" :style="{ '--i': Math.min(i, 12) }"
              >
                <button type="button" class="cv-row" :aria-expanded="openKey === c.id_number"
                        @click="openKey = openKey === c.id_number ? null : c.id_number">
                  <span class="cv-id">
                    <strong>{{ c.name || 'לקוח' }}</strong>
                    <small class="ltr-number">{{ c.id_number }}</small>
                  </span>
                  <span class="cv-ctx">{{ c.companies.map(shortCo).join(' · ') }}</span>
                  <span class="cv-pill"><span class="ltr-number">{{ c.products.length }}</span> מוצרים</span>
                  <span v-if="c.accumulation >= 0.5" class="cv-amt">
                    <strong class="ltr-number">₪{{ money(c.accumulation) }}</strong>
                    <small>צבירה</small>
                  </span>
                  <svg class="cv-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
                </button>
                <div class="cv-fold">
                  <div class="cv-fold-in">
                    <div class="cv-fold-body">
                      <ul class="cv-prods">
                        <li v-for="(p, j) in c.products" :key="j" class="cv-prod">
                          <span class="cv-prod-name">{{ productOf(p) }}</span>
                          <span class="cv-prod-meta">
                            {{ shortCo(p.company) }}<template v-if="p.policy"> · <span class="ltr-number">{{ p.policy }}</span></template>
                            <template v-if="p.account_status"> · {{ p.account_status }}</template>
                          </span>
                          <span v-if="p.accumulation >= 0.5" class="cv-prod-amt ltr-number">₪{{ money(p.accumulation) }}</span>
                        </li>
                      </ul>
                      <button type="button" class="cv-open" @click="emit('open-customer', c.id_number, $event.currentTarget)">
                        תיק הלקוח
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            </TransitionGroup>
          </Transition>
          <button v-if="shown.length > limit" type="button" class="cv-more" @click="limit += PAGE">
            עוד <span class="ltr-number">{{ num(shown.length - limit) }}</span>
          </button>
        </section>
      </template>
    </div>
  </DataModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import api from '../../api/client.js'
import DataModal from './DataModal.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  origin: { type: null, default: null },
  asOf: { type: String, default: '' },          // the file's valuation date (YYYY-MM-DD)
  initialSide: { type: String, default: 'out' }, // 'in' | 'out'
  initialCompany: { type: String, default: '' },
})
const emit = defineEmits(['close', 'open-customer'])

const SIDES = [
  { id: 'in', label: 'אצלך' },
  { id: 'out', label: 'לא אצלך' },
]
const PAGE = 20
const HEB_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']

const data = ref(null)
const loading = ref(false)
const error = ref('')
const side = ref('out')
const company = ref('')
const q = ref('')
const openKey = ref(null)
const limit = ref(PAGE)
const slideDir = ref('cv-slide-left')

const s = computed(() => data.value?.summary || {})
const periodLabel = computed(() => {
  const [y, m] = String(data.value?.as_of || '').split('-').map(Number)
  return y && m ? `${HEB_MONTHS[m - 1]} ${y}` : ''
})

const num = (n) => Number(n || 0).toLocaleString('he-IL')
const money = (v) => Math.round(Number(v || 0)).toLocaleString('he-IL')
const shortCo = (c) => String(c || '').replace(/\s*(חברה לביטוח|פנסיה וגמל|גמל ופנסיה|פנסיה מקיפה|בע"מ|בעמ)\s*/g, ' ').trim() || c
function productOf(p) {
  const name = String(p.product || 'מוצר')
  const brand = shortCo(p.company).split(' ')[0]
  return brand && name.startsWith(brand + ' - ') ? name.slice(brand.length + 3) : name
}

// A customer is לא אצלך when even one of their products (in the company in
// scope) is missing from production — the same rule as the server's summary,
// so "הכל" here equals the counts on the card that opened the drill.
function customersFor(co) {
  const by = new Map()
  for (const p of data.value?.products || []) {
    if (co && p.company !== co) continue
    let c = by.get(p.id_number)
    if (!c) by.set(p.id_number, (c = { id_number: p.id_number, name: p.name, all: [] }))
    c.all.push(p)
  }
  const out = []
  for (const c of by.values()) {
    const missing = c.all.filter((p) => p.side === 'out')
    const isOut = missing.length > 0
    if ((side.value === 'out') !== isOut) continue
    const products = isOut ? missing : c.all
    out.push({
      ...c, products,
      companies: [...new Set(products.map((p) => p.company))],
      accumulation: products.reduce((t, p) => t + (Number(p.accumulation) || 0), 0),
    })
  }
  return out.sort((a, b) => b.accumulation - a.accumulation)
}
const countFor = (co) => customersFor(co).length
const companies = computed(() => (data.value?.by_company || [])
  .map((c) => ({ name: c.company, n: side.value === 'out' ? c.out_customers : c.in_customers }))
  .filter((c) => c.n > 0))
const shown = computed(() => {
  const t = q.value.trim()
  return customersFor(company.value).filter((c) => !t || `${c.name || ''} ${c.id_number}`.includes(t))
})

function pick(k) {
  if (k === side.value) return
  slideDir.value = k === 'out' ? 'cv-slide-left' : 'cv-slide-right'
  side.value = k
  // keep the company only when it still has customers on the new side
  if (company.value && !companies.value.some((c) => c.name === company.value)) company.value = ''
  openKey.value = null
  limit.value = PAGE
}
function setCompany(co) {
  company.value = co
  openKey.value = null
  limit.value = PAGE
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: d } = await api.get('/maslaka/coverage', { params: props.asOf ? { as_of: props.asOf } : {} })
    data.value = d
    side.value = props.initialSide === 'in' || !d?.summary?.out_customers ? 'in' : 'out'
    company.value = props.initialCompany
    if (company.value && !companies.value.some((c) => c.name === company.value)) company.value = ''
  } catch {
    error.value = 'לא הצלחנו לטעון. נסו שוב.'
  } finally {
    loading.value = false
  }
}

watch(() => props.open, (o) => {
  if (o) { q.value = ''; openKey.value = null; limit.value = PAGE; load() }
})
</script>

<style scoped>
.cv { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.cv-note { margin: 18px 4px; text-align: center; font-size: 14px; color: var(--text-muted); }

.cv-mod { animation: cv-rise 0.7s cubic-bezier(0.22, 1, 0.36, 1) both; }
.cv-kpis.cv-mod { animation-delay: 0.05s; }
.cv-listmod.cv-mod { animation-delay: 0.18s; }
@keyframes cv-rise { from { opacity: 0; transform: translateY(18px) scale(0.985); } to { opacity: 1; transform: none; } }

/* 1. the two sides — selector with a gliding pill (MaslakaDeltaDrill .md-glider) */
.cv-kpis { display: grid; grid-template-columns: 2fr 1fr; gap: 8px; }
.cv-pick { position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 5px;
  border: 1px solid var(--border-subtle); border-radius: 14px; background: var(--card-bg); }
.cv-glider { position: absolute; top: 5px; bottom: 5px; inset-inline-start: 5px; width: calc((100% - 10px - 8px) / 2);
  border-radius: 11px; background: var(--tab-maslaka); pointer-events: none;
  box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-maslaka) 30%, transparent);
  transform: translateX(calc(var(--i, 0) * (-100% - 8px)));
  transition: transform 0.75s cubic-bezier(0.22, 1, 0.36, 1); }
.cv-kpi { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  padding: 10px 14px; border: none; border-radius: 11px; background: transparent; font-family: inherit; text-align: start;
  cursor: pointer; color: var(--text); transition: background 0.2s; }
.cv-kpi:hover:not(.cv-kpi--on) { background: var(--tab-maslaka-wash); }
.cv-kpi:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.cv-kpi-label, .cv-kpi-sub { font-size: 12.5px; color: var(--text-muted); transition: color 0.4s ease 0.15s; }
.cv-kpi-n { font-size: 26px; font-weight: 800; line-height: 1.1; transition: color 0.4s ease 0.15s; }
.cv-kpi--on .cv-kpi-label, .cv-kpi--on .cv-kpi-n, .cv-kpi--on .cv-kpi-sub { color: #fff; }
.cv-kpi--quiet { cursor: default; padding: 15px 16px; border: 1px solid var(--border-subtle); border-radius: 14px; background: var(--bg); }

/* 2. company text tabs + search + list */
.cv-listmod { display: flex; flex-direction: column; gap: 10px; }
.cv-tabs { display: flex; flex-wrap: wrap; gap: 4px 18px; border-bottom: 1px solid var(--border-subtle); }
.cv-tab { position: relative; padding: 8px 2px 10px; border: none; background: none; cursor: pointer; font-family: inherit;
  font-size: 13.5px; font-weight: 600; color: var(--text-muted); transition: color 0.2s; }
.cv-tab span { font-weight: 500; }
.cv-tab::after { content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px; border-radius: 2px;
  background: var(--tab-maslaka); transform: scaleX(0); transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1); }
.cv-tab:hover, .cv-tab--on { color: var(--text); }
.cv-tab--on::after { transform: scaleX(1); }
.cv-tab:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.cv-search { display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 12px; border-radius: 10px;
  background: var(--bg); color: var(--text-muted); }
.cv-search:focus-within { background: var(--card-bg); box-shadow: 0 0 0 2px var(--tab-maslaka); }
.cv-search input { flex: 1; min-width: 0; border: none; outline: none; background: none; font: inherit; font-size: 14px; color: var(--text); }

.cv-slide-left-enter-active, .cv-slide-right-enter-active {
  transition: opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1) 0.1s, transform 0.85s cubic-bezier(0.22, 1, 0.36, 1) 0.1s; }
.cv-slide-left-leave-active, .cv-slide-right-leave-active { transition: opacity 0.15s ease; }
.cv-slide-left-leave-to, .cv-slide-right-leave-to { opacity: 0; }
.cv-slide-left-enter-from { opacity: 0; transform: translateX(-24px); }
.cv-slide-right-enter-from { opacity: 0; transform: translateX(24px); }

.cv-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.cv-li-enter-active { transition: opacity 0.45s ease, transform 0.45s cubic-bezier(0.22, 1, 0.36, 1); transition-delay: calc(var(--i) * 35ms); }
.cv-li-enter-from { opacity: 0; transform: translateY(10px); }
.cv-card { border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); transition: background 0.2s, border-color 0.2s, box-shadow 0.2s; }
.cv-card:hover { background: var(--tab-maslaka-wash); border-color: color-mix(in srgb, var(--tab-maslaka) 35%, var(--border-subtle)); }
.cv-card--open { border-color: color-mix(in srgb, var(--tab-maslaka) 35%, var(--border-subtle)); box-shadow: var(--shadow-sm); }
.cv-row { width: 100%; display: flex; align-items: center; gap: 14px; padding: 11px 14px; border: none; background: none;
  cursor: pointer; font-family: inherit; text-align: start; border-radius: 12px; }
.cv-row:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: -2px; }
.cv-id { flex: 0 0 170px; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.cv-id strong { font-size: 14.5px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-id small { align-self: flex-start; font-size: 12.5px; color: var(--text-muted); }
.cv-ctx { flex: 1; min-width: 0; font-size: 13px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-pill { flex: none; padding: 3px 10px; border-radius: 999px; background: var(--tab-maslaka-wash); color: var(--tab-maslaka);
  font-size: 12px; font-weight: 700; }
.cv-amt { flex: 0 0 110px; display: flex; flex-direction: column; align-items: flex-start; gap: 0; }
.cv-amt strong { font-size: 14.5px; font-weight: 800; color: var(--text); }
.cv-amt small { font-size: 11.5px; color: var(--text-muted); }
.cv-chev { flex: none; color: var(--text-muted); transition: transform 0.35s cubic-bezier(0.32, 0.72, 0, 1); }
.cv-card--open .cv-chev { transform: rotate(180deg); }
.cv-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.4s cubic-bezier(0.32, 0.72, 0, 1); }
.cv-card--open .cv-fold { grid-template-rows: 1fr; }
.cv-fold-in { overflow: hidden; min-height: 0; }
.cv-fold-body { display: flex; align-items: flex-end; gap: 16px; margin: 0 14px 12px; padding-top: 8px; border-top: 1px solid var(--border-subtle); }
.cv-prods { flex: 1; min-width: 0; list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.cv-prod { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 2fr) 110px; align-items: baseline; gap: 12px; font-size: 13.5px; }
.cv-prod-name { font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-prod-meta { color: var(--text-muted); font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-prod-amt { font-weight: 700; color: var(--text); }
.cv-open { flex: none; display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border: none; border-radius: 10px;
  cursor: pointer; background: var(--tab-maslaka); color: #fff; font-family: inherit; font-size: 13px; font-weight: 700;
  box-shadow: 0 3px 10px color-mix(in srgb, var(--tab-maslaka) 25%, transparent); transition: transform 0.15s, filter 0.15s; }
.cv-open:hover { transform: translateY(-1px); filter: brightness(1.1); }
.cv-more { align-self: center; padding: 8px 20px; border-radius: 10px; border: 1px solid var(--border); background: var(--card-bg);
  cursor: pointer; font-family: inherit; font-size: 13.5px; font-weight: 600; color: var(--text-secondary); }
.cv-more:hover { color: var(--tab-maslaka); border-color: var(--tab-maslaka); }

@media (max-width: 760px) {
  .cv-kpis { grid-template-columns: 1fr; }
  .cv-kpi--quiet { flex-direction: row; align-items: baseline; justify-content: space-between; padding: 8px 14px; }
  .cv-kpi--quiet .cv-kpi-n { font-size: 17px; }
}
@media (max-width: 640px) {
  .cv-id { flex-basis: 120px; }
  .cv-ctx, .cv-pill { display: none; }
  .cv-fold-body { flex-direction: column; align-items: stretch; }
  .cv-prod { grid-template-columns: 1fr auto; }
  .cv-prod-meta { grid-column: 1 / -1; grid-row: 2; }
}
@media (prefers-reduced-motion: reduce) {
  .cv-mod, .cv-li-enter-active, .cv-glider, .cv-slide-left-enter-active, .cv-slide-right-enter-active { animation: none; transition: none; }
  .cv-fold, .cv-chev, .cv-tab::after { transition: none; }
}
</style>
