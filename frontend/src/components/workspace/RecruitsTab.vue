<template>
  <div class="recruits-tab">
    <!-- No production file warning -->
    <div v-if="!productionStore.currentFile && !productionStore.loading" class="hint-banner">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="16" x2="12" y2="12"/>
        <line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
      <span>העלה קובץ פרודוקציה בלשונית "פרודוקציה" כדי לבדוק מגויסים מולו</span>
    </div>

    <!-- Upload button — big centered when no recruits -->
    <div class="recruit-uploader" v-if="!hasRecruits">
      <div v-if="recruitsStore.uploading" class="upload-loading-card">
        <div class="upload-loading-top">
          <div class="loader">
            <div class="loader-ring"></div>
            <div class="loader-ring delay"></div>
          </div>
          <div class="loading-info">
            <span class="loading-text">{{ recruitStageLabel }}</span>
            <span class="loading-hint">{{ recruitStageHint }}</span>
          </div>
        </div>

        <div class="progress-bar-track">
          <div class="progress-bar-fill" :style="{ width: recruitProgressWidth }"></div>
          <div class="progress-bar-shimmer"></div>
        </div>

        <div class="upload-steps">
          <div class="upload-step" :class="{ active: recruitStage >= 1, done: recruitStage > 1 }">
            <div class="step-icon">
              <svg v-if="recruitStage > 1" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else class="ltr-number">1</span>
            </div>
            <span>העלאה</span>
          </div>
          <div class="step-line" :class="{ filled: recruitStage > 1 }"></div>
          <div class="upload-step" :class="{ active: recruitStage >= 2, done: recruitStage > 2 }">
            <div class="step-icon">
              <svg v-if="recruitStage > 2" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else class="ltr-number">2</span>
            </div>
            <span>ניתוח</span>
          </div>
          <div class="step-line" :class="{ filled: recruitStage > 2 }"></div>
          <div class="upload-step" :class="{ active: recruitStage >= 3 }">
            <div class="step-icon"><span class="ltr-number">3</span></div>
            <span>שמירה</span>
          </div>
        </div>

        <span class="loading-wait-hint">קבצים גדולים עשויים לקחת עד דקה</span>
      </div>

      <button v-else class="upload-btn" @click="openFilePicker">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <span>העלה קובץ גיוס חדש</span>
      </button>
      <input
        ref="fileInputRef"
        type="file"
        accept=".xlsx,.xls"
        @change="onFileSelected"
        style="display: none"
      />

      <div class="options-row">
        <label class="toggle-label">
          <div class="toggle" :class="{ on: needPassword }">
            <input type="checkbox" v-model="needPassword" />
            <div class="toggle-track"><div class="toggle-thumb"></div></div>
          </div>
          <span>קובץ מוצפן</span>
        </label>
      </div>

      <Transition name="slide-down">
        <div class="password-field" v-if="needPassword">
          <input type="password" v-model="password" placeholder="סיסמת הקובץ..." dir="ltr" />
        </div>
      </Transition>
    </div>

    <!-- Upload loading card (centered, shown when uploading regardless of recruits) -->
    <div class="recruit-uploader" v-if="hasRecruits && recruitsStore.uploading">
      <div class="upload-loading-card">
        <div class="upload-loading-top">
          <div class="loader">
            <div class="loader-ring"></div>
            <div class="loader-ring delay"></div>
          </div>
          <div class="loading-info">
            <span class="loading-text">{{ recruitStageLabel }}</span>
            <span class="loading-hint">{{ recruitStageHint }}</span>
          </div>
        </div>
        <div class="progress-bar-track">
          <div class="progress-bar-fill" :style="{ width: recruitProgressWidth }"></div>
          <div class="progress-bar-shimmer"></div>
        </div>
        <span class="loading-wait-hint">קבצים גדולים עשויים לקחת עד דקה</span>
      </div>
    </div>

    <!-- Inner tabs -->
    <div class="inner-tabs" v-if="recruitsStore.recruits.length > 0 || recruitsStore.comparisonResult || recruitsStore.commissionComparisonResult">
      <button
        class="inner-tab"
        :class="{ active: innerTab === 'list' }"
        @click="innerTab = 'list'"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 00-3-3.87"/>
          <path d="M16 3.13a4 4 0 010 7.75"/>
        </svg>
        רשימת מגויסים
        <span class="tab-count" v-if="recruitsStore.recruits.length">{{ recruitsStore.recruits.length }}</span>
      </button>
      <button
        class="inner-tab"
        :class="{ active: innerTab === 'comparison', 'has-result': !!recruitsStore.comparisonResult }"
        @click="innerTab = 'comparison'"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        השוואה מול פרודוקציה
        <span class="tab-dot" v-if="recruitsStore.comparisonResult"></span>
      </button>
      <button
        class="inner-tab"
        :class="{ active: innerTab === 'commission', 'has-result': !!recruitsStore.commissionComparisonResult }"
        @click="innerTab = 'commission'"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
        </svg>
        השוואה מול נפרעים
        <span class="tab-dot" v-if="recruitsStore.commissionComparisonResult"></span>
      </button>
      <!-- Small upload icon when recruits exist -->
      <button
        v-if="hasRecruits && !recruitsStore.uploading"
        class="upload-icon-btn"
        @click="openFilePicker"
        title="העלה קובץ נוסף"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </button>
      <input
        v-if="hasRecruits"
        ref="fileInputRef2"
        type="file"
        accept=".xlsx,.xls"
        @change="onFileSelected"
        style="display: none"
      />
    </div>

    <!-- Tab: List -->
    <div v-if="innerTab === 'list'">
      <div class="list-toolbar">
        <button class="btn-portal-links" @click="showPortalLinks = true">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
            <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
          </svg>
          קישורים ללקוחות
          <span class="portal-badge" v-if="activePortalLinks > 0">{{ activePortalLinks }}</span>
        </button>
      </div>
      <RecruitForm />
    </div>

    <!-- Tab: Comparison -->
    <div v-if="innerTab === 'comparison'">
      <!-- Decoration: circles + waves before comparison result -->
      <template v-if="!recruitsStore.comparisonResult">
        <div class="float-circle fc-1"></div>
        <div class="float-circle fc-2"></div>
        <div class="float-circle fc-3"></div>
        <div class="float-circle fc-4"></div>
        <div class="wave-bg">
          <div class="shimmer"></div>
          <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="rwg1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
                <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
                <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
                <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
              </linearGradient>
            </defs>
            <path fill="url(#rwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
          </svg>
          <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="rwg2" x1="100%" y1="0%" x2="0%" y2="0%">
                <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
                <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
                <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
                <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
              </linearGradient>
            </defs>
            <path fill="url(#rwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
          </svg>
          <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="rwg3" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
                <stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/>
                <stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/>
              </linearGradient>
            </defs>
            <path fill="url(#rwg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
          </svg>
        </div>
      </template>

      <!-- Compare button -->
      <div class="compare-section" v-if="recruitsStore.recruits.length > 0 && !recruitsStore.comparisonResult">
        <button
          class="btn-compare"
          :disabled="!productionStore.currentFile || recruitsStore.comparing"
          @click="runProductionComparison"
        >
          <template v-if="recruitsStore.comparing">
            <div class="btn-spinner"></div>
            <span>בודק...</span>
          </template>
          <template v-else>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            <span>בדוק מול פרודוקציה</span>
          </template>
        </button>
        <p class="compare-hint" v-if="!productionStore.currentFile">
          יש להעלות קובץ פרודוקציה לפני ביצוע בדיקה
        </p>
      </div>

      <Transition name="results">
        <RecruitComparisonResults
          v-if="recruitsStore.comparisonResult"
          :result="recruitsStore.comparisonResult"
        />
      </Transition>

      <div v-if="!recruitsStore.comparisonResult && !recruitsStore.comparing && recruitsStore.recruits.length === 0" class="empty-comparison">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <p>העלה קובץ גיוס כדי להתחיל בהשוואה</p>
      </div>
    </div>

    <!-- Tab: Commission Comparison -->
    <div v-if="innerTab === 'commission'">
      <!-- Decoration -->
      <template v-if="!recruitsStore.commissionComparisonResult">
        <div class="float-circle fc-1"></div>
        <div class="float-circle fc-2"></div>
        <div class="float-circle fc-3"></div>
        <div class="float-circle fc-4"></div>
      </template>

      <!-- Compare section -->
      <div class="compare-section" v-if="recruitsStore.recruits.length > 0 && !recruitsStore.commissionComparisonResult">
        <button
          class="btn-compare"
          :disabled="recruitsStore.comparingCommission || commUploading"
          @click="runCommissionComparison(null)"
        >
          <template v-if="recruitsStore.comparingCommission">
            <div class="btn-spinner"></div>
            <span>בודק...</span>
          </template>
          <template v-else>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
            </svg>
            <span>בדוק מול נפרעים</span>
          </template>
        </button>
        <input
          ref="commFileInput"
          type="file"
          accept=".xlsx,.xls"
          multiple
          @change="onCommFileSelect"
          style="display: none"
        />
      </div>

      <!-- Company filter tags + upload more -->
      <div v-if="recruitsStore.commissionComparisonResult?.commission_files?.length" class="commission-files-info">
        <span>סנן לפי חברה:</span>
        <button
          class="commission-file-tag"
          :class="{ active: !recruitsStore.commissionFilterCompany }"
          @click="runCommissionComparison(null)"
        >הכל</button>
        <button
          v-for="f in recruitsStore.commissionComparisonResult.commission_files"
          :key="f"
          class="commission-file-tag"
          :class="{ active: recruitsStore.commissionFilterCompany === f }"
          @click="runCommissionComparison(f)"
        >{{ f }}</button>
        <button class="comm-add-file-btn" @click="$refs.commFileInput2.click()" title="העלה קובץ נפרעים נוסף">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
        <input
          ref="commFileInput2"
          type="file"
          accept=".xlsx,.xls"
          multiple
          @change="onCommFileSelect"
          style="display: none"
        />
      </div>

      <Transition name="results">
        <RecruitComparisonResults
          v-if="recruitsStore.commissionComparisonResult"
          :result="recruitsStore.commissionComparisonResult"
        />
      </Transition>

      <div v-if="!recruitsStore.commissionComparisonResult && !recruitsStore.comparingCommission && recruitsStore.recruits.length === 0" class="empty-comparison">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
        </svg>
        <p>העלה קובץ גיוס כדי להשוות מול נפרעים</p>
      </div>
    </div>

    <Transition name="fade">
      <p class="error-msg" v-if="recruitsStore.error">{{ recruitsStore.error }}</p>
    </Transition>

    <!-- Portal Links Modal -->
    <PortalLinksManager :show="showPortalLinks" @close="showPortalLinks = false" />
  </div>
</template>

<script setup>
import { ref, computed, inject, watch, onMounted } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import { useRecruitsStore } from '../../stores/recruits.js'
import { usePortalStore } from '../../stores/portal.js'
import RecruitForm from './RecruitForm.vue'
import RecruitComparisonResults from './RecruitComparisonResults.vue'
import PortalLinksManager from './PortalLinksManager.vue'
import api from '../../api/client.js'

const productionStore = useProductionStore()
const recruitsStore = useRecruitsStore()
const portalStore = usePortalStore()

const fileInputRef = ref(null)
const fileInputRef2 = ref(null)
const hasRecruits = computed(() => recruitsStore.recruits.length > 0)
const needPassword = ref(false)
const password = ref('')
const innerTab = ref('list')
const commDragging = ref(false)
const commUploading = ref(false)
const commUploadedFiles = ref([])
const showPortalLinks = ref(false)
const activePortalLinks = computed(() =>
  portalStore.links.filter(l => l.is_active && new Date(l.expires_at) > new Date()).length
)
const recruitStage = ref(0) // 0=idle, 1=uploading, 2=parsing, 3=saving

const recruitStageLabel = computed(() => {
  if (recruitStage.value === 1) return 'מעלה קובץ...'
  if (recruitStage.value === 2) return 'מנתח נתונים ומזהה מגויסים...'
  if (recruitStage.value === 3) return 'שומר מגויסים במערכת...'
  return 'מעבד...'
})

const recruitStageHint = computed(() => {
  if (recruitStage.value === 1) return 'מעביר את הקובץ לשרת'
  if (recruitStage.value === 2) return 'מפענח עמודות ומזהה פורמט'
  if (recruitStage.value === 3) return 'כמעט סיימנו!'
  return ''
})

const recruitProgressWidth = computed(() => {
  if (recruitStage.value === 1) return '30%'
  if (recruitStage.value === 2) return '65%'
  if (recruitStage.value === 3) return '90%'
  return '0%'
})

// Receive files from full-page drop overlay
const droppedFiles = inject('droppedFiles', null)
if (droppedFiles) {
  watch(droppedFiles, (val) => {
    if (val && val.length > 0) {
      uploadFile(val[0])
    }
  })
}

onMounted(() => {
  if (!productionStore.currentFile && !productionStore.loading) {
    productionStore.fetchCurrent()
  }
  // If there's already a comparison result, show that tab
  if (recruitsStore.comparisonResult) {
    innerTab.value = 'comparison'
  }
})

function openFilePicker() {
  (fileInputRef.value || fileInputRef2.value)?.click()
}

function onFileSelected(e) {
  const selected = e.target.files
  if (selected && selected.length > 0) {
    const file = selected[0]
    const ext = file.name.split('.').pop().toLowerCase()
    if (ext === 'xlsx' || ext === 'xls') {
      uploadFile(file)
    }
  }
  e.target.value = ''
}

async function uploadFile(file) {
  recruitsStore.error = null
  recruitStage.value = 1
  try {
    // Transition through stages as time passes
    setTimeout(() => { if (recruitsStore.uploading) recruitStage.value = 2 }, 1500)
    setTimeout(() => { if (recruitsStore.uploading) recruitStage.value = 3 }, 5000)

    await recruitsStore.uploadRecruits(
      file,
      needPassword.value ? password.value : null
    )
    password.value = ''
    needPassword.value = false
    // Auto-run comparison after loading recruits
    if (productionStore.currentFile) {
      innerTab.value = 'comparison'
      await recruitsStore.compareRecruits()
    }
  } catch (e) {
    // error handled in store
  } finally {
    recruitStage.value = 0
  }
}

async function runProductionComparison() {
  try {
    await recruitsStore.compareRecruits()
  } catch (e) {
    // error handled in store
  }
}

async function runCommissionComparison(company = null) {
  try {
    await recruitsStore.compareRecruitsCommission(company)
  } catch (e) {
    // error handled in store
  }
}

function onCommFileDrop(e) {
  commDragging.value = false
  const files = Array.from(e.dataTransfer.files).filter(f => {
    const ext = f.name.split('.').pop().toLowerCase()
    return ext === 'xlsx' || ext === 'xls'
  })
  if (files.length) uploadCommFiles(files)
}

function onCommFileSelect(e) {
  const files = Array.from(e.target.files)
  if (files.length) uploadCommFiles(files)
  e.target.value = ''
}

async function uploadCommFiles(files) {
  commUploading.value = true
  recruitsStore.error = null
  try {
    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      await api.post('/uploads', formData)
    }
    commUploadedFiles.value = files.map(f => f.name)
    // Auto-run comparison after upload
    await recruitsStore.compareRecruitsCommission(null)
  } catch (e) {
    recruitsStore.error = e.response?.data?.detail || 'שגיאה בהעלאת קובץ נפרעים'
  } finally {
    commUploading.value = false
  }
}

// Load existing commission files on mount to show which are already available
async function loadCommissionFiles() {
  try {
    const res = await api.get('/uploads')
    const commFiles = res.data.filter(u => u.file_category === 'commission')
    const seen = new Set()
    commUploadedFiles.value = commFiles
      .filter(u => { const k = u.company_source || u.filename; if (seen.has(k)) return false; seen.add(k); return true })
      .map(u => u.company_source || u.filename)
  } catch { /* ignore */ }
}

watch(() => innerTab.value, (tab) => {
  if (tab === 'commission') loadCommissionFiles()
})
</script>

<style scoped>
.recruits-tab {
  animation: slideUp 0.4s var(--transition);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hint-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: var(--amber-light);
  border: 1px solid var(--amber-light);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--amber);
}

/* ── Upload ── */
.recruit-uploader {
  max-width: 560px;
  margin: 0 auto;
  position: relative;
}

/* Floating blur circles */
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

@keyframes floatBob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-16px) rotate(2deg); }
  66% { transform: translateY(8px) rotate(-1deg); }
}

/* Waves fixed to bottom of page */
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

.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 16px 24px;
  border: 1.5px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--card-bg);
  color: var(--text);
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s var(--transition);
}

.upload-btn svg { color: var(--accent-emerald); flex-shrink: 0; }

.upload-btn:hover {
  border-color: var(--accent-emerald);
  background: var(--green-light);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(46, 132, 74, 0.1);
}

.upload-btn:active { transform: translateY(0); }

.upload-loading-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  background: var(--card-bg);
  border: 1.5px solid var(--green-light);
  border-radius: var(--radius-md);
  animation: fadeIn 0.3s ease;
}

.upload-loading-top {
  display: flex;
  align-items: center;
  gap: 14px;
}

.loading-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.loader { width: 28px; height: 28px; position: relative; flex-shrink: 0; }

.loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--accent-emerald);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 4px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.loading-text { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
.loading-hint { font-size: 11px; color: var(--text-muted); }

/* Progress bar */
.progress-bar-track {
  position: relative;
  width: 100%;
  height: 6px;
  background: var(--border-subtle);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-emerald), var(--accent-cyan, var(--accent-emerald)));
  border-radius: 3px;
  transition: width 1s ease;
}

.progress-bar-shimmer {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  animation: shimmerSlide 2s ease-in-out infinite;
}

@keyframes shimmerSlide {
  0% { left: -100%; }
  100% { left: 100%; }
}

/* Upload steps */
.upload-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.upload-step {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.4;
  transition: all 0.4s ease;
}

.upload-step.active { opacity: 1; color: var(--accent-emerald); }
.upload-step.done { color: var(--accent-emerald); opacity: 0.8; }

.step-icon {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  background: var(--border-subtle);
  color: var(--text-muted);
  transition: all 0.4s ease;
  flex-shrink: 0;
}

.upload-step.active .step-icon {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-emerald);
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.2);
  animation: stepPulse 1.5s ease-in-out infinite;
}

.upload-step.done .step-icon {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  animation: none;
}

@keyframes stepPulse {
  0%, 100% { box-shadow: 0 0 6px rgba(16, 185, 129, 0.2); }
  50% { box-shadow: 0 0 16px rgba(16, 185, 129, 0.35); }
}

.step-line {
  width: 28px;
  height: 2px;
  background: var(--border-subtle);
  margin: 0 6px;
  transition: background 0.4s ease;
  border-radius: 1px;
}

.step-line.filled { background: var(--accent-emerald); }

.loading-wait-hint {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  opacity: 0.6;
  animation: fadeInUp 0.5s ease;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 0.6; transform: translateY(0); }
}

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

.options-row { margin-top: 12px; }

.toggle-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
}

.toggle { position: relative; }
.toggle input { position: absolute; opacity: 0; pointer-events: none; }

.toggle-track {
  width: 36px;
  height: 20px;
  background: var(--border-subtle);
  border-radius: 10px;
  transition: all 0.3s var(--transition);
  position: relative;
}

.toggle.on .toggle-track { background: var(--green-light); }

.toggle-thumb {
  width: 16px;
  height: 16px;
  background: var(--text-secondary);
  border-radius: 50%;
  position: absolute;
  top: 2px;
  right: 2px;
  transition: all 0.3s var(--transition);
}

.toggle.on .toggle-thumb {
  right: 18px;
  background: var(--accent-emerald);
  box-shadow: 0 0 8px var(--green-light);
}

.password-field { margin-top: 12px; }

.password-field input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  background: var(--bg-surface);
  color: var(--text);
  transition: all 0.25s var(--transition);
}

.password-field input:focus {
  border-color: var(--accent-emerald);
  box-shadow: 0 0 0 3px var(--green-light);
}

/* ── Inner Tabs ── */
.inner-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid var(--border-subtle);
  padding-bottom: 0;
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

.tab-count {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 10px;
  background: rgba(127, 86, 217, 0.08);
  color: var(--accent-violet);
}

.tab-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent-emerald);
  box-shadow: 0 0 6px var(--green-light);
}

/* ── Small upload icon button ── */
.upload-icon-btn {
  margin-inline-start: auto;
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

/* ── Compare ── */
.compare-section {
  text-align: center;
  padding: 24px 0;
}

.btn-compare {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 36px;
  background: linear-gradient(135deg, var(--primary), var(--primary-deep));
  color: white;
  border-radius: 14px;
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  transition: all 0.3s var(--transition);
  position: relative;
  overflow: hidden;
}

.btn-compare::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%);
  background-size: 200% 100%;
  animation: shimmer 3s ease-in-out infinite;
}

.btn-compare:hover:not(:disabled) {
  box-shadow: 0 8px 32px rgba(245, 124, 0, 0.15);
  transform: translateY(-2px);
}

.btn-compare:disabled { opacity: 0.3; cursor: not-allowed; }
.btn-compare:disabled::before { display: none; }

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.compare-hint { font-size: 12px; color: var(--text-muted); margin-top: 10px; }
.compare-hint-info { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }

.commission-files-info {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 8px 16px; font-size: 12px; color: var(--text-muted);
}
.commission-file-tag {
  background: var(--bg-alt, #f1f5f9); padding: 4px 12px;
  border-radius: 6px; font-weight: 600; color: var(--text-muted);
  font-size: 11px; border: 1px solid transparent;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.commission-file-tag:hover { border-color: var(--primary); color: var(--primary); }
.commission-file-tag.active {
  background: var(--primary); color: white; border-color: var(--primary);
}

.comm-uploaded-list {
  display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; justify-content: center;
}
.comm-uploaded-tag {
  background: var(--accent-emerald-bg, #ecfdf5); color: var(--accent-emerald, #10b981);
  padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;
}
.comm-add-file-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 6px;
  border: 1px dashed var(--border, #e2e8f0); background: transparent;
  color: var(--text-muted); cursor: pointer; transition: all 0.15s;
}
.comm-add-file-btn:hover { border-color: var(--primary); color: var(--primary); }

.empty-comparison {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-muted);
}
.empty-comparison svg { margin-bottom: 12px; opacity: 0.3; }
.empty-comparison p { font-size: 14px; }

/* Transitions */
.slide-down-enter-active { animation: slideDown 0.3s var(--transition); }
.slide-down-leave-active { animation: slideDown 0.2s var(--transition) reverse; }
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.results-enter-active { animation: slideUp 0.5s var(--transition); }
.results-leave-active { animation: fadeOut 0.2s ease-out; }
@keyframes fadeOut { to { opacity: 0; } }

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }

/* ── List toolbar ── */
.list-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.btn-portal-links {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 16px;
  background: var(--card-bg);
  border: 1.5px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s var(--transition);
}

.btn-portal-links svg { color: var(--primary); }

.btn-portal-links:hover {
  border-color: var(--primary);
  background: var(--primary-light);
  color: var(--primary);
  box-shadow: 0 2px 8px rgba(245, 124, 0, 0.1);
}

.portal-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 10px;
  background: var(--primary-light);
  color: var(--primary);
}

.error-msg {
  color: var(--red);
  font-size: 13px;
  text-align: center;
  padding: 8px 12px;
  background: var(--red-light);
  border-radius: 8px;
  border: 1px solid var(--red-light);
}
</style>
