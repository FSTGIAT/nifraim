<template>
  <form @submit.prevent="handleRegister">
    <div class="field">
      <label>שם מלא</label>
      <input type="text" v-model="fullName" placeholder="שם מלא" />
    </div>
    <div class="field">
      <label>אימייל</label>
      <input type="email" v-model="email" required placeholder="your@email.com" dir="ltr" />
    </div>
    <div class="field">
      <label>סיסמה</label>
      <input type="password" v-model="password" required placeholder="••••••••" dir="ltr" minlength="6" />
    </div>
    <Transition name="fade">
      <p class="error" v-if="error">{{ error }}</p>
    </Transition>
    <button type="submit" class="btn-submit" :disabled="loading">
      <template v-if="loading">
        <div class="btn-spinner"></div>
        <span>נרשם...</span>
      </template>
      <template v-else>הרשם</template>
    </button>
    <p class="link">
      כבר יש לך חשבון? <router-link to="/login">התחבר כאן</router-link>
    </p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()

const fullName = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await auth.register(email.value, password.value, fullName.value || null)
    router.push('/workspace')
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בהרשמה'
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
  color: #A0A0A0;
}

input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  font-size: 15px;
  font-family: 'Heebo', sans-serif;
  background: #1a1a1a;
  color: #F5F5F5;
  transition: all 0.2s;
}

input:focus {
  border-color: #F57C00;
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.15);
  outline: none;
}

input::placeholder {
  color: #555;
}

.btn-submit {
  width: 100%;
  padding: 14px;
  background: #F57C00;
  color: #0a0a0a;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 700;
  font-family: 'Heebo', sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-submit:hover:not(:disabled) {
  background: #FF9800;
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.3);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(10, 10, 10, 0.3);
  border-top-color: #0a0a0a;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.error {
  color: #ef5350;
  font-size: 14px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: rgba(239, 83, 80, 0.1);
  border-radius: 10px;
  border: 1px solid rgba(239, 83, 80, 0.2);
}

.link {
  text-align: center;
  margin-top: 28px;
  font-size: 15px;
  color: #666;
}

.link a {
  color: #F57C00;
  font-weight: 600;
  transition: color 0.2s;
  text-decoration: none;
}

.link a:hover {
  color: #FF9800;
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
