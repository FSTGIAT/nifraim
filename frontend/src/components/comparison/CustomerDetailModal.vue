<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="customer" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-card">
          <!-- Header -->
          <div class="modal-header">
            <button class="modal-close" @click="$emit('close')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
            <div class="header-right">
              <div class="header-name">{{ customer.name }}</div>
              <div class="header-id ltr-number">ת.ז {{ customer.id_number }}</div>
              <div v-if="customer.client_phone || customer.client_email || customer.employer_name" class="header-contact">
                <span v-if="customer.client_phone" class="contact-item ltr-number">{{ customer.client_phone }}</span>
                <span v-if="customer.client_email" class="contact-item ltr-number">{{ customer.client_email }}</span>
                <span v-if="customer.employer_name" class="contact-item">{{ customer.employer_name }}</span>
              </div>
            </div>
            <div class="header-chips">
              <span class="chip chip-commission" v-if="customer.commission_count > 0">{{ customer.commission_count }} מוצרים</span>
              <span class="chip chip-success" v-if="customer.paid_count > 0">{{ customer.paid_count }} שולם</span>
            </div>
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
            <div
              v-for="(p, i) in sortedProducts"
              :key="i"
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
                <div class="amt" v-if="!p.paid && !p.source && rateLabel(p)">
                  <span class="amt-lbl">אחוז</span>
                  <span class="amt-val ltr-number amt-muted">{{ rateLabel(p) }}</span>
                </div>
                <div class="amt" v-if="!p.paid && !p.source && expectedCommission(p) != null">
                  <span class="amt-lbl">עמלה צפויה</span>
                  <span class="amt-val ltr-number amt-expected">{{ fmtCell(expectedCommission(p)) }}</span>
                </div>
                <div class="amt" v-if="p.sign_date">
                  <span class="amt-lbl">הצטרפות</span>
                  <span class="amt-val amt-date">{{ formatDate(p.sign_date) }}</span>
                </div>
              </div>
            </div>

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
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import api from '../../api/client.js'
import { openMailCompose } from '../../utils/mailHelper.js'
import { calcExpectedCommission } from '../../utils/commissionCalc.js'

const props = defineProps({
  customer: { type: Object, default: null },
  commissionRates: { type: Array, default: () => [] },
  category: { type: String, default: '' },
  userName: { type: String, default: '' },
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
    premium: products.reduce((s, p) => s + (p.premium || 0), 0),
    commission: products.reduce((s, p) => s + (p.commission || 0), 0),
    balance: products.reduce((s, p) => s + (p.balance || 0), 0),
    expectedCommission: expComm,
  }
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

function rateLabel(p) {
  const rate = findRate(p)
  if (!rate) return null
  return (rate.rate * 100).toFixed(2) + '%'
}

function expectedCommission(p) {
  const rate = findRate(p)
  if (!rate) return null
  return calcExpectedCommission(p, rate.rate)
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

  // Build product lines with premium
  const productLines = products.map(p => {
    const date = p.sign_date ? formatDate(p.sign_date) : ''
    const premiumStr = p.premium > 0 ? ` | פרמיה: ₪${Math.round(p.premium)}` : ''
    return `- ${p.product || ''}${date ? ' מתאריך ' + date : ''}${premiumStr}`
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

async function togglePaid(product) {
  product.paid = !product.paid
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
/* Overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

/* Card */
.modal-card {
  width: 100%;
  max-width: 600px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
}

/* ── Header ── */
.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #F7F8FA;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
}

.header-right { flex: 1; min-width: 0; }
.header-name { font-size: 15px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.header-id { font-size: 11px; color: var(--text-muted); margin-top: 1px; }
.header-contact { display: flex; gap: 8px; font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.contact-item + .contact-item::before { content: '·'; margin-left: 8px; color: var(--light-gray); }

.header-chips { display: flex; gap: 5px; flex-shrink: 0; }
.chip { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
.chip-commission { background: rgba(127, 86, 217, 0.08); color: var(--accent-violet); }
.chip-success { background: var(--green-light); color: var(--green); }

.modal-close {
  position: absolute; top: 10px; left: 10px;
  background: transparent; border: 1px solid var(--border);
  color: var(--text-muted); width: 26px; height: 26px;
  border-radius: 6px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s; z-index: 2;
}
.modal-close:hover { background: var(--border-subtle); color: var(--text); }

/* ── KPI strip ── */
.kpi-strip {
  display: flex;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  background: #FAFBFC;
}

.kpi {
  flex: 1;
  padding: 8px 12px;
  text-align: center;
  border-left: 1px solid var(--border-subtle);
}
.kpi:last-child { border-left: none; }

.kpi-label { display: block; font-size: 10px; font-weight: 600; color: var(--text-muted); letter-spacing: 0.2px; }
.kpi-val { display: block; font-size: 13px; font-weight: 800; color: var(--text); margin-top: 1px; }
.kpi-green { color: var(--green); }
.kpi-cyan { color: #06A59A; }
.kpi-expected { color: var(--accent-emerald, #059669); }

/* ── Product rows ── */
.products-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
}

.products-scroll::-webkit-scrollbar { width: 4px; }
.products-scroll::-webkit-scrollbar-track { background: transparent; }
.products-scroll::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.12); border-radius: 4px; }

.p-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  transition: background 0.12s;
}

.p-row:hover { background: #F5F7FA; }

.p-production-only {
  border-right: 3px solid var(--amber);
  background: rgba(251, 146, 60, 0.03);
}

.p-commission {
  border-right: 3px solid var(--accent-violet);
  background: rgba(127, 86, 217, 0.03);
}

.p-paid {
  border-right: 3px solid var(--green);
}

/* Checkbox */
.p-cb {
  width: 20px; height: 20px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; cursor: pointer;
  border: 2px solid; background: transparent; padding: 0;
  margin-top: 1px; transition: all 0.12s;
}
.cb-off { border-color: var(--light-gray); color: transparent; }
.cb-off:hover { border-color: var(--green); background: var(--green-light); }
.cb-on { border-color: var(--green); background: var(--green-light); color: var(--green); }
.cb-on:hover { border-color: var(--red); background: var(--red-light); }

/* Identity */
.p-identity { flex: 1; min-width: 0; }
.p-name {
  font-size: 12px; font-weight: 600; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  line-height: 1.4;
}
.p-sub {
  display: flex; gap: 6px; align-items: center;
  font-size: 11px; color: var(--text-muted); margin-top: 1px;
}
.p-sub span + span::before { content: '·'; margin-left: 6px; color: var(--light-gray); }

.p-tag-info {
  font-size: 9px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 6px;
  background: rgba(1, 118, 211, 0.06);
  color: var(--primary);
}

.p-tag-production {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 6px;
  background: rgba(251, 146, 60, 0.08);
  color: var(--amber);
  border: 1px solid rgba(251, 146, 60, 0.12);
}

/* Amounts grid — right side */
.p-amounts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  flex-shrink: 0;
  max-width: 280px;
  justify-content: flex-end;
}

.amt {
  display: flex;
  align-items: baseline;
  gap: 4px;
  white-space: nowrap;
}

.amt-lbl {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
}

.amt-val {
  font-size: 12px;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

.amt-green { color: var(--green); }
.amt-muted { color: var(--primary); font-weight: 600; }
.amt-expected { color: var(--accent-emerald, #059669); font-weight: 700; }
.amt-date { color: var(--text-muted); font-size: 11px; font-weight: 500; }

/* Empty state */
.empty-msg {
  text-align: center; padding: 32px; color: var(--text-muted); font-size: 13px;
}

/* ── Footer ── */
.modal-footer {
  padding: 8px 12px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.btn-mail-footer {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%; padding: 8px;
  border: 1px solid var(--primary); border-radius: 6px;
  background: var(--primary-light); color: var(--primary);
  font-size: 12px; font-weight: 600; font-family: inherit;
  cursor: pointer; transition: all 0.15s;
}
.btn-mail-footer:hover { background: var(--primary); border-color: var(--primary); color: #fff; }

/* Transition */
.modal-enter-active { animation: modalIn 0.2s ease-out; }
.modal-leave-active { animation: modalIn 0.12s ease reverse; }
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.ltr-number { direction: ltr; unicode-bidi: isolate; }
</style>
