<template>
  <div class="unpaid-tab">
    <!-- Empty state -->
    <div v-if="rows.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="1" x2="12" y2="23"/>
          <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
        </svg>
      </div>
      <h3>אין נתוני השוואה</h3>
      <p>יש לבצע השוואה בלשונית "השוואת נפרעים" כדי לראות סיכום חובות</p>
    </div>

    <!-- Has data -->
    <template v-else>
      <!-- Summary cards -->
      <div class="summary-row">
        <div class="summary-card highlight">
          <span class="sc-label">סה״כ חיוב לא משולם</span>
          <span class="sc-value red ltr-number">{{ formatCurrency(totals.amount) }}</span>
        </div>
        <div class="summary-card">
          <span class="sc-label">מוצרים לא משולמים</span>
          <span class="sc-value ltr-number">{{ totals.count.toLocaleString() }}</span>
        </div>
        <div class="summary-card">
          <span class="sc-label">השוואות פעילות</span>
          <span class="sc-value ltr-number">{{ rows.length }}</span>
        </div>
      </div>

      <!-- Table -->
      <div class="table-card">
        <div class="table-toolbar">
          <button class="btn-clear" @click="clearAll">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
            </svg>
            <span>נקה הכל</span>
          </button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th class="th-company">חברה</th>
              <th class="th-category">קטגוריה</th>
              <th class="th-count">מוצרים</th>
              <th class="th-amount">חיוב לא משולם</th>
              <th class="th-bar"></th>
              <th class="th-actions"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.key">
              <td class="td-company">
                <div class="company-cell">
                  <span class="company-avatar" :style="{ background: row.color }">{{ row.initial }}</span>
                  <span class="company-name">{{ row.company }}</span>
                </div>
              </td>
              <td class="td-category">
                <span class="category-pill" :class="row.catKey">{{ row.category }}</span>
              </td>
              <td class="td-count ltr-number">{{ row.count.toLocaleString() }}</td>
              <td class="td-amount ltr-number">{{ formatCurrency(row.amount) }}</td>
              <td class="td-bar">
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: row.pct + '%' }"></div>
                </div>
              </td>
              <td class="td-actions">
                <button class="btn-delete-row" @click="deleteRow(row.catKey)" title="מחק">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useComparisonStore } from '../../stores/comparison.js'
import api from '../../api/client.js'

const comparisonStore = useComparisonStore()
const commissionRates = ref([])

onMounted(async () => {
  try {
    const res = await api.get('/commission-rates')
    commissionRates.value = res.data
  } catch (e) { /* rates not available */ }
})

const CATEGORY_LABELS = {
  gemel_hishtalmut: 'גמל והשתלמות',
  insurance: 'ביטוח',
}

const COMPANY_COLORS = {
  'אקסלנס': '#10b981',
  'הפניקס': '#f59e0b',
  'מנורה': '#6366f1',
  'הכשרה': '#ec4899',
  'מור': '#0ea5e9',
  'אלטשולר': '#a855f7',
}

function getColor(name) {
  if (!name) return '#94a3b8'
  for (const [key, val] of Object.entries(COMPANY_COLORS)) {
    if (name.includes(key)) return val
  }
  return '#94a3b8'
}

function matchesCompany(productCompany, commCompanies) {
  if (!productCompany) return false
  const lower = productCompany.toLowerCase()
  return commCompanies.some(c => {
    const cl = c.toLowerCase()
    return lower.includes(cl) || cl.includes(lower)
  })
}

// Same rate lookup logic as ComparisonDashboard
function stripHe(s) { return s.startsWith('ה') && s.length > 2 ? s.slice(1) : null }

const INSURANCE_HINTS = ['פוליסות', 'ביטוח', 'פוליסה']
const GEMEL_HINTS = ['גמל', 'השתלמות']

function findRate(product, categoryLabel) {
  if (!commissionRates.value.length) return null
  const base = [product.company, product.company_full].filter(Boolean)
  const candidates = [...base]
  for (const c of base) { const s = stripHe(c); if (s) candidates.push(s) }
  const matches = new Set()
  for (const companyName of candidates) {
    const cl = companyName.toLowerCase()
    const fw = cl.split(/[\s\-]/)[0]
    for (const r of commissionRates.value) {
      const rn = r.company_name.toLowerCase()
      if (r.company_name === companyName || cl.includes(rn) || rn.includes(cl)
          || (fw.length > 2 && rn.startsWith(fw))) {
        matches.add(r)
      }
    }
  }
  if (matches.size === 0) return null
  const arr = [...matches]
  if (arr.length === 1) return arr[0].rate
  // Prefer rate matching the category
  let hints = null
  if (categoryLabel) {
    if (categoryLabel.includes('ביטוח')) hints = INSURANCE_HINTS
    else if (categoryLabel.includes('גמל')) hints = GEMEL_HINTS
  }
  if (!hints) {
    if (product.accumulation && product.accumulation > 0) hints = GEMEL_HINTS
    else if (product.premium && product.premium > 0) hints = INSURANCE_HINTS
  }
  if (hints) {
    const preferred = arr.find(r => hints.some(h => r.company_name.includes(h)))
    if (preferred) return preferred.rate
  }
  return arr[0].rate
}

function calcExpectedCommission(product, categoryLabel) {
  const rate = findRate(product, categoryLabel)
  if (rate) {
    if (product.accumulation != null && product.accumulation !== 0) {
      return product.accumulation * rate / 12
    }
    if (product.premium != null && product.premium !== 0) {
      return product.premium * rate * 100 / 12
    }
  }
  // Fallback: raw value
  return (product.premium || 0) || (product.accumulation || 0)
}

const rows = computed(() => {
  const list = []

  for (const catKey of ['gemel_hishtalmut', 'insurance']) {
    const result = comparisonStore.results[catKey]
    if (!result) continue

    const commSources = result.commission_company_sources || []
    const commSource = result.commission_company_source
    const companies = commSources.length > 0 ? commSources : (commSource ? [commSource] : [])
    const displayCompany = companies[0] || 'לא ידוע'
    const categoryLabel = result.commission_category_label || CATEGORY_LABELS[catKey]

    if (companies.length === 0) continue

    let unpaidCount = 0
    let unpaidAmount = 0

    for (const customer of result.customers) {
      // Only count fully-unmatched customers (same as ComparisonDashboard totalUnpaidCharge)
      if (customer.match_status === 'only_production') {
        const products = (customer.production_products || [])
          .filter(p => matchesCompany(p.company, companies) || matchesCompany(p.company_full, companies))
        for (const p of products) {
          unpaidCount += 1
          unpaidAmount += calcExpectedCommission(p, categoryLabel)
        }
      }
    }

    list.push({
      key: catKey + '-' + displayCompany,
      company: displayCompany,
      catKey,
      category: CATEGORY_LABELS[catKey] || catKey,
      count: unpaidCount,
      amount: unpaidAmount,
      initial: displayCompany.charAt(0),
      color: getColor(displayCompany),
    })
  }

  const maxAmount = list.reduce((max, r) => Math.max(max, r.amount), 1)
  return list
    .sort((a, b) => b.amount - a.amount)
    .map(r => ({ ...r, pct: maxAmount > 0 ? Math.round((r.amount / maxAmount) * 100) : 0 }))
})

const totals = computed(() => {
  let count = 0
  let amount = 0
  for (const r of rows.value) {
    count += r.count
    amount += r.amount
  }
  return { count, amount }
})

function deleteRow(catKey) {
  comparisonStore.resetCategory(catKey)
}

function clearAll() {
  comparisonStore.resetCategory('gemel_hishtalmut')
  comparisonStore.resetCategory('insurance')
}

function formatCurrency(val) {
  if (!val) return '₪0'
  return '₪' + Math.round(val).toLocaleString('he-IL')
}
</script>

<style scoped>
.unpaid-tab {
  animation: slideUp 0.4s var(--transition);
  max-width: 800px;
  margin: 0 auto;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 60px 24px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
}

.empty-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  background: var(--primary-light);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
}

.empty-state h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 320px;
  margin: 0 auto;
}

/* Summary cards */
.summary-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.summary-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-card.highlight {
  border-color: rgba(234, 0, 30, 0.15);
  background: linear-gradient(135deg, var(--card-bg), var(--red-light));
}

.sc-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.sc-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.5px;
}

.sc-value.red {
  color: var(--red);
}

/* Table */
.table-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.table-toolbar {
  display: flex;
  justify-content: flex-start;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg);
}

.btn-clear {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--bg-surface);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear:hover {
  background: var(--red-light);
  border-color: var(--red-light);
  color: var(--red);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 14px 16px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-align: right;
  background: var(--bg);
  border-bottom: 1px solid var(--border-subtle);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.data-table td {
  padding: 16px;
  font-size: 14px;
  color: var(--text);
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.data-table tbody tr {
  transition: background 0.15s;
}

.data-table tbody tr:hover {
  background: var(--primary-glow);
}

/* Company cell */
.th-company { min-width: 140px; }

.company-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.company-avatar {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 800;
  color: white;
  flex-shrink: 0;
}

.company-name {
  font-weight: 700;
  font-size: 15px;
}

/* Category pill */
.th-category, .td-category {
  width: 120px;
}

.category-pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.category-pill.gemel_hishtalmut {
  background: rgba(16, 185, 129, 0.1);
  color: var(--accent-emerald);
}

.category-pill.insurance {
  background: rgba(6, 165, 154, 0.1);
  color: var(--accent-cyan);
}

/* Count & Amount */
.th-count, .td-count {
  width: 80px;
  text-align: center;
}

.th-amount, .td-amount {
  width: 140px;
  text-align: left;
}

.td-amount {
  font-weight: 800;
  font-size: 16px;
  color: var(--red);
  font-variant-numeric: tabular-nums;
}

.th-bar { width: 140px; }
.td-bar { width: 140px; }

/* Bar */
.bar-track {
  height: 8px;
  background: var(--border-subtle);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--red), var(--amber));
  border-radius: 4px;
  transition: width 0.5s var(--transition);
  min-width: 4px;
}

/* Actions */
.th-actions { width: 48px; }
.td-actions { width: 48px; text-align: center; }

.btn-delete-row {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-delete-row:hover {
  background: var(--red-light);
  color: var(--red);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

@media (max-width: 768px) {
  .summary-row {
    grid-template-columns: 1fr;
  }

  .th-bar, .td-bar {
    display: none;
  }
}

@media (max-width: 480px) {
  .th-category, .td-category {
    display: none;
  }
}
</style>
