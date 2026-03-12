<template>
  <div class="workspace">
    <WorkspaceHeader @logout="handleLogout" />

    <WorkspaceTabs v-model="activeTab" />

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
import OnboardingTour from '../components/workspace/OnboardingTour.vue'
import ProductionTab from '../components/workspace/ProductionTab.vue'
import ComparisonTab from '../components/workspace/ComparisonTab.vue'
import RecruitsTab from '../components/workspace/RecruitsTab.vue'
import UnpaidSummaryTab from '../components/workspace/UnpaidSummaryTab.vue'
import CommissionRatesTab from '../components/workspace/CommissionRatesTab.vue'
import CompanyEmailsTab from '../components/workspace/CompanyEmailsTab.vue'

const router = useRouter()
const auth = useAuthStore()
const comparisonStore = useComparisonStore()
const activeTab = ref('production')

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
} = useOnboardingTour({ activeTab })

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
    droppedFiles.value = Array.from(files)
    // Reset after a tick so watchers can fire again for same files
    setTimeout(() => { droppedFiles.value = null }, 100)
  }
}

function onDocDrop(e) {
  // Prevent browser default file open
  e.preventDefault()
  dragCounter.value = 0
  isFullPageDrag.value = false
}

onMounted(async () => {
  await auth.fetchUser()
  document.addEventListener('dragenter', onDragEnter)
  document.addEventListener('dragleave', onDragLeave)
  document.addEventListener('dragover', onDragOver)
  document.addEventListener('drop', onDocDrop)
  document.addEventListener('keydown', tourKeydown)
  if (shouldShowTour()) {
    setTimeout(() => startTour(), 800)
  }
})

onUnmounted(() => {
  document.removeEventListener('dragenter', onDragEnter)
  document.removeEventListener('dragleave', onDragLeave)
  document.removeEventListener('dragover', onDragOver)
  document.removeEventListener('drop', onDocDrop)
  document.removeEventListener('keydown', tourKeydown)
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
