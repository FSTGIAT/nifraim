<template>
  <div class="agency-shell" :dir="'rtl'">
    <AgencyShellDecor />
    <ImpersonationBanner />

    <!-- ─── Header ─── -->
    <header class="agency-header">
      <div class="header-inner">
        <div class="header-right">
          <router-link to="/agency" class="brand">
            <span class="brand-mark">N</span>
            <div>
              <div class="brand-name">Nifraim</div>
              <div class="brand-sub">פאנל סוכנות{{ agency ? ' · ' + agency.name : '' }}</div>
            </div>
          </router-link>
        </div>
        <div class="header-actions">
          <span class="user-name" v-if="auth.user">
            <span class="role-tag">{{ roleLabel(auth.user.role) }}</span>
            {{ auth.user.full_name || auth.user.email }}
          </span>
          <button class="btn-logout" @click="logout">יציאה</button>
        </div>
      </div>
    </header>

    <main class="agency-main">
      <div v-if="initialLoading" class="state">
        <div class="spinner"></div>
        <span>טוען נתוני סוכנות…</span>
      </div>

      <template v-else>
        <!-- Compact greeting strip -->
        <AgencyHomeStrip
          :first-name="firstName"
          :agency-name="agency?.name || ''"
          :overview="overview"
        />

        <!-- Always-visible tab strip — mirrors WorkspaceTabs -->
        <AgencyTabs v-model="activeTab" />

        <!-- Tab content -->
        <div class="tab-content">
          <AgencyOverviewTab
            v-if="activeTab === 'overview'"
            @select-tab="(t) => activeTab = t"
            @open-modal="onOpenModal"
            @view-agent="openAgentDetail"
            @open-ai="openAiSheet"
          />
          <AgencyComparisonTab        v-else-if="activeTab === 'comparison'"        @viewAgent="openAgentDetail" />
          <AgencyProductionTab        v-else-if="activeTab === 'production'"        @viewAgent="openAgentDetail" />
          <AgencyCommissionRatesTab   v-else-if="activeTab === 'commission-rates'" />
          <AgencyCompanyEmailsTab     v-else-if="activeTab === 'company-emails'" />
          <AgencyRecruitsTab          v-else-if="activeTab === 'recruits'"        />
          <AgencyAiLibrary
            v-else-if="activeTab === 'ai-library'"
            :data="agencyStore.knowledge"
            :loading="agencyStore.loading.knowledge"
            @refresh="agencyStore.fetchKnowledge()"
          />
        </div>
      </template>
    </main>

    <!-- Agent drill-in modal -->
    <AgencyAgentDetail
      :open="!!agentDetail"
      :data="agentDetail"
      @close="agentDetail = null"
      @uploadAs="onUploadAs"
    />

    <!-- AI conversation sheet — slide-in chat panel, agency-flavored -->
    <AiConversationSheet
      v-model:open="aiSheetOpen"
      :view-title="aiSheetViewTitle"
      :initial-question="aiSheetInitialQ"
      prompt-persona="agency_accountant"
    />

    <!-- Floating AI button — always visible, bottom-left in RTL -->
    <button
      class="ag-ai-fab"
      :class="{ 'ag-ai-fab--active': aiSheetOpen }"
      @click="openAiSheet({})"
      :title="'עוזר AI לסוכנות'"
      aria-label="פתח עוזר AI"
    >
      <span class="ag-ai-fab-orb" aria-hidden="true"></span>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8z"/>
        <path d="M19 3v4"/><path d="M5 17v4"/><path d="M3 19h4"/><path d="M17 19h4"/>
      </svg>
      <span class="ag-ai-fab-label">עוזר AI</span>
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useAgencyStore } from '../stores/agency.js'
import { startImpersonation } from '../api/client.js'

import ImpersonationBanner from '../components/agency/ImpersonationBanner.vue'
import AgencyShellDecor from '../components/agency/AgencyShellDecor.vue'
import AgencyHomeStrip from '../components/agency/AgencyHomeStrip.vue'
import AgencyTabs from '../components/agency/AgencyTabs.vue'
import AgencyOverviewTab from '../components/agency/tabs/AgencyOverviewTab.vue'
import AgencyComparisonTab from '../components/agency/tabs/AgencyComparisonTab.vue'
import AgencyProductionTab from '../components/agency/tabs/AgencyProductionTab.vue'
import AgencyCommissionRatesTab from '../components/agency/tabs/AgencyCommissionRatesTab.vue'
import AgencyCompanyEmailsTab from '../components/agency/tabs/AgencyCompanyEmailsTab.vue'
import AgencyRecruitsTab from '../components/agency/tabs/AgencyRecruitsTab.vue'
import AgencyAgentDetail from '../components/agency/AgencyAgentDetail.vue'
import AgencyAiLibrary from '../components/agency/AgencyAiLibrary.vue'
import AiConversationSheet from '../components/workspace/AiConversationSheet.vue'

const router = useRouter()
const auth = useAuthStore()
const agencyStore = useAgencyStore()

const initialLoading = ref(true)
const activeTab = ref('overview') // dashboard tab is the default landing
const agentDetail = ref(null)
const aiSheetOpen = ref(false)
const aiSheetViewTitle = ref('')
const aiSheetInitialQ = ref('')

const agency = computed(() => agencyStore.agency)
const overview = computed(() => agencyStore.overview)
const firstName = computed(() => (auth.user?.full_name || '').split(' ')[0] || 'חשב')

onMounted(async () => {
  if (!auth.user) await auth.fetchUser()
  await agencyStore.fetchSelf()
  await agencyStore.fetchOverview()
  initialLoading.value = false
})

function roleLabel(r) {
  if (r === 'agency_accountant') return 'חשב עמלות'
  if (r === 'agency_admin') return 'מנהל סוכנות'
  return ''
}

function logout() {
  auth.logout()
  router.push('/login')
}

async function openAgentDetail(rowOrId) {
  const id = typeof rowOrId === 'string' ? rowOrId : rowOrId.user_id
  agentDetail.value = null
  try {
    agentDetail.value = await agencyStore.fetchAgentDetail(id)
  } catch {
    alert('שגיאה בטעינת פירוט סוכן')
  }
}

function onOpenModal(kind) {
  if (kind === 'agents') activeTab.value = 'comparison'
  else if (kind === 'unpaid-detail') activeTab.value = 'comparison'
}

function openAiSheet({ initialQuestion = '', viewTitle = 'לוח בקרה — סוכנות' } = {}) {
  aiSheetViewTitle.value = viewTitle
  aiSheetInitialQ.value = initialQuestion || ''
  aiSheetOpen.value = true
}

import { watch } from 'vue'
// Lazy-load AI library knowledge when the user lands on that tab
watch(activeTab, async (t) => {
  if (t === 'ai-library' && !agencyStore.knowledge) {
    await agencyStore.fetchKnowledge()
  }
})

async function onUploadAs(rowOrId) {
  const agentId = typeof rowOrId === 'string' ? rowOrId : rowOrId.user_id
  const agentName = typeof rowOrId === 'string' ? '' : rowOrId.full_name
  try {
    const res = await agencyStore.impersonate(agentId)
    startImpersonation(res.access_token, res.target_name || agentName)
    window.location.href = '/workspace?tab=production'
  } catch (e) {
    alert(e.response?.data?.detail || 'נכשל בכניסה לסוכן')
  }
}
</script>

<style scoped>
.agency-shell {
  min-height: 100vh;
  background:
    radial-gradient(1200px 600px at 90% -10%, rgba(232, 102, 10, 0.05), transparent 60%),
    radial-gradient(900px 500px at -10% 110%, rgba(127, 86, 217, 0.04), transparent 60%),
    var(--bg);
  font-family: 'Heebo', sans-serif;
  position: relative;
}

.agency-header {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(140%) blur(10px);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  position: sticky; top: 0; z-index: 100;
  box-shadow: var(--shadow-sm);
}
.header-inner {
  max-width: 1280px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between; gap: 24px;
}
.header-right { display: flex; align-items: center; gap: 28px; }
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: inherit; }
.brand-mark {
  width: 34px; height: 34px; border-radius: 10px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-deep) 100%);
  color: #fff; display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 15px;
  box-shadow: 0 6px 14px rgba(245, 124, 0, 0.32);
}
.brand-name { font-size: 15px; font-weight: 800; color: var(--text); line-height: 1; }
.brand-sub { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.header-actions { display: flex; align-items: center; gap: 12px; }
.user-name {
  font-size: 13px; color: var(--text);
  display: inline-flex; align-items: center; gap: 8px;
}
.role-tag {
  background: var(--primary-light);
  color: var(--primary-deep); padding: 3px 10px; border-radius: 999px;
  font-size: 10.5px; font-weight: 700;
}
.btn-logout {
  background: transparent; border: 1px solid var(--border); border-radius: 8px;
  padding: 6px 12px; color: var(--text-secondary); font-size: 12.5px; cursor: pointer;
  transition: all .15s;
}
.btn-logout:hover { background: var(--text); color: #fff; border-color: var(--text); }

.agency-main {
  max-width: 1280px; margin: 0 auto;
  padding: 22px 24px 80px;
  position: relative; z-index: 2;
}

.tab-content {
  margin-top: 6px;
  animation: fadeUp .35s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.state { padding: 80px; text-align: center; color: var(--text-muted); position: relative; z-index: 2; }
.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin .8s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 700px) {
  .agency-main { padding: 16px 14px 60px; }
}

/* ─── Floating AI button (FAB) — bottom-left in RTL, always visible ─── */
.ag-ai-fab {
  position: fixed;
  bottom: 24px;
  /* RTL: left edge of viewport visually = "outside" — use right since direction:rtl */
  left: 24px;
  z-index: 1000;
  display: inline-flex; align-items: center; gap: 10px;
  padding: 12px 18px;
  background: linear-gradient(135deg, #F57C00 0%, #FF9800 60%, #C85A00 100%);
  color: #fff;
  border: none;
  border-radius: 999px;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 12px 32px -8px rgba(245, 124, 0, 0.55), 0 0 0 4px rgba(255, 255, 255, 0.3);
  transition: transform .2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow .2s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}
.ag-ai-fab:hover {
  transform: translateY(-3px) scale(1.03);
  box-shadow: 0 18px 40px -10px rgba(245, 124, 0, 0.7), 0 0 0 6px rgba(255, 255, 255, 0.4);
}
.ag-ai-fab--active {
  transform: scale(0.96);
  background: linear-gradient(135deg, #C85A00 0%, #F57C00 100%);
}
.ag-ai-fab-orb {
  position: absolute;
  inset: -50% -10% auto auto;
  width: 70%;
  aspect-ratio: 1;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.55), transparent 60%);
  filter: blur(12px);
  pointer-events: none;
  animation: ag-fab-orb 4s ease-in-out infinite;
}
@keyframes ag-fab-orb {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(-6px, 4px) scale(1.1); }
}
.ag-ai-fab-label { position: relative; z-index: 1; }
.ag-ai-fab svg { position: relative; z-index: 1; }

@media (max-width: 700px) {
  .ag-ai-fab-label { display: none; }
  .ag-ai-fab { padding: 14px; }
}
</style>
