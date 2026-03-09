<template>
  <div class="portal-page">
    <div class="portal-header">
      <div class="portal-brand">
        <div class="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span class="brand-name">Nifraim</span>
      </div>
    </div>

    <div class="portal-content">
      <!-- Password Form -->
      <PortalPasswordForm
        v-if="!portalStore.authenticated"
        :token="token"
        :loading="loading"
        :error="portalStore.error"
        @submit="onLogin"
      />

      <!-- Dashboard -->
      <PortalDashboard
        v-else-if="portalStore.dashboardData"
        :data="portalStore.dashboardData"
        @logout="onLogout"
      />

      <!-- Loading dashboard data -->
      <div v-else-if="loading" class="portal-loading">
        <div class="spinner"></div>
        <p>טוען נתונים...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { usePortalStore } from '../stores/portal.js'
import PortalPasswordForm from '../components/portal/PortalPasswordForm.vue'
import PortalDashboard from '../components/portal/PortalDashboard.vue'

const route = useRoute()
const portalStore = usePortalStore()
const token = computed(() => route.params.token)
const loading = ref(false)

async function onLogin() {
  loading.value = true
  try {
    await portalStore.fetchDashboard(token.value)
  } catch {
    // error shown in store
  } finally {
    loading.value = false
  }
}

function onLogout() {
  portalStore.logout()
}
</script>

<style scoped>
.portal-page {
  min-height: 100vh;
  background: var(--bg);
  direction: rtl;
}

.portal-header {
  padding: 14px 32px;
  text-align: center;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--card-bg);
}

.portal-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--primary), var(--accent-cyan, #FF9800));
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.brand-icon svg {
  width: 18px;
  height: 18px;
}

.brand-name {
  font-size: 20px;
  font-weight: 800;
  color: var(--text);
}

.portal-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 20px;
}

.portal-loading {
  text-align: center;
  padding: 80px 0;
  color: var(--text-muted);
  font-size: 14px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}
</style>
