<template>
  <!-- The comparison tab's customer list — same language as the Production
       drills (QA 2026-10-01), in the comparison tab's green: a summary strip,
       the product filter as one select (not a wall of chips), search, sort,
       and calm customer cards that say the status in words. -->
  <div class="ccl">
    <div class="ccl-stats">
      <div class="ccl-stat">
        <span class="ccl-lbl">לקוחות</span>
        <span class="ccl-val ltr-number">{{ shown.length.toLocaleString() }}</span>
      </div>
      <div v-if="totReceived > 0 && !allUnpaid" class="ccl-stat">
        <span class="ccl-lbl">עמלה שהתקבלה</span>
        <span class="ccl-val ltr-number">{{ money(totReceived) }}</span>
      </div>
      <div v-if="totExpected > 0" class="ccl-stat">
        <span class="ccl-lbl">צפוי ולא שולם</span>
        <span class="ccl-val ltr-number">{{ money(totExpected) }}</span>
      </div>
      <div v-if="totPremium > 0" class="ccl-stat">
        <span class="ccl-lbl">פרמיה</span>
        <span class="ccl-val ltr-number">{{ money(totPremium) }}</span>
      </div>
    </div>

    <!-- Company cut (QA 2026-10-01: "can't filter by company"). Text tabs with
         counts, per the style rules — not chips. -->
    <div v-if="companies.length > 1" class="ccl-cos" role="tablist" aria-label="סינון לפי חברה">
      <button type="button" role="tab" :aria-selected="!company" :class="{ on: !company }" @click="company = null">
        הכל <span class="ltr-number">{{ customers.length }}</span>
      </button>
      <button v-for="co in companies" :key="co.name" type="button" role="tab"
              :aria-selected="company === co.name" :class="{ on: company === co.name }"
              @click="company = co.name">
        {{ co.name }} <span class="ltr-number">{{ co.count }}</span>
      </button>
    </div>

    <div class="ccl-tools">
      <label class="ccl-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input v-model.trim="query" type="search" placeholder="חיפוש לפי שם או ת.ז" />
      </label>
      <div v-if="products.length > 1" class="ccl-select">
        <select v-model="product" aria-label="סינון לפי מוצר">
          <option :value="null">כל המוצרים</option>
          <option v-for="p in products" :key="p" :value="p">{{ p }}</option>
        </select>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
      </div>
      <template v-if="actions">
        <button class="ccl-act" type="button" @click="actions.mail(shown)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>
          שלח מייל
        </button>
        <button class="ccl-act" type="button" @click="actions.excel(shown)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><polyline points="9 15 12 18 15 15"/><line x1="12" y1="18" x2="12" y2="12"/></svg>
          Excel
        </button>
      </template>
      <div class="ccl-sort" role="group" aria-label="מיון">
        <button v-for="s in SORTS" :key="s.key" :class="{ on: sortKey === s.key }" @click="sortKey = s.key">
          {{ s.label }}
        </button>
      </div>
    </div>

    <ul class="ccl-list">
      <li v-if="!shown.length" class="ccl-none">אין לקוחות שתואמים לסינון.</li>
      <li v-for="(c, i) in visible" :key="c.id_number" :style="{ '--d': Math.min(i, 12) * 30 + 'ms' }">
        <button class="ccl-row" @click="$emit('open', c, $event.currentTarget)">
          <span class="ccl-who">
            <span class="ccl-name">{{ nameOf(c) }}</span>
            <span class="ccl-id ltr-number">{{ c.id_number }}</span>
          </span>
          <!-- WHAT this customer is about: the company and the product (QA
               2026-10-01: the card said only "רק בפרודוקציה"). -->
          <span class="ccl-what">
            <span class="ccl-co">
              <span v-for="co in companiesOf(c).slice(0, 2)" :key="co" class="ccl-co-item">
                <CompanyLogo :company="co" :size="16" :frame="false" />{{ co }}
              </span>
              <span v-if="companiesOf(c).length > 2" class="ccl-more-co ltr-number">+{{ companiesOf(c).length - 2 }}</span>
            </span>
            <span class="ccl-prod">
              {{ productLine(c) }}<template v-if="statusNote(c)"> · <b>{{ statusNote(c) }}</b></template>
            </span>
          </span>
          <span class="ccl-pill ltr-number" :title="`${productCount(c)} מוצרים`">{{ productCount(c) }}</span>
          <span class="ccl-fig">
            <template v-if="expectedOf(c) >= 0.5">
              <span class="ltr-number">{{ money(expectedOf(c)) }}</span>
              <small>צפוי ולא שולם</small>
            </template>
            <!-- Never "התקבל" on an unpaid customer: that money came from OTHER
                 companies and read as if this one paid (QA 2026-10-01). -->
            <template v-else-if="(c.match_status !== 'only_production' || (paidView && c.partially_paid)) && receivedOf(c) >= 0.5">
              <span class="ltr-number">{{ money(receivedOf(c)) }}</span>
              <small>התקבל</small>
            </template>
            <template v-else-if="accumOf(c) >= 0.5">
              <span class="ltr-number">{{ money(accumOf(c)) }}</span>
              <small>{{ c.match_status === 'only_production' ? 'צבירה שלא שולמה' : 'צבירה' }}</small>
            </template>
            <template v-else-if="premiumOf(c) >= 0.5">
              <span class="ltr-number">{{ money(premiumOf(c)) }}</span>
              <small>פרמיה</small>
            </template>
          </span>
          <svg class="ccl-go" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </li>
    </ul>
    <button v-if="shown.length > limit" class="ccl-more" @click="limit += 100">
      הצג עוד <span class="ltr-number">{{ Math.min(100, shown.length - limit) }}</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { money } from '../../utils/chartDefaults'
import { expectedFor } from '../../utils/expectedCommission'
import CompanyLogo from '../workspace/CompanyLogo.vue'
import { normalizeCompany } from '../../utils/companyNorm.js'

const props = defineProps({
  customers: { type: Array, default: () => [] },
  rates: { type: Array, default: () => [] },      // the agent's agreement shelf
  category: { type: String, default: '' },
  // { mail(), excel() } for lists that came from a KPI card.
  actions: { type: Object, default: null },
  // Opened from one company's bar — start on that company's tab.
  initialCompany: { type: String, default: null },
  // A "נמצא בשניהם" list from one company's bar: it holds customers paid HERE
  // but unpaid at another company — their cards show the paid side.
  paidView: { type: Boolean, default: false },
})
defineEmits(['open'])

const query = ref('')
const product = ref(null)
const company = ref(null)
const sortKey = ref('value')
const limit = ref(100)
const SORTS = [
  { key: 'value', label: 'סכום' },
  { key: 'products', label: 'מוצרים' },
  { key: 'name', label: 'שם' },
]
watch(() => props.customers, () => {
  query.value = ''; product.value = null; limit.value = 100
  company.value = startCompany()
})
watch([query, product, company, sortKey], () => { limit.value = 100 })
// A product picked under another company may not exist here — clear it.
watch(company, () => { if (product.value && !products.value.includes(product.value)) product.value = null })

const nameOf = c => [c.first_name, c.last_name].filter(Boolean).join(' ') || c.id_number
// Only a status the list title doesn't already say: a customer in both files
// with some policies unpaid.
function statusNote(c) {
  if (c.match_status === 'matched' && c.unpaid_count > 0) {
    return `${c.unpaid_count} ${c.unpaid_count === 1 ? 'מוצר' : 'מוצרים'} לא שולמו`
  }
  // Paid here, unpaid at another company — say where it is unpaid.
  if (props.paidView && c.partially_paid) {
    const unpaidAt = [...new Set((c.production_products || []).map(p => p.company).filter(Boolean))]
    if (unpaidAt.length) return `לא שולם ב${unpaidAt.join(', ')}`
  }
  // Unpaid here, paid by another company — say who did pay.
  if (c.match_status === 'only_production' && c.partially_paid) {
    // Unpaid is per product: the same company may have paid this customer's
    // OTHER products — then say that, not "paid only at X".
    const unpaidAt = new Set((c.production_products || []).map(p => p.company).filter(Boolean))
    const paidBy = [...new Set((c.commission_products || []).map(p => p.company).filter(Boolean))]
    if (paidBy.some(co => unpaidAt.has(co))) return 'שולמו רק חלק מהמוצרים'
    if (paidBy.length) return `שולם רק ב${paidBy.join(', ')}`
  }
  // An inactive fund says so — it's why it earns nothing.
  if (c.match_status === 'only_production') {
    const st = [...new Set((c.production_products || []).map(p => p.status).filter(Boolean))]
    if (st.length === 1 && st[0] !== 'פעיל') return st[0]
  }
  return ''
}

// The products this card is ABOUT: the unpaid ones for an unpaid customer, the
// paid lines for a נפרעים-only one, everything for a matched one. Grouped on
// the short brand `company` — `company_full` would split one insurer in two.
function relevantOf(c) {
  if (props.paidView && c.partially_paid) {
    return [...(c.paid_production_products || []), ...(c.commission_products || [])]
  }
  if (c.match_status === 'only_production') return c.production_products || []
  if (c.match_status === 'only_commission') return c.commission_products || []
  return [...(c.production_products || []), ...(c.commission_products || [])]
}
function companiesOf(c) {
  return [...new Set(relevantOf(c).map(p => p.company).filter(Boolean))]
}
function productLine(c) {
  const names = [...new Set(relevantOf(c)
    .filter(p => !company.value || p.company === company.value)
    .map(p => p.product || p.product_type).filter(Boolean))]
  if (!names.length) return ''
  return names.length > 1 ? `${names[0]} +${names.length - 1}` : names[0]
}
const companies = computed(() => {
  const n = {}
  for (const c of props.customers) for (const co of companiesOf(c)) n[co] = (n[co] || 0) + 1
  return Object.entries(n).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count)
})
// The tab for `initialCompany`, but only when every customer in the list is
// on it — a tab that hides part of the list would make the badge lie.
function startCompany() {
  const want = props.initialCompany && normalizeCompany(props.initialCompany)
  if (!want) return null
  const tab = companies.value.find(co => normalizeCompany(co.name) === want)
  return tab && tab.count === props.customers.length ? tab.name : null
}
// First open: `startCompany` reads `companies`, so it runs only once that exists.
company.value = startCompany()
const byCompany = computed(() => company.value
  ? props.customers.filter(c => companiesOf(c).includes(company.value))
  : props.customers)
const productCount = c => Math.max(c.production_count || 0, c.commission_count || 0)
// Expected commission on the policies that were NOT paid — the same rule as
// the customer window (utils/expectedCommission), including its fallback to
// the agreement shelf, so the list and the window never disagree. A customer
// only in production keeps its unpaid policies in `production_products`.
// With a company tab selected, every figure is THAT company's only — a
// customer unpaid at הראל and אלטשולר showed both under the הראל tab.
const atCompany = list => (company.value ? list.filter(p => p.company === company.value) : list)
const unpaidOf = c => (props.paidView && c.partially_paid) ? [] : atCompany(c.match_status === 'only_production'
  ? (c.production_products || [])
  : (c.product_matches?.unmatched_production || []))
const expectedOf = c => unpaidOf(c)
  .reduce((s, p) => s + (Number(expectedFor(p, props.rates, props.category)) || 0), 0)
// Sort weight: what is owed first; for an unpaid customer never the money
// another company paid.
const valueOf = c => expectedOf(c) * 1000
  + (c.match_status === 'only_production' ? accumOf(c) / 100 : (c.total_commission || 0))
const sumOf = (arr, k) => (arr || []).reduce((s, p) => s + (Number(p[k]) || 0), 0)
const accumOf = c => sumOf(atCompany(c.production_products || []), 'accumulation')
const receivedOf = c => (company.value ? sumOf(atCompany(c.commission_products || []), 'commission') : (c.total_commission || 0))
const premiumOf = c => (company.value ? sumOf(atCompany(relevantOf(c)), 'premium') : (c.total_premium || 0))

function namesOf(c) {
  return [
    ...(c.production_products || []).map(p => p.product),
    ...(c.commission_products || []).map(p => p.product),
    ...(c.product_matches?.matched || []).map(p => p.production_product || p.commission_product || p.product),
    ...(c.product_matches?.unmatched_production || []).map(p => p.product),
    ...(c.product_matches?.unmatched_commission || []).map(p => p.product),
  ].filter(Boolean)
}
const products = computed(() => [...new Set(byCompany.value.flatMap(c => company.value
  ? relevantOf(c).filter(p => p.company === company.value).map(p => p.product).filter(Boolean)
  : namesOf(c)))].sort())

const shown = computed(() => {
  const q = query.value.toLowerCase()
  let list = byCompany.value
  if (product.value) list = list.filter(c => namesOf(c).includes(product.value))
  if (q) list = list.filter(c => nameOf(c).toLowerCase().includes(q) || String(c.id_number || '').includes(q))
  const by = {
    value: (a, b) => valueOf(b) - valueOf(a),
    products: (a, b) => productCount(b) - productCount(a),
    name: (a, b) => nameOf(a).localeCompare(nameOf(b), 'he'),
  }[sortKey.value]
  return [...list].sort(by)
})
const visible = computed(() => shown.value.slice(0, limit.value))
const allUnpaid = computed(() => props.customers.length > 0 && props.customers.every(c => c.match_status === 'only_production'))
const totReceived = computed(() => shown.value.reduce((s, c) => s + receivedOf(c), 0))
const totExpected = computed(() => shown.value.reduce((s, c) => s + expectedOf(c), 0))
const totPremium = computed(() => shown.value.reduce((s, c) => s + premiumOf(c), 0))
</script>

<style scoped>
.ccl { --acc: var(--tab-comparison); display: flex; flex-direction: column; gap: 14px; }
.ccl-stats { display: flex; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.ccl-stat { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 13px 16px; }
.ccl-stat + .ccl-stat { border-inline-start: 1px solid var(--border-subtle); }
.ccl-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.ccl-val { font-size: 20px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.ccl-stat:first-child .ccl-val { color: var(--acc); }

.ccl-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ccl-search {
  flex: 1 1 220px; display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 38px;
  border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg); color: var(--text-muted);
}
.ccl-search:focus-within { border-color: var(--acc); background: var(--card-bg); }
.ccl-search input { flex: 1; border: none; background: none; outline: none; font: inherit; font-size: 13px; color: var(--text); }
.ccl-select { position: relative; display: flex; align-items: center; }
.ccl-select select {
  appearance: none; height: 38px; padding: 0 12px 0 30px; border-radius: 10px; max-width: 240px;
  border: 1px solid var(--border-subtle); background: var(--card-bg); font: inherit; font-size: 13px; color: var(--text); cursor: pointer;
}
.ccl-select select:focus { outline: none; border-color: var(--acc); }
.ccl-select svg { position: absolute; left: 11px; pointer-events: none; color: var(--text-muted); }
.ccl-sort { display: flex; padding: 3px; border-radius: 10px; background: var(--bg); gap: 2px; }
.ccl-sort button {
  border: none; background: none; font: inherit; font-size: 12px; font-weight: 600; color: var(--text-muted);
  padding: 7px 12px; border-radius: 8px; cursor: pointer;
}
.ccl-sort button.on { background: var(--card-bg); color: var(--acc); box-shadow: var(--shadow-sm); }

.ccl-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.ccl-list li { animation: cclIn 0.35s cubic-bezier(0.2, 0, 0.2, 1) both; animation-delay: var(--d); }
@keyframes cclIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.ccl-none { text-align: center; color: var(--text-muted); font-size: 13px; padding: 20px; }
.ccl-row {
  width: 100%; display: grid; align-items: center; gap: 12px;
  grid-template-columns: minmax(130px, 1.4fr) minmax(0, 1fr) 34px 130px 14px;
  padding: 11px 14px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg);
  font: inherit; color: var(--text); text-align: right; cursor: pointer; transition: border-color 0.2s ease;
}
.ccl-row:hover { border-color: var(--acc); }
.ccl-row:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
.ccl-who { display: flex; flex-direction: column; min-width: 0; }
.ccl-name { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ccl-id { font-size: 11.5px; color: var(--text-muted); }
.ccl-what { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ccl-co { display: flex; align-items: center; gap: 10px; min-width: 0; font-size: 12.5px; font-weight: 700; color: var(--text); }
.ccl-co-item { display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
.ccl-more-co { font-size: 11px; color: var(--text-muted); }
.ccl-prod { font-size: 12px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ccl-prod b { font-weight: 600; color: var(--text); }
.ccl-cos { display: flex; gap: 4px; flex-wrap: wrap; border-bottom: 1px solid var(--border-subtle); }
.ccl-cos button {
  border: none; background: none; font: inherit; font-size: 13px; font-weight: 600; color: var(--text-muted);
  padding: 8px 10px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.ccl-cos button span { font-size: 11.5px; font-weight: 500; opacity: 0.75; }
.ccl-cos button:hover { color: var(--text); }
.ccl-cos button.on { color: var(--acc); border-bottom-color: var(--acc); }
.ccl-cos button:focus-visible { outline: 2px solid var(--acc); outline-offset: -2px; }
.ccl-pill {
  justify-self: center; min-width: 28px; height: 24px; padding: 0 8px; border-radius: 12px; background: var(--bg);
  font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center;
}
.ccl-fig { display: flex; flex-direction: column; align-items: flex-start; font-size: 14px; font-weight: 700; line-height: 1.2; }
.ccl-fig small { font-size: 10.5px; font-weight: 500; color: var(--text-muted); }
.ccl-go { color: var(--text-muted); }
.ccl-more {
  align-self: center; border: 1px solid var(--border-subtle); background: var(--card-bg); border-radius: 10px;
  padding: 9px 16px; font: inherit; font-size: 13px; font-weight: 600; color: var(--acc); cursor: pointer;
}
@media (max-width: 640px) {
  .ccl-stats { flex-wrap: wrap; }
  .ccl-stat { flex: 1 1 45%; padding: 10px 12px; }
  .ccl-val { font-size: 17px; }
  .ccl-row { grid-template-columns: minmax(0, 1fr) 30px 100px 12px; gap: 8px; padding: 10px; }
  .ccl-what { grid-column: 1 / -1; grid-row: 2; }
}
@media (prefers-reduced-motion: reduce) { .ccl-list li { animation: none; } .ccl-row { transition: none; } }
.ccl-act {
  display: inline-flex; align-items: center; gap: 6px; height: 38px; padding: 0 12px; border-radius: 10px;
  border: 1px solid var(--border-subtle); background: var(--card-bg); color: var(--text);
  font: inherit; font-size: 12.5px; font-weight: 600; cursor: pointer; transition: border-color 0.15s ease;
}
.ccl-act:hover { border-color: var(--acc); color: var(--acc); }
.ccl-act:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
</style>
