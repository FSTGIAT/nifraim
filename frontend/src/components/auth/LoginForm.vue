<template>
  <form @submit.prevent="handleLogin">
    <div class="field">
      <label>אימייל</label>
      <input type="email" v-model="email" required placeholder="your@email.com" dir="ltr" />
    </div>
    <div class="field">
      <label>סיסמה</label>
      <input type="password" v-model="password" required placeholder="••••••••" dir="ltr" />
    </div>
    <Transition name="fade">
      <p class="error" v-if="error">{{ error }}</p>
    </Transition>
    <button type="submit" class="btn-primary" :disabled="loading">
      <template v-if="loading">
        <div class="btn-spinner"></div>
        <span>מתחבר...</span>
      </template>
      <template v-else>התחבר</template>
    </button>
    <p class="link">
      אין לך חשבון? <router-link to="/register">הרשם כאן</router-link>
    </p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    router.push('/workspace')
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בהתחברות'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.field {
  margin-bottom: 20px;
}

label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-secondary);
}

input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 15px;
  background: var(--bg-surface);
  color: var(--text);
  transition: all 0.25s var(--transition);
}

input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

input::placeholder {
  color: var(--text-muted);
}

.btn-primary {
  width: 100%;
  padding: 13px;
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s var(--transition);
  position: relative;
  overflow: hidden;
}

.btn-primary::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.08) 50%, transparent 60%);
  background-size: 200% 100%;
  animation: shimmer 3s ease-in-out infinite;
}

.btn-primary:hover:not(:disabled) {
  box-shadow: 0 8px 24px var(--primary-light);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.5;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.error {
  color: var(--red);
  font-size: 13px;
  margin-bottom: 14px;
  padding: 8px 12px;
  background: var(--red-light);
  border-radius: 8px;
  border: 1px solid var(--red-light);
}

.link {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--text-muted);
}

.link a {
  color: var(--primary);
  font-weight: 600;
  transition: color 0.2s;
}

.link a:hover {
  color: var(--accent-cyan);
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }
</style>
