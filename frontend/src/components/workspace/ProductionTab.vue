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
      <!-- No file: show uploader -->
      <ProductionUploader v-if="!productionStore.currentFile" />

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
          <input
            ref="fileInputRef"
            type="file"
            accept=".xlsx,.xls"
            @change="onFileSelected"
            style="display: none"
          />
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
          />
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import ProductionUploader from './ProductionUploader.vue'
import ProductionDashboard from './ProductionDashboard.vue'
import ProductionComparison from './ProductionComparison.vue'

const productionStore = useProductionStore()
const innerTab = ref('insights')
const fileInputRef = ref(null)

onMounted(() => {
  productionStore.fetchCurrent()
})

// When file loads, fetch analytics
watch(() => productionStore.currentFile, (newVal) => {
  if (newVal) {
    productionStore.fetchAnalytics()
  }
}, { immediate: true })

function switchToComparison() {
  innerTab.value = 'comparison'
  if (!productionStore.history.length) {
    productionStore.fetchHistory()
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
      productionStore.uploadProduction(file).then(() => {
        productionStore.fetchAnalytics()
        productionStore.fetchHistory()
      })
    }
  }
  e.target.value = ''
}

async function handleDelete() {
  if (confirm('האם למחוק את קובץ הפרודוקציה?')) {
    try {
      await productionStore.removeCurrent()
    } catch (e) {
      // error handled in store
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
</style>
