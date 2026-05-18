<template>
  <section class="insights">
    <!-- Hero status panel (dark gradient) — each KPI tile drills into a focused modal -->
    <HeroStatusPanel
      :open-count="current.open_count || 0"
      :open-amount="current.open_amount || 0"
      :paid-count="current.paid_count || 0"
      :debt-customers="current.debt_customers || 0"
      :debt-companies="current.debt_companies || 0"
      :last-computed-at="lastComputedAt"
      :insight-lines="insightLines"
      :loading="loading"
      @tile-click="onHeroTile"
    />

    <!-- Animated dock — primary entry point for automation, full width -->
    <div class="reload-strip">
      <PortalAutomationDock
        @success="$emit('automation-success', $event)"
        @navigate-to-credentials="$emit('navigate-to-credentials')"
      />
    </div>

    <!-- Two-card grid -->
    <div class="card-grid">
      <InsightBarCard
        title="חיובים פתוחים — לפי חברה"
        :subtitle="bySubtitle"
        :total-label="totalOpenLabel"
        :items="companyItems"
        @select="openCompany"
        @open-all="openAllCompanies"
      />
      <InsightBarCard
        title="לקוחות עם חוב גבוה"
        :subtitle="customerSubtitle"
        :total-label="topCustomerLabel"
        :items="customerItems"
        @select="openCustomer"
        @open-all="openAllCustomers"
      />
    </div>

    <details class="manual-fallback">
      <summary>אין פורטל מוגדר? העלה ידנית</summary>
      <CommissionUploader />
    </details>

    <InsightDrillModal
      :open="modalOpen"
      :title="modalTitle"
      :subtitle="modalSubtitle"
      :label-header="modalLabelHeader"
      :items="modalItems"
      :kind="modalKind"
      :category="activeCategory"
      @close="modalOpen = false"
      @drill-customer="onDrillCustomer"
    />

    <CustomerDetailModal
      :customer="detailCustomer"
      :commission-rates="commissionRates"
      :category="categoryLabel"
      :user-name="authStore.user?.full_name || ''"
      @close="onCustomerDetailClose"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../../api/client.js'
import { shortShekel } from '../../utils/monthDeltas.js'
import PortalAutomationDock from '../workspace/PortalAutomationDock.vue'
import CommissionUploader from '../workspace/CommissionUploader.vue'
import HeroStatusPanel from './HeroStatusPanel.vue'
import InsightBarCard from './InsightBarCard.vue'
import InsightDrillModal from './InsightDrillModal.vue'
import CustomerDetailModal from './CustomerDetailModal.vue'
import { useComparisonStore } from '../../stores/comparison.js'
import { useAuthStore } from '../../stores/auth.js'

const props = defineProps({
  category: { type: String, default: null },
})
defineEmits(['automation-success', 'navigate-to-credentials'])

const comparisonStore = useComparisonStore()
const authStore = useAuthStore()
const insights = ref(null)
const loading = ref(true)

const activeCategory = computed(() => props.category || comparisonStore.activeCategory)
const categoryLabel = computed(() =>
  activeCategory.value === 'insurance' ? 'ביטוח' :
  activeCategory.value === 'gemel_hishtalmut' ? 'גמל והשתלמות' : '',
)
const lastComputedAt = computed(() => insights.value?.trend?.[insights.value.trend.length - 1]?.computed_at || null)

// Commission rates — loaded once for the customer drill modal so the expected-
// commission column renders meaningfully (mirrors ComparisonDashboard pattern).
const commissionRates = ref([])
async function fetchCommissionRates() {
  try {
    const res = await api.get('/commission-rates')
    commissionRates.value = Array.isArray(res.data) ? res.data : []
  } catch { /* non-blocking */ }
}

async function fetchInsights(cat) {
  if (!cat) return
  loading.value = true
  try {
    const res = await api.get('/comparison/insights', { params: { category: cat } })
    insights.value = res.data
  } catch (e) {
    console.warn('insights fetch failed', e)
    insights.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchInsights(activeCategory.value)
  fetchCommissionRates()
})
watch(activeCategory, (cat) => fetchInsights(cat))

const current = computed(() => insights.value?.current || {})

const totalOpenLabel = computed(() => `סה״כ ${shortShekel(current.value?.open_amount ?? 0)}`)
const topCustomerLabel = computed(() => {
  const n = (current.value?.debt_customers ?? 0).toLocaleString('he-IL')
  return `${n} לקוחות חייבים`
})

const bySubtitle = computed(() => {
  const n = (current.value?.debt_companies ?? 0)
  return `${n} חברות עם חיובים פתוחים`
})
const customerSubtitle = computed(() => {
  const n = (current.value?.top_customers || []).length
  if (!n) return 'אין לקוחות עם חוב פתוח'
  return `מציג את ${n} הלקוחות עם החוב הגדול ביותר`
})

// Items for the two cards — shape: { label, amount, count, meta, since, raw }
const companyItems = computed(() =>
  (current.value?.companies || []).map((c) => ({
    label: c.company,
    amount: c.amount,
    count: c.count,
    meta: c.customers ? `${c.customers} לקוחות · ${c.count} חיובים` : `${c.count} חיובים`,
    since: c.since || null,
    raw: c,
  })),
)
const customerItems = computed(() =>
  (current.value?.top_customers || []).map((c) => ({
    label: c.name,
    amount: c.amount,
    count: c.count,
    meta: c.companies > 1 ? `${c.companies} חברות · ${c.count} חיובים` : `${c.count} חיובים`,
    since: c.since || null,
    raw: c,
  })),
)
// Same source as companyItems but sorted by chargeable count instead of amount.
// Used by the "חברות פעילות" tile so it surfaces a different lead than the
// amount-sorted "סך חיוב פתוח" tile.
const companyItemsByCount = computed(
  () => [...companyItems.value].sort((a, b) => (b.count || 0) - (a.count || 0)),
)

// ───── AI-style insight banner (deterministic v1, derived from data) ─────
const insightLines = computed(() => {
  const c = current.value
  if (!c) return []
  const lines = []
  const total = c.open_amount || 0
  const companies = c.companies || []
  const customers = c.top_customers || []

  if (total > 0 && companies.length) {
    const top = companies[0]
    const topShare = total > 0 ? Math.round((top.amount / total) * 100) : 0
    if (topShare >= 30) {
      lines.push(`${topShare}% מהחיובים הפתוחים מרוכזים אצל ${top.company}.`)
    }
  }
  if (customers.length >= 2 && total > 0) {
    const topTwoSum = (customers[0]?.amount || 0) + (customers[1]?.amount || 0)
    const topTwoShare = Math.round((topTwoSum / total) * 100)
    if (topTwoShare >= 25) {
      lines.push(`שני הלקוחות הגדולים אחראים ל-${topTwoShare}% מסך החיוב הפתוח.`)
    }
  }
  if (c.paid_count === 0 && c.open_count > 0) {
    lines.push('עדיין לא נרשמו חיובים ששולמו בקטגוריה הזו.')
  }
  return lines.slice(0, 2)
})

// ───── Drill modal ─────
const modalOpen = ref(false)
const modalTitle = ref('')
const modalSubtitle = ref('')
const modalLabelHeader = ref('שם')
const modalItems = ref([])
// modalKind drives the row-expansion fetch in InsightDrillModal:
//   'company'  → expand fetches GET /debts?company=<row.label>&status=open
//   'customer' → expand fetches GET /debts?customer_id_number=<row.raw.id_number>&status=open
//   null       → rows are not expandable
const modalKind = ref(null)

function openCompany(item) {
  modalTitle.value = item.label
  modalSubtitle.value = `סך חיוב פתוח · ${shortShekel(item.amount)}`
  modalLabelHeader.value = 'חברה'
  modalItems.value = [item]
  modalKind.value = 'company'
  modalOpen.value = true
}
function openCustomer(item) {
  modalTitle.value = item.label
  modalSubtitle.value = `סך חוב · ${shortShekel(item.amount)}`
  modalLabelHeader.value = 'לקוח'
  modalItems.value = [item]
  modalKind.value = 'customer'
  modalOpen.value = true
}
function openAllCompanies() {
  modalTitle.value = 'חיובים פתוחים — לפי חברה'
  modalSubtitle.value = `${companyItems.value.length} חברות`
  modalLabelHeader.value = 'חברה'
  modalItems.value = companyItems.value
  modalKind.value = 'company'
  modalOpen.value = true
}
function openAllCustomers() {
  modalTitle.value = 'לקוחות עם חוב גבוה'
  modalSubtitle.value = `${customerItems.value.length} לקוחות`
  modalLabelHeader.value = 'לקוח'
  modalItems.value = customerItems.value
  modalKind.value = 'customer'
  modalOpen.value = true
}

// ───── Hero KPI tile drill ─────
// Each tile in the dark hero panel is a button. Routed here so the parent
// owns the modal config (titles, subtitles, item shape).
function onHeroTile(id) {
  const c = current.value || {}
  if (id === 'open-amount') {
    modalTitle.value = 'סך החיוב הפתוח — לפי חברה'
    modalSubtitle.value = `סה״כ ${shortShekel(c.open_amount || 0)} פתוח ב-${companyItems.value.length} חברות`
    modalLabelHeader.value = 'חברה'
    modalItems.value = companyItems.value
    modalKind.value = 'company'
    modalOpen.value = true
    return
  }
  if (id === 'debt-customers') {
    modalTitle.value = 'כל הלקוחות עם חוב פתוח'
    modalSubtitle.value = `${(c.debt_customers || 0).toLocaleString('he-IL')} לקוחות · סה״כ ${shortShekel(c.open_amount || 0)}`
    modalLabelHeader.value = 'לקוח'
    modalItems.value = customerItems.value
    modalKind.value = 'customer'
    modalOpen.value = true
    return
  }
  if (id === 'debt-companies') {
    modalTitle.value = 'חברות פעילות — לפי מספר חיובים'
    modalSubtitle.value = `${(c.debt_companies || 0).toLocaleString('he-IL')} חברות · ${(c.open_count || 0).toLocaleString('he-IL')} חיובים פתוחים`
    modalLabelHeader.value = 'חברה'
    modalItems.value = companyItemsByCount.value
    modalKind.value = 'company'
    modalOpen.value = true
  }
}

// ───── Customer drill (InsightDrillModal → CustomerDetailModal) ─────
// Builds the customer shape expected by the existing CustomerDetailModal
// out of the open-debt rows for this customer. Contact fields stay null
// (the modal's v-if hides them); products are the open debts.
const detailCustomer = ref(null)
// Remember whether the drill list was open before we drilled into a customer.
// When the customer modal closes we restore it so the user lands back in the
// list, not on an empty page (CustomerDetailModal's z-index is lower than the
// drill modal's, so we hide the drill while the detail is up).
const drillWasOpen = ref(false)

function onCustomerDetailClose() {
  detailCustomer.value = null
  if (drillWasOpen.value) {
    modalOpen.value = true
    drillWasOpen.value = false
  }
}

async function onDrillCustomer({ idNumber, item }) {
  if (!idNumber) return
  // Hide the drill list while the customer modal is up (it has a lower
  // z-index and would otherwise sit behind). We restore it on close.
  drillWasOpen.value = modalOpen.value
  modalOpen.value = false
  // Optimistic skeleton so the modal opens immediately while debts load.
  detailCustomer.value = {
    id_number: idNumber,
    name: item?.label || idNumber,
    paid_count: 0,
    unpaid_count: item?.count || 0,
    commission_count: 0,
    total_commission: 0,
    paid_commission: 0,
    client_phone: null,
    client_email: null,
    employer_name: null,
    employer_id: null,
    products: [],
  }
  try {
    const params = { status: 'open', customer_id_number: idNumber }
    if (activeCategory.value) params.category = activeCategory.value
    const res = await api.get('/debts', { params })
    const rows = Array.isArray(res.data) ? res.data : []
    detailCustomer.value = {
      ...detailCustomer.value,
      unpaid_count: rows.length,
      products: rows.map((d) => ({
        product: d.product || 'חיוב פתוח',
        company: d.company_name || '',
        company_full: d.company_name || '',
        accumulation: d.accumulation || 0,
        premium: d.premium || 0,
        balance: 0,
        commission: 0,
        policy_number: d.policy_number || '',
        fund_type: null,
        management_fee: null,
        management_fee_amount: null,
        paid: false,
        source: null,
        sign_date: d.created_at || null,
      })),
    }
  } catch {
    // Leave the skeleton; user can close. (Errors are rare; debts is already-cached.)
  }
}
</script>

<style scoped>
.insights {
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: 'Heebo', sans-serif;
  overflow: visible;
}

.reload-strip { display: flex; flex-direction: column; gap: 8px; overflow: visible; }
.manual-fallback {
  font-size: 13px;
  color: var(--text-muted);
  background: var(--card-bg);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 6px 14px;
}
.manual-fallback summary { cursor: pointer; padding: 6px 4px; font-weight: 600; user-select: none; }
.manual-fallback summary:hover { color: var(--text); }
.manual-fallback[open] summary { color: var(--text); margin-bottom: 8px; }

/* Two-card grid */
.card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 880px) {
  .card-grid { grid-template-columns: 1fr; }
}
</style>
