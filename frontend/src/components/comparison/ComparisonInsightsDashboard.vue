<template>
  <section class="insights">
    <!-- Animated dock — primary entry point for automation -->
    <div class="reload-strip">
      <PortalAutomationDock
        @success="$emit('automation-success', $event)"
        @navigate-to-credentials="$emit('navigate-to-credentials')"
      />
      <details class="manual-fallback">
        <summary>אין פורטל מוגדר? העלה ידנית</summary>
        <CommissionUploader />
      </details>
    </div>

    <!-- Header strip -->
    <header class="head-strip">
      <div>
        <h3 class="hs-title">סטטוס נפרעים</h3>
        <p class="hs-sub">{{ subTitle }}</p>
      </div>
      <span v-if="lastComputedAt" class="hs-period">עודכן {{ relativeHebrew(lastComputedAt) }}</span>
    </header>

    <!-- AI insight banner -->
    <div v-if="insightLines.length" class="ai-banner" role="note">
      <span class="ai-badge" aria-hidden="true">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8z"/>
        </svg>
      </span>
      <ul class="ai-text">
        <li v-for="(line, i) in insightLines" :key="i">{{ line }}</li>
      </ul>
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

    <InsightDrillModal
      :open="modalOpen"
      :title="modalTitle"
      :subtitle="modalSubtitle"
      :label-header="modalLabelHeader"
      :items="modalItems"
      @close="modalOpen = false"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../../api/client.js'
import { shortShekel } from '../../utils/monthDeltas.js'
import { relativeHebrew } from '../../utils/relativeTime.js'
import PortalAutomationDock from '../workspace/PortalAutomationDock.vue'
import CommissionUploader from '../workspace/CommissionUploader.vue'
import InsightBarCard from './InsightBarCard.vue'
import InsightDrillModal from './InsightDrillModal.vue'
import { useComparisonStore } from '../../stores/comparison.js'

const props = defineProps({
  category: { type: String, default: null },
})
defineEmits(['automation-success', 'navigate-to-credentials'])

const comparisonStore = useComparisonStore()
const insights = ref(null)
const loading = ref(true)

const activeCategory = computed(() => props.category || comparisonStore.activeCategory)
const lastComputedAt = computed(() => insights.value?.trend?.[insights.value.trend.length - 1]?.computed_at || null)

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

onMounted(() => fetchInsights(activeCategory.value))
watch(activeCategory, (cat) => fetchInsights(cat))

const current = computed(() => insights.value?.current || {})
const subTitle = computed(() => {
  if (loading.value) return 'טוען נתונים…'
  if (!current.value || (!current.value.open_count && !current.value.paid_count && !insights.value?.has_any_history)) {
    return 'אין נתוני נפרעים — הפעל אוטומציה למעלה או העלה דוח'
  }
  return 'מצב נוכחי על פי קבצי הנפרעים שעובדו'
})

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

// Items for the two cards — shape: { label, amount, count, meta }
const companyItems = computed(() =>
  (current.value?.companies || []).map((c) => ({
    label: c.company,
    amount: c.amount,
    count: c.count,
    meta: c.customers ? `${c.customers} לקוחות · ${c.count} חיובים` : `${c.count} חיובים`,
    raw: c,
  })),
)
const customerItems = computed(() =>
  (current.value?.top_customers || []).map((c) => ({
    label: c.name,
    amount: c.amount,
    count: c.count,
    meta: c.companies > 1 ? `${c.companies} חברות · ${c.count} חיובים` : `${c.count} חיובים`,
    raw: c,
  })),
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

function openCompany(item) {
  modalTitle.value = item.label
  modalSubtitle.value = `סך חיוב פתוח · ${shortShekel(item.amount)}`
  modalLabelHeader.value = 'חברה'
  modalItems.value = [item]
  modalOpen.value = true
}
function openCustomer(item) {
  modalTitle.value = item.label
  modalSubtitle.value = `סך חוב · ${shortShekel(item.amount)}`
  modalLabelHeader.value = 'לקוח'
  modalItems.value = [item]
  modalOpen.value = true
}
function openAllCompanies() {
  modalTitle.value = 'חיובים פתוחים — לפי חברה'
  modalSubtitle.value = `${companyItems.value.length} חברות`
  modalLabelHeader.value = 'חברה'
  modalItems.value = companyItems.value
  modalOpen.value = true
}
function openAllCustomers() {
  modalTitle.value = 'לקוחות עם חוב גבוה'
  modalSubtitle.value = `${customerItems.value.length} לקוחות`
  modalLabelHeader.value = 'לקוח'
  modalItems.value = customerItems.value
  modalOpen.value = true
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
.manual-fallback { font-size: 13px; color: var(--text-muted); }
.manual-fallback summary { cursor: pointer; padding: 6px 4px; font-weight: 600; }
.manual-fallback summary:hover { color: var(--text); }
.manual-fallback[open] summary { color: var(--text); margin-bottom: 8px; }

.head-strip {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--border-subtle);
}
.hs-title { margin: 0; font-size: 18px; font-weight: 800; color: var(--text); letter-spacing: -0.2px; }
.hs-sub { margin: 4px 0 0; font-size: 12.5px; color: var(--text-muted); }
.hs-period {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11.5px;
  letter-spacing: 0.3px;
  color: var(--primary-deep, #c2410c);
  background: rgba(245, 124, 0, 0.08);
  border: 1px solid rgba(245, 124, 0, 0.22);
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 700;
}

/* AI insight banner */
.ai-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.06), transparent 70%);
  border: 1px solid rgba(245, 124, 0, 0.18);
}
.ai-badge {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(245, 124, 0, 0.32);
}
.ai-text {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 13px;
  color: var(--text);
  font-weight: 600;
}
.ai-text li::before { content: '· '; color: var(--primary, #F57C00); font-weight: 800; }

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
