<template>
  <div class="comparison-tab">
    <!-- No production file warning -->
    <div v-if="!productionStore.currentFile && !productionStore.loading" class="no-production">
      <div class="empty-icon">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      </div>
      <h3>לא נמצא קובץ פרודוקציה</h3>
      <p>יש להעלות קובץ פרודוקציה בלשונית "פרודוקציה" לפני ביצוע השוואה</p>
    </div>

    <template v-else-if="productionStore.currentFile">
      <!-- Toolbar: production badge + category toggle -->
      <div class="comparison-toolbar">
        <div class="toolbar-production">
          <div class="toolbar-prod-dot"></div>
          <span class="toolbar-prod-name">{{ productionStore.currentFile.filename }}</span>
          <span class="toolbar-prod-count ltr-number">{{ productionStore.currentFile.record_count.toLocaleString() }}</span>
        </div>

        <div class="category-toggle">
          <button
            v-for="cat in categories"
            :key="cat.key"
            class="toggle-segment"
            :class="{ active: comparisonStore.activeCategory === cat.key }"
            @click="onSelectCategory(cat.key)"
          >
            <span class="segment-label">{{ cat.label }}</span>
            <span v-if="comparisonStore.hasResultFor(cat.key)" class="segment-dot"></span>
          </button>
        </div>
      </div>

      <!-- Content area -->
      <Transition name="tab-switch" mode="out-in">
        <!-- No category selected → prompt -->
        <div v-if="!comparisonStore.activeCategory" key="no-category" class="category-prompt">
          <p>בחר קטגוריה להשוואה</p>
        </div>

        <!-- Category selected, no result → uploader + recent -->
        <div v-else-if="!comparisonStore.result" :key="'upload-' + comparisonStore.activeCategory">
          <CommissionUploader />
        </div>

        <!-- Has result → comparison dashboard -->
        <div v-else :key="'result-' + comparisonStore.activeCategory" class="results-section">
          <ComparisonDashboard
            :customers="relevantCustomers"
            :categoryLabel="comparisonStore.result?.commission_category_label || ''"
            :companySource="comparisonStore.result?.commission_company_source || ''"
          />
        </div>
      </Transition>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import { useComparisonStore } from '../../stores/comparison.js'
import CommissionUploader from './CommissionUploader.vue'
import ComparisonDashboard from '../comparison/ComparisonDashboard.vue'

const productionStore = useProductionStore()
const comparisonStore = useComparisonStore()

const categories = [
  {
    key: 'gemel_hishtalmut',
    label: 'גמל והשתלמות',
    description: 'קופות גמל, קרנות השתלמות',
  },
  {
    key: 'insurance',
    label: 'ביטוח',
    description: 'חיים, בריאות, חסכון, סיעודי',
  },
]

function onSelectCategory(cat) {
  if (comparisonStore.activeCategory === cat && comparisonStore.result) {
    // Clicking the active category that has results → reset to uploader
    comparisonStore.resetCategory(cat)
  } else {
    comparisonStore.selectCategory(cat)
  }
}

/**
 * Filter customers to only show relevant "not paid" (only_production) entries.
 * When comparing against a specific company's commission file (e.g. הפניקס),
 * only show production products from that company as "not paid".
 * Products from other companies (e.g. אלטשולר) won't be in a הפניקס file — that's expected.
 */
const relevantCustomers = computed(() => {
  if (!comparisonStore.result) return []

  const customers = comparisonStore.result.customers
  const commSources = comparisonStore.result.commission_company_sources || []
  const commSource = comparisonStore.result.commission_company_source
  const companies = commSources.length > 0 ? commSources : (commSource ? [commSource] : [])

  // If no commission company info, return all customers as-is
  if (companies.length === 0) return customers

  function matchesCommissionCompany(productCompany) {
    if (!productCompany) return false
    const lower = productCompany.toLowerCase()
    return companies.some(c => {
      const cl = c.toLowerCase()
      return lower.includes(cl) || cl.includes(lower)
    })
  }

  return customers
    .map(c => {
      // matched and only_commission — keep as-is
      if (c.match_status !== 'only_production') {
        // For matched customers, also filter unmatched_production to relevant company
        if (c.match_status === 'matched' && c.product_matches) {
          const relevantUnmatched = (c.product_matches.unmatched_production || [])
            .filter(p => matchesCommissionCompany(p.company))
          if (relevantUnmatched.length !== (c.product_matches.unmatched_production || []).length) {
            return {
              ...c,
              unpaid_count: relevantUnmatched.length,
              product_matches: {
                ...c.product_matches,
                unmatched_production: relevantUnmatched,
              },
            }
          }
        }
        return c
      }

      // only_production — filter products to matching company (check both short name and managing entity)
      const relevantProducts = (c.production_products || [])
        .filter(p => matchesCommissionCompany(p.company) || matchesCommissionCompany(p.company_full))

      // If no products match the commission company, exclude this customer
      if (relevantProducts.length === 0) return null

      return {
        ...c,
        production_products: relevantProducts,
        production_count: relevantProducts.length,
        product_matches: {
          matched: [],
          unmatched_production: relevantProducts.map(p => ({
            product: p.product,
            product_type: p.product_type,
            company: p.company,
            company_full: p.company_full,
            premium: p.premium,
            policy_number: p.policy_number,
            accumulation: p.accumulation,
            sign_date: p.sign_date,
          })),
          unmatched_commission: [],
        },
      }
    })
    .filter(Boolean) // Remove null entries (excluded only_production customers)
    .sort((a, b) => {
      // Item 6: Sort by highest financial value
      const isInsurance = comparisonStore.activeCategory === 'insurance'
      if (isInsurance) {
        return (b.total_premium || 0) - (a.total_premium || 0)
      }
      // Gemel: sort by total balance (sum of all production product accumulations)
      const balA = (a.production_products || []).reduce((s, p) => s + (p.accumulation || 0), 0)
      const balB = (b.production_products || []).reduce((s, p) => s + (p.accumulation || 0), 0)
      return balB - balA
    })
})

onMounted(() => {
  if (!productionStore.currentFile && !productionStore.loading) {
    productionStore.fetchCurrent()
  }
  // Auto-select first category so toggle always has an active segment
  if (!comparisonStore.activeCategory) {
    comparisonStore.selectCategory('gemel_hishtalmut')
  }
})
</script>

<style scoped>
.comparison-tab {
  animation: slideUp 0.4s var(--transition);
}

.no-production {
  text-align: center;
  padding: 60px 24px;
  background: var(--amber-light);
  border: 1px solid var(--amber-light);
  border-radius: var(--radius-lg);
}

.empty-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  background: var(--amber-light);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--amber);
}

.no-production h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.no-production p {
  font-size: 14px;
  color: var(--text-secondary);
}

/* Toolbar */
.comparison-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 16px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 20px;
}

.toolbar-production {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.toolbar-prod-dot {
  width: 7px;
  height: 7px;
  background: var(--accent-emerald);
  border-radius: 50%;
  flex-shrink: 0;
  animation: pulse-soft 2s ease-in-out infinite;
}

.toolbar-prod-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-prod-count {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg);
  padding: 2px 8px;
  border-radius: 6px;
  flex-shrink: 0;
  white-space: nowrap;
}

/* Category toggle */
.category-toggle {
  display: flex;
  background: var(--bg);
  border-radius: 10px;
  padding: 3px;
  flex-shrink: 0;
}

.toggle-segment {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 18px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
  transition: all 0.25s var(--transition);
  white-space: nowrap;
}

.toggle-segment:hover:not(.active) {
  color: var(--text);
  background: rgba(0, 0, 0, 0.03);
}

.toggle-segment.active {
  color: var(--primary-deep);
  background: var(--bg-surface);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.segment-dot {
  width: 6px;
  height: 6px;
  background: var(--accent-emerald);
  border-radius: 50%;
  flex-shrink: 0;
}

/* Category prompt */
.category-prompt {
  text-align: center;
  padding: 60px 24px;
  color: var(--text-muted);
  font-size: 15px;
}

.results-section {}

/* Tab switch transitions */
.tab-switch-enter-active {
  animation: slideUp 0.4s var(--transition);
}
.tab-switch-leave-active {
  animation: fadeOut 0.15s ease-out;
}
@keyframes fadeOut {
  to {
    opacity: 0;
    transform: translateY(-8px);
  }
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

@media (max-width: 640px) {
  .comparison-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .category-toggle {
    justify-content: center;
  }
}

</style>
