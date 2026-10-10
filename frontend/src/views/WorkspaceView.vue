<template>
  <div class="workspace" :class="{ 'workspace--railed': viewMode === 'content' }">
    <!-- Floating action menu (React island). Visible only in home view,
         where there's no tabs strip to dock it inside. Items fan DOWN from
         the trigger here — fanning left/across would push items off the
         viewport's left edge since the trigger sits at left:32px. -->
    <!-- The nav rail (user · search · settings · Mail Agent · help · sign-out)
         is on EVERY page, home and tabs alike — inside a tab it was the only
         way to reach those items. Inside a tab, `.workspace--railed` reserves
         a left gutter so the rail never sits on content.
         Mounted OUTSIDE the view Transition on purpose: inside `.home-view`
         it would inherit `.view-receding` and fade away with the grid every
         time a card launches. -->
    <HomeSidebar
      :items="circleMenuItems"
      :active="railActive"
      :user="auth.user"
      :show-bell="bellInRail"
      @select="onMenuSelect"
    />

    <!-- Nifraim Mail Agent — opens from the rail / round menu / bell. -->
    <MailAgentModal :open="mailAgentOpen" @close="closeMailAgent" />

    <!-- Rail windows — same shell as the Mail Agent, opened from the side rail. -->
    <RailWindow :open="contactsOpen" label="אנשי קשר" accent="var(--tab-emails)" round
                reveal-from='.rail-item[data-rail-key="contacts"] .rail-ico' @close="closeContacts">
      <CompanyEmailsTab />
    </RailWindow>
    <RailWindow :open="recruitsOpen" label="ניהול תיק אישי" accent="var(--tab-recruits)" width="1180px" @close="closeRecruits">
      <RecruitsTab />
    </RailWindow>

    <!-- Client lookup — opens from the menu's Search item. -->
    <ClientSearchModal v-model:open="searchOpen" />

    <!-- Email-provider settings — opens from the menu's Settings item. -->
    <EmailSettingsModal v-model:open="emailSettingsOpen" :open-mailbox="backFromConsent" />

    <!-- Phone-forward setup — lifted here so the activation checklist can open it. -->
    <PhoneForwardModal :open="phoneForwardOpen" @close="phoneForwardOpen = false" />

    <!-- Portal-automation run progress — floats above everything while
         a run is in flight or just finished. Auto-dismisses on success
         after 5s; user can dismiss failures manually. -->
    <PortalRunProgressFloat @open-phone-forward="phoneForwardOpen = true" />

    <!-- "Batch results ready" toast — shows when the run-all batch finishes
         while the user is anywhere but the automation tab. -->
    <BatchResultsToast
      :active-tab="viewMode === 'content' ? activeTab : ''"
      @navigate="onBatchToastNavigate"
    />

    <!-- Notifications bell: lives in the sidebar rail (HomeSidebar :show-bell).
         The corner spot is only the fallback where the rail is hidden (phones)
         or too short. Exactly ONE bell is mounted — it owns the store poll. -->
    <div v-if="!bellInRail" class="ws-bell-anchor">
      <NotificationBell />
    </div>

    <!-- Monthly cycle. Home with room: the big emotion clock in the empty
         band right of the cards. Everywhere else (tabs, smaller screens): the
         small alarm-clock icon in the top-right corner. -->
    <div v-if="showEmotionClock" class="ws-emotion-clock">
      <CycleEmotionClock @select="(tab) => onCardSelect(tab)" />
      <!-- סוכן המשרד — the back-office agent (mail + unpaid commission) -->
      <NifraAgentIcon size="big" @open="openCollector" />
      <!-- no room on the left band (1360–1399px): the calls widget joins this column -->
      <CallWidget v-if="!roomForCallWidget" size="big" pop-side="left" />
    </div>
    <!-- שיחות — record a conversation; ivrit.ai transcribes, Claude summarises.
         Home only, in the empty band between the side rail and the cards,
         above the insights orbit. -->
    <div v-if="showEmotionClock && roomForCallWidget" class="ws-call-widget">
      <CallWidget size="big" pop-side="right" />
    </div>
    <div
      v-else
      class="ws-cycle-small"
      :class="{ 'ws-cycle-small--below-bell': !bellInRail, 'ws-cycle-small--content': viewMode === 'content' }"
    >
      <!-- The clock is always on top (user 2026-10-10). Nifra AI follows as one circle of the stack —
           it was a separate fixed 70px circle that sat on top of Nifra Agent when the bell is in the rail. -->
      <CycleRailIcon @select="(tab) => onCardSelect(tab)" />
      <AiAssistantWidget v-if="viewMode === 'content'" size="small" />
      <NifraAgentIcon size="small" @open="openCollector" />
      <NifraMarketIcon v-if="viewMode === 'content'" size="small" @open="openMarket" />
      <NifraInsightsIcon v-if="viewMode === 'content'" size="small" :badge="insightsStore.dueBadge" @open="openInsights" />
      <CallWidget size="small" pop-side="left" />
    </div>
    <NifraMarketStudio v-model:open="marketOpen" :origin-el="marketOrigin" />
    <!-- Nifra Insights — the calls by product + today's promises; its reminders speak on every screen -->
    <NifraInsightsStudio v-model:open="insightsOpen" :origin-el="insightsOrigin" />
    <ReminderToasts @open="openInsights" />
    <OfficeAgentPanel v-model:open="collectorOpen" :origin-el="collectorOrigin" :focus-card="agentFocusCard"
                      @open-mail="collectorOpen = false; mailAgentOpen = true" @open-vizs="onLatestVizs"
                      @open-call="(id) => { collectorOpen = false; callsStore.requestOpenCall(id) }" />

    <!-- The AI assistant — one widget on the right rail, on every tab. It
         replaced `AiInsightCard`, a full-width summary band that sat above
         each comparison and existed nowhere else. Views publish their context
         to the aiContext store; this opens the one conversation sheet. -->
    <!-- Content mode only. The home screen already has AiChatWidget — a full
         assistant panel with its own sources and suggestions — so a second
         entry point to the same AI would be two doors to one room. -->

    <!-- ONE sheet for the whole workspace. It used to be rendered per
         dashboard, so each carried its own copy plus its own viz plumbing —
         which already exists here. -->
    <AiConversationSheet
      v-model:open="aiCtx.open"
      :view-title="aiCtx.viewTitle"
      :view-context="aiCtx.viewContextString"
      :initial-question="aiCtx.initialQuestion"
      @latest-vizs="onLatestVizs"
    />

    <!-- ONE viz panel for both modes. It lived inside the home-only block, so
         a chart the content-mode sheet received set aiVizOpen on a panel that
         was never mounted — the answer arrived, the graph never opened. -->
    <AiVizPanel v-model:open="aiVizOpen" :vizs="activeVizs" />

    <!-- User-to-user messenger — collapsed pill in the BOTTOM-RIGHT (the only
         free corner). Self-contained: it never touches the worker/automation
         plane, and its presence heartbeat is a person, not a Windows PC. -->
    <MessengerDock v-if="!setupState.modalOpen" />

    <!-- Nifra Market — the fund-rankings studio, in the bottom-left of home (where the insights orbit was,
         removed 2026-10-10). Inside the tabs it's the small circle in the corner stack. -->
    <div v-if="viewMode === 'home'" class="ws-market-spot">
      <NifraInsightsIcon :size="isPhone ? 'small' : 'big'" :badge="insightsStore.dueBadge" @open="openInsights" />
    </div>
    <!-- Market sits up beside Nifra Calls (user 2026-10-10), tied to the Calls widget's position. -->
    <div v-if="viewMode === 'home'" class="ws-market-own">
      <NifraMarketIcon :size="isPhone ? 'small' : 'big'" @open="openMarket" />
    </div>

    <!-- Fund-track detail viz — opens when user clicks a ticker chip. -->
    <FundTrackVizPanel v-model:open="fundDetailOpen" :viz="fundDetailViz" />

    <!-- While the launch morph is running it owns the swap outright: the
         slide would otherwise play underneath it, two animations arguing over
         one transition. -->
    <Transition :name="morphRunning ? 'view-none' : 'view-switch'" mode="out-in">
      <!-- HOME MODE -->
      <div v-if="viewMode === 'home'" key="home" class="home-view" :class="{ 'view-receding': morphReceding === 'home' }">
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
          <!-- Nifra Market's surfer drops by on the home waves now and then -->
          <WaveSurfer :bottom="86" :every="40" :delay="10" :size="46" tone="canvas" />
          <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="hwg1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color: var(--tab-production); stop-opacity: 0.2"/>
                <stop offset="30%" style="stop-color: var(--tab-maslaka); stop-opacity: 0.12"/>
                <stop offset="60%" style="stop-color: var(--tab-recruits); stop-opacity: 0.18"/>
                <stop offset="100%" style="stop-color: var(--tab-production); stop-opacity: 0.1"/>
              </linearGradient>
            </defs>
            <path fill="url(#hwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
          </svg>
          <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="hwg2" x1="100%" y1="0%" x2="0%" y2="0%">
                <stop offset="0%" style="stop-color: var(--tab-recruits); stop-opacity: 0.16"/>
                <stop offset="40%" style="stop-color: var(--tab-maslaka); stop-opacity: 0.1"/>
                <stop offset="70%" style="stop-color: var(--tab-production); stop-opacity: 0.14"/>
                <stop offset="100%" style="stop-color: var(--tab-recruits); stop-opacity: 0.08"/>
              </linearGradient>
            </defs>
            <path fill="url(#hwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
          </svg>
          <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="hwg3" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color: var(--tab-maslaka); stop-opacity: 0.12"/>
                <stop offset="50%" style="stop-color: var(--tab-production); stop-opacity: 0.08"/>
                <stop offset="100%" style="stop-color: var(--tab-maslaka); stop-opacity: 0.14"/>
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
        </div>
      </div>

      <!-- CONTENT MODE -->
      <div v-else key="content" :class="{ 'view-receding': morphReceding === 'content' }">
        <WorkspaceTabs
          v-model="activeTab"
          :view-mode="viewMode"
          @select-pill="onPillSelect"
          @go-home="goHome"
        >
        </WorkspaceTabs>

        <main class="workspace-main">
          <div class="tab-content">
            <!-- Same rule as the view switch: while the morph is running it
                 owns the swap, or the tab slide plays underneath it. -->
            <Transition :name="morphRunning ? 'view-none' : 'tab-switch'" mode="out-in">
              <ProductionTab v-if="activeTab === 'production'" key="production" @go-to-comparison="onCardSelect('comparison')" @go-to-portal-automation="activeTab = 'portal-automation'" @go-to-maslaka="onCardSelect('maslaka')" @navigate="onCardSelect" />
              <ComparisonTab v-else-if="activeTab === 'comparison'" key="comparison" @go-to-portal-automation="activeTab = 'portal-automation'" />
              <CommissionRatesTab v-else-if="activeTab === 'commission-rates'" key="commission-rates" />
              <PortalTab v-else-if="activeTab === 'portal'" key="portal" />
              <AiLibraryTab v-else-if="activeTab === 'ai-library'" key="ai-library" />
              <MaslakaTab v-else-if="activeTab === 'maslaka'" key="maslaka" />
              <PortalAutomationTab v-else-if="activeTab === 'portal-automation'" key="portal-automation" :auto-open-add="autoOpenAddPortal" @opened="autoOpenAddPortal = false" @go-to-comparison="onCardSelect('comparison')" />
            </Transition>
          </div>
        </main>

      </div>
    </Transition>

    <!-- The launching app. One childless fixed box: it grows out of the card
         you pressed and flattens its corners into the screen, then hands over
         to the real view. Above the header (100) and tabs (90), below every
         modal (1000+) so nothing can be launched over a dialog. -->
    <div
      v-if="morphRunning"
      ref="morphSurface"
      class="launch-surface"
      :style="morphStyle"
      aria-hidden="true"
    >
      <span v-if="morphTab" ref="morphGlyph" class="launch-glyph">
        <!-- the home card's own drawing sketches itself as the app opens -->
        <HomeCardDrawing v-if="DRAWN_TABS.has(morphTab)" :name="morphTab" />
        <AppIcon v-else :name="morphTab" :size="22" />
      </span>
    </div>

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
      @open-mail-agent="mailAgentOpen = true"
      @open-agreements="onCardSelect('commission-rates')"
      @open-maslaka="onCardSelect('maslaka')"
      @run-automation="onCardSelect('portal-automation')"
    />

    <!-- Left the setup wizard for a step that lives elsewhere (portal, Mail
         Agent, מסלקה, manual agreement upload): one tap back, always. -->
    <Transition name="setup-return">
      <button
        v-if="setupState.away && !setupState.modalOpen"
        type="button"
        class="setup-return"
        @click="resumeSetup()"
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        חזרה להפעלת האוטומציה
      </button>
    </Transition>

    <!-- Monthly cycle (מחזור) events: worker waiting / upload production /
         partial run / comparison ready — each shown once (also emailed). -->
    <!-- Waits for the full-screen setup wizard to close (it would cover it). -->
    <CycleNotificationModal v-if="!setupState.modalOpen" @navigate="(tab) => onCardSelect(tab)" />

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
import { applyCanvas } from '../utils/appCanvas.js'
import { ref, computed, onMounted, onUnmounted, provide, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useComparisonStore } from '../stores/comparison.js'
import { useProductionStore } from '../stores/production.js'
import { usePortalAutomationStore } from '../stores/portalAutomation.js'
import { useSetupPipeline } from '../composables/useSetupPipeline.js'
import { openSetup, setupState, resumeSetup, resumeSetupIfAway } from '../utils/setupState.js'
import ClientSearchModal from '../components/workspace/ClientSearchModal.vue'
import EmailSettingsModal from '../components/workspace/EmailSettingsModal.vue'
import PhoneForwardModal from '../components/workspace/PhoneForwardModal.vue'
import SetupProgressCard from '../components/workspace/SetupProgressCard.vue'
import SetupPipelineModal from '../components/workspace/SetupPipelineModal.vue'
import CycleRailIcon from '../components/workspace/CycleRailIcon.vue'
import CycleEmotionClock from '../components/workspace/CycleEmotionClock.vue'
import NifraAgentIcon from '../components/workspace/NifraAgentIcon.vue'
import OfficeAgentPanel from '../components/workspace/OfficeAgentPanel.vue'
import NifraMarketIcon from '../components/market/NifraMarketIcon.vue'
import NifraMarketStudio from '../components/market/NifraMarketStudio.vue'
import NifraInsightsIcon from '../components/insights/NifraInsightsIcon.vue'
import NifraInsightsStudio from '../components/insights/NifraInsightsStudio.vue'
import ReminderToasts from '../components/insights/ReminderToasts.vue'
import { useCallsInsightsStore } from '../stores/callsInsights.js'
import WaveSurfer from '../components/market/WaveSurfer.vue'
import CycleNotificationModal from '../components/workspace/CycleNotificationModal.vue'
import { useCycleStore } from '../stores/cycle.js'
import PortalRunProgressFloat from '../components/workspace/PortalRunProgressFloat.vue'
import BatchResultsToast from '../components/workspace/BatchResultsToast.vue'
import NotificationBell from '../components/workspace/NotificationBell.vue'
import HomeSidebar from '../components/workspace/HomeSidebar.vue'
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
import MailAgentModal from '../components/workspace/MailAgentModal.vue'
import RailWindow from '../components/workspace/RailWindow.vue'
import CompanyEmailsTab from '../components/workspace/CompanyEmailsTab.vue'
import { useMailAgentStore } from '../stores/mailAgent.js'
import PortalTab from '../components/workspace/PortalTab.vue'
import AiLibraryTab from '../components/workspace/AiLibraryTab.vue'
import PortalAutomationTab from '../components/workspace/PortalAutomationTab.vue'
import MaslakaTab from '../components/workspace/MaslakaTab.vue'
import CallWidget from '../components/calls/CallWidget.vue'
import { useOfficeAgentStore } from '../stores/officeAgent.js'
import { useCallsStore } from '../stores/calls.js'
import AiChatWidget from '../components/workspace/AiChatWidget.vue'
import AiVizPanel from '../components/workspace/AiVizPanel.vue'
import AiAssistantWidget from '../components/workspace/AiAssistantWidget.vue'
import AiConversationSheet from '../components/workspace/AiConversationSheet.vue'
import { useAiContextStore } from '../stores/aiContext.js'
import { useLaunchMorph } from '../composables/useLaunchMorph.js'
import AppIcon from '../components/icons/AppIcon.vue'
import HomeCardDrawing from '../components/workspace/HomeCardDrawing.vue'
const DRAWN_TABS = new Set(['production', 'comparison', 'commission-rates', 'portal', 'ai-library', 'maslaka', 'portal-automation'])

const router = useRouter()
const auth = useAuthStore()
const comparisonStore = useComparisonStore()
const productionStore = useProductionStore()
const portalAutomationStore = usePortalAutomationStore()
const messengerStore = useMessengerStore()
const activeTab = ref('production')
const viewMode = ref('home')

// ── iOS-style app launch ───────────────────────────────────────────────
// Pressing a home card grows that card's rectangle into the view; going home
// shrinks it back into the same card.
const morph = useLaunchMorph()
const morphRunning = morph.running
const morphReceding = morph.receding
const morphSurface = morph.surfaceEl
const morphGlyph = morph.glyphEl
const morphTab = morph.tab
// The surface is always a full-viewport box; where it appears to be is
// entirely the transform's business. This seed is only what it mounts with,
// before the animation's `fill: both` takes over on the next frame.
const morphStyle = computed(() => ({
  ...(morph.seed.value || {}),
  '--launch-accent': morph.accent.value || 'transparent',
}))

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
const aiCtx = useAiContextStore()
const aiVizOpen = ref(false)
const activeVizs = ref(null)
function onLatestVizs(vizs) {
  activeVizs.value = vizs
  if (Array.isArray(vizs) && vizs.length) aiVizOpen.value = true
}

// Tab order for keyboard arrow navigation (the floating on-screen arrow
// buttons were removed — they covered content; ArrowLeft/ArrowRight remain)
const tabOrder = ['production', 'comparison', 'commission-rates', 'portal', 'portal-automation']

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
  const rect = typeof payload === 'object' ? payload.rect : null
  // Old links (AI answers, empty-state CTAs) to the former emails tab now
  // open the contacts window.
  if (tabId === 'company-emails') { openContacts(null); return }
  if (tabId === 'recruits') { openRecruits(null); return }

  const commit = () => {
    activeTab.value = tabId
    viewMode.value = 'content'
  }
  // Pressed on a home card → grow the view out of it. Every other caller
  // (the setup wizard, the batch toast, the command menu) has no rectangle to
  // grow from and just switches.
  if (rect && viewMode.value === 'home') {
    morph.launch({ rect, radius: payload.radius, accent: payload.accent, tabId, from: 'home', commit })
  } else {
    commit()
  }

  // The merged comparison already covers every company, so there is no
  // category to select. Only compute when we have nothing cached at all.
  if (tabId === 'comparison' && company) {
    if (!comparisonStore.hasResult && uploadId && productionStore.currentFile?.id) {
      comparisonStore.autoCompare(productionStore.currentFile.id, uploadId).catch(() => {})
    }
  }
}

/* A pill press in the mini-strip. Same launch, different rectangle: it grows
   out of the pill rather than out of a home card, and the tab you are leaving
   is what falls back behind it. */
function onPillSelect(payload) {
  const tabId = payload.tab
  if (tabId === activeTab.value) return
  morph.launch({
    rect: payload.rect,
    radius: payload.radius,
    accent: payload.accent,
    tabId,
    from: 'content',
    commit: () => { activeTab.value = tabId },
  })
}

// אנשי קשר is a window, not a tab: it launches out of its rail icon (or just
// appears, when opened from elsewhere without a rectangle) and folds back.
function openContacts() {
  // a circle reveal out of the rail icon (RailWindow reveal-from) — no launch surface
  contactsOpen.value = true
}
function closeContacts() {
  contactsOpen.value = false
}

function openRecruits(rect) {
  if (recruitsOpen.value) return
  morph.launch({ rect, radius: 8, accent: 'var(--tab-recruits)', tabId: 'recruits', from: 'modal', commit: () => { recruitsOpen.value = true } })
}
function closeRecruits() {
  if (!recruitsOpen.value) return
  morph.dismiss({ tabId: 'recruits', commit: () => { recruitsOpen.value = false } })
}

function closeMailAgent() {
  if (!mailAgentOpen.value) return
  morph.dismiss({ tabId: 'mail', commit: () => { mailAgentOpen.value = false; resumeSetupIfAway('mail') } })
}

function goHome() {
  if (viewMode.value === 'home') return
  morph.dismiss({ tabId: activeTab.value, commit: () => { viewMode.value = 'home' } })
}

// ── Batch results toast → navigation ───────────────────────────────────
function onBatchToastNavigate(tab) {
  if (tab === 'comparison') {
    // One merged comparison — just pull the freshest one the batch persisted.
    comparisonStore.fetchLatest().catch(() => {})
  }
  onCardSelect({ tab })
}

// Setup wizard (אשף ההפעלה) — the single first-run pipeline. Auto-opens after
// the welcome wipe (and on reloads) while setup is incomplete and the user
// hasn't ✕-closed the home card.
const setup = useSetupPipeline()
const cycleStore = useCycleStore()

// Live media queries for chrome placement (bell in the rail vs the corner;
// room for the big emotion clock on home).
function useMq(query) {
  const m = window.matchMedia(query)
  const r = ref(m.matches)
  const on = (e) => { r.value = e.matches }
  m.addEventListener('change', on)
  onUnmounted(() => m.removeEventListener('change', on))
  return r
}
// The rail is hidden ≤720px wide and has no room for the bell ≤720px tall.
const bellInRail = useMq('(min-width: 721px) and (min-height: 721px)')
const roomForEmotionClock = useMq('(min-width: 1360px) and (min-height: 640px)')
// ── Collection agent (סוכן גבייה) ──
// Nifra Market — the fund rankings studio, another circle beside Nifra Agent / Nifra Calls
const marketOpen = ref(false)
const marketOrigin = ref(null)
function openMarket(el) { marketOrigin.value = el || null; marketOpen.value = true }
// Nifra Insights — the calls by product, beside Nifra Market
const insightsStore = useCallsInsightsStore()
const insightsOpen = ref(false)
const insightsOrigin = ref(null)
function openInsights(el) { insightsOrigin.value = el || null; insightsOpen.value = true }
const collectorOpen = ref(false)
const collectorOrigin = ref(null)
function openCollector(el) {
  collectorOrigin.value = el || null
  agentFocusCard.value = null
  collectorOpen.value = true
}

// ── Nifra Agent opens by itself when a call's follow-up is ready ──
// The office store raises popRequest (once per call, per user); we open the
// panel on that card — but never on top of the calls studio: it waits until
// the studio closes. The orb gets a short attention pulse.
const officeStore = useOfficeAgentStore()
const callsStore = useCallsStore()
// a call opened from Nifra Insights: when the calls studio closes, the agent lands back in Insights
watch(() => callsStore.studioOpen, (open) => {
  if (open || callsStore.returnTo !== 'insights') return
  callsStore.returnTo = null
  setTimeout(() => openInsights(null), 260)   // after the calls studio's fold
})
const agentFocusCard = ref(null)
watch(
  () => [officeStore.popRequest, callsStore.studioOpen, collectorOpen.value, setupState.modalOpen],
  ([cardId, studio, open, setupUp]) => {
    if (!cardId || studio || open || setupUp) return
    officeStore.markPopped(cardId)
    officeStore.clearPop()
    collectorOrigin.value = document.querySelector('.nai .nai-ring') || null
    agentFocusCard.value = cardId
    setTimeout(() => { collectorOpen.value = true }, 650) // let the orb pulse first
  },
)
// a summary can finish while the page is just sitting there — refresh the
// brief quietly every 30s (only while the tab is visible)
let agentTimer = null
onMounted(() => {
  officeStore.load()
  agentTimer = setInterval(() => { if (document.visibilityState === 'visible' && !collectorOpen.value) officeStore.load() }, 30000)
})
onUnmounted(() => clearInterval(agentTimer))

const showEmotionClock = computed(() => viewMode.value === 'home' && roomForEmotionClock.value)
// The calls widget's left band (rail ends at ~100px, cards start at (vw-882)/2) is wide enough from 1400px.
const roomForCallWidget = useMq('(min-width: 1400px) and (min-height: 700px)')
const isPhone = useMq('(max-width: 720px)')   // Nifra Market's home spot: the small circle on phones

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

// A modal with its own drop zone marks itself `data-own-drop`. While one is
// open the page-wide overlay stays off — otherwise it covers the modal, labels
// the drag "Excel", and swallows the file (e.g. the signed מסלקה PDF).
function modalOwnsDrop() {
  return !!document.querySelector('[data-own-drop]')
}

function onDragEnter(e) {
  e.preventDefault()
  if (modalOwnsDrop()) return
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

// The bell's actions navigate by setting location.hash (#comparison, #automation,
// #mail). Nothing read it, so those buttons silently did nothing. Map the hash
// to a tab here, then clear it so the same button works twice.
const HASH_TABS = { '#comparison': 'comparison', '#automation': 'portal-automation' }
function onHashNav() {
  if (window.location.hash === '#mail') {
    mailAgentOpen.value = true
    history.replaceState(null, '', window.location.pathname + window.location.search)
    return
  }
  const tab = HASH_TABS[window.location.hash]
  if (!tab) return
  onCardSelect(tab)
  history.replaceState(null, '', window.location.pathname + window.location.search)
}

onMounted(async () => {
  applyCanvas() // the logged-in agent's background (per user)
  window.addEventListener('hashchange', onHashNav)
  refreshMailBadge()
  mailBadgeTimer = setInterval(refreshMailBadge, 2 * 60 * 1000)
  onHashNav()
  await auth.fetchUser()
  // Microsoft sends the browser back here after the consent screen. Reopen the
  // settings panel so the agent sees the result instead of a bare workspace, and
  // strip the query so a refresh doesn't reopen it forever. Go all the way to the
  // mailbox card: the outcome — including a refused permission — is written there,
  // and settings alone still leaves the agent hunting for it.
  const params = new URLSearchParams(window.location.search)
  if (params.get('mailbox')) {
    emailSettingsOpen.value = true
    backFromConsent.value = true
    window.history.replaceState({}, '', window.location.pathname)
  }
  // Person-presence beat (20s). Started here rather than in MessengerDock so it
  // keeps running — and keeps the unread badge current — while the dock is
  // closed. Awaited fetchUser above means myId is set before the first poll.
  messengerStore.startPresence()
  // Resume a run-all batch that's still in-flight on the server (page reload
  // mid-batch) — polling + the post-batch store refresh continue even if the
  // user never opens the automation tab. Fire-and-forget; failures are benign.
  portalAutomationStore.hydrateBatch()
  // Monthly cycle: status drives the Production-tab lock; unseen cycle events
  // pop the notification modal.
  cycleStore.fetchStatus()
  cycleStore.fetchNotifications()
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
  clearInterval(mailBadgeTimer)
  window.removeEventListener('hashchange', onHashNav)
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

// Side-rail menu items (HomeSidebar). `icon` names a glyph in its ICONS map.
const baseMenuItems = [
  { key: 'home',     label: 'בית',      icon: 'Home' },
  { key: 'search',   label: 'חיפוש',    icon: 'Search' },
  { key: 'settings', label: 'הגדרות',   icon: 'Settings' },
  { key: 'mail',     label: 'Mail Agent', icon: 'Mail' },
  // Company emails left the tabs: it is a contacts book, opened from the rail.
  { key: 'contacts', label: 'אנשי קשר', icon: 'Contacts' },
  // So did the personal portfolio (recruits) — a rail window too.
  { key: 'recruits', label: 'ניהול תיק אישי', icon: 'Briefcase' },
  { key: 'help',     label: 'עזרה',     icon: 'HelpCircle' },
  { key: 'logout',   label: 'התנתקות',  icon: 'LogOut' },
]
// Modals owned by WorkspaceView so they overlay everything (above ticker + menu).
const searchOpen = ref(false)
const mailAgentOpen = ref(false)
// The Mail Agent item carries a badge: mail waiting for the agent's approval
// (a ready draft or a reply needed) — the same number as its big counter.
const mailAgentStore = useMailAgentStore()
const mailPending = computed(() => {
  const b = mailAgentStore.summary?.by_status || {}
  return (b.drafted || 0) + (b.needs_reply || 0)
})
const circleMenuItems = computed(() => {
  const items = baseMenuItems.map((it) => (it.key === 'mail' && mailPending.value ? { ...it, badge: mailPending.value } : it))
  // Admins get the operations dashboard (/admin) right in the rail.
  if (auth.user?.is_admin) items.splice(items.length - 1, 0, { key: 'admin', label: 'ניהול', icon: 'Shield' })
  return items
})
let mailBadgeTimer = null
function refreshMailBadge() { mailAgentStore.fetchSummary().catch(() => {}) }
watch(mailAgentOpen, (open) => { if (!open) refreshMailBadge() })
const emailSettingsOpen = ref(false)
// Set only on the return leg from Microsoft's consent screen.
const backFromConsent = ref(false)
// Only the NEXT open jumps to the mailbox card (the consent return).
watch(emailSettingsOpen, (open) => { if (!open) backFromConsent.value = false })
const fundDetailOpen = ref(false)
const fundDetailViz = ref(null)
const fundTickerStore = useFundTickerStore()

// Which rail item is "open" right now — highlights it in the rail.
const contactsOpen = ref(false)
const recruitsOpen = ref(false)
const railActive = computed(() =>
  mailAgentOpen.value ? 'mail' : contactsOpen.value ? 'contacts' : recruitsOpen.value ? 'recruits' : '')

function onMenuSelect(key, rect) {
  if (key === 'logout')   { handleLogout(); return }
  if (key === 'admin')    { router.push('/admin'); return }
  if (key === 'home')     { goHome(); return }
  if (key === 'search')   { searchOpen.value = true; return }
  if (key === 'settings') { emailSettingsOpen.value = true; return }
  // Mail Agent and contacts open with the same iPhone-style launch as the home
  // cards, growing out of their rail icon (and folding back into it on close).
  if (key === 'mail') {
    if (mailAgentOpen.value) return
    morph.launch({ rect, radius: 8, accent: 'var(--tab-mail)', tabId: 'mail', from: 'modal', commit: () => { mailAgentOpen.value = true } })
    return
  }
  if (key === 'contacts') { openContacts(rect); return }
  if (key === 'recruits') { openRecruits(rect); return }
  // help — TODO. No-op for now so the menu still closes.
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
/* Right rail, reading top to bottom: alerts · assistant · people. Offset far
   enough below the bell that the two never read as one control, and well
   clear of the messenger pill in the bottom corner. */
/* Cycle: big emotion clock, vertically centred in the empty band between the
   cards grid (882px, centred) and the right rail. */
.ws-emotion-clock {
  display: flex; flex-direction: column; align-items: center; gap: 18px;
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  inset-inline-start: max(40px, calc(25vw - 260px));  /* RTL: visual-RIGHT */
  z-index: 50;
}
/* Cycle: small alarm-clock icon — the bell's old corner (the bell moved into
   the rail); under the corner bell when that fallback is showing. */
.ws-cycle-small { position: fixed; top: 44px; inset-inline-start: 18px; z-index: 200; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.ws-cycle-small--below-bell { top: 104px; }
/* the AI widget is inside the stack now — no band to leave above it */
.ws-cycle-small--below-bell.ws-cycle-small--content { top: 104px; }
@media (max-width: 720px) {
  .ws-bell-anchor { top: 40px; inset-inline-start: 10px; }
  .ws-cycle-small--below-bell { top: 96px; inset-inline-start: 10px; }
  .ws-cycle-small--below-bell.ws-cycle-small--content { top: 96px; }
}
@media (max-width: 640px) {
  .ws-bell-anchor { top: 8px; }
  .ws-cycle-small--below-bell:not(.ws-cycle-small--content) { top: 62px; }
}


/* Insights hub launcher — bottom-LEFT in viewport pixels (not RTL-flipped).
   Above the waves (z:0), below modals (1010+), onboarding (5000+), and the
   dropzone overlay (9999). Hidden in print so it doesn't show up on the
   dashboard PDF the agent prints for customers. */
/* Calls widget: centred in the band between the side rail (right edge ≈100px)
   and the card grid (left edge = (100vw − 882px)/2), clear of the insights
   orbit below it (bottom 24px + 280px). 118px ring + caption ≈ 154px tall. */
.ws-call-widget {
  position: fixed;
  left: calc((100vw - 882px) / 4 - 9px);
  bottom: 312px;
  z-index: 50;
}
/* Nifra Market's home spot — bottom-left, centred where the 280px insights orbit stood */
.ws-market-spot { position: fixed; bottom: 86px; left: 105px; z-index: 102; display: flex; align-items: flex-end; gap: 22px; }
@media (max-width: 720px) { .ws-market-spot { bottom: 18px; left: 18px; } }
@media print { .ws-market-spot { display: none; } }
/* Market: to the right of Nifra Calls and a step below it — Calls' own left formula + 101px, never closer
   to Insights than its old spot beside it (105 + 118 ring + 22 gap). */
.ws-market-own {
  position: fixed; z-index: 102;
  left: max(calc((100vw - 882px) / 4 - 9px + 101px), 245px);
  bottom: 168px;
}
@media (max-width: 720px) { .ws-market-own { bottom: 18px; left: 90px; } }
@media print { .ws-market-own { display: none; } }

/* ─── Home view blur circles ─── */
.home-view {
  position: relative;
}

.home-content {
  position: relative;
  z-index: 1;
}

/* The ambient wash takes the TAB palette, one colour per blob, rather than
   seven shades of orange. `tab_identity_system` is explicit that orange is the
   brand ACTION colour and never an identity — an all-orange home was that
   violation at full-screen size. Home is the index of every tab, so it reads
   as all of them at once. (The upload empty states keep their orange circles
   and waves; that pairing is pinned to uploads, not to this screen.) */
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
  background: color-mix(in srgb, var(--tab-production) 11.6%, transparent);
  border: 1px solid color-mix(in srgb, var(--tab-production) 14.7%, transparent);
  animation: floatBob 8s ease-in-out infinite;
}

.fc-2 {
  width: 160px;
  height: 160px;
  bottom: 25%;
  left: -40px;
  background: color-mix(in srgb, var(--tab-recruits) 10.5%, transparent);
  border: 1px solid color-mix(in srgb, var(--tab-recruits) 12.6%, transparent);
  animation: floatBob 6.5s ease-in-out infinite reverse;
}

.fc-3 {
  width: 90px;
  height: 90px;
  top: 30%;
  left: 8%;
  background: color-mix(in srgb, var(--tab-commission) 12.6%, transparent);
  animation: floatBob 10s ease-in-out infinite 2s;
}

.fc-4 {
  width: 120px;
  height: 120px;
  top: 55%;
  right: 6%;
  background: color-mix(in srgb, var(--tab-comparison) 9.5%, transparent);
  border: 1px solid color-mix(in srgb, var(--tab-comparison) 10.5%, transparent);
  animation: floatBob 9s ease-in-out infinite 1s;
}

.fc-5 {
  width: 50px;
  height: 50px;
  top: 18%;
  right: 22%;
  background: color-mix(in srgb, var(--tab-emails) 12.6%, transparent);
  animation: floatBob 7s ease-in-out infinite 3s;
}

.fc-6 {
  width: 280px;
  height: 280px;
  bottom: 8%;
  right: -90px;
  background: color-mix(in srgb, var(--tab-maslaka) 8.4%, transparent);
  border: 1px solid color-mix(in srgb, var(--tab-maslaka) 10.5%, transparent);
  animation: floatBob 12s ease-in-out infinite 0.5s;
}

.fc-7 {
  width: 65px;
  height: 65px;
  bottom: 35%;
  left: 18%;
  background: color-mix(in srgb, var(--tab-ai) 14.7%, transparent);
  border: 1px solid color-mix(in srgb, var(--tab-ai) 12.6%, transparent);
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

/* Inside a tab the fixed rail owns the left edge: keep content clear of it.
   Rail = left 24 + 76 wide (≥1181px) / left 12 + 66 wide (721–1180px);
   hidden ≤720px. The hover-open rail is an overlay on purpose — it doesn't
   reflow the page. */
.workspace--railed { padding-left: 112px; }
@media (max-width: 1180px) { .workspace--railed { padding-left: 88px; } }
@media (max-width: 720px) { .workspace--railed { padding-left: 0; } }

.workspace-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px 60px;
  transition: max-width 0.5s cubic-bezier(0.16, 1, 0.3, 1), padding 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.tab-content {
  min-height: 400px;
}
/* The top-right corner holds floating widgets (the AI orb, the cycle clock).
   The tab strip already keeps clear of them; the page did not, so between
   phone width and ~1380px (where the centred 1200px column reaches that
   corner) they sat on top of content — a hero label read as "דוקציה…" (QA
   2026-09-30). Reserve the same gutter on that side. RTL: inline-start = right. */
@media (min-width: 701px) and (max-width: 1380px) {
  .workspace-main { padding-inline-start: 88px; }
}


/* ── iOS-style app launch ──────────────────────────────────────────────── */
.launch-surface {
  position: fixed;
  /* Laid out at the full viewport and scaled DOWN to wherever it should be.
     Animating a transform keeps the travel on the compositor; animating
     left/top/width/height put a layout pass in every frame and you could see
     it. `transform-origin` at the top-left corner is what makes the
     translate a plain viewport coordinate, RTL or not. */
  inset: 0;
  transform-origin: 0 0;
  z-index: 900;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.16);
  pointer-events: none;
  overflow: hidden;
  display: grid;
  place-items: center;
  will-change: transform, opacity, border-radius;
}
/* The glyph rides inside the surface, so it inherits its scale — its own
   animation counter-scales it back to a readable size. */
/* the glyph is on screen ~⅓s during a launch — sketch the drawing inside that */
.launch-glyph :deep(.s) { animation-duration: 0.32s !important; animation-delay: 0s !important; }
.launch-glyph :deep(.dot), .launch-glyph :deep(.pct) { animation-delay: 0.2s !important; }
.launch-glyph {
  display: grid;
  place-items: center;
  color: var(--launch-accent, var(--text-muted));
  --accent: var(--launch-accent);
  --accent-ink: var(--launch-accent);
  opacity: 0;
  will-change: transform, opacity;
}
/* A hairline of the tab's own colour rides up with the surface, so you can
   see WHICH app is opening for the whole of the travel. */
.launch-surface::before {
  content: '';
  position: absolute;
  inset-inline: 0;
  top: 0;
  height: 3px;
  background: var(--launch-accent, transparent);
}
/* The view you are leaving falls back as the app comes forward. */
.view-receding {
  transform: scale(0.965);
  opacity: 0.45;
  transition: transform 0.42s cubic-bezier(0.32, 0.72, 0, 1), opacity 0.42s ease;
}
.view-none-enter-active,
.view-none-leave-active { animation: none; transition: none; }
@media (prefers-reduced-motion: reduce) {
  .view-receding { transform: none; opacity: 1; transition: none; }
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
    /* The corner widgets stack down the right edge on small screens; keep
       the page clear of them, lined up under the tab strip's 64px gutter. */
    padding-inline-start: 64px;
  }
}
.setup-return {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); z-index: 1040;
  display: inline-flex; align-items: center; gap: 8px; height: 44px; padding: 0 20px;
  border: none; border-radius: 999px; background: var(--primary, #181818); color: #fff;
  font-family: 'Heebo', sans-serif; font-size: 14px; font-weight: 700; cursor: pointer;
  box-shadow: 0 10px 28px rgba(24, 24, 24, 0.28);
}
.setup-return:hover { background: var(--primary-deep, #000); }
.setup-return-enter-active, .setup-return-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.setup-return-enter-from, .setup-return-leave-to { opacity: 0; transform: translate(-50%, 12px); }
</style>
