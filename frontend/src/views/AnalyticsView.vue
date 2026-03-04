<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <div class="header-content">
        <div class="header-right">
          <h1>לוח בקרה - התאמת עמלות</h1>
          <TabNav />
        </div>
        <div class="header-actions">
          <span class="user-name" v-if="auth.user">{{ auth.user.full_name || auth.user.email }}</span>
          <button class="btn-logout" @click="handleLogout">יציאה</button>
        </div>
      </div>
    </header>

    <main class="analytics-main">
      <div v-if="analyticsStore.loading" class="loading-state">
        <div class="spinner"></div>
        <span>טוען נתוני ניתוח...</span>
      </div>

      <div v-else-if="analyticsStore.error" class="error-state">
        <p>{{ analyticsStore.error }}</p>
        <button class="btn-retry" @click="loadAnalytics">נסה שוב</button>
      </div>

      <div v-else-if="!analyticsStore.data" class="empty-state">
        <p>אין נתונים לניתוח</p>
        <p class="hint">העלה קובץ Excel בלשונית הרשומות כדי להתחיל</p>
      </div>

      <div v-else class="charts-grid">
        <StatusPieChart :data="analyticsStore.data.status_distribution" />
        <CompanyBarChart :data="analyticsStore.data.company_breakdown" />
        <ProductChart :data="analyticsStore.data.product_breakdown" />
        <TopMismatchesTable :data="analyticsStore.data.top_mismatches" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useRecordsStore } from '../stores/records.js'
import { useAnalyticsStore } from '../stores/analytics.js'
import TabNav from '../components/dashboard/TabNav.vue'
import StatusPieChart from '../components/analytics/StatusPieChart.vue'
import CompanyBarChart from '../components/analytics/CompanyBarChart.vue'
import ProductChart from '../components/analytics/ProductChart.vue'
import TopMismatchesTable from '../components/analytics/TopMismatchesTable.vue'

const router = useRouter()
const auth = useAuthStore()
const recordsStore = useRecordsStore()
const analyticsStore = useAnalyticsStore()

onMounted(async () => {
  await auth.fetchUser()
  loadAnalytics()
})

watch(() => recordsStore.filters.uploadId, () => {
  loadAnalytics()
})

function loadAnalytics() {
  analyticsStore.fetchAnalytics(recordsStore.filters.uploadId || null)
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
}

.dashboard-header {
  background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
  border-bottom: 1px solid var(--border);
  padding: 16px 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.header-content h1 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-name {
  color: var(--text-secondary);
  font-size: 14px;
}

.btn-logout {
  background: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 16px;
  color: var(--text-secondary);
  font-size: 14px;
  transition: all 0.2s;
}

.btn-logout:hover {
  background: var(--red);
  color: white;
  border-color: var(--red);
}

.analytics-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 80px 24px;
  color: var(--text-secondary);
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state p {
  color: var(--red);
  margin-bottom: 12px;
}

.btn-retry {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 24px;
  font-size: 14px;
}

.btn-retry:hover {
  background: var(--primary-hover);
}

.empty-state .hint {
  font-size: 13px;
  color: var(--light-gray);
  margin-top: 8px;
}

@media (max-width: 900px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  .header-right {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
