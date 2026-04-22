<template>
  <div class="portal-page">
    <!-- Cream-DNA background orbs -->
    <div class="portal-orbs" aria-hidden="true">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
    </div>

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
/* ── Cream DNA: scope marketing tokens AND override app tokens on .portal-page ──
 * All portal/*.vue children use --primary / --bg / --card-bg / --text / --text-muted / --border
 * Redefining them here cascades to every child without touching each file.
 */
.portal-page {
  /* Landing tokens */
  --land-orange: #E8660A;
  --land-orange-bright: #F57C00;
  --land-orange-deep: #C85A00;
  --land-orange-glow: rgba(232, 102, 10, 0.1);
  --cream-bg: #F5F0EB;
  --cream-surface: #EDE8E1;
  --cream-surface-3: #F9F6F2;
  --cream-text: #2D2522;
  --cream-text-muted: rgba(45, 37, 34, 0.6);
  --cream-text-dim: rgba(45, 37, 34, 0.35);

  /* Override app tokens so children inherit cream theme */
  --primary: #E8660A;
  --primary-deep: #C85A00;
  --primary-light: rgba(232, 102, 10, 0.08);
  --primary-glow: rgba(232, 102, 10, 0.1);
  --amber: #C85A00;
  --bg: #F5F0EB;
  --bg-surface: #F9F6F2;
  --card-bg: #FFFFFF;
  --text: #2D2522;
  --text-secondary: rgba(45, 37, 34, 0.75);
  --text-muted: rgba(45, 37, 34, 0.55);
  --border: rgba(45, 37, 34, 0.1);
  --border-subtle: rgba(45, 37, 34, 0.06);
  --shadow-sm: 0 1px 3px rgba(45, 37, 34, 0.05);
  --shadow-md: 0 2px 8px rgba(45, 37, 34, 0.06);
  --shadow-lg: 0 12px 32px -8px rgba(45, 37, 34, 0.12);
  --shadow-glow: 0 0 0 3px rgba(232, 102, 10, 0.15);

  min-height: 100vh;
  background: var(--cream-bg);
  color: var(--cream-text);
  font-family: 'Heebo', sans-serif;
  direction: rtl;
  position: relative;
  overflow-x: hidden;
}

/* ── Background orbs ── */
.portal-orbs {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.portal-orbs .orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
}

.portal-orbs .orb-1 {
  width: 600px;
  height: 600px;
  background: rgba(232, 102, 10, 0.18);
  top: -15%;
  left: -10%;
}

.portal-orbs .orb-2 {
  width: 460px;
  height: 460px;
  background: rgba(232, 102, 10, 0.12);
  bottom: -10%;
  right: -5%;
}

.portal-orbs .orb-3 {
  width: 380px;
  height: 380px;
  background: rgba(245, 124, 0, 0.1);
  top: 40%;
  left: 50%;
}

/* ── Branded header (mirrors landing nav--light) ── */
.portal-header {
  position: relative;
  z-index: 2;
  padding: 18px 32px;
  background: rgba(245, 240, 235, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(45, 37, 34, 0.06);
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
  border-radius: 12px;
  background: var(--cream-text);
  color: var(--cream-bg);
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
  color: var(--cream-text);
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
  color: var(--cream-text-muted);
  font-size: 14px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(45, 37, 34, 0.08);
  border-top-color: var(--land-orange);
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
  color: var(--cream-text);
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
}

.portal-error button {
  padding: 14px 32px;
  background: var(--land-orange);
  color: #fff;
  border: none;
  border-radius: 40px;
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(232, 102, 10, 0.25);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.portal-error button:hover {
  background: var(--land-orange-deep);
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(232, 102, 10, 0.32);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Print: white bg, hide orbs ── */
@media print {
  .portal-page {
    background: #fff !important;
  }
  .portal-orbs {
    display: none !important;
  }
  .portal-header {
    background: #fff !important;
    border-bottom: 1px solid #E5E5E5 !important;
  }
}
</style>
