<template>
  <div class="production-tab">
    <div v-if="productionStore.loading" class="loading-state">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span>טוען...</span>
    </div>

    <template v-else>
      <!-- No file: sage hero — manual upload triggered via the hero's icon button -->
      <div v-if="!productionStore.currentFile" class="empty-stack">
        <ProductionHeroPanel
          :landing="productionStore.landing"
          :loading="productionStore.landingLoading"
          @request-manual-upload="openFilePicker"
        />
        <AiCapabilitiesGridIsland />
      </div>

      <!-- File exists: inner tabs + dashboard -->
      <template v-else>
        <!-- Inner tabs bar -->
        <div class="inner-tabs-bar">
          <div class="inner-tabs">
            <button
              class="inner-tab"
              :class="{ active: innerTab === 'insights' }"
              @click="innerTab = 'insights'"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
              תובנות
            </button>
            <button
              class="inner-tab"
              :class="{ active: innerTab === 'comparison' }"
              @click="switchToComparison"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              השוואת קבצים
              <span class="tab-dot" v-if="productionStore.comparisonResult"></span>
            </button>
            <button
              class="inner-tab"
              :class="{ active: innerTab === 'volume' }"
              @click="innerTab = 'volume'"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 20V10"/>
                <path d="M18 20V4"/>
                <path d="M6 20v-4"/>
              </svg>
              השוואה מול היקפים
              <span class="tab-dot" v-if="volumeStore.comparisonResult"></span>
            </button>
            <button
              class="inner-tab"
              :class="{ active: innerTab === 'history' }"
              @click="switchToHistory"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              היסטוריה
              <span class="tab-dot" v-if="productionStore.history.length"></span>
            </button>
          </div>

          <!-- File pill -->
          <div class="file-pill">
            <div class="pulse-dot"></div>
            <span class="fp-name">{{ productionStore.currentFile.filename }}</span>
            <span class="fp-count ltr-number">{{ productionStore.currentFile.record_count.toLocaleString() }}</span>
            <button class="fp-delete" @click="handleDelete" title="מחק קובץ">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          <!-- Upload icon button -->
          <button
            class="upload-icon-btn"
            @click="openFilePicker"
            title="החלף קובץ פרודוקציה"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </button>
        </div>

        <!-- Uploading indicator -->
        <div v-if="productionStore.uploading" class="uploading-banner">
          <div class="loader-sm">
            <div class="loader-ring"></div>
          </div>
          <span>מעלה קובץ חדש...</span>
        </div>

        <!-- Tab content: Insights -->
        <div v-if="innerTab === 'insights'">
          <div v-if="productionStore.analyticsLoading" class="loading-state">
            <div class="loader">
              <div class="loader-ring"></div>
              <div class="loader-ring delay"></div>
            </div>
            <span>טוען תובנות...</span>
          </div>
          <ProductionDashboard
            v-else-if="productionStore.analytics"
            :analytics="productionStore.analytics"
          />
        </div>

        <!-- Tab content: Comparison -->
        <div v-if="innerTab === 'comparison'">
          <ProductionComparison
            :history="productionStore.history"
            :comparisonResult="productionStore.comparisonResult"
            :comparing="productionStore.comparing"
            :currentFileId="productionStore.currentFile.id"
            @compare="handleCompare"
            @reset="productionStore.resetComparison()"
            @go-to-comparison="$emit('go-to-comparison')"
          />
        </div>

        <!-- Tab content: Volume -->
        <div v-if="innerTab === 'volume'">
          <VolumeComparison />
        </div>

        <!-- Tab content: History (production files by month) -->
        <div v-if="innerTab === 'history'" class="history-panel">
          <div v-if="!productionStore.history.length" class="history-empty">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <p>אין עדיין קבצי פרודוקציה היסטוריים.</p>
            <small>קבצים שתחליף יעברו לכאן ויקובצו לפי חודש.</small>
          </div>

          <section
            v-for="grp in historyByMonth"
            :key="grp.key"
            class="month-group"
          >
            <header
              class="month-head"
              @click="toggleMonth(grp.key)"
              :class="{ 'is-collapsed': !openMonths[grp.key] }"
            >
              <svg class="month-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
              <span class="month-label">{{ grp.label }}</span>
              <span class="month-count">{{ grp.files.length }} {{ grp.files.length === 1 ? 'קובץ' : 'קבצים' }}</span>
              <span class="month-records ltr-number">{{ grp.totalRecords.toLocaleString() }} רשומות</span>
            </header>

            <ul v-if="openMonths[grp.key]" class="month-files">
              <li
                v-for="f in grp.files"
                :key="f.id"
                class="hist-file"
              >
                <div class="hf-main">
                  <div class="hf-icon" :title="(f.format_type || '').includes('production') ? 'פרודוקציה' : f.format_type">
                    <svg v-if="(f.filename || '').toLowerCase().endsWith('.zip')" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                  </div>
                  <div class="hf-text">
                    <div class="hf-name" :title="f.filename">{{ f.filename }}</div>
                    <div class="hf-meta">
                      <span v-if="f.company_source">{{ f.company_source }}</span>
                      <span class="ltr-number">{{ (f.record_count || 0).toLocaleString() }} רשומות</span>
                      <span class="hf-time">{{ relativeHebrew(f.uploaded_at) }}</span>
                    </div>
                  </div>
                </div>
                <a
                  v-if="f.has_file"
                  class="hf-download"
                  :href="`/api/uploads/${f.id}/file`"
                  :download="f.filename"
                  title="הורד קובץ מקור"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                </a>
              </li>
            </ul>
          </section>
        </div>
      </template>
    </template>

    <!-- Hidden file input shared by all upload buttons (hero icon + replace button) -->
    <input
      ref="fileInputRef"
      type="file"
      accept=".xlsx,.xls,.zip"
      @change="onFileSelected"
      style="display: none"
    />

    <!-- Compare suggestion modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCompareModal" class="compare-suggest-overlay" @click.self="showCompareModal = false">
          <div class="compare-suggest-card">
            <div class="cs-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
            </div>
            <h3 class="cs-title">קובץ חדש הועלה בהצלחה!</h3>
            <p class="cs-body">רוצה להשוות עם הקובץ הקודם?</p>
            <div v-if="previousFile" class="cs-file">
              <span class="cs-file-name">{{ previousFile.filename }}</span>
              <span class="cs-file-meta ltr-number">{{ previousFile.record_count?.toLocaleString() }} רשומות</span>
            </div>
            <div class="cs-actions">
              <button class="cs-btn cs-btn-primary" @click="acceptCompare">השווה עכשיו</button>
              <button class="cs-btn cs-btn-ghost" @click="showCompareModal = false">אחר כך</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, watch } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import { useVolumeStore } from '../../stores/volume.js'
import ProductionDashboard from './ProductionDashboard.vue'
import ProductionComparison from './ProductionComparison.vue'
import VolumeComparison from './VolumeComparison.vue'
import ProductionHeroPanel from './ProductionHeroPanel.vue'
import AiCapabilitiesGridIsland from './AiCapabilitiesGridIsland.vue'
import { relativeHebrew } from '../../utils/relativeTime.js'

defineEmits(['go-to-comparison', 'go-to-portal-automation'])

const productionStore = useProductionStore()
const volumeStore = useVolumeStore()
const innerTab = ref('insights')
const fileInputRef = ref(null)
const showCompareModal = ref(false)
const previousFile = ref(null)
onMounted(() => {
  productionStore.fetchCurrent()
})

// When file loads, fetch analytics. When it's absent, fetch the landing data
// so the sage hero hydrates immediately on first paint.
watch(() => productionStore.currentFile, (newVal) => {
  if (newVal) {
    productionStore.fetchAnalytics()
  } else {
    productionStore.fetchLanding()
  }
}, { immediate: true })

// After a real upload completes, suggest comparing with previous file
watch(() => productionStore.justUploaded, async (newVal) => {
  if (newVal) {
    productionStore.justUploaded = false
    await productionStore.fetchHistory()
    if (productionStore.history.length > 0) {
      previousFile.value = productionStore.history[0]
      showCompareModal.value = true
    }
  }
})

function switchToComparison() {
  innerTab.value = 'comparison'
  if (!productionStore.history.length) {
    productionStore.fetchHistory()
  }
}

// ── History panel: month-grouped, collapsible ──────────────────────────
const HE_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
const openMonths = reactive({})

function monthKey(iso) {
  if (!iso) return 'unknown'
  const d = new Date(iso)
  if (isNaN(d)) return 'unknown'
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
function monthLabel(key) {
  if (key === 'unknown') return 'לא ידוע'
  const [y, m] = key.split('-')
  return `${HE_MONTHS[parseInt(m, 10) - 1]} ${y}`
}

// Group all production files (current + history) by month, newest month first.
const historyByMonth = computed(() => {
  const all = [...productionStore.history]
  if (productionStore.currentFile) {
    // Show the active file in its month bucket too — it's still part of history.
    all.unshift(productionStore.currentFile)
  }
  const groups = new Map()
  for (const f of all) {
    const k = monthKey(f.uploaded_at)
    if (!groups.has(k)) groups.set(k, [])
    groups.get(k).push(f)
  }
  return [...groups.entries()]
    .sort(([a], [b]) => (b > a ? 1 : -1))
    .map(([key, files]) => ({
      key,
      label: monthLabel(key),
      files: files.sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at)),
      totalRecords: files.reduce((s, f) => s + (f.record_count || 0), 0),
    }))
})

function toggleMonth(key) {
  openMonths[key] = !openMonths[key]
}

function switchToHistory() {
  innerTab.value = 'history'
  if (!productionStore.history.length) {
    productionStore.fetchHistory().then(() => {
      // Auto-open the most recent month so the user sees something immediately
      const newest = historyByMonth.value[0]
      if (newest) openMonths[newest.key] = true
    })
  } else {
    const newest = historyByMonth.value[0]
    if (newest && openMonths[newest.key] === undefined) openMonths[newest.key] = true
  }
}

function openFilePicker() {
  fileInputRef.value?.click()
}

function onFileSelected(e) {
  const files = e.target.files
  if (files && files.length > 0) {
    const file = files[0]
    const ext = file.name.split('.').pop().toLowerCase()
    if (ext === 'xlsx' || ext === 'xls') {
      productionStore.uploadProduction(file)
    } else if (ext === 'zip') {
      // ZIP path goes through the generic /api/uploads endpoint so the
      // server-side Mimshak detection + production classification fires.
      productionStore.uploadProductionZip(file)
    }
  }
  e.target.value = ''
}

function acceptCompare() {
  if (productionStore.currentFile && previousFile.value) {
    handleCompare(productionStore.currentFile.id, previousFile.value.id)
    innerTab.value = 'comparison'
  }
  showCompareModal.value = false
}

async function handleDelete() {
  if (confirm('האם למחוק את קובץ הפרודוקציה?')) {
    try {
      await productionStore.removeCurrent()
    } catch (e) {
      alert(productionStore.error || 'שגיאה במחיקת קובץ פרודוקציה')
    }
  }
}

async function handleCompare(currentId, previousId) {
  try {
    await productionStore.compareProductions(currentId, previousId)
  } catch (e) {
    // error handled in store
  }
}
</script>

<style scoped>
.production-tab {
  animation: slideUp 0.4s var(--transition);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── History panel (production by month) ───────────────────────────── */
.history-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0 24px;
}
.history-empty {
  text-align: center;
  padding: 48px 16px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.history-empty p { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
.history-empty small { font-size: 12px; line-height: 1.6; }

.month-group {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  overflow: hidden;
}
.month-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  background: linear-gradient(180deg, rgba(245, 124, 0, 0.04), rgba(245, 124, 0, 0.01));
  transition: background 0.15s;
}
.month-head:hover { background: rgba(245, 124, 0, 0.07); }
.month-chevron {
  color: var(--primary, #F57C00);
  transition: transform 0.2s cubic-bezier(0.34, 1.4, 0.64, 1);
  flex-shrink: 0;
}
.month-head.is-collapsed .month-chevron { transform: rotate(-90deg); }
.month-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  flex: 1;
}
.month-count {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--primary-deep, #c2410c);
  background: rgba(245, 124, 0, 0.10);
  padding: 3px 9px;
  border-radius: 999px;
}
.month-records {
  font-size: 11.5px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.month-files {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--border-subtle);
}
.hist-file {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px dashed var(--border-subtle);
  transition: background 0.15s;
}
.hist-file:last-child { border-bottom: none; }
.hist-file:hover { background: rgba(245, 124, 0, 0.03); }
.hf-main { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.hf-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.12), rgba(255, 152, 0, 0.06));
  color: var(--primary-deep, #c2410c);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.hf-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.hf-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hf-meta {
  display: flex;
  gap: 10px;
  font-size: 11.5px;
  color: var(--text-muted);
  align-items: center;
}
.hf-meta > span { white-space: nowrap; }
.hf-time { color: var(--primary-deep, #c2410c); font-weight: 600; }
.hf-download {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: rgba(45, 37, 34, 0.05);
  color: var(--text-muted);
  display: grid;
  place-items: center;
  text-decoration: none;
  transition: all 0.15s;
  flex-shrink: 0;
}
.hf-download:hover {
  background: rgba(245, 124, 0, 0.12);
  color: var(--primary-deep, #c2410c);
}

.loading-state {
  text-align: center;
  padding: 64px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loader {
  width: 40px;
  height: 40px;
  position: relative;
  margin: 0 auto 16px;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 6px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

/* Inner tabs bar */
.inner-tabs-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 2px solid var(--border-subtle);
  padding-bottom: 0;
  flex-wrap: wrap;
}

.inner-tabs {
  display: flex;
  gap: 4px;
}

.inner-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: all 0.25s var(--transition);
  white-space: nowrap;
}

.inner-tab:hover { color: var(--text-secondary); }

.inner-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.inner-tab svg { opacity: 0.5; }
.inner-tab.active svg { opacity: 1; color: var(--primary); }

.tab-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent-emerald);
  box-shadow: 0 0 6px var(--green-light);
}

/* File pill */
.file-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
  background: var(--green-light);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: 100px;
  font-size: 12px;
  margin-inline-start: auto;
  max-width: 280px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background: var(--accent-emerald);
  border-radius: 50%;
  animation: pulse-soft 2s ease-in-out infinite;
  flex-shrink: 0;
}

.fp-name {
  color: var(--text-secondary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 140px;
}

.fp-count {
  color: var(--accent-emerald);
  font-weight: 700;
  flex-shrink: 0;
}

.fp-delete {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  padding: 0;
}

.fp-delete:hover {
  background: var(--red-light);
  color: var(--red);
}

/* Upload icon button */
.upload-icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--green-light);
  color: var(--accent-emerald);
  border: 1.5px solid rgba(46, 132, 74, 0.15);
  cursor: pointer;
  transition: all 0.25s var(--transition);
  flex-shrink: 0;
}

.upload-icon-btn:hover {
  background: var(--accent-emerald);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(46, 132, 74, 0.2);
}

/* Uploading banner */
.uploading-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  background: var(--green-light);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--accent-emerald);
  font-weight: 600;
}

.loader-sm {
  width: 18px;
  height: 18px;
  position: relative;
}

.loader-sm .loader-ring {
  border-top-color: var(--accent-emerald);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

/* Compare suggestion modal */
.compare-suggest-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1010;
  backdrop-filter: blur(4px);
}

.compare-suggest-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: 36px 32px 28px;
  max-width: 380px;
  width: 90%;
  text-align: center;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.15);
}

.cs-icon {
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

.cs-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 6px;
}

.cs-body {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.cs-file {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  margin-bottom: 20px;
  font-size: 12px;
}

.cs-file-name {
  color: var(--text-secondary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

.cs-file-meta {
  color: var(--text-muted);
}

.cs-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cs-btn {
  padding: 11px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.25s var(--transition);
}

.cs-btn-primary {
  background: var(--primary);
  color: #fff;
  border: none;
}

.cs-btn-primary:hover {
  background: var(--primary-deep);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(245, 124, 0, 0.25);
}

.cs-btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.cs-btn-ghost:hover {
  background: var(--bg-surface);
  color: var(--text);
}

/* Modal transition */
.modal-enter-active { animation: modalIn 0.3s var(--transition); }
.modal-leave-active { animation: modalIn 0.2s var(--transition) reverse; }
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
</style>
