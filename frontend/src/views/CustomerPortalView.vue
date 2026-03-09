<template>
  <div class="portal-page">
    <div class="portal-header">
      <h1 class="portal-logo">InsureFlow</h1>
    </div>

    <div class="portal-content">
      <!-- Password Form -->
      <PortalPasswordForm
        v-if="!portalStore.authenticated"
        :token="token"
        :loading="portalStore.loading"
        :error="portalStore.error"
        @submit="onLogin"
      />

      <!-- Dashboard -->
      <PortalDashboard
        v-else-if="portalStore.dashboardData"
        :data="portalStore.dashboardData"
        @logout="portalStore.logout()"
      />

      <!-- Loading dashboard data -->
      <div v-else-if="portalStore.loading" class="portal-loading">
        <div class="spinner"></div>
        <p>טוען נתונים...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { usePortalStore } from '../stores/portal.js'
import PortalPasswordForm from '../components/portal/PortalPasswordForm.vue'
import PortalDashboard from '../components/portal/PortalDashboard.vue'

const route = useRoute()
const portalStore = usePortalStore()
const token = computed(() => route.params.token)

async function onLogin() {
  try {
    await portalStore.fetchDashboard(token.value)
  } catch {
    // error shown in store
  }
}
</script>

<style scoped>
.portal-page {
  min-height: 100vh;
  background: var(--bg);
  direction: rtl;
}

.portal-header {
  padding: 20px 32px;
  text-align: center;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--card-bg);
}

.portal-logo {
  font-size: 22px;
  font-weight: 800;
  color: var(--primary);
  margin: 0;
}

.portal-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 20px;
}

.portal-loading {
  text-align: center;
  padding: 80px 0;
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
