<template>
  <div ref="tabRoot" class="recruits-tab">
    <!-- Hero — the Mail Agent's shape (kicker, wordmark with the accent word,
         counters, looping scene), in the portfolio's turquoise. -->
    <header class="rc-hero">
      <div class="rc-hero-copy">
        <span class="rc-kicker">מגויסים</span>
        <h2 class="rc-hero-title">ניהול תיק <span class="rc-hero-title-acc">אישי</span></h2>
        <p class="rc-hero-sub">מעקב אחרי הלקוחות שגייסתם — מול הפרודוקציה והנפרעים.</p>
        <div v-if="hasRecruits" class="rc-stats">
          <div class="rc-stat">
            <span class="rc-stat-n ltr-number">{{ recruitsStore.recruits.length }}</span>
            <span class="rc-stat-l">מגויסים · {{ activeCatLabel }}</span>
          </div>
          <div v-if="recruitsStore.comparisonResult?.found != null" class="rc-stat rc-stat--hot">
            <span class="rc-stat-n ltr-number">{{ recruitsStore.comparisonResult.found }}</span>
            <span class="rc-stat-l">נמצאו בפרודוקציה</span>
          </div>
        </div>
      </div>
      <TabHeroLoop scene="recruits" class="rc-hero-art" />
    </header>

    <!-- No production file warning -->
    <div v-if="!productionStore.currentFile && !productionStore.loading && (hasRecruits || hasAnyRecruits)" class="hint-banner">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="16" x2="12" y2="12"/>
        <line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
      <span>העלה קובץ פרודוקציה בלשונית "פרודוקציה" כדי לבדוק מגויסים מולו</span>
    </div>

    <!-- First use: a realistic photo that dissolves into the card (no frame),
         the headline, the upload action and the format guide. The missing-
         production warning lives here as a note instead of a separate bar. -->
    <section v-if="!hasRecruits && !hasAnyRecruits" class="rc-welcome">
      <div v-if="rcWelcomeArt" class="rc-photo" aria-hidden="true"><img :src="rcWelcomeArt" alt="" /></div>
      <div class="rc-welcome-copy">
      <h3 class="rc-welcome-title">העלו את קובץ הגיוס<br><span class="rc-welcome-acc">ונבדוק כל מגויס</span></h3>
      <!-- Loading state -->
      <div v-if="recruitsStore.uploading" class="upload-loading">
        <div class="loading-content">
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
        </div>
        <span class="loading-wait-hint">קבצים גדולים עשויים לקחת עד דקה</span>
      </div>

      <!-- Upload button -->
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

      <!-- File format guide -->
      <div class="format-guide">
        <button class="format-guide-toggle" @click="showFormatGuide = !showFormatGuide">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          <span>איזה פורמט קובץ נדרש?</span>
          <svg class="guide-chevron" :class="{ open: showFormatGuide }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
        <Transition name="slide-down">
          <div v-if="showFormatGuide" class="format-guide-content">
            <p class="guide-intro">הקובץ צריך להיות Excel (.xlsx / .xls) עם העמודות הבאות:</p>

            <div class="columns-section">
              <h5>עמודות חובה</h5>
              <div class="column-chips">
                <span class="col-chip required">ת.ז</span>
                <span class="col-chip required">שם פרטי</span>
                <span class="col-chip required">שם משפחה</span>
                <span class="col-chip required">חברה מקבלת</span>
                <span class="col-chip required">מוצר</span>
              </div>
            </div>

            <div class="columns-section">
              <h5>עמודות מומלצות</h5>
              <div class="column-chips">
                <span class="col-chip">תאריך חתימה</span>
                <span class="col-chip">סוג גיוס</span>
                <span class="col-chip">מספר קופה/פוליסה</span>
                <span class="col-chip">סכום העברה צפוי</span>
                <span class="col-chip">סכום העברה בפועל</span>
                <span class="col-chip">מעמד</span>
                <span class="col-chip">פעיל/לא פעיל</span>
                <span class="col-chip">דמי ניהול</span>
                <span class="col-chip">מקור הליד</span>
                <span class="col-chip">הערות</span>
              </div>
            </div>

            <p class="guide-hint">סדר העמודות לא חשוב — המערכת מזהה אותן אוטומטית</p>
          </div>
        </Transition>
      </div>
      <p v-if="!productionStore.currentFile && !productionStore.loading" class="rc-note">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        כדי לבדוק את המגויסים צריך גם קובץ פרודוקציה — מעלים אותו בלשונית "פרודוקציה".
      </p>
      </div>
    </section>

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

    <!-- The three views: one gliding pill (the app's view switch) -->
    <template v-if="hasRecruits || hasAnyRecruits || recruitsStore.comparisonResult || recruitsStore.commissionComparisonResult">
      <div class="rc-switch" role="tablist" aria-label="תצוגה" :style="{ '--rc-i': VIEWS.findIndex(v => v.id === innerTab) }">
        <span class="rc-glider" aria-hidden="true"></span>
        <button v-for="v in VIEWS" :key="v.id" type="button" role="tab" class="rc-switch-btn"
                :class="{ active: innerTab === v.id }" :aria-selected="innerTab === v.id" @click="innerTab = v.id">
          <span class="rc-switch-title">{{ v.label }}</span>
          <span class="rc-switch-sub">{{ v.sub }}</span>
        </button>
      </div>

      <!-- Which list, and the file actions — only on the list view -->
      <div v-if="innerTab === 'list'" class="rc-toolbar">
        <div class="rc-cats" role="tablist" aria-label="רשימה">
          <button v-for="c in CATS" :key="c.id" type="button" role="tab"
                  :class="{ on: recruitsStore.activeCategory === c.id }" :aria-selected="recruitsStore.activeCategory === c.id"
                  @click="switchCategory(c.id)">
            {{ c.label }}<span v-if="recruitsStore.activeCategory === c.id && recruitsStore.recruits.length" class="ltr-number">{{ recruitsStore.recruits.length }}</span>
          </button>
        </div>
        <button v-if="hasRecruits && !recruitsStore.uploading" class="rc-icon-btn" type="button" @click="openFilePicker"
                title="העלאת קובץ" aria-label="העלאת קובץ">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        </button>
        <button v-if="hasRecruits && !recruitsStore.uploading" ref="clearBtnRef" class="rc-icon-btn rc-icon-btn--danger" type="button"
                @click="openClearConfirm($event)" title="מחיקת הקובץ" aria-label="מחיקת הקובץ">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
        </button>
        <input v-if="hasRecruits" ref="fileInputRef2" type="file" accept=".xlsx,.xls" @change="onFileSelected" style="display: none" />
      </div>
    </template>

    <!-- Tab: List -->
    <div v-if="innerTab === 'list'">
      <!-- Empty category upload -->
      <div v-if="!hasRecruits && !recruitsStore.uploading && hasAnyRecruits" class="recruit-uploader category-empty-uploader">
        <button class="upload-btn" @click="openFilePicker">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <span>העלה קובץ {{ recruitsStore.activeCategory === 'insurance' ? 'ביטוח' : 'פיננסים' }}</span>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          accept=".xlsx,.xls"
          @change="onFileSelected"
          style="display: none"
        />
      </div>

      <template v-if="hasRecruits || recruitsStore.uploading">
        <RecruitForm />
      </template>
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
                <stop offset="0%" stop-color="#0FA39B" stop-opacity="0.10"/>
                <stop offset="30%" stop-color="#0FA39B" stop-opacity="0.06"/>
                <stop offset="60%" stop-color="#0FA39B" stop-opacity="0.10"/>
                <stop offset="100%" stop-color="#0FA39B" stop-opacity="0.05"/>
              </linearGradient>
            </defs>
            <path fill="url(#rwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
          </svg>
          <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="rwg2" x1="100%" y1="0%" x2="0%" y2="0%">
                <stop offset="0%" stop-color="#0FA39B" stop-opacity="0.08"/>
                <stop offset="40%" stop-color="#0FA39B" stop-opacity="0.05"/>
                <stop offset="70%" stop-color="#0FA39B" stop-opacity="0.08"/>
                <stop offset="100%" stop-color="#0FA39B" stop-opacity="0.04"/>
              </linearGradient>
            </defs>
            <path fill="url(#rwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
          </svg>
          <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="rwg3" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#0FA39B" stop-opacity="0.06"/>
                <stop offset="50%" stop-color="#0FA39B" stop-opacity="0.04"/>
                <stop offset="100%" stop-color="#0FA39B" stop-opacity="0.07"/>
              </linearGradient>
            </defs>
            <path fill="url(#rwg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
          </svg>
        </div>
      </template>

      <!-- Before the check: one card — what is checked against, and the button -->
      <div v-if="recruitsStore.recruits.length > 0 && !recruitsStore.comparisonResult" class="rc-run">
        <svg class="rc-run-ico" width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path pathLength="1" d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path pathLength="1" d="M14 2v6h6"/><path pathLength="1" d="M9 15l2 2 4-4"/>
        </svg>
        <div class="rc-run-copy">
          <h4>מי מהמגויסים נקלט בפרודוקציה?</h4>
          <p v-if="productionStore.currentFile">
            <span class="rc-run-file">{{ productionStore.currentFile.filename }}</span>
            · <span class="ltr-number">{{ productionStore.currentFile.record_count?.toLocaleString() }}</span> רשומות
          </p>
          <p v-else>צריך קודם קובץ פרודוקציה.</p>
        </div>
        <button class="rc-run-btn" type="button" :disabled="!productionStore.currentFile || recruitsStore.comparing" @click="runProductionComparison">
          <span v-if="recruitsStore.comparing" class="btn-spinner"></span>
          {{ recruitsStore.comparing ? 'בודק…' : 'בדיקה' }}
        </button>
      </div>

      <Transition name="results">
        <RecruitComparisonResults
          v-if="recruitsStore.comparisonResult"
          :result="recruitsStore.comparisonResult"
          mode="production"
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

      <div v-if="recruitsStore.recruits.length > 0 && !recruitsStore.commissionComparisonResult" class="rc-run">
        <svg class="rc-run-ico" width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle pathLength="1" cx="12" cy="12" r="9"/><path pathLength="1" d="M15 9.5a2.5 2.5 0 00-2.5-1.5h-1a2 2 0 000 4h1a2 2 0 010 4h-1A2.5 2.5 0 019 14.5"/><path pathLength="1" d="M12 6.5v11"/>
        </svg>
        <div class="rc-run-copy">
          <h4>על מי מהמגויסים שולמה עמלה?</h4>
          <p>בודקים מול קובצי הנפרעים שכבר במערכת.</p>
        </div>
        <button class="rc-run-btn" type="button" :disabled="recruitsStore.comparingCommission || commUploading" @click="runCommissionComparison(null)">
          <span v-if="recruitsStore.comparingCommission" class="btn-spinner"></span>
          {{ recruitsStore.comparingCommission ? 'בודק…' : 'בדיקה' }}
        </button>
        <input ref="commFileInput" type="file" accept=".xlsx,.xls" multiple @change="onCommFileSelect" style="display: none" />
      </div>

      <!-- Company filter tags + upload more -->
      <div v-if="recruitsStore.commissionComparisonResult?.commission_files?.length" class="commission-files-info">
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
          mode="commission"
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

    <!-- Clear-file confirmation -->
    <Teleport to="body">
      <Transition name="modal" @enter="onClearEnter">
        <div v-if="showClearConfirm" class="clear-overlay" @click.self="closeClearConfirm">
          <div ref="clearCardRef" class="clear-modal">
            <div class="clear-modal-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                <line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
              </svg>
            </div>
            <h4>למחוק את קובץ המגויסים?</h4>
            <p>כל {{ recruitsStore.recruits.length }} המגויסים ברשימת «{{ activeCatLabel }}» יימחקו. אפשר להעלות קובץ חדש לאחר מכן. הקטגוריה השנייה לא תיפגע.</p>
            <div class="clear-modal-actions">
              <button class="clear-cancel" @click="closeClearConfirm" :disabled="clearing">ביטול</button>
              <button class="clear-confirm" @click="confirmClearFile" :disabled="clearing">
                <span v-if="clearing" class="btn-spinner"></span>
                <span>{{ clearing ? 'מוחק...' : 'מחק קובץ' }}</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, inject, watch, onMounted } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import { useRecruitsStore } from '../../stores/recruits.js'
import RecruitForm from './RecruitForm.vue'
import TabHeroLoop from './TabHeroLoop.vue'
import RecruitComparisonResults from './RecruitComparisonResults.vue'
import api from '../../api/client.js'
import { useOriginMorph } from '../../composables/useOriginMorph'
import { useScrollReveal } from '../../composables/useScrollReveal'

const productionStore = useProductionStore()
// Sections rise in as the agent scrolls to them — same as the Production tab
const tabRoot = ref(null)
useScrollReveal(tabRoot, '.rc-run, .rr-kpis, .rr-chart, .rr-list, .recruit-form')
const recruitsStore = useRecruitsStore()

const fileInputRef = ref(null)
const fileInputRef2 = ref(null)
// Realistic photo for the first-use section; optional (glob → no crash if absent).
const rcWelcomeArt = Object.values(import.meta.glob('../../assets/welcome/recruits-empty.webp', { eager: true, import: 'default' }))[0] || ''
const hasRecruits = computed(() => recruitsStore.recruits.length > 0)
const hasAnyRecruits = ref(false)
const needPassword = ref(false)
const showFormatGuide = ref(false)
const password = ref('')
const innerTab = ref('list')
const showClearConfirm = ref(false)
const clearing = ref(false)
const activeCatLabel = computed(() =>
  recruitsStore.activeCategory === 'insurance' ? 'ביטוח' : 'פיננסים'
)
const VIEWS = [
  { id: 'list', label: 'המגויסים', sub: 'הרשימה שלכם' },
  { id: 'comparison', label: 'מול פרודוקציה', sub: 'מי נקלט' },
  { id: 'commission', label: 'מול נפרעים', sub: 'על מי שולם' },
]
const CATS = [
  { id: 'financial', label: 'פיננסים' },
  { id: 'insurance', label: 'ביטוח' },
]
// The delete confirm grows out of the trash button and folds back into it
const clearMorph = useOriginMorph()
const clearCardRef = ref(null)
function openClearConfirm(ev) { clearMorph.remember(ev.currentTarget); showClearConfirm.value = true }
function onClearEnter(el) { clearMorph.grow(el.querySelector('.clear-modal')) }
async function closeClearConfirm() {
  if (clearMorph.hasOrigin() && clearCardRef.value) await clearMorph.shrink(clearCardRef.value)
  showClearConfirm.value = false
}
const commDragging = ref(false)
const commUploading = ref(false)
const commUploadedFiles = ref([])
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

onMounted(async () => {
  if (!productionStore.currentFile && !productionStore.loading) {
    productionStore.fetchCurrent()
  }
  // Load recruits for current category
  await recruitsStore.fetchRecruits()
  // If there's already a comparison result, show that tab
  if (recruitsStore.comparisonResult) {
    innerTab.value = 'comparison'
  }
  // Check if any recruits exist in any category (for showing tabs vs big upload)
  if (recruitsStore.recruits.length > 0) {
    hasAnyRecruits.value = true
  } else {
    try {
      const res = await api.get('/recruits')
      if (res.data.length > 0) hasAnyRecruits.value = true
    } catch { /* ignore */ }
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
    hasAnyRecruits.value = true
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

function switchCategory(cat) {
  recruitsStore.setCategory(cat)
  innerTab.value = 'list'
}

async function confirmClearFile() {
  clearing.value = true
  try {
    await recruitsStore.clearCategory()
    // Re-check whether ANY recruits remain (the other category may still have data)
    try {
      const res = await api.get('/recruits')
      hasAnyRecruits.value = res.data.length > 0
    } catch { hasAnyRecruits.value = false }
    innerTab.value = 'list'
    showClearConfirm.value = false
  } catch {
    // error surfaced via store
  } finally {
    clearing.value = false
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
/* ── Hero (Mail Agent's shape, in the portfolio's turquoise) ── */
.rc-hero {
  position: relative; overflow: hidden; display: flex; align-items: center; min-height: 190px;
  padding: 22px 24px; background: var(--card-bg);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: var(--shadow-sm);
}
.rc-hero::before {
  content: ''; position: absolute; inset-inline-end: -6%; top: -60%; width: 44%; height: 220%;
  background: radial-gradient(circle, var(--tab-recruits-wash), transparent 70%); pointer-events: none;
}
.rc-hero-copy { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 6px; max-width: 60%; min-width: 0; }
.rc-kicker {
  align-self: flex-start; padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 800;
  background: var(--tab-recruits-wash); color: var(--tab-recruits-ink);
}
.rc-hero-title {
  align-self: flex-start; margin: 4px 0 0;
  font-family: 'Rubik', 'Heebo', sans-serif; font-size: clamp(28px, 3.3vw, 40px); font-weight: 700;
  letter-spacing: -0.035em; line-height: 1.05; color: var(--text);
}
.rc-hero-title-acc { color: var(--tab-recruits-ink); }
.rc-hero-sub { margin: 2px 0 0; font-size: 13.5px; color: var(--text-muted); }
.rc-hero-art {
  position: absolute; inset-inline-end: 4px; top: 50%; transform: translateY(-50%);
  width: min(270px, 36%); aspect-ratio: 420 / 300; pointer-events: none; z-index: 0;
}
.rc-stats { display: flex; gap: 22px; margin-top: 10px; }
.rc-stat { display: flex; flex-direction: column; align-items: flex-start; }
.rc-stat-n { font-size: 26px; font-weight: 800; line-height: 1.1; color: var(--text); font-variant-numeric: tabular-nums; }
.rc-stat--hot .rc-stat-n { color: var(--tab-recruits-ink); }
.rc-stat-l { font-size: 11.5px; font-weight: 600; color: var(--text-muted); }
@media (max-width: 720px) {
  .rc-hero { min-height: 0; }
  .rc-hero-copy { max-width: 100%; }
  .rc-hero-art, .rc-hero::before { display: none; }
}

.recruits-tab {
  animation: slideUp 0.4s var(--transition);
  display: flex;
  flex-direction: column;
  gap: 12px;
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

/* ── Identity header (mirrors emails/portal/shelf: title right, hero left) ── */

/* ── First use: photo dissolving into the card (same pattern as the
   agreements welcome in CommissionRateTable.vue) ── */
.rc-welcome {
  position: relative; overflow: hidden; min-height: 360px; display: flex; align-items: center;
  border-radius: var(--radius-md); border: 1px solid var(--border-subtle); background: var(--card-bg); box-shadow: var(--shadow-sm);
}
.rc-photo {
  position: absolute; top: 0; bottom: 0; inset-inline-end: 0; width: 62%; z-index: 0;
  -webkit-mask-image: linear-gradient(to right, #000 0%, #000 50%, transparent 95%);
          mask-image: linear-gradient(to right, #000 0%, #000 50%, transparent 95%);
}
.rc-photo img { width: 100%; height: 100%; object-fit: cover; object-position: left center; display: block; }
.rc-welcome-copy { position: relative; z-index: 1; width: min(460px, 50%); padding: 36px 40px; display: flex; flex-direction: column; gap: 14px; }
.rc-welcome-title {
  margin: 0; font-family: 'Heebo', sans-serif; font-weight: 900;
  font-size: clamp(28px, 3.2vw, 40px); line-height: 1.08; letter-spacing: -0.03em; color: var(--text);
}
.rc-welcome-acc { color: var(--tab-recruits-ink); }
.rc-welcome-copy .upload-btn { align-self: flex-start; width: auto; padding-inline: 22px; }
.rc-welcome-copy .format-guide { align-self: stretch; }
.rc-note {
  margin: 0; display: flex; align-items: flex-start; gap: 7px; font-size: 12.5px; line-height: 1.5;
  color: var(--amber); /* dark gold warning ink */
}
.rc-note svg { flex-shrink: 0; margin-top: 2px; }
@media (max-width: 860px) {
  .rc-welcome { flex-direction: column; align-items: stretch; min-height: 0; }
  .rc-photo { position: relative; width: 100%; height: 200px;
    -webkit-mask-image: linear-gradient(to bottom, #000 55%, transparent 100%);
            mask-image: linear-gradient(to bottom, #000 55%, transparent 100%); }
  .rc-welcome-copy { width: auto; padding: 4px 20px 24px; }
  .rc-welcome-copy .upload-btn { align-self: stretch; }
}

/* ── Upload ── */
.recruit-uploader {
  max-width: 560px;
  margin: 0 auto;
  position: relative;
}
.upload-card {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 22px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 14px);
  box-shadow: var(--shadow-sm);
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
  background: rgba(15, 163, 155, 0.045);
  border: 1px solid rgba(15, 163, 155, 0.06);
  animation: floatBob 8s ease-in-out infinite;
}

.fc-2 {
  width: 160px;
  height: 160px;
  bottom: 25%;
  left: -40px;
  background: rgba(15, 163, 155, 0.035);
  border: 1px solid rgba(15, 163, 155, 0.05);
  animation: floatBob 6.5s ease-in-out infinite reverse;
}

.fc-3 {
  width: 90px;
  height: 90px;
  top: 30%;
  left: 8%;
  background: rgba(15, 163, 155, 0.05);
  animation: floatBob 10s ease-in-out infinite 2s;
}

.fc-4 {
  width: 120px;
  height: 120px;
  top: 55%;
  right: 6%;
  background: rgba(15, 163, 155, 0.03);
  border: 1px solid rgba(15, 163, 155, 0.04);
  animation: floatBob 9s ease-in-out infinite 1s;
}

.fc-5 {
  width: 50px;
  height: 50px;
  top: 18%;
  right: 22%;
  background: rgba(15, 163, 155, 0.055);
  animation: floatBob 7s ease-in-out infinite 3s;
}

.fc-6 {
  width: 280px;
  height: 280px;
  bottom: 8%;
  right: -90px;
  background: rgba(15, 163, 155, 0.025);
  border: 1px solid rgba(15, 163, 155, 0.035);
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
  border: none;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--tab-recruits-ink, #1E7D78), var(--tab-recruits, #3DB6B0));
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s var(--transition);
}

.upload-btn svg { color: #fff; flex-shrink: 0; }

.upload-btn:hover {
  background: linear-gradient(135deg, #17635F, var(--tab-recruits-ink, #1E7D78));
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(61, 182, 176, 0.28);
}

.upload-btn:active { transform: translateY(0); }

.upload-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  background: var(--card-bg);
  border: 1.5px solid var(--green-light);
  border-radius: var(--radius-md);
}

.loading-content {
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
  background: rgba(46, 132, 74, 0.15);
  color: var(--accent-emerald);
  box-shadow: 0 0 10px rgba(46, 132, 74, 0.2);
  animation: stepPulse 1.5s ease-in-out infinite;
}

.upload-step.done .step-icon {
  background: rgba(46, 132, 74, 0.15);
  color: #2E844A;
  animation: none;
}

@keyframes stepPulse {
  0%, 100% { box-shadow: 0 0 6px rgba(46, 132, 74, 0.2); }
  50% { box-shadow: 0 0 16px rgba(46, 132, 74, 0.35); }
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

/* ── Format Guide ── */
.format-guide {
  margin-top: 16px;
  position: relative;
  z-index: 1;
}

.format-guide-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.25s var(--transition);
}

.format-guide-toggle:hover {
  color: var(--text-secondary);
  border-color: var(--border);
  background: var(--bg-surface);
}

.guide-chevron {
  margin-inline-start: auto;
  transition: transform 0.25s ease;
}

.guide-chevron.open {
  transform: rotate(180deg);
}

.format-guide-content {
  padding: 16px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-top: none;
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}

.guide-intro {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 14px;
}

.columns-section {
  margin-bottom: 12px;
}

.columns-section h5 {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.column-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.col-chip {
  display: inline-block;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.col-chip.required {
  background: var(--tab-recruits-wash);
  border-color: rgba(61, 182, 176, 0.28);
  color: var(--tab-recruits-ink);
}

.guide-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 10px;
  font-style: italic;
}





















.empty-category {
  text-align: center; padding: 48px 24px;
  color: var(--text-muted); display: flex;
  flex-direction: column; align-items: center; gap: 12px;
}
.empty-category p { font-size: 14px; font-weight: 600; margin: 0; }
.btn-upload-compact {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 24px; border-radius: 10px;
  background: var(--primary); color: white;
  font-size: 13px; font-weight: 700; font-family: inherit;
  border: none; cursor: pointer; transition: all 0.2s;
}
.btn-upload-compact:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(24, 24, 24, 0.2); }














.clear-overlay {
  position: fixed;
  inset: 0;
  background: rgba(24, 20, 18, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
  padding: 20px;
}
.clear-modal {
  width: min(400px, 100%);
  background: var(--card-bg);
  border-radius: var(--radius-lg, 16px);
  padding: 26px 24px 20px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.22);
  text-align: center;
}
.clear-modal-icon {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  margin: 0 auto 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--red-light);
  color: var(--red);
}
.clear-modal h4 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
}
.clear-modal p {
  margin: 0 0 20px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-muted);
}
.clear-modal-actions {
  display: flex;
  gap: 10px;
}
.clear-modal-actions button {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 16px;
  border-radius: var(--radius-sm, 10px);
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s var(--transition);
}
.clear-cancel {
  background: var(--bg-surface, #F3F3F3);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}
.clear-cancel:hover:not(:disabled) { background: var(--border-subtle); }
.clear-confirm {
  background: var(--red);
  color: #fff;
  border: none;
}
.clear-confirm:hover:not(:disabled) { background: #A62F2A; box-shadow: 0 4px 14px rgba(194, 57, 52, 0.3); }
.clear-modal-actions button:disabled { opacity: 0.6; cursor: not-allowed; }

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .clear-modal, .modal-leave-active .clear-modal { transition: transform 0.2s ease; }
.modal-enter-from .clear-modal, .modal-leave-to .clear-modal { transform: scale(0.94); }












.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}


.compare-hint-info { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }

.commission-files-info {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 8px 16px; font-size: 12px; color: var(--text-muted);
}
.commission-file-tag {
  background: var(--bg-alt, #F3F3F3); padding: 4px 12px;
  border-radius: 6px; font-weight: 600; color: var(--text-muted);
  font-size: 11px; border: 1px solid transparent;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.commission-file-tag:hover { border-color: var(--tab-recruits); color: var(--tab-recruits-ink); }
.commission-file-tag.active {
  background: var(--tab-recruits); color: white; border-color: var(--tab-recruits);
}

.comm-uploaded-list {
  display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; justify-content: center;
}
.comm-uploaded-tag {
  background: var(--accent-emerald-bg, #EBF7EE); color: var(--accent-emerald, #2E844A);
  padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;
}
.comm-add-file-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 6px;
  border: 1px dashed var(--border, #E5E5E5); background: transparent;
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
  box-shadow: 0 2px 8px rgba(24, 24, 24, 0.1);
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

/* ── View switch: the app's gliding pill, in the portfolio's turquoise ── */
.rc-switch {
  position: relative; display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
  padding: 5px; border-radius: 16px; background: var(--card-bg);
  border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm);
  /* Always reachable while scrolling, and clear of the window's ✕ in the corner */
  position: sticky; top: 0; z-index: 5; margin-inline-end: 44px;
}
.rc-glider {
  position: absolute; top: 5px; bottom: 5px; inset-inline-start: 5px; z-index: 0; pointer-events: none;
  width: calc((100% - 22px) / 3); border-radius: 11px;
  background: var(--tab-recruits-ink);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-recruits-ink) 30%, transparent);
  transform: translateX(calc(var(--rc-i, 0) * (-100% - 6px)));
  transition: transform 0.75s cubic-bezier(0.22, 1, 0.36, 1);
}
.rc-switch-btn {
  position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 7px 12px; border: none; border-radius: 11px; background: transparent;
  font: inherit; color: var(--text-muted); cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}
.rc-switch-btn:hover:not(.active) { background: var(--tab-recruits-wash); color: var(--tab-recruits-ink); }
.rc-switch-btn.active { color: #fff; transition: color 0.4s ease 0.2s; }
.rc-switch-btn:focus-visible { outline: 2px solid var(--tab-recruits-ink); outline-offset: 2px; }
.rc-switch-title { font-size: 15px; font-weight: 700; }
.rc-switch-sub { font-size: 12px; opacity: 0.85; }

/* ── List toolbar: which list + file actions ── */
.rc-toolbar { display: flex; align-items: center; gap: 8px; }
.rc-cats { display: flex; gap: 18px; margin-inline-end: auto; }
.rc-cats button {
  position: relative; display: inline-flex; align-items: baseline; gap: 6px;
  padding: 6px 2px 8px; border: none; background: none; font: inherit;
  font-size: 14px; font-weight: 600; color: var(--text-muted); cursor: pointer;
}
.rc-cats button .ltr-number { font-weight: 500; }
.rc-cats button.on { color: var(--tab-recruits-ink); }
.rc-cats button::after {
  content: ''; position: absolute; inset-inline: 0; bottom: 0; height: 2px; border-radius: 2px;
  background: var(--tab-recruits-ink); transform: scaleX(0); transition: transform 0.3s ease;
}
.rc-cats button.on::after { transform: scaleX(1); }
.rc-icon-btn {
  display: inline-grid; place-items: center; width: 36px; height: 36px;
  border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--card-bg);
  color: var(--text-secondary); cursor: pointer; transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.rc-icon-btn:hover { border-color: var(--tab-recruits); color: var(--tab-recruits-ink); }
.rc-icon-btn--danger:hover { border-color: var(--red); color: var(--red); background: var(--red-light); }

/* ── Before a check: one card ── */
.rc-run {
  position: relative; z-index: 1;
  display: flex; align-items: center; gap: 16px;
  padding: 20px 22px; background: var(--card-bg);
  border: 1px solid var(--border-subtle); border-radius: 14px; box-shadow: var(--shadow-sm);
}
.rc-run-ico { flex-shrink: 0; color: var(--tab-recruits-ink); }
.rc-run-ico > * { stroke-dasharray: 1; stroke-dashoffset: 1; animation: rcDraw 1.2s cubic-bezier(0.65, 0, 0.35, 1) 0.2s forwards; }
.rc-run-ico > *:nth-child(2) { animation-delay: 0.45s; }
.rc-run-ico > *:nth-child(3) { animation-delay: 0.7s; }
@keyframes rcDraw { to { stroke-dashoffset: 0; } }
.rc-run-copy { flex: 1; min-width: 0; }
.rc-run-copy h4 { margin: 0 0 4px; font-size: 16px; font-weight: 800; color: var(--text); }
.rc-run-copy p { margin: 0; font-size: 13px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc-run-file { color: var(--text-secondary); font-weight: 600; }
.rc-run-btn {
  flex-shrink: 0; display: inline-flex; align-items: center; gap: 8px;
  padding: 11px 26px; border: none; border-radius: 10px;
  background: var(--tab-recruits-ink); color: #fff; font: inherit; font-size: 14.5px; font-weight: 700; cursor: pointer;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-recruits-ink) 30%, transparent);
  transition: transform 0.15s ease;
}
.rc-run-btn:hover:not(:disabled) { transform: translateY(-1px); }
.rc-run-btn:disabled { opacity: 0.5; cursor: default; }

@media (max-width: 640px) {
  .rc-switch-sub { display: none; }
  .rc-run { flex-wrap: wrap; }
  .rc-run-btn { width: 100%; justify-content: center; }
}
@media (prefers-reduced-motion: reduce) {
  .rc-glider, .rc-switch-btn { transition: none; }
  .rc-run-ico > * { animation: none; stroke-dashoffset: 0; }
}

/* נפרעים: which company's file — text tabs, like every filter in the app */
.commission-files-info {
  display: flex !important; flex-wrap: wrap; align-items: center; gap: 4px 18px !important;
  padding: 0 !important; background: none !important; border: none !important;
  border-bottom: 1px solid var(--border-subtle) !important; border-radius: 0 !important;
}
.commission-file-tag {
  position: relative; padding: 6px 2px 9px !important; border: none !important; border-radius: 0 !important;
  background: none !important; box-shadow: none !important;
  font: inherit; font-size: 13.5px !important; font-weight: 600 !important; color: var(--text-muted) !important; cursor: pointer;
}
.commission-file-tag.active { color: var(--tab-recruits-ink) !important; }
.commission-file-tag::after {
  content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px; border-radius: 2px;
  background: var(--tab-recruits-ink); transform: scaleX(0); transition: transform 0.3s ease;
}
.commission-file-tag.active::after { transform: scaleX(1); }
.comm-add-file-btn { margin-inline-start: auto; }

/* The list's header bar: which list + file actions, joined to the list card below */
.rc-toolbar {
  padding: 8px 12px 0 8px; background: var(--card-bg);
  border: 1px solid var(--border-subtle); border-bottom: none;
  border-radius: 14px 14px 0 0; box-shadow: var(--shadow-sm);
  position: relative; z-index: 1;
}
.rc-cats { align-self: stretch; align-items: flex-end; }
.rc-cats button { padding: 10px 4px 12px; font-size: 14.5px; }
.rc-toolbar .rc-icon-btn { width: 34px; height: 34px; margin-bottom: 6px; border-color: transparent; background: var(--bg); }
.rc-toolbar + div { margin-top: -12px; }
.rc-toolbar + div :deep(.recruit-form) { border-radius: 0 0 14px 14px; border-top: 1px solid var(--border-subtle); }
</style>
