<template>
  <div class="workspace">
    <!-- Floating action menu (React island). Visible only in home view,
         where there's no tabs strip to dock it inside. Items fan DOWN from
         the trigger here — fanning left/across would push items off the
         viewport's left edge since the trigger sits at left:32px. -->
    <CircleMenuIsland
      v-if="viewMode === 'home'"
      :items="circleMenuItems"
      layout="down"
      class="ws-floating-menu"
      @select="onMenuSelect"
    />

    <!-- Client lookup — opens from the menu's Search item. -->
    <ClientSearchModal v-model:open="searchOpen" />

    <!-- Email-provider settings — opens from the menu's Settings item. -->
    <EmailSettingsModal v-model:open="emailSettingsOpen" />

    <!-- Phone-forward setup — lifted here so the activation checklist can open it. -->
    <PhoneForwardModal :open="phoneForwardOpen" @close="phoneForwardOpen = false" />

    <!-- Portal-automation run progress — floats above everything while
         a run is in flight or just finished. Auto-dismisses on success
         after 5s; user can dismiss failures manually. -->
    <PortalRunProgressFloat />

    <!-- "Batch results ready" toast — shows when the run-all batch finishes
         while the user is anywhere but the automation tab. -->
    <BatchResultsToast
      :active-tab="viewMode === 'content' ? activeTab : ''"
      @navigate="onBatchToastNavigate"
    />

    <!-- Notifications bell — always-visible top-right alert center. -->
    <div class="ws-bell-anchor">
      <NotificationBell />
    </div>

    <!-- User-to-user messenger — collapsed pill in the BOTTOM-RIGHT (the only
         free corner). Self-contained: it never touches the worker/automation
         plane, and its presence heartbeat is a person, not a Windows PC. -->
    <MessengerDock />

    <!-- Insights hub: floating radial-orbital launcher in the BOTTOM-LEFT.
         Two nodes: 3-month commission comparison + yield/track recommendations.
         HOME view only — inside the tab content it would overlap the working
         area on every tab, so it's gated like the floating CircleMenu. -->
    <RadialOrbitalIsland
      v-if="viewMode === 'home'"
      :items="radialItems"
      :size="280"
      :orbit-radius="92"
      class="ws-insights-launcher"
      @select="onRadialSelect"
    />
    <MonthlyCommissionModal v-model:open="monthlyOpen" />
    <YieldRecommendationsModal v-model:open="yieldOpen" />

    <!-- Fund-track detail viz — opens when user clicks a ticker chip. -->
    <FundTrackVizPanel v-model:open="fundDetailOpen" :viz="fundDetailViz" />

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

        <div class="home-content">
          <SetupProgressCard />
          <WorkspaceTabs
            v-model="activeTab"
            :view-mode="viewMode"
            @select-card="onCardSelect"
          />
          <AiChatWidget @navigate-tab="onCardSelect" @latest-vizs="onLatestVizs" />
          <AiVizPanel v-model:open="aiVizOpen" :vizs="activeVizs" />
        </div>
      </div>

      <!-- CONTENT MODE -->
      <div v-else key="content">
        <WorkspaceTabs
          v-model="activeTab"
          :view-mode="viewMode"
          @go-home="goHome"
        >
          <template #strip-end>
            <CircleMenuIsland
              :items="circleMenuItems"
              layout="down-left"
              class="strip-circle-menu"
              @select="onMenuSelect"
            />
          </template>
        </WorkspaceTabs>

        <main class="workspace-main">
          <div class="tab-content">
            <Transition name="tab-switch" mode="out-in">
              <ProductionTab v-if="activeTab === 'production'" key="production" @go-to-comparison="onCardSelect('comparison')" @go-to-portal-automation="activeTab = 'portal-automation'" />
              <ComparisonTab v-else-if="activeTab === 'comparison'" key="comparison" @go-to-portal-automation="activeTab = 'portal-automation'" />
              <CommissionRatesTab v-else-if="activeTab === 'commission-rates'" key="commission-rates" />
              <CompanyEmailsTab v-else-if="activeTab === 'company-emails'" key="company-emails" />
              <RecruitsTab v-else-if="activeTab === 'recruits'" key="recruits" />
              <PortalTab v-else-if="activeTab === 'portal'" key="portal" />
              <AiLibraryTab v-else-if="activeTab === 'ai-library'" key="ai-library" />
              <PortalAutomationTab v-else-if="activeTab === 'portal-automation'" key="portal-automation" :auto-open-add="autoOpenAddPortal" @opened="autoOpenAddPortal = false" @go-to-comparison="onCardSelect('comparison')" />
            </Transition>
          </div>
        </main>

      </div>
    </Transition>

    <!-- Post-login welcome wipe -->
    <WelcomeOverlay
      v-if="welcomeOpen"
      :user-name="auth.user?.full_name || ''"
      @done="onWelcomeDone"
    />

    <!-- Setup wizard (אשף ההפעלה) -->
    <SetupPipelineModal
      @open-phone-forward="phoneForwardOpen = true"
      @open-add-portal="onActivationAddPortal"
      @run-automation="onCardSelect('portal-automation')"
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
import { ref, computed, onMounted, onUnmounted, provide, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useComparisonStore } from '../stores/comparison.js'
import { useProductionStore } from '../stores/production.js'
import { usePortalAutomationStore } from '../stores/portalAutomation.js'
import { useSetupPipeline } from '../composables/useSetupPipeline.js'
import { openSetup } from '../utils/setupState.js'
import CircleMenuIsland from '../components/workspace/CircleMenuIsland.vue'
import RadialOrbitalIsland from '../components/workspace/RadialOrbitalIsland.vue'
import MonthlyCommissionModal from '../components/workspace/MonthlyCommissionModal.vue'
import YieldRecommendationsModal from '../components/workspace/YieldRecommendationsModal.vue'
import ClientSearchModal from '../components/workspace/ClientSearchModal.vue'
import EmailSettingsModal from '../components/workspace/EmailSettingsModal.vue'
import PhoneForwardModal from '../components/workspace/PhoneForwardModal.vue'
import SetupProgressCard from '../components/workspace/SetupProgressCard.vue'
import SetupPipelineModal from '../components/workspace/SetupPipelineModal.vue'
import PortalRunProgressFloat from '../components/workspace/PortalRunProgressFloat.vue'
import BatchResultsToast from '../components/workspace/BatchResultsToast.vue'
import NotificationBell from '../components/workspace/NotificationBell.vue'
import MessengerDock from '../components/workspace/MessengerDock.vue'
import { useMessengerStore } from '../stores/messenger.js'
import FundTrackVizPanel from '../components/workspace/FundTrackVizPanel.vue'
import { useFundTickerStore } from '../stores/fundTicker.js'
import WorkspaceTabs from '../components/workspace/WorkspaceTabs.vue'
import WelcomeOverlay from '../components/workspace/WelcomeOverlay.vue'
import ProductionTab from '../components/workspace/ProductionTab.vue'
import ComparisonTab from '../components/workspace/ComparisonTab.vue'
import RecruitsTab from '../components/workspace/RecruitsTab.vue'
import CommissionRatesTab from '../components/workspace/CommissionRatesTab.vue'
import CompanyEmailsTab from '../components/workspace/CompanyEmailsTab.vue'
import PortalTab from '../components/workspace/PortalTab.vue'
import AiLibraryTab from '../components/workspace/AiLibraryTab.vue'
import PortalAutomationTab from '../components/workspace/PortalAutomationTab.vue'
import AiChatWidget from '../components/workspace/AiChatWidget.vue'
import AiVizPanel from '../components/workspace/AiVizPanel.vue'

const router = useRouter()
const auth = useAuthStore()
const comparisonStore = useComparisonStore()
const productionStore = useProductionStore()
const portalAutomationStore = usePortalAutomationStore()
const messengerStore = useMessengerStore()
const activeTab = ref('production')
const viewMode = ref('home')

// Setup wizard → setup entry points
const phoneForwardOpen = ref(false)
const autoOpenAddPortal = ref(false)
function onActivationAddPortal() {
  autoOpenAddPortal.value = true
  onCardSelect('portal-automation')
}

// AI viz modal — opens whenever the top-level AiChatWidget surfaces viz
// payload(s) (bar / donut / kpi / fund-track). Multi-viz: synthesis answers
// can ship 2-3 blocks which AiVizPanel renders as a carousel.
const aiVizOpen = ref(false)
const activeVizs = ref(null)
function onLatestVizs(vizs) {
  activeVizs.value = vizs
  if (Array.isArray(vizs) && vizs.length) aiVizOpen.value = true
}

// Tab order for keyboard arrow navigation (the floating on-screen arrow
// buttons were removed — they covered content; ArrowLeft/ArrowRight remain)
const tabOrder = ['production', 'comparison', 'commission-rates', 'company-emails', 'recruits', 'portal', 'portal-automation']

const currentIndex = computed(() => tabOrder.indexOf(activeTab.value))
const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value < tabOrder.length - 1)

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

function onCardSelect(payload) {
  // Accept string or { tab, company, uploadId } object
  const tabId = typeof payload === 'string' ? payload : payload.tab
  const company = typeof payload === 'object' ? payload.company : null
  const uploadId = typeof payload === 'object' ? payload.uploadId : null

  activeTab.value = tabId
  viewMode.value = 'content'

  // Auto-select comparison category if company is provided
  if (tabId === 'comparison' && company) {
    const cats = ['gemel_hishtalmut', 'insurance']
    // Find category with a cached result matching the company
    const matchedCat = cats.find(cat => {
      const r = comparisonStore.results[cat]
      if (!r) return false
      const sources = r.commission_company_sources || []
      const source = r.commission_company_source || ''
      const allSources = sources.length ? sources : (source ? [source] : [])
      return allSources.some(s =>
        s.includes(company) || company.includes(s)
      )
    })
    if (matchedCat) {
      comparisonStore.selectCategory(matchedCat)
    } else if (uploadId && productionStore.currentFile?.id) {
      // No cached result — auto-trigger comparison computation
      comparisonStore.autoCompare(productionStore.currentFile.id, uploadId).catch(() => {})
    } else {
      // Fallback: select first category with any result
      const fallback = cats.find(cat => comparisonStore.results[cat])
      if (fallback) comparisonStore.selectCategory(fallback)
    }
  }
}

function goHome() {
  viewMode.value = 'home'
}

// ── Batch results toast → navigation ───────────────────────────────────
// Prefer a category the batch actually persisted (comparison_categories),
// else the first category with a cached result.
function batchTargetCategory() {
  const batch = portalAutomationStore.batchJustFinished || portalAutomationStore.latestBatch
  const batchCats = batch?.comparison_categories || []
  const order = ['gemel_hishtalmut', 'insurance']
  return (
    order.find((c) => batchCats.includes(c)) ||
    order.find((c) => comparisonStore.results[c]) ||
    null
  )
}

function onBatchToastNavigate(tab) {
  if (tab === 'comparison') {
    const cat = batchTargetCategory()
    if (cat) {
      comparisonStore.selectCategory(cat)
      comparisonStore.fetchLatest(cat).catch(() => {})
    }
  }
  onCardSelect({ tab })
}

// Setup wizard (אשף ההפעלה) — the single first-run pipeline. Auto-opens after
// the welcome wipe (and on reloads) while setup is incomplete and the user
// hasn't ✕-closed the home card.
const setup = useSetupPipeline()

async function maybeOpenSetup() {
  if (setup.isCompleted()) return
  await setup.bootstrap()
  if (setup.allDone.value) { setup.markCompleted(); return }
  if (setup.isClosed()) { setup.pinReminder(); return }
  openSetup()
}

// Post-login welcome overlay
const welcomeOpen = ref(false)

function onWelcomeDone() {
  welcomeOpen.value = false
  maybeOpenSetup()
}

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
  // Person-presence beat (20s). Started here rather than in MessengerDock so it
  // keeps running — and keeps the unread badge current — while the dock is
  // closed. Awaited fetchUser above means myId is set before the first poll.
  messengerStore.startPresence()
  // Resume a run-all batch that's still in-flight on the server (page reload
  // mid-batch) — polling + the post-batch store refresh continue even if the
  // user never opens the automation tab. Fire-and-forget; failures are benign.
  portalAutomationStore.hydrateBatch()
  document.addEventListener('dragenter', onDragEnter)
  document.addEventListener('dragleave', onDragLeave)
  document.addEventListener('dragover', onDragOver)
  document.addEventListener('drop', onDocDrop)
  document.addEventListener('keydown', onKeydown)

  if (sessionStorage.getItem('justLoggedIn') === '1') {
    sessionStorage.removeItem('justLoggedIn')
    welcomeOpen.value = true
  } else {
    maybeOpenSetup()
  }
})

onUnmounted(() => {
  document.removeEventListener('dragenter', onDragEnter)
  document.removeEventListener('dragleave', onDragLeave)
  document.removeEventListener('dragover', onDragOver)
  document.removeEventListener('drop', onDocDrop)
  document.removeEventListener('keydown', onKeydown)
  messengerStore.stopPresence()
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}

// CircleMenu — React island. Item `icon` is a lucide-react export name.
const circleMenuItems = [
  { key: 'home',     label: 'בית',      icon: 'Home' },
  { key: 'search',   label: 'חיפוש',    icon: 'Search' },
  { key: 'settings', label: 'הגדרות',   icon: 'Settings' },
  { key: 'help',     label: 'עזרה',     icon: 'HelpCircle' },
  { key: 'logout',   label: 'התנתקות',  icon: 'LogOut' },
]
// Modals owned by WorkspaceView so they overlay everything (above ticker + menu).
const searchOpen = ref(false)
const emailSettingsOpen = ref(false)
const fundDetailOpen = ref(false)
const fundDetailViz = ref(null)
const fundTickerStore = useFundTickerStore()

function onMenuSelect(key) {
  if (key === 'logout')   { handleLogout(); return }
  if (key === 'home')     { goHome(); return }
  if (key === 'search')   { searchOpen.value = true; return }
  if (key === 'settings') { emailSettingsOpen.value = true; return }
  // help — TODO. No-op for now so the menu still closes.
}

// ── Insights hub (radial-orbital, bottom-left) ─────────────────────────
// IDs are stable integers so the radial composition can render dependable
// keys; the React component cares about `id` rather than the Vue-style `key`.
const RADIAL_MONTHLY = 1
const RADIAL_YIELD = 2
const radialItems = [
  { id: RADIAL_MONTHLY, title: 'עמלות 3 חודשים', iconName: 'BarChart3', energy: 90 },
  { id: RADIAL_YIELD,   title: 'תשואות וניוד',    iconName: 'TrendingUp', energy: 80 },
]
const monthlyOpen = ref(false)
const yieldOpen = ref(false)
function onRadialSelect(id) {
  if (id === RADIAL_MONTHLY) monthlyOpen.value = true
  else if (id === RADIAL_YIELD) yieldOpen.value = true
}

// No trigger since the StockTicker strip was removed — kept, with FundTrackVizPanel
// and stores/fundTicker.js, so a future entry point can re-wire it in one line.
async function openFundDetail(trackId) {
  if (!trackId) return
  // Open immediately so the modal's loading spinner is visible while the fetch resolves.
  fundDetailViz.value = null
  fundDetailOpen.value = true
  try {
    const data = await fundTickerStore.fetchTrackDetail(trackId)
    if (!data || !fundDetailOpen.value) return
    fundDetailViz.value = {
      type: 'fund-track',
      title: data.label,
      period_label: data.period_label,
      averages: data.averages || { month: null, y1: null, y3: null, y5: null },
      funds: Array.isArray(data.funds) ? data.funds : [],
    }
  } catch (e) {
    console.error('[WorkspaceView] fund detail fetch failed', e)
    fundDetailOpen.value = false
  }
}
</script>

<style scoped>
.workspace {
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

/* Notifications bell — always-visible top-right alert center.
 * Above modals (1000+) is still allowed for the dropdown panel (which is
 * teleported to body with its own z-index 1500). */
.ws-bell-anchor {
  position: fixed;
  top: 44px;
  inset-inline-start: 18px;  /* RTL: visual-RIGHT */
  z-index: 200;
}
@media (max-width: 720px) {
  .ws-bell-anchor { top: 40px; inset-inline-start: 10px; }
}
@media (max-width: 640px) {
  .ws-bell-anchor { top: 8px; }
}

/* Floating CircleMenu island — top-LEFT corner with breathing room so the
   orbital items don't clip when they sweep outward. z-index stays below
   modals (1000+) and onboarding (5000+). */
.ws-floating-menu {
  position: fixed;
  top: 48px;
  left: 32px;
  z-index: 102;
  direction: ltr;
  pointer-events: none; /* let the inner React component own its own hitboxes */
}
.ws-floating-menu :deep(*) { pointer-events: auto; }
@media (max-width: 720px) {
  .ws-floating-menu { top: 12px; left: 12px; }
}

/* In-strip CircleMenu — sits inside <WorkspaceTabs> at the strip-end slot,
   beside the home-pill (4-rect icon). `direction: ltr` keeps the orbital
   items' transform math (negative-x = left) predictable inside an RTL page.
   `position: relative` + high z-index so items can fan out LEFT, over any
   sibling chrome that happens to live next to the strip. */
.strip-circle-menu {
  position: relative;
  z-index: 95;
  margin-inline-start: 6px;
  direction: ltr;
}

/* Insights hub launcher — bottom-LEFT in viewport pixels (not RTL-flipped).
   Above the waves (z:0), below modals (1010+), onboarding (5000+), and the
   dropzone overlay (9999). Hidden in print so it doesn't show up on the
   dashboard PDF the agent prints for customers. */
.ws-insights-launcher {
  position: fixed;
  bottom: 24px;
  left: 24px;
  z-index: 102;
  pointer-events: none;
}
.ws-insights-launcher :deep(*) { pointer-events: auto; }
@media (max-width: 720px) {
  .ws-insights-launcher { bottom: 14px; left: 14px; }
  .ws-insights-launcher :deep(.radial-orbital-island) { transform: scale(0.85); transform-origin: bottom left; }
}
@media print {
  .ws-insights-launcher { display: none; }
}

/* ─── Home view blur circles ─── */
.home-view {
  position: relative;
}

.home-content {
  position: relative;
  z-index: 1;
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

.tab-content {
  min-height: 400px;
}

/* View switch transitions */
/* Top-level tab switch — directional slide+fade so moving between tabs reads
   as the content sliding in (RTL-aware: new view enters from the inline-start). */
.view-switch-enter-active {
  animation: viewSlideIn 0.26s var(--transition);
}
.view-switch-leave-active {
  animation: viewSlideOut 0.15s ease-in;
}
@keyframes viewSlideIn {
  from { opacity: 0; transform: translateX(-22px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes viewSlideOut {
  from { opacity: 1; transform: translateX(0); }
  to { opacity: 0; transform: translateX(14px); }
}
@media (prefers-reduced-motion: reduce) {
  .view-switch-enter-active,
  .view-switch-leave-active { animation: none; }
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

@media (prefers-reduced-motion: reduce) {
  .tab-switch-enter-active,
  .tab-switch-leave-active { animation: none; }
}

@media (max-width: 768px) {
  .workspace-main {
    padding: 24px 16px 40px;
  }
}
</style>
