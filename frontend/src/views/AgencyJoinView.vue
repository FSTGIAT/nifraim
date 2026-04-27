<template>
  <div class="join-page">
    <div class="join-card">
      <div v-if="loading" class="state">טוען הזמנה...</div>
      <div v-else-if="error" class="state error">{{ error }}</div>
      <div v-else>
        <h1>הוזמנת לסוכנות {{ data.agency.name }}</h1>
        <p class="muted">ההזמנה הופנתה ל-<strong>{{ data.email }}</strong></p>
        <p v-if="data.email.toLowerCase() !== auth.user?.email?.toLowerCase()" class="warn">
          את/ה מחובר/ת בתור {{ auth.user?.email }}. ההזמנה הופנתה לכתובת אחרת.
        </p>
        <button v-else class="btn-accept" :disabled="accepting" @click="accept">
          {{ accepting ? 'מצרף...' : 'הצטרפות לסוכנות' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const error = ref('')
const accepting = ref(false)
const data = ref(null)

onMounted(async () => {
  if (!auth.user) await auth.fetchUser()
  try {
    const res = await api.get(`/agency/invites/lookup/${route.params.token}`)
    data.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'הזמנה לא תקינה או פגה'
  } finally {
    loading.value = false
  }
})

async function accept() {
  accepting.value = true
  try {
    await api.post('/agency/invites/accept', { token: route.params.token })
    await auth.fetchUser()
    router.push(auth.homePath)
  } catch (e) {
    error.value = e.response?.data?.detail || 'נכשל הצירוף לסוכנות'
  } finally {
    accepting.value = false
  }
}
</script>

<style scoped>
.join-page {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #FFF8F0 0%, #FFFFFF 60%);
  font-family: 'Heebo', sans-serif;
}
.join-card {
  background: #fff;
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  padding: 36px 40px;
  width: min(440px, 90vw);
  text-align: center;
  box-shadow: var(--shadow-lg);
}
h1 { font-size: 22px; margin-bottom: 12px; color: var(--text); }
.muted { color: var(--text-muted); margin-bottom: 24px; }
.warn { color: var(--red); margin-top: 18px; font-size: 14px; }
.btn-accept {
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 12px 28px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
}
.btn-accept:hover:not(:disabled) { background: var(--primary-deep); }
.btn-accept:disabled { opacity: 0.6; cursor: wait; }
.state { padding: 30px; color: var(--text-muted); }
.state.error { color: var(--red); }
</style>
