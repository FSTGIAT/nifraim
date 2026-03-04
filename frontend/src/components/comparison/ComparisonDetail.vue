<template>
  <div class="detail-content">
    <!-- Commission products section — FIRST, prominent -->
    <div v-if="allCommissionProducts.length > 0" class="products-section commission-section">
      <h4>
        מוצרים בנפרעים ({{ allCommissionProducts.length }})
        <span v-if="totalCommission > 0" class="section-total">
          סה"כ עמלה: <span class="ltr-val">{{ formatAmount(totalCommission) }}</span>
        </span>
        <span v-if="totalBalance > 0" class="section-total">
          סה"כ יתרה: <span class="ltr-val">{{ formatAmount(totalBalance) }}</span>
        </span>
      </h4>

      <!-- Matched products (in both files) -->
      <div
        v-for="(m, i) in customer.product_matches.matched"
        :key="'matched-' + i"
        class="product-row matched"
      >
        <div class="product-status-badge matched-badge">שולם</div>
        <div class="product-info">
          <div class="product-name">{{ m.production_product || '—' }}</div>
          <div class="product-meta">
            <span class="meta-item">חשבון: <span class="ltr-val">{{ m.policy_number }}</span></span>
            <span v-if="m.monthly_pct != null" class="meta-item">אחוז חודשי: <span class="ltr-val">{{ formatPct(m.monthly_pct) }}</span></span>
          </div>
        </div>
        <div class="product-amounts">
          <div v-if="m.balance != null" class="amount-item">
            <span class="amount-label">יתרה</span>
            <span class="amount-value ltr-val">{{ formatAmount(m.balance) }}</span>
          </div>
          <div v-if="expectedFromFile(m) != null" class="amount-item expected">
            <span class="amount-label">צפוי</span>
            <span class="amount-value ltr-val">{{ formatAmount(expectedFromFile(m)) }}</span>
          </div>
          <div class="amount-item commission">
            <span class="amount-label">עמלה</span>
            <span class="amount-value ltr-val" :class="commissionDiffClass(m)">{{ formatAmount(m.commission) }}</span>
          </div>
        </div>
      </div>

      <!-- Unmatched commission products (only in commission file) -->
      <div
        v-for="(c, i) in unmatchedCommissionProducts"
        :key="'comm-' + i"
        class="product-row commission-only"
      >
        <div class="product-status-badge commission-badge">
          {{ customer.match_status === 'only_commission' ? 'משלם' : 'רק בנפרעים' }}
        </div>
        <div v-if="customer.has_paying_company" class="product-status-badge paying-badge">חברה משלמת</div>
        <div class="product-info">
          <div class="product-name">{{ c.product || '—' }}</div>
          <div class="product-meta">
            <span v-if="c.account" class="meta-item">חשבון: <span class="ltr-val">{{ c.account }}</span></span>
            <span v-if="c.annual_pct != null" class="meta-item">אחוז שנתי: <span class="ltr-val">{{ formatPct(c.annual_pct) }}</span></span>
            <span v-if="c.monthly_pct != null" class="meta-item">אחוז חודשי: <span class="ltr-val">{{ formatPct(c.monthly_pct) }}</span></span>
          </div>
        </div>
        <div class="product-amounts">
          <div v-if="c.balance != null" class="amount-item">
            <span class="amount-label">יתרה</span>
            <span class="amount-value ltr-val">{{ formatAmount(c.balance) }}</span>
          </div>
          <div class="amount-item commission">
            <span class="amount-label">עמלה</span>
            <span class="amount-value ltr-val">{{ formatAmount(c.commission) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state for commission -->
    <div v-if="allCommissionProducts.length === 0 && customer.match_status !== 'only_production'" class="empty-section">
      אין מוצרים בנפרעים
    </div>

    <!-- Production-only products — SECOND, collapsed -->
    <details v-if="productionOnlyProducts.length > 0" class="production-details">
      <summary class="production-summary">
        <span class="production-summary-text">
          רק בפרודוקציה ({{ productionOnlyProducts.length }})
          <span v-if="totalExpectedCommission > 0" class="expected-total">
            עמלה צפויה: <span class="ltr-val">{{ formatAmount(totalExpectedCommission) }}</span>
          </span>
        </span>
        <svg class="chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </summary>
      <div class="production-products">
        <div
          v-for="(p, i) in productionOnlyProducts"
          :key="'prod-' + i"
          class="product-row production-only"
        >
          <div class="product-status-badge production-badge">רק בפרודוקציה</div>
          <div v-if="p.accumulation === 0 || p.accumulation === null" class="product-status-badge withdrawal-badge">משיכה / ניוד</div>
          <div class="product-info">
            <div class="product-name">{{ p.product || '—' }}</div>
            <div class="product-meta">
              <span v-if="p.policy_number" class="meta-item">חשבון: <span class="ltr-val">{{ p.policy_number }}</span></span>
              <span v-if="p.product_type" class="meta-item">{{ p.product_type }}</span>
              <span v-if="p.company" class="meta-item">{{ p.company }}</span>
            </div>
          </div>
          <div class="product-amounts">
            <div v-if="p.accumulation != null" class="amount-item accumulation">
              <span class="amount-label">צבירה</span>
              <span class="amount-value ltr-val" :class="{ 'zero-accumulation': p.accumulation === 0 }">{{ formatAmount(p.accumulation) }}</span>
            </div>
            <div v-if="p.premium != null" class="amount-item">
              <span class="amount-label">פרמיה</span>
              <span class="amount-value ltr-val">{{ formatAmount(p.premium) }}</span>
            </div>
            <div v-if="findRateForProduct(p)" class="amount-item rate-info">
              <span class="amount-label">אחוז נפרע</span>
              <span class="amount-value ltr-val">{{ findRateForProduct(p).ratePct }}</span>
            </div>
            <div v-else class="amount-item rate-missing">
              <span class="amount-label">אחוז נפרע</span>
              <span class="amount-value">לא הוגדר</span>
            </div>
            <div v-if="expectedCommission(p) != null" class="amount-item expected-commission">
              <span class="amount-label">עמלה צפויה</span>
              <span class="amount-value ltr-val">{{ formatAmount(expectedCommission(p)) }}</span>
            </div>
          </div>
        </div>
      </div>
    </details>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  customer: { type: Object, required: true },
  rates: { type: Array, default: () => [] },
})

const unmatchedCommissionProducts = computed(() => {
  if (props.customer.match_status === 'only_commission') {
    return props.customer.commission_products || []
  }
  return props.customer.product_matches?.unmatched_commission || []
})

const allCommissionProducts = computed(() => {
  const matched = props.customer.product_matches?.matched || []
  return [...matched, ...unmatchedCommissionProducts.value]
})

const productionOnlyProducts = computed(() =>
  props.customer.product_matches?.unmatched_production || []
)

const totalCommission = computed(() =>
  allCommissionProducts.value.reduce((sum, p) => sum + (p.commission || 0), 0)
)

const totalBalance = computed(() =>
  allCommissionProducts.value.reduce((sum, p) => sum + (p.balance || 0), 0)
)

function formatAmount(val) {
  if (val == null) return '—'
  return '₪ ' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatPct(val) {
  if (val == null) return '—'
  return (val * 100).toFixed(4) + '%'
}

function expectedFromFile(matchedProduct) {
  if (matchedProduct.monthly_pct == null || matchedProduct.balance == null) return null
  return matchedProduct.balance * matchedProduct.monthly_pct
}

function commissionDiffClass(matchedProduct) {
  const expected = expectedFromFile(matchedProduct)
  if (expected == null || matchedProduct.commission == null) return ''
  const diff = Math.abs(matchedProduct.commission - expected)
  if (diff < 1) return 'match-ok'
  return 'match-diff'
}

function expectedCommission(product) {
  const rateInfo = findRateForProduct(product)
  if (!rateInfo) return null
  // Gemel/Hishtalmut: accumulation * rate / 12
  if (product.accumulation != null && product.accumulation !== 0) {
    return product.accumulation * rateInfo.rate / 12
  }
  // Insurance: premium * rate / 12
  if (product.premium != null && product.premium !== 0) {
    return product.premium * rateInfo.rate * 100 / 12
  }
  return null
}

const totalExpectedCommission = computed(() =>
  productionOnlyProducts.value.reduce((sum, p) => sum + (expectedCommission(p) || 0), 0)
)

function stripHe(s) { return s.startsWith('ה') && s.length > 2 ? s.slice(1) : null }

const INSURANCE_HINTS = ['פוליסות', 'ביטוח', 'פוליסה']
const GEMEL_HINTS = ['גמל', 'השתלמות']

function findRateForProduct(product) {
  if (!props.rates.length) return null

  // Try matching with both short company name and full receiving_company
  // Also try without Hebrew definite article ה (e.g. הפניקס → פניקס)
  const base = [product.company, product.company_full].filter(Boolean)
  const candidates = [...base]
  for (const c of base) { const s = stripHe(c); if (s) candidates.push(s) }
  if (candidates.length === 0) return null

  // Collect all matching rates
  const matches = new Set()
  for (const companyName of candidates) {
    const cl = companyName.toLowerCase()
    const fw = cl.split(/[\s\-]/)[0]
    for (const r of props.rates) {
      const rn = r.company_name.toLowerCase()
      if (r.company_name === companyName || cl.includes(rn) || rn.includes(cl)
          || (fw.length > 2 && rn.startsWith(fw))) {
        matches.add(r)
      }
    }
  }
  if (matches.size === 0) return null
  const arr = [...matches]
  let best = arr[0]
  if (arr.length > 1) {
    // Prefer rate matching the product category (inferred from data)
    const hints = (product.accumulation && product.accumulation > 0) ? GEMEL_HINTS
                : (product.premium && product.premium > 0) ? INSURANCE_HINTS : null
    if (hints) {
      const preferred = arr.find(r => hints.some(h => r.company_name.includes(h)))
      if (preferred) best = preferred
    }
  }
  return {
    rate: best.rate,
    ratePct: (best.rate * 100).toFixed(2) + '%',
    frequency: best.payment_frequency,
  }
}
</script>

<style scoped>
.detail-content {
  padding: 16px 24px;
  background: var(--bg);
  border-top: 1px solid var(--border-subtle);
}

.products-section h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-subtle);
}

.product-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
  transition: background 0.2s;
}

.product-row:hover {
  background: var(--bg);
}

.product-row.matched {
  border-right: 3px solid var(--green);
}

.product-row.commission-only {
  border-right: 3px solid var(--accent-violet);
  background: rgba(127, 86, 217, 0.04);
}

.product-row.production-only {
  border-right: 3px solid var(--amber);
  background: rgba(251, 146, 60, 0.04);
}

.product-status-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
  white-space: nowrap;
  flex-shrink: 0;
}

.matched-badge {
  background: var(--green-light);
  color: var(--green);
  border: 1px solid var(--green-light);
}

.commission-badge {
  background: rgba(127, 86, 217, 0.08);
  color: var(--accent-violet);
  border: 1px solid rgba(127, 86, 217, 0.08);
}

.production-badge {
  background: rgba(251, 146, 60, 0.08);
  color: var(--amber);
  border: 1px solid rgba(251, 146, 60, 0.12);
}

.withdrawal-badge {
  background: rgba(251, 146, 60, 0.12);
  color: var(--amber);
  border: 1px solid rgba(251, 146, 60, 0.15);
}

.paying-badge {
  background: var(--green-light);
  color: var(--green);
  border: 1px solid var(--green-light);
}

.section-total {
  font-weight: 400;
  font-size: 12px;
  margin-right: 12px;
  color: var(--text);
}

.product-info {
  flex: 1;
  min-width: 0;
}

.product-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.product-meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.product-amounts {
  display: flex;
  gap: 16px;
  flex-shrink: 0;
}

.amount-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.amount-label {
  font-size: 10px;
  color: var(--text-muted);
}

.amount-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.amount-item.commission .amount-value {
  color: var(--green);
}

.amount-item.commission .amount-value.match-ok {
  color: var(--green);
}

.amount-item.commission .amount-value.match-diff {
  color: var(--amber);
}

.amount-item.expected .amount-value {
  color: var(--text-muted);
  font-size: 12px;
}

.amount-item.rate-info .amount-value {
  color: var(--primary);
  font-size: 14px;
}

.amount-item.rate-missing .amount-value {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 400;
}

.amount-item.accumulation .amount-value {
  color: #38BDF8;
}

.amount-item.accumulation .amount-value.zero-accumulation {
  color: var(--amber);
}

.amount-item.expected-commission .amount-value {
  color: var(--accent-emerald);
  font-weight: 700;
}

.expected-total {
  font-weight: 400;
  font-size: 12px;
  margin-right: 12px;
  color: var(--accent-emerald);
}

.ltr-val {
  direction: ltr;
  unicode-bidi: isolate;
}

/* Production-only collapsed section */
.production-details {
  margin-top: 16px;
}

.production-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(251, 146, 60, 0.04);
  border: 1px solid rgba(251, 146, 60, 0.12);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--amber);
  list-style: none;
  transition: background 0.2s;
}

.production-summary::-webkit-details-marker {
  display: none;
}

.production-summary:hover {
  background: rgba(251, 146, 60, 0.08);
}

.production-summary-text {
  flex: 1;
}

.production-summary .chevron {
  transition: transform 0.2s;
}

.production-details[open] .production-summary .chevron {
  transform: rotate(180deg);
}

.production-products {
  margin-top: 8px;
}

.empty-section {
  font-size: 13px;
  color: var(--text-muted);
  padding: 12px;
  text-align: center;
  background: var(--bg);
  border-radius: 8px;
  border: 1px dashed var(--border-subtle);
}
</style>
