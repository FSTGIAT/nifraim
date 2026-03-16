<template>
  <div class="comparison-controls">
    <div class="controls-start">
      <div class="results-count">{{ filteredCustomers.length }} לקוחות</div>
      <button
        class="toggle-production-btn"
        :class="{ active: hideOnlyProduction }"
        @click="hideOnlyProduction = !hideOnlyProduction"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path v-if="!hideOnlyProduction" d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle v-if="!hideOnlyProduction" cx="12" cy="12" r="3"/>
          <path v-if="hideOnlyProduction" d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
          <line v-if="hideOnlyProduction" x1="1" y1="1" x2="23" y2="23"/>
        </svg>
        <span>הסתר לא שולם</span>
        <span v-if="onlyProductionCount > 0" class="production-count-badge">{{ onlyProductionCount }}</span>
      </button>
    </div>
    <div class="controls-end">
      <button class="btn-download" @click="downloadExcel" title="הורד לאקסל">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        <span>Excel</span>
      </button>
    </div>
  </div>

  <div class="table-wrapper">
    <table>
      <colgroup>
        <col style="width: 40px" />
        <col style="width: 22%" />
        <col style="width: 12%" />
        <col style="width: 12%" />
        <col style="width: 14%" />
        <col style="width: 14%" />
        <col style="width: 16%" />
      </colgroup>
      <thead>
        <tr>
          <th></th>
          <th>שם</th>
          <th>ת.ז</th>
          <th class="center">מוצרים בנפרעים</th>
          <th class="num">סה"כ עמלה</th>
          <th class="num">סה"כ יתרה</th>
          <th>סטטוס</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="customer in filteredCustomers" :key="customer.id_number">
          <tr
            @click="toggleExpand(customer.id_number)"
            class="customer-row"
          >
            <td class="expand-cell">
              <svg :class="{ rotated: isExpanded(customer.id_number) }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
            </td>
            <td>{{ fullName(customer) }}</td>
            <td><span class="ltr-number">{{ customer.id_number }}</span></td>
            <td class="center">
              <span v-if="commissionCount(customer) > 0" class="badge-commission">{{ commissionCount(customer) }}</span>
              <span v-else class="dim">—</span>
            </td>
            <td class="num"><span class="ltr-number">{{ formatAmount(customerCommission(customer)) }}</span></td>
            <td class="num"><span class="ltr-number">{{ formatAmount(customerBalance(customer)) }}</span></td>
            <td>
              <div class="status-wrap">
                <ComparisonBadge :status="customer.match_status" />
                <span
                  v-if="customer.has_paying_company && (customer.match_status === 'only_production' || customer.match_status === 'only_commission')"
                  class="paying-tag"
                >חברה משלמת</span>
              </div>
            </td>
          </tr>
          <tr v-if="isExpanded(customer.id_number)" class="detail-row">
            <td colspan="7" class="detail-cell">
              <ComparisonDetail :customer="customer" :rates="commissionRates" />
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <div v-if="filteredCustomers.length === 0" class="empty">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="8" y1="11" x2="14" y2="11"/>
      </svg>
      <p>אין תוצאות</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import ComparisonBadge from './ComparisonBadge.vue'
import ComparisonDetail from './ComparisonDetail.vue'
import api from '../../api/client.js'
import { useComparisonStore } from '../../stores/comparison.js'

const comparisonStore = useComparisonStore()

const props = defineProps({
  customers: { type: Array, required: true },
  drillCustomerId: { type: String, default: '' },
})

const expandedIds = ref(new Set())
const commissionRates = ref([])
const hideOnlyProduction = ref(false)

onMounted(async () => {
  try {
    const res = await api.get('/commission-rates')
    commissionRates.value = res.data
  } catch (e) {
    // rates not available — continue without them
  }
})

async function refreshRates() {
  try {
    const res = await api.get('/commission-rates')
    commissionRates.value = res.data
  } catch (e) { /* ignore */ }
}

const onlyProductionCount = computed(() =>
  props.customers.filter(c => c.match_status === 'only_production').length
)

const filteredCustomers = computed(() => {
  let list = props.customers

  // Optionally hide only_production
  if (hideOnlyProduction.value) {
    list = list.filter(c => c.match_status !== 'only_production')
  }

  // Drill-down to specific customer
  if (props.drillCustomerId) {
    list = list.filter(c => c.id_number === props.drillCustomerId)
    if (list.length > 0 && !expandedIds.value.has(props.drillCustomerId)) {
      expandedIds.value.add(props.drillCustomerId)
    }
  }

  if (comparisonStore.searchQuery.trim()) {
    const q = comparisonStore.searchQuery.trim().toLowerCase()
    list = list.filter(c =>
      (c.first_name && c.first_name.toLowerCase().includes(q)) ||
      (c.last_name && c.last_name.toLowerCase().includes(q)) ||
      (c.id_number && c.id_number.includes(q))
    )
  }
  return list
})


function toggleExpand(id) {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id)
  } else {
    expandedIds.value.add(id)
  }
}

function isExpanded(id) {
  return expandedIds.value.has(id)
}

function fullName(c) {
  const parts = [c.first_name, c.last_name].filter(Boolean)
  return parts.length > 0 ? parts.join(' ') : '—'
}

function commissionCount(c) {
  return c.commission_count || 0
}

function customerCommission(c) {
  return c.total_commission || 0
}

function customerBalance(c) {
  let total = 0
  const matched = c.product_matches?.matched || []
  for (const p of matched) {
    total += (p.balance || 0)
  }
  const unmatchedComm = c.product_matches?.unmatched_commission || []
  for (const p of unmatchedComm) {
    total += (p.balance || 0)
  }
  const commProducts = c.commission_products || []
  for (const p of commProducts) {
    total += (p.balance || 0)
  }
  return total
}

function formatAmount(val) {
  if (val == null || val === 0) return '—'
  return '₪ ' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const STATUS_LABELS = {
  matched: 'נמצא בשניהם',
  only_production: 'רק בפרודוקציה',
  only_commission: 'רק בנפרעים',
}

function downloadExcel() {
  const rows = []

  for (const c of filteredCustomers.value) {
    const name = fullName(c)
    const status = STATUS_LABELS[c.match_status] || c.match_status

    const matched = c.product_matches?.matched || []
    const unmatchedComm = c.product_matches?.unmatched_commission || []
    const commProducts = c.commission_products || []
    const unmatchedProd = c.product_matches?.unmatched_production || []

    const allCommission = [...matched, ...unmatchedComm, ...commProducts]

    if (allCommission.length === 0 && unmatchedProd.length === 0) {
      rows.push({
        'שם': name,
        'ת.ז': c.id_number,
        'סטטוס': status,
        'חברה משלמת': c.has_paying_company ? 'כן' : '',
        'מוצר': '',
        'חשבון/פוליסה': '',
        'יתרה': '',
        'עמלה': '',
        'מקור': '',
      })
      continue
    }

    for (const m of matched) {
      rows.push({
        'שם': name,
        'ת.ז': c.id_number,
        'סטטוס': status,
        'חברה משלמת': c.has_paying_company ? 'כן' : '',
        'מוצר': m.production_product || m.commission_product || '',
        'חשבון/פוליסה': m.policy_number || '',
        'יתרה': m.balance ?? '',
        'עמלה': m.commission ?? '',
        'מקור': 'נמצא בשניהם',
      })
    }

    for (const u of unmatchedComm) {
      rows.push({
        'שם': name,
        'ת.ז': c.id_number,
        'סטטוס': status,
        'חברה משלמת': c.has_paying_company ? 'כן' : '',
        'מוצר': u.product || '',
        'חשבון/פוליסה': u.account || '',
        'יתרה': u.balance ?? '',
        'עמלה': u.commission ?? '',
        'מקור': 'רק בנפרעים',
      })
    }

    for (const u of commProducts) {
      rows.push({
        'שם': name,
        'ת.ז': c.id_number,
        'סטטוס': status,
        'חברה משלמת': c.has_paying_company ? 'כן' : '',
        'מוצר': u.product || '',
        'חשבון/פוליסה': u.account || '',
        'יתרה': u.balance ?? '',
        'עמלה': u.commission ?? '',
        'מקור': 'רק בנפרעים',
      })
    }

    for (const p of unmatchedProd) {
      rows.push({
        'שם': name,
        'ת.ז': c.id_number,
        'סטטוס': status,
        'חברה משלמת': c.has_paying_company ? 'כן' : '',
        'מוצר': p.product || '',
        'חשבון/פוליסה': p.policy_number || '',
        'יתרה': '',
        'עמלה': '',
        'מקור': 'לא שולם',
      })
    }
  }

  const ws = XLSX.utils.json_to_sheet(rows)
  ws['!Dir'] = 'rtl'
  ws['!cols'] = [
    { wch: 20 }, { wch: 12 }, { wch: 16 }, { wch: 12 },
    { wch: 30 }, { wch: 16 }, { wch: 14 }, { wch: 14 },
    { wch: 16 },
  ]
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'נפרעים')
  XLSX.writeFile(wb, `נפרעים_${new Date().toLocaleDateString('he-IL')}.xlsx`)
}

defineExpose({ refreshRates })
</script>

<style scoped>
.comparison-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 12px;
}

.controls-start {
  display: flex;
  align-items: center;
  gap: 10px;
}

.controls-end {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.toggle-production-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.toggle-production-btn:hover {
  border-color: var(--amber);
  color: var(--text);
}

.toggle-production-btn.active {
  background: rgba(251, 146, 60, 0.08);
  border-color: var(--amber);
  color: var(--amber);
}

.production-count-badge {
  background: var(--border-subtle);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 8px;
}

.toggle-production-btn.active .production-count-badge {
  background: rgba(251, 146, 60, 0.15);
  color: var(--amber);
}

.btn-download {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1px solid var(--green-light);
  border-radius: 8px;
  background: var(--green-light);
  color: var(--green);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.25s;
  white-space: nowrap;
}

.btn-download:hover {
  background: var(--green-light);
  border-color: var(--green-light);
  box-shadow: 0 4px 16px var(--green-light);
  transform: translateY(-1px);
}

.btn-download:active {
  transform: translateY(0);
}

.results-count {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
  white-space: nowrap;
  padding: 6px 14px;
  background: var(--bg-surface);
  border-radius: 20px;
  border: 1px solid var(--glass-border);
}

.table-wrapper {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

thead {
  background: var(--bg);
}

th {
  padding: 14px 12px;
  text-align: right;
  font-weight: 600;
  font-size: 12px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--glass-border);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

th.num,
td.num {
  text-align: left;
}

th.center,
td.center {
  text-align: center;
}

td {
  padding: 12px 12px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 14px;
  vertical-align: middle;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text);
}

.customer-row {
  cursor: pointer;
  transition: background 0.2s;
}

.customer-row:hover {
  background: var(--primary-light) !important;
}

tbody tr:nth-child(4n+1):not(.detail-row) {
  background: rgba(255, 255, 255, 0.015);
}

.expand-cell {
  text-align: center;
  color: var(--text-muted);
}

.expand-cell svg {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  transform: rotate(180deg);
}

.expand-cell svg.rotated {
  transform: rotate(90deg);
}

.detail-row {
  background: transparent !important;
}

.detail-cell {
  padding: 0 !important;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.dim {
  color: var(--text-muted);
}

.badge-commission {
  display: inline-block;
  background: rgba(127, 86, 217, 0.08);
  color: var(--accent-violet);
  font-weight: 700;
  font-size: 13px;
  padding: 2px 10px;
  border-radius: 12px;
  border: 1px solid rgba(127, 86, 217, 0.12);
}

.status-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.paying-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 700;
  background: var(--green-light);
  color: var(--green);
  border: 1px solid var(--green-light);
  white-space: nowrap;
}

.empty {
  text-align: center;
  padding: 56px 16px;
  color: var(--text-muted);
  font-size: 15px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
</style>
