<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <div class="header-content">
        <div class="header-right">
          <div class="brand">
            <div class="brand-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <h1>לוח בקרה</h1>
          </div>
          <TabNav />
        </div>
        <div class="header-actions">
          <router-link to="/" class="btn-workspace">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"/>
              <polyline points="12 19 5 12 12 5"/>
            </svg>
            <span>חזרה</span>
          </router-link>
          <div class="user-pill" v-if="auth.user">
            <div class="user-avatar">{{ avatarLetter }}</div>
            <span class="user-label">{{ auth.user.full_name || auth.user.email }}</span>
          </div>
          <button class="btn-logout" @click="handleLogout">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </div>
      </div>
    </header>

    <main class="dashboard-main">
      <!-- Comparison Mode -->
      <template v-if="comparisonStore.result">
        <div class="comparison-header">
          <h2>תוצאות השוואה</h2>
          <button class="btn-back" @click="comparisonStore.reset()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
            <span>חזור לרשומות</span>
          </button>
        </div>
        <ComparisonSummaryCards :summary="dashActiveSummary" />
        <div class="dashboard-grid">
          <div class="main-content">
            <ComparisonTable
              ref="comparisonTableRef"
              :customers="comparisonStore.result.customers"
              :availableCompanies="comparisonStore.result.available_companies || []"
              :initialCompany="comparisonStore.result.commission_company_source || ''"
              @summary-update="dashFilteredSummary = $event"
            />
          </div>
          <aside class="sidebar">
            <FileUploader @uploaded="handleUpload" @compared="handleCompared" />
            <UploadHistory
              :uploads="uploadsStore.uploads"
              @delete="handleDeleteUpload"
              @filter="filterByUpload"
            />
            <CommissionRateTable @rates-changed="handleRatesChanged" />
          </aside>
        </div>
      </template>

      <!-- Normal Records Mode -->
      <template v-else>
        <SummaryCards :summary="recordsStore.summary" />
        <div class="dashboard-grid">
          <div class="main-content">
            <FilterBar
              :filters="recordsStore.filters"
              :uploads="uploadsStore.uploads"
              @apply="recordsStore.applyFilters()"
              @reset="recordsStore.resetFilters()"
            />
            <ReconciliationTable
              :records="recordsStore.records"
              :loading="recordsStore.loading"
              :sortBy="recordsStore.filters.sortBy"
              :sortDir="recordsStore.filters.sortDir"
              @sort="recordsStore.setSort"
              @client-click="openClientDetail"
            />
            <Pagination
              :page="recordsStore.pagination.page"
              :pages="recordsStore.pagination.pages"
              :total="recordsStore.pagination.total"
              @change="recordsStore.setPage"
            />
          </div>

          <aside class="sidebar">
            <FileUploader @uploaded="handleUpload" @compared="handleCompared" />
            <UploadHistory
              :uploads="uploadsStore.uploads"
              @delete="handleDeleteUpload"
              @filter="filterByUpload"
            />
            <CommissionRateTable />
          </aside>
        </div>
      </template>
    </main>

    <ClientDetailModal
      v-if="selectedClient"
      :idNumber="selectedClient"
      @close="selectedClient = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useRecordsStore } from '../stores/records.js'
import { useUploadsStore } from '../stores/uploads.js'
import { useComparisonStore } from '../stores/comparison.js'
import SummaryCards from '../components/dashboard/SummaryCards.vue'
import FileUploader from '../components/dashboard/FileUploader.vue'
import UploadHistory from '../components/dashboard/UploadHistory.vue'
import FilterBar from '../components/dashboard/FilterBar.vue'
import ReconciliationTable from '../components/dashboard/ReconciliationTable.vue'
import Pagination from '../components/dashboard/Pagination.vue'
import ClientDetailModal from '../components/dashboard/ClientDetailModal.vue'
import CommissionRateTable from '../components/commission/CommissionRateTable.vue'
import TabNav from '../components/dashboard/TabNav.vue'
import ComparisonSummaryCards from '../components/comparison/ComparisonSummaryCards.vue'
import ComparisonTable from '../components/comparison/ComparisonTable.vue'

const router = useRouter()
const auth = useAuthStore()
const recordsStore = useRecordsStore()
const uploadsStore = useUploadsStore()
const comparisonStore = useComparisonStore()

const selectedClient = ref(null)
const comparisonTableRef = ref(null)
const dashFilteredSummary = ref(null)

const dashActiveSummary = computed(() => {
  return dashFilteredSummary.value || comparisonStore.result?.summary || {}
})

const avatarLetter = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || ''
  return name.charAt(0).toUpperCase()
})

onMounted(async () => {
  await auth.fetchUser()
  await uploadsStore.fetchUploads()
  await Promise.all([recordsStore.fetchRecords(), recordsStore.fetchSummary()])
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}

async function handleUpload() {
  await uploadsStore.fetchUploads()
  await Promise.all([recordsStore.fetchRecords(), recordsStore.fetchSummary()])
}

async function handleCompared() {
  await uploadsStore.fetchUploads()
}

async function handleDeleteUpload(id) {
  await uploadsStore.deleteUpload(id)
  await Promise.all([recordsStore.fetchRecords(), recordsStore.fetchSummary()])
}

function filterByUpload(uploadId) {
  recordsStore.filters.uploadId = uploadId
  recordsStore.applyFilters()
}

function openClientDetail(idNumber) {
  selectedClient.value = idNumber
}

function handleRatesChanged() {
  if (comparisonTableRef.value) {
    comparisonTableRef.value.refreshRates()
  }
}
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

.dashboard-header {
  background: var(--bg);
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  height: 64px;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.header-content h1 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-workspace {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.25s;
}

.btn-workspace:hover {
  background: var(--bg-surface);
  color: var(--text);
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 6px;
  background: var(--bg-surface);
  border-radius: 100px;
  border: 1px solid var(--border-subtle);
}

.user-avatar {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-violet) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: white;
}

.user-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-logout {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: all 0.25s;
}

.btn-logout:hover {
  background: var(--red-light);
  color: var(--red);
}

.dashboard-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 24px;
  margin-top: 24px;
}

.main-content {
  min-width: 0;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Comparison Header */
.comparison-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.comparison-header h2 {
  font-size: 20px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.5px;
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: 8px 16px;
  color: var(--text-secondary);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.25s;
}

.btn-back:hover {
  background: var(--bg-surface);
  color: var(--text);
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .sidebar {
    order: -1;
  }
}
</style>
