<template>
  <div ref="tabRoot" class="production-tab" :class="{ 'production-tab--stage': backdropVariant, 'production-tab--band': bandH }">
    <!-- תובנות: one hero panel behind the section bar + the KPI row, so they
         read as one header block. Sized to the KPI row's bottom (it wraps). -->
    <div v-if="bandH" class="pt-band" :style="{ height: bandH + 'px' }" aria-hidden="true"></div>
    <!-- Big faint animated backdrop behind the sub-screens (not תובנות). -->
    <ProdBackdrop v-if="backdropVariant" :variant="backdropVariant" />
    <!-- Monthly cycle: before the agent's first cycle only THIS tab is locked. -->
    <CycleLockedState
      v-if="cycleStore.locked"
      @go-to-portal-automation="$emit('go-to-portal-automation')"
      @go-to-maslaka="$emit('go-to-maslaka')"
    />

    <div v-else-if="productionStore.loading || !productionStore.currentLoaded" class="loading-state">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span>טוען...</span>
    </div>

    <template v-else>
      <!-- Monthly cycle: the cycle's נפרעים are in and production is still
           manual (no מסלקה feed yet) → ask for THIS period's production. -->
      <div v-if="cycleStore.status?.needs_production_upload && productionStore.currentFile" class="cy-banner" role="status">
        <span class="cy-banner-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>
        </span>
        <div class="cy-banner-text">
          <strong>הנפרעים של {{ cycleStore.status.current_period_label }} כבר כאן</strong>
          <span>העלה/י את קובץ הפרודוקציה של {{ cycleStore.status.current_period_label }} (מאתר המסלקה) — וההשוואה תרוץ לבד.</span>
        </div>
        <button type="button" class="cy-banner-btn" @click="openFilePicker">העלאת פרודוקציה</button>
      </div>
      <div v-if="uploadError" class="cy-error" role="alert">
        <span>{{ uploadError }}</span>
        <button type="button" class="cy-error-x" aria-label="סגור" @click="uploadError = ''">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>

      <!-- No production yet: the tab's identity hero + one extra-big door to
           the automation (which is what fills this screen), on its own stage.
           Manual upload stays as a small action in the hero; a file dropped
           anywhere on the page uploads too. -->
      <section v-if="!productionStore.currentFile" class="pt-empty">
        <header class="pt-hero">
          <div class="pt-hero-copy">
            <span class="pt-kicker">פרודוקציה</span>
            <h2 class="pt-hero-title"><span dir="ltr">Nifraim</span> <span class="pt-hero-title-acc">פרודוקציה</span></h2>
            <button v-if="canUpload" type="button" class="pt-manual" @click="openFilePicker">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2"
                   stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="m21 11-8.5 8.5a5 5 0 0 1-7-7L14 4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L15 7" />
              </svg>
              העלאה ידנית
            </button>
          </div>
          <TabHeroLoop scene="production" flow="ltr" class="pt-hero-art" />
        </header>

        <!-- The stage follows the monthly cycle: what to do NOW (upload the
             period's production, wait for the computer, watch the download,
             or simply the next 21st). Before launch: the legacy door. -->
        <div class="pt-stage">
          <div class="pt-cta">
            <BigAddButton
              :label="emptyCta.label"
              color="var(--tab-production)"
              :size="250"
              @click="onEmptyCta"
            >
              <svg v-if="emptyCta.icon === 'upload'" viewBox="0 0 24 24" width="84" height="84" fill="none" stroke="currentColor"
                   stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m17 8-5-5-5 5" /><path d="M12 3v12" />
              </svg>
              <svg v-else-if="emptyCta.icon === 'clock'" viewBox="0 0 24 24" width="84" height="84" fill="none" stroke="currentColor"
                   stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="13" r="8" /><path d="M12 9v4l2 2" /><path d="M5 3 2 6" /><path d="m22 6-3-3" />
              </svg>
              <svg v-else-if="emptyCta.icon === 'monitor'" viewBox="0 0 24 24" width="84" height="84" fill="none" stroke="currentColor"
                   stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="2" y="3" width="20" height="14" rx="2" /><path d="M8 21h8M12 17v4" />
              </svg>
              <AppIcon v-else name="portal-automation" :size="84" />
            </BigAddButton>
            <!-- First-run hint: a hand glides in from the screen's bottom-right
                 and taps the ring. Only on this empty state. -->
            <PointingHand from="bottom-right" color="var(--tab-production)" />
          </div>
          <!-- The cycle's נפרעים are in → one clear ask: this month's production. -->
          <div v-if="emptyCta.action === 'upload' && uploadFlow" class="pt-ready">
            <span class="pt-ready-chip">
              <span class="pt-ready-dot" aria-hidden="true"></span>
              ההורדה של <span class="ltr-number">{{ uploadFlow.cycleDay }}</span> הסתיימה
            </span>
            <h3 class="pt-ready-title">
              הנפרעים של <span class="pt-ready-acc">{{ uploadFlow.month }}</span> כבר כאן
            </h3>
            <ol class="pt-flow" aria-label="מה נשאר">
              <li class="pt-flow-step is-done">
                <span class="pt-flow-ic" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                </span>
                <span class="pt-flow-label">נפרעים</span>
                <span class="pt-flow-sub">הורדו אוטומטית</span>
              </li>
              <li class="pt-flow-line" aria-hidden="true"></li>
              <li class="pt-flow-step is-now">
                <span class="pt-flow-ic" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>
                </span>
                <span class="pt-flow-label">פרודוקציה</span>
                <span class="pt-flow-sub">מאתר המסלקה</span>
              </li>
              <li class="pt-flow-line" aria-hidden="true"></li>
              <li class="pt-flow-step">
                <span class="pt-flow-ic" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/></svg>
                </span>
                <span class="pt-flow-label">השוואה</span>
                <span class="pt-flow-sub">רצה לבד</span>
              </li>
            </ol>
          </div>
          <div v-else-if="emptyCta.title" class="pt-cta-copy">
            <strong>{{ emptyCta.title }}</strong>
            <span>{{ emptyCta.note }}</span>
            <!-- The ring's label was only a hover tooltip; the action is now
                 a real, visible button — plus manual upload beside it. -->
            <div class="pt-cta-actions">
              <button type="button" class="pt-cta-btn" @click="onEmptyCta">{{ emptyCta.label }}</button>
              <button v-if="canUpload && emptyCta.action !== 'upload'" type="button"
                      class="pt-cta-btn pt-cta-btn--ghost" @click="openFilePicker">העלאת קובץ ידנית</button>
            </div>
          </div>
        </div>
      </section>

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

          <!-- A מסלקה book mixes months: a breathing icon beside the file says
               which company is on which month; hover or focus opens the lines
               (kiko 2026-10-10: September for 4 companies, the rest July). -->
          <button v-if="bookMonths.length" ref="bmIconEl" type="button" class="bm-icon"
                  :aria-expanded="bmOpen" aria-label="איזה חודש לכל חברה"
                  @mouseenter="openBm" @mouseleave="bmOpen = false" @focus="openBm" @blur="bmOpen = false"
                  @click="bmOpen ? (bmOpen = false) : openBm()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3" y="4" width="18" height="17" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />
              <path d="M12 14v3l2 1" />
            </svg>
            <span class="bm-dot" aria-hidden="true"></span>
          </button>
          <!-- At page level so the KPI cards below can never cover it. -->
          <Teleport to="body">
            <Transition name="bm-pop">
              <div v-if="bmOpen && bookMonths.length" class="bm-pop" role="tooltip" :style="bmStyle">
                <span v-for="(line, i) in bookMonths" :key="i" class="bm-line"
                      :class="{ 'bm-line-head': i === 0 }" :style="{ '--i': i }">{{ line }}</span>
              </div>
            </Transition>
          </Teleport>

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
            v-if="canUpload"
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
          <!-- Upload closed for this cycle (מסלקה delivers it, or the cycle's
               download hasn't ended): the upload shrinks to a small status
               icon; hover/focus says why. -->
          <span
            v-else-if="uploadGateNote"
            class="gate-icon"
            tabindex="0"
            role="img"
            :aria-label="uploadGateNote"
          >
            <svg v-if="cycleStore.status?.production_source === 'maslaka'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M3 22h18"/><path d="M6 18v-7"/><path d="M10 18v-7"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="m12 2 8 5H4z"/>
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
            </svg>
            <span class="gate-tip" role="tooltip">{{ uploadGateNote }}</span>
          </span>
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
            @go-to-automation="$emit('go-to-portal-automation')"
            @navigate="$emit('navigate', $event)"
          />
        </div>

        <!-- Tab content: Comparison -->
        <div v-if="innerTab === 'comparison'">
          <ProductionComparison
            :history="productionStore.history"
            :comparisonResult="productionStore.comparisonResult"
            :comparing="productionStore.comparing"
            :currentFileId="productionStore.currentFile.id"
            :currentFile="productionStore.currentFile"
            @compare="handleCompare"
            @reset="productionStore.resetComparison()"
          />
        </div>

        <!-- Tab content: Volume -->
        <div v-if="innerTab === 'volume'">
          <VolumeComparison />
        </div>

        <!-- Tab content: History (production files by month) -->
        <div v-if="innerTab === 'history'" class="history-panel">
          <ProdSectionHero
            kicker="היסטוריה"
            title="כל קובץ,"
            accent="לפי חודש"
            line="כל קובץ פרודוקציה שהעליתם או שהורד אוטומטית — מסודר לפי החודש שהוא מתאר."
            scene="prod-history"
          />
          <p v-if="!historyByMonth.length" class="history-empty">עוד אין קבצי פרודוקציה.</p>

          <div v-if="historyByMonth.length" class="history-timeline">
          <section
            v-for="(grp, gi) in historyByMonth"
            :key="grp.key"
            class="month-group"
            :class="{ 'is-latest': gi === 0 }"
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
                :class="{ 'is-current': productionStore.currentFile && f.id === productionStore.currentFile.id }"
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
                    <div class="hf-name" :title="f.filename">
                      {{ f.filename }}
                      <span v-if="productionStore.currentFile && f.id === productionStore.currentFile.id" class="hf-live">פעיל</span>
                    </div>
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
import { computed, reactive, ref, onMounted, onBeforeUnmount, nextTick, watch, inject } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import { useVolumeStore } from '../../stores/volume.js'
import ProductionDashboard from './ProductionDashboard.vue'
import ProductionComparison from './ProductionComparison.vue'
import VolumeComparison from './VolumeComparison.vue'
import ProductionTrendChart from './ProductionTrendChart.vue'
import TabHeroLoop from './TabHeroLoop.vue'
import BigAddButton from './BigAddButton.vue'
import AppIcon from '../icons/AppIcon.vue'
import PointingHand from './PointingHand.vue'
import { relativeHebrew } from '../../utils/relativeTime.js'
import CycleLockedState from './CycleLockedState.vue'
import ProdSectionHero from './ProdSectionHero.vue'
import ProdBackdrop from './ProdBackdrop.vue'
import { useCycleStore, bookMonthsLines } from '../../stores/cycle.js'
import { useAuthStore } from '../../stores/auth.js'

const emit = defineEmits(['go-to-comparison', 'go-to-portal-automation', 'go-to-maslaka', 'navigate'])

const productionStore = useProductionStore()
const volumeStore = useVolumeStore()
const cycleStore = useCycleStore()
const bmIconEl = ref(null)
const bmOpen = ref(false)
const bmStyle = ref({})
// Under the icon, its left edge on the icon's, kept on screen.
function openBm() {
  const r = bmIconEl.value?.getBoundingClientRect()
  if (!r) return
  const width = Math.min(460, window.innerWidth - 32)
  const left = Math.max(16, Math.min(r.left, window.innerWidth - width - 16))
  bmStyle.value = { top: `${r.bottom + 10}px`, left: `${left}px`, width: `${width}px`,
                    '--ox': `${r.left + r.width / 2 - left}px` }
  bmOpen.value = true
}
const bookMonths = computed(() => bookMonthsLines(productionStore.currentFile?.company_months,
  productionStore.currentFile?.company_families))
const auth = useAuthStore()

// Monthly cycle: manual production is accepted only in the cycle's window
// (the server enforces it; this only hides dead buttons). Unknown status →
// show the buttons and let the server answer.
const canUpload = computed(() =>
  !cycleStore.loaded || !cycleStore.status || cycleStore.manualUploadOpen || !!auth.user?.is_admin,
)
const uploadGateNote = computed(() => {
  const st = cycleStore.status
  if (!st || st.locked || st.prelaunch || canUpload.value) return ''
  if (st.production_source === 'maslaka') return `הפרודוקציה של ${st.current_period_label} מגיעה אוטומטית מהמסלקה ב-15 לחודש — אין צורך להעלות ידנית`
  return 'העלאת הפרודוקציה תיפתח בסיום ההורדה האוטומטית של המחזור'
})
const uploadError = ref('')

// Empty-state call, per cycle state (see the template comment).
const emptyCta = computed(() => {
  const st = cycleStore.status
  // Every state says what happens and what to press. The pre-launch state
  // had no title or note, so the stage showed a lone icon (QA 2026-09-30).
  const legacy = {
    label: 'מעבר להורדה אוטומטית', icon: 'automation', action: 'automation',
    title: 'עוד אין כאן פרודוקציה',
    note: 'חברו את ההורדה האוטומטית מהחברות — והפרודוקציה תגיע לכאן לבד. אפשר גם להעלות קובץ ידנית.',
  }
  if (!st || st.prelaunch) return legacy
  const period = st.current_period_label
  if (st.manual_upload_open) {
    return {
      label: `העלאת פרודוקציה ל${period}`, icon: 'upload', action: 'upload',
      title: `הנפרעים של ${period} כבר כאן`,
      note: `העלה/י את קובץ הפרודוקציה של ${period} (מאתר המסלקה) — וההשוואה תרוץ לבד.`,
    }
  }
  if (st.worker_waiting) {
    return {
      label: 'למצב המחשב', icon: 'monitor', action: 'automation',
      title: `המחזור של ${period} ממתין למחשב`,
      note: 'ההורדה תתחיל לבד ברגע שהמחשב יודלק ויתחבר. אחריה תיפתח כאן העלאת הפרודוקציה.',
    }
  }
  if (['pending', 'running'].includes(st.cycle_batch_status)) {
    return {
      label: 'לצפייה בהורדה', icon: 'automation', action: 'automation',
      title: `הנפרעים של ${period} יורדים עכשיו`,
      note: 'בסיום ההורדה תיפתח כאן העלאת הפרודוקציה של החודש.',
    }
  }
  if (st.production_source === 'maslaka') {
    return {
      label: 'למסלקה', icon: 'clock', action: 'maslaka',
      title: 'הפרודוקציה מגיעה אוטומטית מהמסלקה',
      note: `הפרודוקציה של ${period} נשלחת מהמסלקה ב-15 בחודש — אין צורך להעלות דבר.`,
    }
  }
  const next = st.next_cycle_at ? new Date(st.next_cycle_at) : null
  return {
    label: 'מעבר לאוטומציה', icon: 'clock', action: 'automation',
    title: next ? `הנפרעים יורדים לבד ב-${next.getDate()}.${next.getMonth() + 1} · 06:00` : 'הנפרעים יורדים לבד ב-21 לחודש',
    note: 'אין צורך ללחוץ על כלום — רק שהמחשב יהיה דלוק.',
  }
})
// "Upload" state details: the period month and the day its cycle ran (string
// math on the ISO date — no Date/time-zone drift).
const uploadFlow = computed(() => {
  const p = cycleStore.status?.current_period
  if (!p) return null
  const [, m] = p.split('-').map(Number)
  return { month: cycleStore.status.current_period_label, cycleDay: `21.${(m % 12) + 1}` }
})
function onEmptyCta() {
  const a = emptyCta.value.action
  if (a === 'upload') openFilePicker()
  else if (a === 'maslaka') emit('go-to-maslaka')
  else emit('go-to-portal-automation')
}
const innerTab = ref('insights')
// ── תובנות header band: measure down to the KPI row's bottom ──
const tabRoot = ref(null)
const bandH = ref(0)
let bandRO = null
function measureBand() {
  const root = tabRoot.value
  const kpi = root?.querySelector('.kpi-row')
  if (!root || !kpi || innerTab.value !== 'insights') { bandH.value = 0; return }
  bandH.value = Math.round(kpi.getBoundingClientRect().bottom - root.getBoundingClientRect().top) + 16
}
onMounted(() => {
  if (typeof ResizeObserver !== 'undefined' && tabRoot.value) {
    bandRO = new ResizeObserver(() => measureBand())
    bandRO.observe(tabRoot.value)
  }
})
onBeforeUnmount(() => bandRO?.disconnect())
watch(() => [innerTab.value, productionStore.analytics, productionStore.currentFile], () => {
  nextTick(measureBand); setTimeout(measureBand, 300)
})
const backdropVariant = computed(() => {
  if (!productionStore.currentFile || cycleStore.locked) return null
  return { comparison: 'compare', volume: 'volume', history: 'history' }[innerTab.value] || null
})
const fileInputRef = ref(null)
const showCompareModal = ref(false)
const previousFile = ref(null)
onMounted(() => {
  productionStore.fetchCurrent()
})

// When file loads, fetch analytics. When it's absent, fetch the landing data
// so the sage hero hydrates immediately on first paint. Only once
// /production/current has answered — before that a null file is unknown, not
// absent, and fetching /landing for an agent who has a file is wasted work.
watch(() => [productionStore.currentLoaded, productionStore.currentFile], ([loaded, file]) => {
  if (!loaded) return
  if (file) {
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
    // Group by the reporting month the file is FOR (period_month) when the
    // backend detected one; fall back to when it was uploaded.
    const k = monthKey(f.period_month || f.uploaded_at)
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

// A file dropped anywhere on the page (WorkspaceView's overlay) uploads here
// too — the empty state has no drop zone of its own.
const droppedFiles = inject('droppedFiles', null)
if (droppedFiles) {
  watch(droppedFiles, (val) => {
    if (val?.length) onFileSelected({ target: { files: val } })
  })
}

async function onFileSelected(e) {
  const files = e.target.files
  const file = files && files.length > 0 ? files[0] : null
  if (e.target) e.target.value = ''
  if (!file) return
  if (!canUpload.value) {
    uploadError.value = uploadGateNote.value || 'העלאת פרודוקציה אינה זמינה כרגע'
    return
  }
  uploadError.value = ''
  const ext = file.name.split('.').pop().toLowerCase()
  try {
    if (ext === 'xlsx' || ext === 'xls') {
      await productionStore.uploadProduction(file)
    } else if (ext === 'zip') {
      // ZIP path goes through the generic /api/uploads endpoint so the
      // server-side Mimshak detection + production classification fires.
      await productionStore.uploadProductionZip(file)
    } else {
      return
    }
    cycleStore.fetchStatus()
  } catch (_) {
    uploadError.value = productionStore.error || 'שגיאה בהעלאת הקובץ'
  }
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
/* ── Monthly cycle banners ── */
.cy-banner {
  display: flex; align-items: center; gap: 14px; padding: 16px 18px;
  background: var(--card-bg); border: 1px solid color-mix(in srgb, var(--tab-production) 35%, transparent);
  border-radius: var(--radius-md, 14px); box-shadow: var(--shadow-sm);
}
.cy-banner-icon {
  flex-shrink: 0; width: 42px; height: 42px; border-radius: 12px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--tab-production-wash); color: var(--tab-production);
}
.cy-banner-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.cy-banner-text strong { font-size: 15px; font-weight: 800; color: var(--text-primary, #181818); }
.cy-banner-text span { font-size: 13.5px; line-height: 1.6; color: var(--text-secondary, #706E6B); }
.cy-banner-btn {
  flex-shrink: 0; height: 40px; padding: 0 18px; border: none; border-radius: 10px;
  background: var(--tab-production); color: #fff; font-family: inherit; font-size: 14px; font-weight: 700;
  cursor: pointer; box-shadow: 0 4px 12px rgba(47, 115, 196, 0.25); transition: transform 0.15s ease;
}
.cy-banner-btn:hover { transform: translateY(-1px); }
@media (max-width: 640px) { .cy-banner { flex-wrap: wrap; } .cy-banner-btn { width: 100%; } }
.cy-error {
  display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 10px;
  background: rgba(234, 0, 30, 0.06); border: 1px solid rgba(234, 0, 30, 0.22);
  color: var(--red-deep, #b91c1c); font-size: 13.5px; font-weight: 600;
}
.cy-error span { flex: 1; }
.cy-error-x { border: none; background: transparent; color: inherit; cursor: pointer; display: inline-flex; padding: 4px; }

.production-tab {
  position: relative;
  animation: slideUp 0.4s var(--transition);
  display: flex;
  flex-direction: column;
  gap: 20px;
}
/* sub-screens with the backdrop fill the viewport; content sits above it */
.production-tab--stage { min-height: calc(100vh - 110px); }
.production-tab > :not(.pbd):not(.pt-band) { position: relative; z-index: 1; }
/* the תובנות header panel behind the section bar + KPIs */
.pt-band {
  position: absolute; z-index: 0; top: 0; inset-inline: 0;
  border-radius: 22px; pointer-events: none;
  border: 1px solid var(--border-subtle);
  background: var(--card-bg, #FFFFFF);
  box-shadow: 0 10px 30px rgba(24, 24, 24, 0.06);
}
/* the bar and the KPI row sit INSIDE the panel, with room to breathe */
.production-tab--band > .inner-tabs-bar { margin: 18px 22px 0; }
.production-tab--band :deep(.kpi-row) { margin: -4px 22px 12px; } /* the panel ends 16px under the KPIs; the next card starts 16px after it (was -8px: overlapped by 4px) */
@media (max-width: 640px) {
  .production-tab--band > .inner-tabs-bar { margin: 12px 12px 0; }
  .production-tab--band :deep(.kpi-row) { margin-inline: 12px; }
}

/* ── Empty state: hero + stage (same shape as השוואת נפרעים) ─────── */
.pt-empty { display: flex; flex-direction: column; gap: 18px; }
.pt-hero {
  position: relative; overflow: hidden; display: flex; align-items: center; min-height: 170px;
  padding: 22px 26px; background: var(--card-bg);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
}
.pt-hero::before {
  content: ''; position: absolute; inset-inline-end: -6%; top: -60%; width: 44%; height: 220%;
  background: radial-gradient(circle, var(--tab-production-wash), transparent 70%); pointer-events: none;
}
.pt-hero-copy { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 8px; max-width: 58%; }
.pt-kicker {
  align-self: flex-start; padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 800;
  background: var(--tab-production-wash); color: var(--tab-production);
}
.pt-hero-title {
  margin: 2px 0 0; font-family: 'Rubik', 'Heebo', sans-serif;
  font-size: clamp(28px, 3.3vw, 40px); font-weight: 700; letter-spacing: -0.03em; line-height: 1.05; color: var(--text);
}
.pt-hero-title-acc { color: var(--tab-production); }
.pt-manual {
  align-self: flex-start; display: inline-flex; align-items: center; gap: 7px; margin-top: 4px;
  height: 34px; padding: 0 14px; border-radius: 999px; cursor: pointer;
  font-family: inherit; font-size: 13px; font-weight: 700; color: var(--tab-production);
  background: var(--card-bg); border: 1px solid color-mix(in srgb, var(--tab-production) 35%, transparent);
}
.pt-manual:hover { background: var(--tab-production-wash); }
.pt-manual:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
.pt-hero-art {
  position: absolute; inset-inline-end: 4px; top: 50%; transform: translateY(-50%);
  width: min(330px, 40%); aspect-ratio: 420 / 300; pointer-events: none;
}
/* The stage the big ring sits on: a soft glow in the tab colour over a faint
   dot grid, so the button reads as the one thing on the screen. */
.pt-stage {
  display: grid; place-items: center; min-height: 380px; padding: 30px;
  color: var(--tab-production);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 50% 50%, color-mix(in srgb, var(--tab-production) 16%, transparent) 0, transparent 46%),
    radial-gradient(color-mix(in srgb, var(--tab-production) 16%, transparent) 1.2px, transparent 1.4px) 0 0 / 22px 22px,
    var(--card-bg);
}
.pt-stage { grid-auto-flow: row; gap: 22px; align-content: center; }
.pt-cta { position: relative; display: grid; place-items: center; }
.pt-cta-copy { display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; max-width: 440px; }
.pt-cta-copy strong { font-size: 19px; font-weight: 800; color: var(--text-primary, #181818); }
.pt-cta-copy span { font-size: 14px; line-height: 1.6; color: var(--text-secondary, #706E6B); }
.pt-cta-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 12px; }
.pt-cta-btn {
  border: none; border-radius: 10px; padding: 11px 20px; font: inherit; font-size: 14px; font-weight: 700;
  background: var(--tab-production); color: #fff; cursor: pointer;
  box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-production) 28%, transparent);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.pt-cta-btn:hover { transform: translateY(-1px); }
.pt-cta-btn:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
.pt-cta-btn--ghost {
  background: var(--card-bg); color: var(--tab-production); box-shadow: none;
  border: 1px solid color-mix(in srgb, var(--tab-production) 40%, var(--border-subtle));
}
@media (prefers-reduced-motion: reduce) { .pt-cta-btn { transition: none; } }
/* Cycle "upload" state: chip → two-tone title → 3-step flow */
.pt-ready { display: flex; flex-direction: column; align-items: center; gap: 14px; text-align: center; }
.pt-ready-chip {
  display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px;
  background: var(--card-bg); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm);
  color: var(--text-secondary, #706E6B); font-size: 13px; font-weight: 600;
}
.pt-ready-dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--green);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--green) 18%, transparent);
}
.pt-ready-title {
  margin: 0; font-size: clamp(24px, 2.6vw, 32px); font-weight: 900; letter-spacing: -0.03em; line-height: 1.15;
  text-wrap: balance;
  color: var(--text-primary, #181818);
}
.pt-ready-acc { color: var(--tab-production); }
.pt-flow {
  list-style: none; margin: 6px 0 0; padding: 0;
  display: flex; align-items: flex-start; justify-content: center; gap: 10px;
}
.pt-flow-step { display: flex; flex-direction: column; align-items: center; gap: 4px; width: 104px; }
.pt-flow-ic {
  width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center;
  background: var(--card-bg); border: 1.5px solid var(--border-subtle); color: var(--text-muted, #939393);
}
.pt-flow-step.is-done .pt-flow-ic { background: var(--green); border-color: var(--green); color: #fff; }
.pt-flow-step.is-now .pt-flow-ic {
  background: var(--tab-production); border-color: var(--tab-production); color: #fff;
  animation: ptFlowPulse 2.2s ease-in-out infinite;
}
.pt-flow-label { font-size: 14px; font-weight: 800; color: var(--text-primary, #181818); }
.pt-flow-step:not(.is-done):not(.is-now) .pt-flow-label { color: var(--text-secondary, #706E6B); }
.pt-flow-sub { font-size: 12px; color: var(--text-secondary, #706E6B); }
.pt-flow-line {
  flex: 0 0 44px; height: 0; margin-top: 20px;
  border-top: 2px dashed color-mix(in srgb, var(--tab-production) 35%, transparent);
}
@keyframes ptFlowPulse {
  0%, 100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--tab-production) 35%, transparent); }
  50% { box-shadow: 0 0 0 8px color-mix(in srgb, var(--tab-production) 0%, transparent); }
}
@media (prefers-reduced-motion: reduce) { .pt-flow-step.is-now .pt-flow-ic { animation: none; } }
@media (max-width: 480px) {
  .pt-flow { gap: 4px; }
  .pt-flow-step { width: 84px; }
  .pt-flow-line { flex-basis: 18px; }
}
@media (max-width: 640px) {
  .pt-hero-art { display: none; }
  .pt-hero-copy { max-width: none; }
  .pt-stage { min-height: 300px; }
}

/* ── History panel (production by month) ───────────────────────────── */
.history-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0 24px;
}
.history-empty { margin: 0; text-align: center; padding: 24px 16px; font-size: 14px; font-weight: 600; color: var(--text-secondary, #706E6B); }

/* month timeline: a rail on the start side, one node per month */
.history-timeline { position: relative; display: flex; flex-direction: column; gap: 12px; padding-inline-start: 30px; }
.history-timeline::before {
  content: ''; position: absolute; inset-inline-start: 9px; top: 18px; bottom: 18px; width: 2px;
  background: linear-gradient(180deg, var(--tab-production), color-mix(in srgb, var(--tab-production) 12%, transparent));
  border-radius: 2px;
}
.month-group { position: relative; box-shadow: var(--shadow-sm); }
.month-group::before {
  content: ''; position: absolute; inset-inline-start: -27px; top: 16px; width: 14px; height: 14px; border-radius: 50%;
  background: var(--card-bg); border: 3px solid color-mix(in srgb, var(--tab-production) 45%, transparent);
}
.month-group.is-latest::before { background: var(--tab-production); border-color: color-mix(in srgb, var(--tab-production) 30%, var(--card-bg)); box-shadow: 0 0 0 4px var(--tab-production-wash); }
.hf-live {
  display: inline-flex; align-items: center; margin-inline-start: 8px; padding: 1px 8px; border-radius: 999px;
  font-size: 11px; font-weight: 800; color: var(--green); background: color-mix(in srgb, var(--green) 12%, transparent);
  vertical-align: 1px;
}
.hist-file.is-current { background: color-mix(in srgb, var(--tab-production) 4%, transparent); }

.month-group {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
}
.month-group > .month-head { border-radius: 14px 14px 0 0; }
.month-group > .month-head.is-collapsed { border-radius: 14px; }
.month-group .month-files { border-radius: 0 0 14px 14px; overflow: hidden; }
.month-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  background: linear-gradient(180deg, rgba(47, 115, 196, 0.04), rgba(47, 115, 196, 0.01));
  transition: background 0.15s;
}
.month-head:hover { background: rgba(47, 115, 196, 0.07); }
.month-chevron {
  color: var(--tab-production);
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
  color: var(--primary-deep);
  background: rgba(47, 115, 196, 0.10);
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
.hist-file:hover { background: rgba(47, 115, 196, 0.03); }
.hf-main { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.hf-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(47, 115, 196, 0.12), rgba(47, 115, 196, 0.06));
  color: var(--primary-deep);
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
.hf-time { color: var(--primary-deep); font-weight: 600; }
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
  background: rgba(47, 115, 196, 0.12);
  color: var(--primary-deep);
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
  gap: 10px;
  flex-wrap: wrap;
}
/* Off the תובנות band, the bar is ONE card: segments, file and upload
   together (it used to float as three separate pills over the backdrop). */
.production-tab:not(.production-tab--band) .inner-tabs-bar {
  padding: 6px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
}
.production-tab:not(.production-tab--band) .inner-tabs {
  padding: 0; border: none; box-shadow: none; background: none;
}
.production-tab:not(.production-tab--band) .file-pill {
  background: var(--bg); border-color: transparent; box-shadow: none;
}
.production-tab:not(.production-tab--band) .upload-icon-btn { box-shadow: none; }

/* segmented control: white card, the active section filled in the tab colour */
.inner-tabs {
  display: flex;
  gap: 4px;
  padding: 5px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
  scrollbar-width: none;
}
.inner-tab { flex-shrink: 0; }

.inner-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 38px;
  padding: 0 16px;
  font-size: 13.5px;
  font-weight: 700;
  font-family: inherit;
  color: var(--text-secondary, #706E6B);
  background: transparent;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
  white-space: nowrap;
}

.inner-tab:hover { color: var(--tab-production); background: var(--tab-production-wash); }
.inner-tab:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 1px; }

.inner-tab.active {
  color: #fff;
  background: var(--tab-production);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-production) 30%, transparent);
}

.inner-tab svg { opacity: 0.7; }
.inner-tab.active svg { opacity: 1; color: #fff; }
.inner-tab.active .tab-dot { background: #fff; box-shadow: none; }

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
  height: 38px;
  padding: 0 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  box-shadow: var(--shadow-sm);
  font-size: 12.5px;
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
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card-bg);
  color: var(--tab-production);
  border: 1px solid color-mix(in srgb, var(--tab-production) 30%, transparent);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
  flex-shrink: 0;
}

.upload-icon-btn:hover {
  background: var(--tab-production);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-production) 30%, transparent);
}
.upload-icon-btn:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }

/* Upload closed this cycle → small status icon + tooltip */
.gate-icon {
  position: relative; width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; cursor: help;
  background: var(--tab-production-wash); color: var(--tab-production);
  border: 1.5px solid rgba(47, 115, 196, 0.18);
}
.gate-icon:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
.gate-tip {
  position: absolute; top: calc(100% + 8px); inset-inline-end: 0; z-index: 20;
  width: max-content; max-width: min(260px, 46vw); padding: 8px 12px; border-radius: 10px;
  background: var(--primary, #181818); color: #fff; font-size: 12.5px; font-weight: 600; line-height: 1.5;
  box-shadow: var(--shadow-md, 0 6px 18px rgba(0, 0, 0, 0.18));
  opacity: 0; transform: translateY(-4px); pointer-events: none; transition: opacity 0.15s ease, transform 0.15s ease;
}
.gate-icon:hover .gate-tip, .gate-icon:focus-visible .gate-tip { opacity: 1; transform: none; }

/* Uploading banner */
.bm-icon {
  position: relative; width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; padding: 0;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  background: var(--tab-production); color: #fff; border: none; font: inherit;
  animation: bmBreath 2.2s ease-in-out infinite;
}
/* a small dot in the corner: "something here is new" */
.bm-dot {
  position: absolute; top: 1px; inset-inline-end: 1px; width: 10px; height: 10px; border-radius: 50%;
  background: var(--red); box-shadow: 0 0 0 2px var(--card-bg);
}
.bm-icon:hover, .bm-icon:focus-visible { animation-play-state: paused; }
.bm-icon:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
@keyframes bmBreath {
  0%, 100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--tab-production) 45%, transparent); transform: scale(1); }
  50% { box-shadow: 0 0 0 9px color-mix(in srgb, var(--tab-production) 0%, transparent); transform: scale(1.06); }
}
@media (prefers-reduced-motion: reduce) { .bm-icon { animation: none; } }

.uploading-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  background: var(--green-light);
  border: 1px solid rgba(46, 132, 74, 0.15);
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
  box-shadow: 0 6px 20px rgba(24, 24, 24, 0.25);
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

<style>
/* ProductionTab's month card — teleported to <body>, so unscoped. */
.bm-pop {
  position: fixed; z-index: 1500; box-sizing: border-box;
  display: flex; flex-direction: column; gap: 5px; padding: 12px 16px; direction: rtl; text-align: start;
  background: var(--card-bg); color: var(--text-secondary); font-family: inherit; font-size: 12.5px; line-height: 1.55;
  border: 1px solid color-mix(in srgb, var(--tab-production) 30%, transparent); border-radius: 14px;
  box-shadow: 0 14px 34px color-mix(in srgb, var(--tab-production) 22%, rgba(0, 0, 0, 0.12));
  transform-origin: var(--ox, 20px) top;
}
.bm-line-head {
  color: var(--tab-production); font-weight: 700; font-size: 13px;
  padding-bottom: 6px; margin-bottom: 2px; border-bottom: 1px solid var(--border-subtle);
}
/* Opens growing out of the icon, its lines arriving one after another. */
.bm-pop-enter-active { transition: opacity 0.22s ease, transform 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.2); }
.bm-pop-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.bm-pop-enter-from, .bm-pop-leave-to { opacity: 0; transform: translateY(-6px) scale(0.92); }
.bm-pop-enter-active .bm-line { animation: bmLineIn 0.4s ease both; animation-delay: calc(0.08s + var(--i) * 0.07s); }
@keyframes bmLineIn { from { opacity: 0; transform: translateX(10px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) {
  .bm-pop-enter-active, .bm-pop-leave-active { transition: none; }
  .bm-pop-enter-active .bm-line { animation: none; }
}
</style>
