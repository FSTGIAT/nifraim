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
        v-if="state === 'login'"
        :token="token"
        :loading="loggingIn"
        :error="portalStore.error"
        @submit="onLogin"
      />

      <!-- Loading dashboard data -->
      <div v-else-if="state === 'loading'" class="portal-loading">
        <div class="spinner"></div>
        <p>טוען נתונים...</p>
      </div>

      <!-- Dashboard -->
      <PortalDashboard
        v-else-if="state === 'dashboard'"
        :data="portalStore.dashboardData"
        :token="token"
        @logout="onLogout"
      />

      <!-- Error state -->
      <div v-else-if="state === 'error'" class="portal-error">
        <p>{{ portalStore.error || 'שגיאה בטעינת הנתונים' }}</p>
        <button @click="state = 'login'; portalStore.logout()">נסה שוב</button>
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

const state = ref('login')   // login | loading | dashboard | error
const loggingIn = ref(false)

async function onLogin(password) {
  loggingIn.value = true
  portalStore.error = null
  try {
    await portalStore.accessPortal(token.value, password)
    // Password accepted — now fetch dashboard
    state.value = 'loading'
    await portalStore.fetchDashboard(token.value)
    state.value = 'dashboard'
  } catch {
    if (state.value === 'loading') {
      state.value = 'error'
    }
    // If still on login, error is shown by the form
  } finally {
    loggingIn.value = false
  }
}

function onLogout() {
  portalStore.logout()
  state.value = 'login'
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

.portal-error {
  text-align: center;
  padding: 60px 0;
}

.portal-error p {
  color: var(--red);
  font-size: 15px;
  margin-bottom: 16px;
}

.portal-error button {
  padding: 10px 24px;
  background: var(--primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  transition: all 0.2s var(--transition);
}

.portal-error button:hover {
  background: var(--primary-deep);
}
</style>
