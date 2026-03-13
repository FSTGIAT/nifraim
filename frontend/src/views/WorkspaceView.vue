<template>
  <div class="workspace">
    <WorkspaceHeader @logout="handleLogout" />

    <Transition name="view-switch" mode="out-in">
      <!-- HOME MODE -->
      <div v-if="viewMode === 'home'" key="home" class="home-view">
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
              <linearGradient id="hwg1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
                <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
                <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
                <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
              </linearGradient>
            </defs>
            <path fill="url(#hwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
          </svg>
          <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="hwg2" x1="100%" y1="0%" x2="0%" y2="0%">
                <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
                <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
                <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
                <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
              </linearGradient>
            </defs>
            <path fill="url(#hwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
          </svg>
          <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="hwg3" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
                <stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/>
                <stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/>
              </linearGradient>
            </defs>
            <path fill="url(#hwg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
          </svg>
        </div>

        <WorkspaceTabs
          v-model="activeTab"
          :view-mode="viewMode"
          @select-card="onCardSelect"
        />
        <AiChatWidget />
      </div>

      <!-- CONTENT MODE -->
      <div v-else key="content">
        <WorkspaceTabs
          v-model="activeTab"
          :view-mode="viewMode"
          @go-home="goHome"
        />

        <main class="workspace-main" :class="{ 'wide-content': activeTab === 'comparison' && !!comparisonStore.result }">
          <div class="tab-content">
            <Transition name="tab-switch" mode="out-in">
              <ProductionTab v-if="activeTab === 'production'" key="production" />
              <ComparisonTab v-else-if="activeTab === 'comparison'" key="comparison" />
              <UnpaidSummaryTab v-else-if="activeTab === 'unpaid-summary'" key="unpaid-summary" />
              <CommissionRatesTab v-else-if="activeTab === 'commission-rates'" key="commission-rates" />
              <CompanyEmailsTab v-else-if="activeTab === 'company-emails'" key="company-emails" />
              <RecruitsTab v-else-if="activeTab === 'recruits'" key="recruits" />
            </Transition>
          </div>
        </main>

        <NavArrowButton
          v-if="hasPrev"
          direction="prev"
          :label="prevLabel"
          @navigate="goPrev"
        />
        <NavArrowButton
          v-if="hasNext"
          direction="next"
          :label="nextLabel"
          @navigate="goNext"
        />
      </div>
    </Transition>

    <!-- Onboarding tour -->
    <OnboardingTour
      :is-active="tourActive"
      :current-step="tourCurrentStep"
      :current-step-index="tourStepIndex"
      :total-steps="tourTotalSteps"
      :spotlight-rect="tourSpotlightRect"
      :tooltip-position="tourTooltipPosition"
      :spotlight-ready="tourSpotlightReady"
      @next="tourNext"
      @prev="tourPrev"
      @skip="tourSkip"
      @complete="tourComplete"
    />

    <!-- Full-page drop overlay -->
    <Teleport to="body">
      <Transition name="overlay-fade">
        <div
          v-if="isFullPageDrag"
          class="fullpage-drop-overlay"
          @drop.prevent="onOverlayDrop"
          @dragover.prevent
          @dragleave.prevent
        >
          <div class="drop-overlay-border">
            <svg class="marching-border" width="100%" height="100%">
              <rect x="8" y="8" rx="20" ry="20"
                width="calc(100% - 16px)" height="calc(100% - 16px)"
                fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="2.5"
                stroke-dasharray="12 8" />
            </svg>
          </div>
          <div class="drop-overlay-content">
            <div class="drop-overlay-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <h2>שחרר קבצים כאן</h2>
            <p>{{ dropContextLabel }}</p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, provide, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useComparisonStore } from '../stores/comparison.js'
import { useOnboardingTour } from '../composables/useOnboardingTour.js'
import WorkspaceHeader from '../components/workspace/WorkspaceHeader.vue'
import WorkspaceTabs from '../components/workspace/WorkspaceTabs.vue'
import NavArrowButton from '../components/workspace/NavArrowButton.vue'
import OnboardingTour from '../components/workspace/OnboardingTour.vue'
import ProductionTab from '../components/workspace/ProductionTab.vue'
import ComparisonTab from '../components/workspace/ComparisonTab.vue'
import RecruitsTab from '../components/workspace/RecruitsTab.vue'
import UnpaidSummaryTab from '../components/workspace/UnpaidSummaryTab.vue'
import CommissionRatesTab from '../components/workspace/CommissionRatesTab.vue'
import CompanyEmailsTab from '../components/workspace/CompanyEmailsTab.vue'
import AiChatWidget from '../components/workspace/AiChatWidget.vue'

const router = useRouter()
const auth = useAuthStore()
const comparisonStore = useComparisonStore()
const activeTab = ref('production')
const viewMode = ref('home')

// Tab order for navigation
const tabOrder = ['production', 'comparison', 'unpaid-summary', 'commission-rates', 'company-emails', 'recruits']
const tabLabels = {
  'production': 'פרודוקציה',
  'comparison': 'השוואת נפרעים',
  'unpaid-summary': 'סיכום חובות',
  'commission-rates': 'טבלת עמלות',
  'company-emails': 'אימיילים לחברות',
  'recruits': 'My File',
}

const currentIndex = computed(() => tabOrder.indexOf(activeTab.value))
const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value < tabOrder.length - 1)
const prevLabel = computed(() => hasPrev.value ? tabLabels[tabOrder[currentIndex.value - 1]] : '')
const nextLabel = computed(() => hasNext.value ? tabLabels[tabOrder[currentIndex.value + 1]] : '')

function goNext() {
  if (hasNext.value) {
    activeTab.value = tabOrder[currentIndex.value + 1]
  }
}

function goPrev() {
  if (hasPrev.value) {
    activeTab.value = tabOrder[currentIndex.value - 1]
  }
}

function onCardSelect(tabId) {
  activeTab.value = tabId
  viewMode.value = 'content'
}

function goHome() {
  viewMode.value = 'home'
}

// Onboarding tour
const {
  isActive: tourActive,
  currentStep: tourCurrentStep,
  currentStepIndex: tourStepIndex,
  totalSteps: tourTotalSteps,
  spotlightRect: tourSpotlightRect,
  tooltipPosition: tourTooltipPosition,
  spotlightReady: tourSpotlightReady,
  shouldShowTour,
  startTour,
  nextStep: tourNext,
  prevStep: tourPrev,
  skipTour: tourSkip,
  completeTour: tourComplete,
  onKeydown: tourKeydown,
  cleanup: cleanupTour,
} = useOnboardingTour({ activeTab, viewMode })

// Full-page drag & drop
const isFullPageDrag = ref(false)
const dragCounter = ref(0)
const droppedFiles = shallowRef(null)

provide('droppedFiles', droppedFiles)

const dropContextLabel = computed(() => {
  if (activeTab.value === 'production') return 'קובץ פרודוקציה'
  if (activeTab.value === 'comparison') return 'קבצי נפרעים להשוואה'
  return 'קבצי Excel'
})

function onDragEnter(e) {
  e.preventDefault()
  dragCounter.value++
  if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
    isFullPageDrag.value = true
  }
}

function onDragLeave(e) {
  e.preventDefault()
  dragCounter.value--
  if (dragCounter.value <= 0) {
    dragCounter.value = 0
    isFullPageDrag.value = false
  }
}

function onDragOver(e) {
  e.preventDefault()
}

function onOverlayDrop(e) {
  dragCounter.value = 0
  isFullPageDrag.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    // Auto-switch to production content mode on file drop from home
    if (viewMode.value === 'home') {
      activeTab.value = 'production'
      viewMode.value = 'content'
    }
    droppedFiles.value = Array.from(files)
    setTimeout(() => { droppedFiles.value = null }, 100)
  }
}

function onDocDrop(e) {
  e.preventDefault()
  dragCounter.value = 0
  isFullPageDrag.value = false
}

function onKeydown(e) {
  // Let tour handle its own keys first
  if (tourActive.value) {
    tourKeydown(e)
    return
  }
  // Arrow nav only in content mode
  if (viewMode.value !== 'content') return
  if (e.key === 'ArrowLeft') {
    goNext() // RTL: left = next
  } else if (e.key === 'ArrowRight') {
    goPrev() // RTL: right = prev
  }
}

onMounted(async () => {
  await auth.fetchUser()
  document.addEventListener('dragenter', onDragEnter)
  document.addEventListener('dragleave', onDragLeave)
  document.addEventListener('dragover', onDragOver)
  document.addEventListener('drop', onDocDrop)
  document.addEventListener('keydown', onKeydown)
  if (shouldShowTour()) {
    setTimeout(() => startTour(), 800)
  }
})

onUnmounted(() => {
  document.removeEventListener('dragenter', onDragEnter)
  document.removeEventListener('dragleave', onDragLeave)
  document.removeEventListener('dragover', onDragOver)
  document.removeEventListener('drop', onDocDrop)
  document.removeEventListener('keydown', onKeydown)
  cleanupTour()
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.workspace {
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

/* ─── Home view blur circles ─── */
.home-view {
  position: relative;
}

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

.workspace-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px 60px;
  transition: max-width 0.5s cubic-bezier(0.16, 1, 0.3, 1), padding 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.workspace-main.wide-content {
  max-width: 100%;
  padding: 20px 32px 60px;
}

.tab-content {
  min-height: 400px;
}

/* View switch transitions */
.view-switch-enter-active {
  animation: fadeInUp 0.4s var(--transition);
}

.view-switch-leave-active {
  animation: cardFadeOut 0.2s ease-out;
}

/* Full-page drop overlay */
.fullpage-drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.drop-overlay-border {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.drop-overlay-border svg {
  position: absolute;
  inset: 0;
}

.drop-overlay-border rect {
  animation: marchingAnts 1s linear infinite;
}

@keyframes marchingAnts {
  to { stroke-dashoffset: -20; }
}

.drop-overlay-content {
  text-align: center;
  color: white;
  pointer-events: none;
}

.drop-overlay-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: rgba(255, 255, 255, 0.1);
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: dropBounce 1.5s ease-in-out infinite;
}

@keyframes dropBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.drop-overlay-content h2 {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.drop-overlay-content p {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.7);
}

/* Overlay transition */
.overlay-fade-enter-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.overlay-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.overlay-fade-enter-from {
  opacity: 0;
  transform: scale(1.02);
}
.overlay-fade-leave-to {
  opacity: 0;
  transform: scale(0.98);
}

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

@media (max-width: 768px) {
  .workspace-main {
    padding: 24px 16px 40px;
  }

  .workspace-main.wide-content {
    padding: 16px 12px 40px;
  }
}
</style>
