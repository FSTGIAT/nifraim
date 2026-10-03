<template>
  <!-- Customer detail — in the shared centred drill (iPhone-style grow from
       the row pressed, above the list it came from) and the Production drill
       language, in the comparison green (QA 2026-10-01). Logic unchanged:
       paid checkbox, mail to company, drill. -->
  <DataModal :open="!!customer" :origin="origin" :title="customer ? customer.name : ''"
             :subtitle="customer ? 'ת.ז ' + customer.id_number : ''"
             accent="var(--tab-comparison)" :layer="1020" @close="$emit('close')">
    <div v-if="customer" class="cd">
          <div v-if="customer.client_phone || customer.client_email || customer.employer_name || customer.commission_count > 0 || customer.paid_count > 0"
               class="cd-meta">
            <span v-if="customer.client_phone" class="ltr-number">{{ customer.client_phone }}</span>
            <span v-if="customer.client_email" class="ltr-number">{{ customer.client_email }}</span>
            <span v-if="customer.employer_name">{{ customer.employer_name }}</span>
            <span v-if="customer.commission_count > 0" class="cd-chip">{{ customer.commission_count }} מוצרים בנפרעים</span>
            <span v-if="onlyCommCompanies.length" class="cd-chip cd-chip--only">רק בנפרעים · {{ onlyCommCompanies.join(', ') }}</span>
            <span v-if="customer.paid_count > 0" class="cd-chip cd-chip--ok">{{ customer.paid_count }} שולמו</span>
          </div>

          <!-- Summary KPI strip -->
          <div class="kpi-strip">
            <div class="kpi" v-if="totals.commission > 0">
              <span class="kpi-label">עמלה</span>
              <span class="kpi-val ltr-number kpi-green">{{ fmt(totals.commission) }}</span>
            </div>
            <div class="kpi" v-if="totals.balance > 0">
              <span class="kpi-label">צבירה נפרעים</span>
              <span class="kpi-val ltr-number kpi-cyan">{{ fmt(totals.balance) }}</span>
            </div>
            <div class="kpi" v-if="totals.accumulation > 0">
              <span class="kpi-label">צבירה פרודוקציה</span>
              <span class="kpi-val ltr-number">{{ fmt(totals.accumulation) }}</span>
            </div>
            <div class="kpi" v-if="totals.premium > 0">
              <span class="kpi-label">פרמיה</span>
              <span class="kpi-val ltr-number">{{ fmt(totals.premium) }}</span>
            </div>
            <div class="kpi" v-if="totals.expectedCommission > 0">
              <span class="kpi-label">עמלה צפויה</span>
              <span class="kpi-val ltr-number kpi-expected">{{ fmt(totals.expectedCommission) }}</span>
            </div>
          </div>

          <!-- Product rows -->
          <div class="products-scroll">
            <!-- What is NOT paid comes first; paid lines fold into one row
                 (QA 2026-10-01: one unpaid כלל policy sat under 43 paid
                 rows). Repeat payments on one policy merge into one row. -->
            <template v-for="sec in sections" :key="sec.key">
            <button v-if="sections.length > 1" type="button" class="sec-head" :class="'sec-head--' + sec.key"
                    :aria-expanded="sec.open" @click="sec.toggle && sec.toggle()">
              <span class="sec-dot" aria-hidden="true"></span>
              <span class="sec-title">{{ sec.title }}</span>
              <span class="sec-count ltr-number">{{ sec.rows.length }}</span>
              <span v-if="sec.sum >= 0.5" class="sec-sum ltr-number">{{ fmt(sec.sum) }}</span>
              <svg v-if="sec.toggle" class="sec-chev" :class="{ 'sec-chev--open': sec.open }" width="14" height="14"
                   viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"
                   stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
            </button>
            <div class="sec-fold" :class="{ 'sec-fold--open': sec.open }">
            <div class="sec-fold-inner">
            <div
              v-for="(p, i) in sec.rows"
              :key="sec.key + i"
              class="p-row"
              :class="productRowClass(p)"
            >
              <!-- Left: checkbox + name -->
              <button class="p-cb" :class="p.paid ? 'cb-on' : 'cb-off'" @click.stop="togglePaid(p)">
                <svg v-if="p.paid" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
              <div class="p-identity">
                <div class="p-name">{{ shortProduct(p.product) }}</div>
                <div class="p-sub">
                  <span v-if="p.company">{{ shortCompany(p.company) }}</span>
                  <span v-if="p.policy_number" class="ltr-number">{{ p.policy_number }}</span>
                  <span v-if="p.fund_type" class="p-tag-info">{{ p.fund_type }}</span>
                  <span v-if="p.track" class="p-tag-info">{{ p.track }}</span>
                  <span v-if="!p.paid && !p.source" class="p-tag-production">רק בפרודוקציה</span>
                  <span v-if="p.source === 'commission_only'" class="p-tag-commission">רק בנפרעים</span>
                  <span v-if="p._payments > 1" class="p-tag-info ltr-number">{{ p._payments }} תשלומים</span>
                </div>
              </div>

              <!-- Right: amounts — only show non-zero -->
              <div class="p-amounts">
                <div class="amt" v-if="p.commission > 0">
                  <span class="amt-lbl">עמלה</span>
                  <span class="amt-val ltr-number amt-green">{{ fmtCell(p.commission) }}</span>
                </div>
                <div class="amt" v-if="p.balance > 0">
                  <span class="amt-lbl">צבירה נפרעים</span>
                  <span class="amt-val ltr-number">{{ fmtCell(p.balance) }}</span>
                </div>
                <div class="amt" v-if="p.accumulation > 0">
                  <span class="amt-lbl">צבירה פרודוקציה</span>
                  <span class="amt-val ltr-number">{{ fmtCell(p.accumulation) }}</span>
                </div>
                <div class="amt" v-if="p.premium > 0">
                  <span class="amt-lbl">פרמיה</span>
                  <span class="amt-val ltr-number">{{ fmtCell(p.premium) }}</span>
                </div>
                <div class="amt" v-if="p.management_fee != null">
                  <span class="amt-lbl">ד.נ %</span>
                  <span class="amt-val ltr-number amt-muted">{{ (p.management_fee * 100).toFixed(2) }}%</span>
                </div>
                <div class="amt" v-if="p.management_fee_amount > 0">
                  <span class="amt-lbl">ד.נ ₪</span>
                  <span class="amt-val ltr-number">{{ fmtCell(p.management_fee_amount) }}</span>
                </div>
                <!-- Rate + expected now render on PAID lines too. They used to
                     be unpaid-only, which hid the comparison exactly where it
                     matters: on a line that WAS paid, is it the right amount? -->
                <div class="amt" v-if="rateLabel(p)">
                  <span class="amt-lbl">{{ isEstimate(p) ? 'אחוז משוער' : 'אחוז לפי ההסכם' }}</span>
                  <span class="amt-val ltr-number amt-muted">{{ isEstimate(p) ? '~' : '' }}{{ rateLabel(p) }}</span>
                </div>
                <div class="amt" v-if="expectedCommission(p) != null"
                     :title="isEstimate(p) ? 'אין בהסכם שיעור למוצר הזה — הערכה לפי שיעור כללי של החברה' : ''">
                  <span class="amt-lbl">{{ isEstimate(p) ? 'הערכה' : 'אמור לשלם' }}</span>
                  <span class="amt-val ltr-number amt-expected">{{ isEstimate(p) ? '~' : '' }}{{ fmtCell(expectedCommission(p)) }}</span>
                </div>
                <!-- Only ever shown against a FIRM rate — an estimate would
                     manufacture a debt out of a guess. -->
                <div class="amt" v-if="p.commission_gap > 0">
                  <span class="amt-lbl">חסר</span>
                  <span class="amt-val ltr-number amt-gap">{{ fmtCell(p.commission_gap) }}</span>
                </div>
                <div class="amt" v-if="p.sign_date">
                  <span class="amt-lbl">הצטרפות</span>
                  <span class="amt-val amt-date">{{ formatDate(p.sign_date) }}</span>
                </div>
              </div>
            </div>

            </div>
            </div>
            </template>

            <!-- Empty -->
            <div v-if="customer.products.length === 0" class="empty-msg">אין מוצרים</div>
          </div>

          <!-- Footer action -->
          <div class="modal-footer" v-if="unpaidProducts.length > 0">
            <button class="btn-mail-footer" @click="openMail">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="4" width="20" height="16" rx="2"/>
                <path d="M22 7l-10 7L2 7"/>
              </svg>
              שלח מייל לחברה
            </button>
          </div>
    </div>
  </DataModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import DataModal from '../workspace/DataModal.vue'
import api from '../../api/client.js'
import { openMailCompose } from '../../utils/mailHelper.js'
import { calcExpectedCommission } from '../../utils/commissionCalc.js'

const props = defineProps({
  customer: { type: Object, default: null },
  commissionRates: { type: Array, default: () => [] },
  category: { type: String, default: '' },
  userName: { type: String, default: '' },
  // The row / element this drill grows out of.
  origin: { type: null, default: null },
})

const emit = defineEmits(['close', 'drill'])

const totals = computed(() => {
  if (!props.customer) return { accumulation: 0, premium: 0, commission: 0, balance: 0, expectedCommission: 0 }
  const products = props.customer.products
  const expComm = products
    .filter(p => !p.paid && !p.source)
    .reduce((s, p) => s + (expectedCommission(p) || 0), 0)
  return {
    accumulation: products.reduce((s, p) => s + (p.accumulation || 0), 0),
    // Pension deposits are not an insurance premium — same figure as the
    // "לקוחות לפי פרמיה" chart (falls back to the raw sum for other callers).
    premium: props.customer.insurance_premium ?? products.reduce((s, p) => s + (p.premium || 0), 0),
    commission: products.reduce((s, p) => s + (p.commission || 0), 0),
    balance: products.reduce((s, p) => s + (p.balance || 0), 0),
    expectedCommission: expComm,
  }
})

// Companies where this customer has a נפרעים line with no production
// behind it — so a customer with products at two companies says WHERE it is
// only in נפרעים, not just that it is (QA 2026-10-02).
const onlyCommCompanies = computed(() => {
  if (!props.customer) return []
  return [...new Set(props.customer.products
    .filter(p => p.source === 'commission_only')
    .map(p => shortCompany(p.company))
    .filter(Boolean))]
})

const isUnpaidRow = p => !p.paid && !p.source

// Repeat נפרעים lines for the same policy + product (a policy paid in parts,
// or per coverage) become ONE row with the summed amounts — they read as
// duplicates otherwise (QA 2026-10-01: מנורה 351255435 ×3).
function mergeRows(rows) {
  const out = []
  const by = new Map()
  for (const p of rows) {
    const k = p.policy_number ? [p.company, p.policy_number, p.product].join('|') : null
    if (!k || !by.has(k)) {
      const row = { ...p, _members: [p], _payments: 1 }
      if (k) by.set(k, row)
      out.push(row)
      continue
    }
    const m = by.get(k)
    m._members.push(p)
    m._payments += 1
    for (const f of ['commission', 'balance', 'premium', 'management_fee_amount', 'expected_commission', 'commission_gap']) {
      if (p[f] != null || m[f] != null) m[f] = (Number(m[f]) || 0) + (Number(p[f]) || 0)
    }
  }
  return out
}

const paidOpen = ref(false)
watch(() => props.customer, () => { paidOpen.value = false })

const sections = computed(() => {
  const all = sortedProducts.value
  const unpaid = all.filter(isUnpaidRow)
  const paid = mergeRows(all.filter(p => !isUnpaidRow(p)))
  const sumOf = (rows, f) => rows.reduce((t, p) => t + (Number(p[f]) || 0), 0)
  if (!unpaid.length || !paid.length) {
    return [{ key: 'all', rows: unpaid.length ? unpaid : paid, open: true }]
  }
  const cos = [...new Set(paid.map(p => shortCompany(p.company)).filter(Boolean))]
  return [
    { key: 'unpaid', title: 'לא שולם', rows: unpaid, open: true,
      sum: unpaid.reduce((t, p) => t + (expectedCommission(p) || 0), 0) },
    { key: 'paid', title: 'שולם' + (cos.length ? ' · ' + cos.join(', ') : ''), rows: paid,
      sum: sumOf(paid, 'commission'), open: paidOpen.value, toggle: () => { paidOpen.value = !paidOpen.value } },
  ]
})

// Sort products: commission-file products first, production-only at bottom
const sortedProducts = computed(() => {
  if (!props.customer) return []
  return [...props.customer.products].sort((a, b) => {
    const aHasCommission = (a.commission > 0 || a.source === 'commission_only' || a.paid) ? 1 : 0
    const bHasCommission = (b.commission > 0 || b.source === 'commission_only' || b.paid) ? 1 : 0
    return bHasCommission - aHasCommission
  })
})

function productRowClass(p) {
  if (!p.paid && !p.source) return 'p-production-only'
  if (p.source === 'commission_only') return 'p-commission'
  return 'p-paid'
}

function stripHe(s) { return s.startsWith('ה') && s.length > 2 ? s.slice(1) : null }

const INSURANCE_HINTS = ['פוליסות', 'ביטוח', 'פוליסה']
const GEMEL_HINTS = ['גמל', 'השתלמות']

function getCategoryHints(product) {
  if (props.category) {
    if (props.category.includes('ביטוח')) return INSURANCE_HINTS
    if (props.category.includes('גמל')) return GEMEL_HINTS
  }
  if (product.accumulation && product.accumulation > 0) return GEMEL_HINTS
  if (product.premium && product.premium > 0) return INSURANCE_HINTS
  return null
}

function findRate(product) {
  if (props.commissionRates.length === 0) return null
  const base = [product.company, product.company_full].filter(Boolean)
  const candidates = [...base]
  for (const c of base) { const s = stripHe(c); if (s) candidates.push(s) }
  if (candidates.length === 0) return null

  // Collect all matching rates
  const matches = new Set()
  for (const companyName of candidates) {
    const cl = companyName.toLowerCase()
    const fw = cl.split(/[\s\-]/)[0]
    for (const r of props.commissionRates) {
      const rn = r.company_name.toLowerCase()
      if (r.company_name === companyName || cl.includes(rn) || rn.includes(cl)
          || (fw.length > 2 && rn.startsWith(fw))) {
        matches.add(r)
      }
    }
  }
  if (matches.size === 0) return null
  const arr = [...matches]
  if (arr.length === 1) return arr[0]
  // Prefer rate matching the category
  const hints = getCategoryHints(product)
  if (hints) {
    const preferred = arr.find(r => hints.some(h => r.company_name.includes(h)))
    if (preferred) return preferred
  }
  return arr[0]
}

// The backend now resolves each product's rate with the canonical selector
// (rate_select.rate_for_product) and ships it on the product itself. Prefer
// that. `findRate` below is a FALLBACK only, for comparisons persisted before
// this existed — it matches on company name alone and cannot tell two products
// at the same insurer apart, which is exactly the bug this replaces.
// `expected_is_estimate` is null ONLY when the backend had no rate table; once
// it ran it is always a boolean. rate 0 + boolean flag = "the selector looked
// and correctly declined" (typically a gemel-magnitude rate that must not be
// applied to an insurance premium). Falling back to the company-name matcher
// there re-creates the bug this replaced — it returns מגדל's 0.30% for a חיים
// policy purely because the company matches.
function backendResolved(p) {
  return p && p.expected_is_estimate !== undefined && p.expected_is_estimate !== null
}

function isEstimate(p) {
  return p?.expected_is_estimate === true
}

function rateOf(p) {
  if (p && typeof p.rate === 'number' && p.rate > 0) return p.rate
  if (backendResolved(p)) return null
  return findRate(p)?.rate ?? null
}

function rateLabel(p) {
  const rate = rateOf(p)
  if (!rate) return null
  return (rate * 100).toFixed(2) + '%'
}

function expectedCommission(p) {
  if (p && p.expected_commission != null) return p.expected_commission
  if (backendResolved(p)) return null
  const rate = rateOf(p)
  if (!rate) return null
  return calcExpectedCommission(p, rate)
}

const unpaidProducts = computed(() => {
  if (!props.customer) return []
  return props.customer.products.filter(p => !p.paid && !p.source)
})

function openMail() {
  const name = props.customer?.name || ''
  const idNumber = props.customer?.id_number || ''
  const products = unpaidProducts.value

  // Find company email from any matching rate
  let companyEmail = ''
  for (const p of products) {
    const rate = findRate(p)
    if (rate?.company_email) {
      companyEmail = rate.company_email
      break
    }
  }

  // Build product lines with policy/account number and premium
  const productLines = products.map(p => {
    const date = p.sign_date ? formatDate(p.sign_date) : ''
    const premiumStr = p.premium > 0 ? ` | פרמיה: ₪${Math.round(p.premium)}` : ''
    const policyStr = p.policy_number ? ` | מס׳ פוליסה/חשבון: ${p.policy_number}` : ''
    return `- ${p.product || ''}${policyStr}${date ? ' מתאריך ' + date : ''}${premiumStr}`
  }).join('\n')

  const subject = `בקשת תשלום עמלות נפרעים - ${name}`
  const body = `שלום רב,

עבור הלקוח ${name} מספר ת.ז ${idNumber} לא התקבלו עמלות נפרעים עבור המוצרים הבאים:

${productLines}

אודה לטיפולכם ותשלום רטרו בגין לקוח זה.

בברכה,
${props.userName}`

  openMailCompose({ to: companyEmail, subject, body })
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d)) return dateStr
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

async function togglePaid(row) {
  // A merged row stands for several lines of one policy — mark them together.
  const members = row._members || [row]
  const next = !row.paid
  row.paid = next
  for (const m of members) m.paid = next
  const product = members[0]
  if (props.customer) {
    props.customer.paid_count = props.customer.products.filter(p => p.paid).length
    props.customer.unpaid_count = props.customer.products.filter(p => !p.paid).length
    props.customer.paid_commission = props.customer.products.filter(p => p.paid).reduce((s, p) => s + (p.commission || 0), 0)
  }
  if (product.policy_number && props.customer?.id_number) {
    try {
      await api.patch('/comparison/mark-paid', {
        id_number: props.customer.id_number,
        policy_number: product.policy_number,
        paid: product.paid,
      })
    } catch (e) { /* optimistic */ }
  }
}

function shortProduct(name) {
  if (!name) return '—'
  if (name.includes(' - ')) return name.split(' - ').slice(1).join(' - ')
  return name
}

function shortCompany(name) {
  if (!name) return ''
  const words = name.split(/\s+/)
  if (words.length <= 2) return name
  return words.slice(0, 2).join(' ')
}

function fmt(val) {
  if (val == null || val === 0) return '—'
  return '₪' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function fmtCell(val) {
  if (val == null || val === 0) return '—'
  return '₪' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}
</script>

<style scoped>
/* Production-drill language in the comparison green (QA 2026-10-01). */
.cd { --acc: var(--tab-comparison); display: flex; flex-direction: column; gap: 14px; }

.cd-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; font-size: 12.5px; color: var(--text-muted); }
.cd-chip { padding: 2px 10px; border-radius: 10px; background: var(--bg); color: var(--text); font-weight: 600; }
.cd-chip--ok { background: var(--tab-comparison-wash, var(--bg)); color: var(--acc); }
.cd-chip--only { background: color-mix(in srgb, var(--chart-2) 14%, transparent); color: var(--tab-portal-ink); }

/* summary strip */
.kpi-strip { display: flex; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.kpi { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 13px 16px; }
.kpi + .kpi { border-inline-start: 1px solid var(--border-subtle); }
.kpi-label { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.kpi-val { font-size: 20px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.kpi:first-child .kpi-val { color: var(--acc); }

/* product cards */
.products-scroll { display: flex; flex-direction: column; gap: 8px; }
.p-row {
  display: grid; grid-template-columns: 26px minmax(150px, 1fr) minmax(0, 1.6fr); align-items: center; gap: 14px;
  padding: 12px 14px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg);
}
/* The row's state is carried by one quiet mark on the start edge, not a tint. */
.p-row.p-production-only { box-shadow: inset -3px 0 0 var(--amber); }
.p-row.p-paid { box-shadow: inset -3px 0 0 var(--acc); }
.p-row.p-commission { box-shadow: inset -3px 0 0 var(--border-subtle); }

.p-cb {
  width: 22px; height: 22px; border-radius: 7px; display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer; transition: background 0.15s ease, border-color 0.15s ease;
}
.cb-off { background: var(--card-bg); border: 1.5px solid var(--border-subtle); color: transparent; }
.cb-off:hover { border-color: var(--acc); }
.cb-on { background: var(--acc); border: 1.5px solid var(--acc); color: #fff; }

.p-identity { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.p-name { font-size: 14px; font-weight: 700; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.p-sub { display: flex; flex-wrap: wrap; gap: 4px 10px; font-size: 12px; color: var(--text-muted); }
.p-tag-info { color: var(--text-muted); }
.p-tag-production { padding: 1px 8px; border-radius: 8px; background: var(--amber-light); color: var(--amber); font-weight: 600; }
/* Sky = the only_commission status colour (STATUS_COLORS); ink shade for text contrast. */
.p-tag-commission { padding: 1px 8px; border-radius: 8px; background: color-mix(in srgb, var(--chart-2) 14%, transparent); color: var(--tab-portal-ink); font-weight: 600; }

.p-amounts { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px 18px; }
.amt { display: flex; flex-direction: column; align-items: flex-start; min-width: 64px; }
.amt-lbl { font-size: 11px; color: var(--text-muted); }
.amt-val { font-size: 14px; font-weight: 700; color: var(--text); }
.amt-green { color: var(--acc); }
.amt-muted { color: var(--text-muted); font-weight: 600; }
.amt-expected { color: var(--text); }
.amt-gap { color: var(--text); }
.amt-date { font-size: 12.5px; font-weight: 600; color: var(--text-muted); }

.empty-msg { text-align: center; color: var(--text-muted); font-size: 13px; padding: 18px; }

/* action pinned at the bottom of the scrolling drill */
.modal-footer {
  position: sticky; bottom: -16px; margin: 4px -20px -16px; padding: 12px 20px 16px;
  background: linear-gradient(to top, var(--card-bg) 75%, transparent);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
.btn-mail-footer {
  width: 100%; display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 12px 18px; border: none; border-radius: 10px; font: inherit; font-size: 14px; font-weight: 700;
  background: var(--acc); color: #fff; cursor: pointer;
  box-shadow: 0 6px 16px color-mix(in srgb, var(--acc) 28%, transparent);
  transition: transform 0.15s ease;
}
.btn-mail-footer:hover { transform: translateY(-1px); }
.btn-mail-footer:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }

@media (max-width: 640px) {
  .kpi-strip { flex-wrap: wrap; }
  .kpi { flex: 1 1 45%; padding: 10px 12px; }
  .kpi-val { font-size: 17px; }
  .p-row { grid-template-columns: 24px minmax(0, 1fr); }
  .p-amounts { grid-column: 1 / -1; justify-content: flex-start; }
}
@media (prefers-reduced-motion: reduce) { .p-cb, .btn-mail-footer { transition: none; } }
/* ── sections: unpaid first, paid folded ── */
.sec-head {
  width: 100%; display: flex; align-items: center; gap: 8px; margin: 4px 0 6px; padding: 8px 4px;
  background: none; border: none; font: inherit; text-align: right; color: var(--text); cursor: default;
}
.sec-head--paid { cursor: pointer; border-top: 1px solid var(--border-subtle); padding-top: 12px; margin-top: 10px; }
.sec-head--paid:hover .sec-title { color: var(--tab-comparison); }
.sec-head:focus-visible { outline: 2px solid var(--tab-comparison); outline-offset: 2px; border-radius: 8px; }
.sec-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--red, #C23934); flex: 0 0 auto; }
.sec-head--paid .sec-dot { background: var(--tab-comparison); }
.sec-title { font-size: 14px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.sec-count {
  min-width: 22px; height: 22px; padding: 0 7px; border-radius: 11px; background: var(--bg);
  font-size: 12px; font-weight: 700; color: var(--text-muted); display: inline-flex; align-items: center; justify-content: center;
}
.sec-sum { margin-inline-start: auto; font-size: 14px; font-weight: 800; }
.sec-head--unpaid .sec-sum { color: var(--red, #C23934); }
.sec-head--paid .sec-sum { color: var(--tab-comparison); }
.sec-chev { color: var(--text-muted); transition: transform 0.25s ease; flex: 0 0 auto; }
.sec-chev--open { transform: rotate(180deg); }
.sec-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.35s cubic-bezier(0.2, 0, 0.2, 1); }
.sec-fold--open { grid-template-rows: 1fr; }
.sec-fold-inner { overflow: hidden; min-height: 0; display: flex; flex-direction: column; gap: inherit; }
@media (prefers-reduced-motion: reduce) { .sec-fold, .sec-chev { transition: none; } }
</style>
