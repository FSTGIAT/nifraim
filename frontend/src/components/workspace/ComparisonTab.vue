<template>
  <div class="comparison-tab">
    <!-- No production file warning -->
    <div v-if="!productionStore.currentFile && !productionStore.loading" class="no-production">
      <!-- Floating blur circles -->
      <div class="float-circle fc-1"></div>
      <div class="float-circle fc-2"></div>
      <div class="float-circle fc-3"></div>
      <div class="float-circle fc-4"></div>
      <div class="float-circle fc-5"></div>
      <div class="float-circle fc-6"></div>
      <div class="float-circle fc-7"></div>

      <!-- Animated waves at bottom -->
      <div class="wave-bg">
        <div class="shimmer"></div>
        <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs>
            <linearGradient id="ctg1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
              <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
              <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
              <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
            </linearGradient>
          </defs>
          <path fill="url(#ctg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
        </svg>
        <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs>
            <linearGradient id="ctg2" x1="100%" y1="0%" x2="0%" y2="0%">
              <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
              <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
              <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
              <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
            </linearGradient>
          </defs>
          <path fill="url(#ctg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
        </svg>
        <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs>
            <linearGradient id="ctg3" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
              <stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/>
              <stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/>
            </linearGradient>
          </defs>
          <path fill="url(#ctg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
        </svg>
      </div>

      <div class="empty-content">
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

        <!-- Category selected, no result → uploader at TOP + monitor below.
             Once a comparison runs, the monitor collapses so the dashboard
             takes over the screen — same pattern as `השוואת קבצים` under
             Production. -->
        <div v-else-if="!comparisonStore.result" :key="'upload-' + comparisonStore.activeCategory" class="upload-section">
          <!-- Recent commission uploads → click to re-open the comparison
               without uploading the same file again. -->
          <div v-if="recentCommissionUploads.length > 0" class="recent-uploads">
            <div class="recent-head">
              <span class="recent-eyebrow">קבצים אחרונים</span>
              <span class="recent-hint">לחץ כדי לפתוח השוואה ללא העלאה מחדש</span>
            </div>
            <div class="recent-strip">
              <button
                v-for="up in recentCommissionUploads"
                :key="up.id"
                class="recent-chip"
                :class="{ 'is-loading': reopeningId === up.id }"
                :disabled="!!reopeningId"
                @click="reopenComparison(up)"
              >
                <span class="recent-chip-company">{{ up.company_source || 'חברה' }}</span>
                <span class="recent-chip-file">{{ up.filename }}</span>
                <span class="recent-chip-meta">
                  <span class="recent-chip-date">{{ formatUploadDate(up.uploaded_at) }}</span>
                  <span class="recent-chip-count ltr-number">{{ (up.record_count || 0).toLocaleString() }}</span>
                </span>
                <svg v-if="reopeningId !== up.id" class="recent-chip-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>
                <svg v-else class="recent-chip-icon spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>
              </button>
            </div>
          </div>

          <CommissionUploader />
          <UnpaidTrackerMonitor :refresh-key="trackerKey" />
        </div>

        <!-- Has result → comparison dashboard -->
        <div v-else :key="'result-' + comparisonStore.activeCategory" class="results-section">
          <ComparisonDashboard
            :customers="relevantCustomers"
            :categoryLabel="comparisonStore.result?.commission_category_label || ''"
            :companySource="comparisonStore.result?.commission_company_source || ''"
            :companySources="comparisonStore.result?.commission_company_sources || []"
          />
        </div>
      </Transition>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import { useComparisonStore } from '../../stores/comparison.js'
import { useUploadsStore } from '../../stores/uploads.js'
import CommissionUploader from './CommissionUploader.vue'
import ComparisonDashboard from '../comparison/ComparisonDashboard.vue'
import UnpaidTrackerMonitor from '../comparison/UnpaidTrackerMonitor.vue'

const productionStore = useProductionStore()
const comparisonStore = useComparisonStore()
const uploadsStore = useUploadsStore()

// Bump whenever a fresh comparison result arrives — tells the monitor to
// re-fetch by-company / trend so the UI reflects the snapshot we just took.
const trackerKey = ref(0)
watch(() => comparisonStore.result, (r) => {
  if (r) trackerKey.value += 1
})

// Recent commission uploads — top 5, deduped by filename so re-uploads of the
// same file collapse to a single chip showing the latest version.
const recentCommissionUploads = computed(() => {
  const all = uploadsStore.uploads || []
  const seen = new Set()
  const out = []
  for (const u of all) {
    if (u.file_category !== 'commission') continue
    const key = (u.filename || '').trim().toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(u)
    if (out.length >= 5) break
  }
  return out
})

const reopeningId = ref(null)
async function reopenComparison(upload) {
  if (!productionStore.currentFile?.id || reopeningId.value) return
  reopeningId.value = upload.id
  try {
    await comparisonStore.compareExisting(
      productionStore.currentFile.id,
      upload.id,
    )
  } catch (e) {
    // store already populates `error.value` — nothing else to do here
  } finally {
    reopeningId.value = null
  }
}

function formatUploadDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

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
  // Fetch uploads (for the recent-files chips). Cheap re-fetch if already loaded.
  uploadsStore.fetchUploads().catch(() => {})
})
</script>

<style scoped>
.comparison-tab {
  animation: slideUp 0.4s var(--transition);
}

.no-production {
  position: relative;
  text-align: center;
  padding: 80px 24px 100px;
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.empty-content {
  position: relative;
  z-index: 1;
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

/* ─── Floating blur circles ─── */
.float-circle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.fc-1 {
  width: 220px;
  height: 220px;
  top: 10%;
  right: -60px;
  background: rgba(245, 124, 0, 0.045);
  border: 1px solid rgba(245, 124, 0, 0.06);
  animation: floatBob 8s ease-in-out infinite;
}

.fc-2 {
  width: 160px;
  height: 160px;
  bottom: 25%;
  left: -40px;
  background: rgba(245, 124, 0, 0.035);
  border: 1px solid rgba(245, 124, 0, 0.05);
  animation: floatBob 6.5s ease-in-out infinite reverse;
}

.fc-3 {
  width: 90px;
  height: 90px;
  top: 30%;
  left: 8%;
  background: rgba(245, 124, 0, 0.05);
  animation: floatBob 10s ease-in-out infinite 2s;
}

.fc-4 {
  width: 120px;
  height: 120px;
  top: 55%;
  right: 6%;
  background: rgba(245, 124, 0, 0.03);
  border: 1px solid rgba(245, 124, 0, 0.04);
  animation: floatBob 9s ease-in-out infinite 1s;
}

.fc-5 {
  width: 50px;
  height: 50px;
  top: 18%;
  right: 22%;
  background: rgba(255, 152, 0, 0.055);
  animation: floatBob 7s ease-in-out infinite 3s;
}

.fc-6 {
  width: 280px;
  height: 280px;
  bottom: 8%;
  right: -90px;
  background: rgba(245, 124, 0, 0.025);
  border: 1px solid rgba(245, 124, 0, 0.035);
  animation: floatBob 12s ease-in-out infinite 0.5s;
}

.fc-7 {
  width: 65px;
  height: 65px;
  bottom: 35%;
  left: 18%;
  background: rgba(255, 183, 77, 0.06);
  border: 1px solid rgba(255, 183, 77, 0.05);
  animation: floatBob 8.5s ease-in-out infinite reverse 1.5s;
}

@keyframes floatBob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-16px) rotate(2deg); }
  66% { transform: translateY(8px) rotate(-1deg); }
}

/* ─── Waves fixed to bottom ─── */
.wave-bg {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 200px;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.shimmer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100%;
  z-index: 1;
  overflow: hidden;
  mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
}

.shimmer::after {
  content: '';
  position: absolute;
  top: 0;
  left: -80%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 200, 100, 0.1) 35%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 200, 100, 0.1) 65%,
    transparent 100%
  );
  animation: shimmerSweep 7s ease-in-out infinite;
}

@keyframes shimmerSweep {
  0%   { left: -80%; }
  100% { left: 180%; }
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 200%;
  height: 100%;
}

.wave-1 { animation: waveSlide 14s linear infinite; }
.wave-2 { animation: waveSlide 18s linear infinite reverse; }
.wave-3 { animation: waveSlide 22s linear infinite; }

@keyframes waveSlide {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
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

.upload-section {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

/* Recent commission uploads strip */
.recent-uploads {
  background: linear-gradient(180deg, #FFFFFF 0%, #FFFBF5 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: 14px 18px 16px;
  position: relative;
  overflow: hidden;
}
.recent-uploads::before {
  content: '';
  position: absolute;
  top: 0; right: 0; left: 0; height: 3px;
  background: linear-gradient(90deg, #FFB74D, #F57C00 60%, #E65100);
}
.recent-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.recent-eyebrow {
  font-size: 11px;
  font-weight: 800;
  color: var(--primary-deep);
  letter-spacing: 0.6px;
  text-transform: uppercase;
}
.recent-hint {
  font-size: 11px;
  color: var(--text-muted);
}
.recent-strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  scrollbar-width: thin;
  padding-bottom: 4px;
}
.recent-strip::-webkit-scrollbar { height: 6px; }
.recent-strip::-webkit-scrollbar-thumb { background: #E0E0E0; border-radius: 6px; }

.recent-chip {
  flex: 0 0 220px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  text-align: right;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  position: relative;
  transition: all 200ms var(--transition);
}
.recent-chip:hover:not(:disabled) {
  border-color: var(--primary);
  background: var(--primary-light);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.12);
}
.recent-chip:disabled { cursor: wait; opacity: 0.7; }
.recent-chip.is-loading { border-color: var(--primary); background: var(--primary-light); }

.recent-chip-company {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-deep);
}
.recent-chip-file {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.recent-chip-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 2px;
}
.recent-chip-date {
  font-size: 10px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.recent-chip-count {
  font-size: 10px;
  color: var(--text-muted);
  background: #F7F7F7;
  border-radius: 4px;
  padding: 1px 6px;
  font-variant-numeric: tabular-nums;
}
.recent-chip-icon {
  position: absolute;
  top: 12px;
  left: 12px;
  color: var(--primary);
  opacity: 0.7;
  transition: opacity 200ms, transform 200ms;
}
.recent-chip:hover:not(:disabled) .recent-chip-icon {
  opacity: 1;
  transform: translateX(-3px);
}
.recent-chip-icon.spin { animation: rec-spin 0.9s linear infinite; }
@keyframes rec-spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

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
