<template>
  <div class="expired-page">
    <div class="expired-card">
      <div class="expired-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      </div>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
      <p v-if="subscriptionStore.status?.last4_digits" class="card-info">
        כרטיס בתיק: <span class="ltr-number">****{{ subscriptionStore.status.last4_digits }}</span>
      </p>
      <div class="expired-actions">
        <button class="btn-renew" @click="handleRenew" :disabled="renewLoading">
          <span v-if="renewLoading" class="spinner"></span>
          <span v-else>חידוש מנוי</span>
        </button>
        <button class="btn-logout" @click="logout">התנתקות</button>
      </div>
      <p v-if="error" class="error-msg">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSubscriptionStore } from '../stores/subscription.js'

const router = useRouter()
const subscriptionStore = useSubscriptionStore()
const renewLoading = ref(false)
const error = ref('')

onMounted(() => {
  subscriptionStore.fetchStatus()
})

const title = computed(() => {
  const s = subscriptionStore.status
  if (!s) return 'המנוי שלכם לא פעיל'
  if (s.status === 'cancelled') return 'המנוי שלכם בוטל'
  if (s.status === 'expired') return 'המנוי שלכם פג תוקף'
  return 'המנוי שלכם לא פעיל'
})

const subtitle = computed(() => {
  const s = subscriptionStore.status
  if (!s) return 'כדי לגשת למערכת Nifraim, יש לחדש את המנוי.'
  if (s.status === 'cancelled') return 'ביטלתם את המנוי. לחדש מנוי כדי להמשיך להשתמש במערכת.'
  if (s.status === 'expired') return 'חיוב אוטומטי נכשל. חדשו את המנוי כדי להמשיך.'
  return 'כדי לגשת למערכת Nifraim, יש לחדש את המנוי.'
})

async function handleRenew() {
  renewLoading.value = true
  error.value = ''
  try {
    const result = await subscriptionStore.renewSubscription()
    if (result.payment_url) {
      window.location.href = result.payment_url
    }
  } catch (e) {
    error.value = e.message
  } finally {
    renewLoading.value = false
  }
}

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
.expired-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.expired-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 60px 48px;
  text-align: center;
  max-width: 460px;
  width: 100%;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.6s var(--transition);
}

.expired-icon {
  margin-bottom: 24px;
}

.expired-card h1 {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 12px;
  color: var(--text);
}

.expired-card p {
  font-size: 16px;
  color: var(--text-muted);
  margin-bottom: 16px;
  line-height: 1.5;
}

.card-info {
  font-size: 14px !important;
  color: var(--text-secondary) !important;
  background: var(--bg-surface);
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  display: inline-block;
  margin-bottom: 24px !important;
}

.expired-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.btn-renew {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-renew:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.3);
}

.btn-renew:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-logout {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  background: none;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}

.btn-logout:hover {
  border-color: var(--red);
  color: var(--red);
}

.error-msg {
  color: var(--red);
  font-size: 14px;
  margin-top: 16px;
  padding: 10px 14px;
  background: var(--red-light);
  border-radius: var(--radius-sm);
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
