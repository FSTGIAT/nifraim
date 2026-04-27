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
    <div class="forgot-row">
      <router-link to="/forgot-password" class="forgot-link">שכחתי סיסמה</router-link>
    </div>
    <Transition name="fade">
      <p class="error" v-if="error">{{ error }}</p>
    </Transition>
    <button type="submit" class="btn-submit" :disabled="loading">
      <template v-if="loading">
        <div class="btn-spinner"></div>
        <span>מתחבר...</span>
      </template>
      <template v-else>התחבר</template>
    </button>
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
    router.push(auth.homePath)
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בהתחברות'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.field {
  margin-bottom: 22px;
}

label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #555;
}

input {
  width: 100%;
  padding: 14px 16px;
  border: 1.5px solid #E0E0E0;
  border-radius: 10px;
  font-size: 15px;
  font-family: 'Heebo', sans-serif;
  background: #FAFAFA;
  color: #181818;
  transition: all 0.2s;
}

input:focus {
  border-color: #F57C00;
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.12);
  outline: none;
  background: #fff;
}

input::placeholder {
  color: #B0B0B0;
}

.btn-submit {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border: none;
  border-radius: 50px;
  font-size: 16px;
  font-weight: 700;
  font-family: 'Heebo', sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.25);
}

.btn-submit:hover:not(:disabled) {
  background: linear-gradient(135deg, #E65100, #F57C00);
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.35);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.forgot-row {
  text-align: start;
  margin-bottom: 18px;
  margin-top: -8px;
}

.forgot-link {
  font-size: 13px;
  color: #F57C00;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.forgot-link:hover {
  color: #E65100;
  text-decoration: underline;
}

.error {
  color: #d32f2f;
  font-size: 14px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: #FEF1EE;
  border-radius: 10px;
  border: 1px solid rgba(211, 47, 47, 0.15);
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
