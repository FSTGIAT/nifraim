<template>
  <div class="comparison-tab">
    <!-- No production file AND no persisted comparison data → full empty state -->
    <EmptyStateGuide
      v-if="!productionStore.currentFile && !productionStore.loading && !hasPersistedComparison"
      variant="full"
      title="השוואת נפרעים"
      body="לאחר העלאת פרודוקציה, כאן מעלים דוחות נפרעים מחברות הביטוח ומשווים מול הפרודוקציה. ההורדה האוטומטית ממלאת את המסך הזה לבד."
      cta-label="הפעל הורדה אוטומטית"
      cta-step="run"
    >
      <template #illustration>
        <img class="esg-cmp-art" :src="comparisonArt" alt="" aria-hidden="true" />
      </template>
    </EmptyStateGuide>

    <template v-else-if="productionStore.currentFile || hasPersistedComparison">
      <!-- No active production, but persisted comparison data exists →
           slim inline notice instead of blocking the whole tab. -->
      <div v-if="!productionStore.currentFile" class="no-prod-notice">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
          <path d="M12 9v4"/>
          <path d="M12 17h.01"/>
        </svg>
        <span>לא נמצא קובץ פרודוקציה פעיל — מוצגת ההשוואה האחרונה שנשמרה</span>
      </div>

      <!-- Toolbar: production badge + category toggle -->
      <div class="comparison-toolbar">
        <div class="toolbar-sources">
          <div v-if="productionStore.currentFile" class="toolbar-production">
            <div class="toolbar-prod-dot"></div>
            <span class="toolbar-prod-name">{{ productionStore.currentFile.filename }}</span>
            <span class="toolbar-prod-count ltr-number">{{ productionStore.currentFile.record_count.toLocaleString() }}</span>
          </div>
          <!-- נפרעים side: the merged commission source spanning all companies. -->
          <div v-if="nifraimCompanyCount > 0" class="toolbar-nifraim">
            <div class="toolbar-nif-dot"></div>
            <span class="toolbar-nif-name">נפרעים מאוחד</span>
            <span class="toolbar-nif-count ltr-number">{{ nifraimCompanyCount }} חברות</span>
          </div>
        </div>

        <div class="toolbar-end">
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

          <!-- History: last 3 commission files behind a clean icon popover.
               Clicking a file opens its comparison. -->
          <RecentFilesPopover @select="onCommissionFileSelect" />
        </div>
      </div>

      <!-- Content area -->
      <Transition name="tab-switch" mode="out-in">
        <!-- No category selected → prompt -->
        <div v-if="!comparisonStore.activeCategory" key="no-category" class="category-prompt">
          <p>בחר קטגוריה להשוואה</p>
        </div>

        <!-- Category selected, no result → always-on insights dashboard
             (the dashboard hosts a slim "load fresh data" strip with the
              automation panel + manual upload behind a disclosure). -->
        <div v-else-if="!displayResult" :key="'insights-' + comparisonStore.activeCategory" class="insights-stack">
          <ComparisonInsightsDashboard
            @automation-success="onAutomationSuccess"
            @batch-done="onBatchDone"
            @navigate-to-credentials="$emit('go-to-portal-automation')"
          />
        </div>

        <!-- Has result → comparison dashboard -->
        <div v-else :key="'result-' + comparisonStore.activeCategory + (comparisonStore.singleFileView ? '-single' : '')" class="results-section">
          <!-- Ephemeral single-file drill — the merged picture is one click away -->
          <div v-if="comparisonStore.singleFileView" class="single-file-banner">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
              <path d="M15 2v5h5"/>
            </svg>
            <span class="sfb-text">
              מציג קובץ בודד:
              <strong>{{ comparisonStore.singleFileView.filename || 'דוח נפרעים' }}</strong>
            </span>
            <button class="sfb-back" @click="comparisonStore.clearSingleFileView()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
              </svg>
              חזרה לתמונה המלאה
            </button>
          </div>

          <ComparisonDashboard
            :customers="relevantCustomers"
            :categoryLabel="displayResult?.commission_category_label || ''"
            :companySource="displayResult?.commission_company_source || ''"
            :companySources="displayResult?.commission_company_sources || []"
            :initialCompany="drillCompany || ''"
            :periodMonth="displayResult?.period_month || productionStore.currentFile?.period_month || ''"
            :periodFilesCount="displayResult?.period_files_count || 0"
            :periodFilesExcluded="displayResult?.period_files_excluded || 0"
            @initial-company-applied="drillCompany = null"
          />
        </div>
      </Transition>

      <!-- Cross-company reconciliation overview (both categories) — the
           closing "full picture" summary at the bottom of the tab. -->
      <CompanyReconciliationSummary
        :summary="comparisonStore.companySummary"
        @drill="onDrillCompany"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import comparisonArt from '../../assets/kling/hero.webp'
import { useProductionStore } from '../../stores/production.js'
import { useComparisonStore } from '../../stores/comparison.js'
import { useUploadsStore } from '../../stores/uploads.js'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import ComparisonDashboard from '../comparison/ComparisonDashboard.vue'
import ComparisonInsightsDashboard from '../comparison/ComparisonInsightsDashboard.vue'
import CompanyReconciliationSummary from '../comparison/CompanyReconciliationSummary.vue'
import RecentFilesPopover from '../comparison/RecentFilesPopover.vue'
import EmptyStateGuide from './EmptyStateGuide.vue'

defineEmits(['go-to-portal-automation'])

const productionStore = useProductionStore()
const comparisonStore = useComparisonStore()
const uploadsStore = useUploadsStore()
const portalAutomationStore = usePortalAutomationStore()

// Persisted comparison data lets the tab render even without an active
// production file (e.g. it was deleted after the comparison was computed).
const hasPersistedComparison = computed(() =>
  comparisonStore.hasResultFor('gemel_hishtalmut') ||
  comparisonStore.hasResultFor('insurance') ||
  (comparisonStore.companySummary?.companies?.length || 0) > 0
)

// How many companies feed the merged נפרעים side — drives the toolbar badge.
// Sourced from the cross-company summary (loaded on mount) with a fallback to
// the active comparison result's commission_company_sources.
const nifraimCompanyCount = computed(() => {
  const fromSummary = comparisonStore.companySummary?.companies?.length || 0
  if (fromSummary) return fromSummary
  return comparisonStore.result?.commission_company_sources?.length || 0
})

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

async function onSelectCategory(cat) {
  if (comparisonStore.activeCategory === cat && comparisonStore.result) {
    // Clicking the active category that has results → reset to insights view
    comparisonStore.resetCategory(cat)
    return
  }
  comparisonStore.selectCategory(cat)
  // Always hydrate the latest persisted comparison — every compute persists,
  // so /latest is at least as fresh as the in-memory copy. fetchLatest only
  // replaces on success, so the existing result stays visible while the
  // refetch is in flight (no blank flash).
  await comparisonStore.fetchLatest(cat)
}

// What the dashboard renders: the ephemeral single-file drill when active,
// otherwise the merged all-companies comparison for the active category.
const displayResult = computed(() => comparisonStore.singleFileView?.result || comparisonStore.result)

/**
 * Filter customers to only show relevant "not paid" (only_production) entries.
 * When comparing against a specific company's commission file (e.g. הפניקס),
 * only show production products from that company as "not paid".
 * Products from other companies (e.g. אלטשולר) won't be in a הפניקס file — that's expected.
 */
const relevantCustomers = computed(() => {
  if (!displayResult.value) return []

  const customers = displayResult.value.customers
  const commSources = displayResult.value.commission_company_sources || []
  const commSource = displayResult.value.commission_company_source
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

async function onCommissionFileSelect(file) {
  if (!file || !productionStore.currentFile?.id) return
  // Ingest already detected the category; sync the toggle if it differs so
  // the resulting dashboard renders against the right slice.
  const inferredCategory = inferCategoryFromFile(file)
  if (inferredCategory && comparisonStore.activeCategory !== inferredCategory) {
    comparisonStore.selectCategory(inferredCategory)
  }
  try {
    // View-only drill: never persisted, never overwrites the merged picture.
    await comparisonStore.compareExisting(productionStore.currentFile.id, file.id, {
      persist: false,
      filename: file.filename,
    })
  } catch (_) { /* surfaced via store.error */ }
}

// Best-effort: derive (gemel|insurance) from format_type. The runner already
// classifies, but format_type is a robust short label we can match locally.
const _GEMEL_FORMATS = new Set([
  'nifraim', 'hachshara_nifraim', 'menora', 'altshuler',
  'clal_life_nifraim', 'migdal_nifraim', 'harel_nifraim',
])
const _INSURANCE_FORMATS = new Set([
  'agent_tracking', 'company_report', 'clal_health_nifraim',
  'ayalon_nifraim', 'phoenix_insurance_nifraim',
])
function inferCategoryFromFile(file) {
  const f = (file?.format_type || '').toLowerCase()
  if (_GEMEL_FORMATS.has(f)) return 'gemel_hishtalmut'
  if (_INSURANCE_FORMATS.has(f)) return 'insurance'
  return null
}

async function onAutomationSuccess({ run }) {
  // The portal automation pipeline ingests the commission file as an upload.
  if (!run?.upload_id) return

  // Refresh the recent-files strip so the freshly downloaded card appears.
  try { await uploadsStore.fetchUploads() } catch { /* non-blocking */ }

  // Recompute the merged all-companies comparison server-side (folds the
  // fresh upload in as its company's latest source) and rehydrate the
  // active category + the cross-company summary. Never computes a
  // single-company comparison — that used to clobber the merged picture.
  try { await comparisonStore.refreshMerged() } catch { /* non-blocking */ }
}

// Clicking a company row in the summary → open the category that has results
// for it (prefer one with a persisted comparison) and preselect the matching
// company pill inside the dashboard (via the initialCompany prop — the
// dashboard clears the ref once applied so manual pill clicks aren't
// overridden later).
const drillCompany = ref(null)
async function onDrillCompany(company) {
  // Company drill always targets the merged picture, not a single-file view.
  comparisonStore.clearSingleFileView()
  const order = ['gemel_hishtalmut', 'insurance']
  let target = order.find((c) => comparisonStore.hasResultFor(c))
  if (!target) {
    for (const c of order) {
      const r = await comparisonStore.fetchLatest(c)
      if (r) { target = c; break }
    }
  }
  if (target) {
    drillCompany.value = company || null
    comparisonStore.selectCategory(target)
    if (!comparisonStore.hasResultFor(target)) await comparisonStore.fetchLatest(target)
  }
}

// "צפה בתוצאות" from the run-all bar / dock inside the insights view →
// jump straight to the freshest comparison. Prefer a category the batch
// actually persisted (comparison_categories), else the first with a result.
async function onBatchDone() {
  const batch = portalAutomationStore.batchJustFinished || portalAutomationStore.latestBatch
  const batchCats = batch?.comparison_categories || []
  const order = ['gemel_hishtalmut', 'insurance']
  const target =
    order.find((c) => batchCats.includes(c)) ||
    order.find((c) => comparisonStore.hasResultFor(c)) ||
    order[0]
  comparisonStore.selectCategory(target)
  await comparisonStore.fetchLatest(target)
  // The batch just rewrote the merged comparisons — refresh the bottom table.
  comparisonStore.fetchCompanySummary()
}

onMounted(async () => {
  if (!productionStore.currentFile && !productionStore.loading) {
    await productionStore.fetchCurrent()
  }
  // Load the cross-company overview (no-op if no comparisons exist yet).
  comparisonStore.fetchCompanySummary()
  // Auto-select first category so toggle always has an active segment
  if (!comparisonStore.activeCategory) {
    comparisonStore.selectCategory('gemel_hishtalmut')
  }
  // Hydrate the latest persisted result for the active category on every
  // mount — persisted /latest is always >= the in-memory copy, and the
  // existing result stays visible while the refetch resolves.
  const cat = comparisonStore.activeCategory
  if (cat) {
    await comparisonStore.fetchLatest(cat)
  }
  // Populate the recent-files strip with whatever's already on the server.
  // Cheap call (single SELECT) and uploads list is a small payload.
  if (!uploadsStore.uploads.length) {
    try { await uploadsStore.fetchUploads() } catch { /* non-blocking */ }
  }
})
</script>

<style scoped>
.comparison-tab {
  animation: slideUp 0.4s var(--transition);
}

/* Icon for the empty-state guide (slotted into EmptyStateGuide) */
.esg-cmp-art {
  display: block;
  width: min(380px, 86%);
  margin: 0 auto;
  border-radius: 14px;
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
}

/* Slim warning strip — persisted comparison shown without an active production */
.no-prod-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  margin-bottom: 12px;
  background: var(--amber-light);
  border: 1px solid rgba(232, 114, 10, 0.3);
  border-radius: var(--radius-sm);
  color: var(--amber);
  font-size: 13px;
  font-weight: 600;
}

.no-prod-notice svg {
  flex-shrink: 0;
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

.toolbar-sources {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.toolbar-production {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

/* נפרעים badge — orange-tinted to read as the commission side, distinct from
   the emerald production badge. */
.toolbar-nifraim {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding-inline-start: 10px;
  border-inline-start: 1px solid var(--border, #e5e7eb);
}
.toolbar-nif-dot {
  width: 7px;
  height: 7px;
  background: #f57c00;
  border-radius: 50%;
  flex-shrink: 0;
}
.toolbar-nif-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
}
.toolbar-nif-count {
  font-size: 11px;
  color: #b45309;
  background: rgba(245, 124, 0, 0.1);
  padding: 2px 8px;
  border-radius: 6px;
  flex-shrink: 0;
  white-space: nowrap;
}

.toolbar-end {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
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

/* Ephemeral single-file drill banner — cool info tint (chart sky-blue) so it
   reads as "temporary view", clearly distinct from the amber warnings. */
.single-file-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  margin-bottom: 14px;
  background: color-mix(in srgb, var(--chart-2, #4E9DD0) 9%, white);
  border: 1px solid color-mix(in srgb, var(--chart-2, #4E9DD0) 35%, transparent);
  border-radius: var(--radius-sm);
  color: color-mix(in srgb, var(--chart-2, #4E9DD0) 70%, black);
  font-size: 13px;
}

.single-file-banner svg { flex-shrink: 0; }

.sfb-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sfb-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-inline-start: auto;
  padding: 5px 12px;
  border: none;
  border-radius: 8px;
  background: color-mix(in srgb, var(--chart-2, #4E9DD0) 88%, black);
  color: #fff;
  font-size: 12.5px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.2s var(--transition);
}

.sfb-back:hover {
  background: color-mix(in srgb, var(--chart-2, #4E9DD0) 70%, black);
}

.empty-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.manual-fallback {
  background: var(--card-bg);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 8px 14px;
}

.manual-fallback summary {
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 6px 0;
  user-select: none;
}

.manual-fallback summary:hover { color: var(--text); }

.manual-fallback[open] summary { margin-bottom: 12px; }

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
@media (prefers-reduced-motion: reduce) {
  .tab-switch-enter-active,
  .tab-switch-leave-active { animation: none; }
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
