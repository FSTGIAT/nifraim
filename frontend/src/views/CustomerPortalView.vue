<template>
  <div class="portal-page">
    <header class="portal-header">
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
    </header>

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
    state.value = 'loading'
    await portalStore.fetchDashboard(token.value)
    state.value = 'dashboard'
  } catch {
    if (state.value === 'loading') state.value = 'error'
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
/* ── Flat sky theme: override app tokens on .portal-page ──
 * All portal/*.vue children use --primary / --bg / --card-bg / --text / --text-muted / --border
 * Redefining them here cascades to every child without touching each file.
 */
.portal-page {
  --primary: #4E9DD0;
  --primary-deep: #35719A;
  --primary-light: rgba(78, 157, 208, 0.12);
  --primary-glow: rgba(78, 157, 208, 0.14);
  --bg: #F5F8FB;
  --bg-surface: #FFFFFF;
  --card-bg: #FFFFFF;
  --text: #1A2733;
  --text-secondary: rgba(26, 39, 51, 0.78);
  --text-muted: rgba(26, 39, 51, 0.55);
  --border: rgba(26, 39, 51, 0.10);
  --border-subtle: rgba(26, 39, 51, 0.06);
  --green: #2E844A;
  --green-light: #EBF7EE;
  --green-deep: #1B5E20;
  --red: #EA001E;
  --red-deep: #C23934;
  --red-light: #FEF1EE;
  --amber: #E8720A;
  --amber-light: #FFF3E0;
  --shadow-sm: 0 1px 3px rgba(26, 39, 51, 0.06);
  --shadow-md: 0 2px 8px rgba(26, 39, 51, 0.07);
  --shadow-lg: 0 12px 32px -8px rgba(26, 39, 51, 0.14);
  --shadow-glow: 0 0 0 3px rgba(78, 157, 208, 0.18);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;

  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: 'Heebo', sans-serif;
  direction: rtl;
  position: relative;
  overflow-x: hidden;
}

/* ── Branded header ── */
.portal-header {
  position: relative;
  z-index: 2;
  padding: 18px 32px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  text-align: center;
}

.portal-brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.brand-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-icon svg {
  width: 20px;
  height: 20px;
}

.brand-name {
  font-size: 22px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.3px;
}

.portal-content {
  position: relative;
  z-index: 2;
  max-width: 1100px;
  margin: 0 auto;
  padding: 36px 20px 60px;
}

.portal-loading {
  text-align: center;
  padding: 100px 0;
  color: var(--text-muted);
  font-size: 14px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 18px;
}

.portal-error {
  text-align: center;
  padding: 80px 20px;
  max-width: 480px;
  margin: 0 auto;
}

.portal-error p {
  color: var(--text);
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
}

.portal-error button {
  padding: 14px 32px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.portal-error button:hover {
  background: var(--primary-deep);
  box-shadow: var(--shadow-md);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Print: white bg ── */
@media print {
  .portal-page {
    background: #fff !important;
  }
  .portal-header {
    background: #fff !important;
    border-bottom: 1px solid var(--border) !important;
  }
}
</style>
