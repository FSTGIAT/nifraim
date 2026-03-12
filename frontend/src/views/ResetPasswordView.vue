<template>
  <div class="auth-split">
    <!-- Gradient Panel (Left) -->
    <div class="auth-brand-panel">
      <div class="brand-content">
        <div class="brand-logo">
          <div class="brand-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span class="brand-name">Nifraim</span>
        </div>
        <h1 class="brand-heading">סיסמה חדשה</h1>
        <p class="brand-subtitle">בחרו סיסמה חדשה לחשבון שלכם</p>
      </div>
      <svg class="brand-wave" viewBox="0 0 500 150" preserveAspectRatio="none">
        <path d="M0,60 C150,120 350,0 500,80 L500,150 L0,150 Z" fill="rgba(255,255,255,0.08)"/>
        <path d="M0,90 C120,140 380,30 500,100 L500,150 L0,150 Z" fill="rgba(255,255,255,0.05)"/>
      </svg>
      <div class="brand-circle brand-circle-1"></div>
      <div class="brand-circle brand-circle-2"></div>
      <div class="brand-circle brand-circle-3"></div>
    </div>

    <!-- Form Panel (Right) -->
    <div class="auth-form-panel">
      <div class="form-content">
        <template v-if="!done">
          <h2 class="form-heading">הגדרת סיסמה חדשה</h2>
          <p class="form-subtitle">הזינו את הסיסמה החדשה שלכם</p>

          <form @submit.prevent="handleSubmit">
            <div class="field">
              <label>סיסמה חדשה</label>
              <input type="password" v-model="password" required placeholder="••••••••" dir="ltr" minlength="6" />
            </div>
            <div class="field">
              <label>אימות סיסמה</label>
              <input type="password" v-model="confirmPassword" required placeholder="••••••••" dir="ltr" minlength="6" />
            </div>
            <Transition name="fade">
              <p class="error" v-if="error">{{ error }}</p>
            </Transition>
            <button type="submit" class="btn-submit" :disabled="loading">
              <template v-if="loading">
                <div class="btn-spinner"></div>
                <span>שומר...</span>
              </template>
              <template v-else>שמור סיסמה חדשה</template>
            </button>
          </form>
        </template>

        <div class="success-state" v-else>
          <div class="success-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
          </div>
          <h3 class="success-title">הסיסמה שונתה בהצלחה!</h3>
          <p class="success-text">כעת תוכלו להתחבר עם הסיסמה החדשה שלכם.</p>
          <router-link to="/login" class="back-link">התחבר</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import client from '../api/client.js'

const route = useRoute()

const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)
const done = ref(false)

async function handleSubmit() {
  error.value = ''

  if (password.value !== confirmPassword.value) {
    error.value = 'הסיסמאות אינן תואמות'
    return
  }

  if (password.value.length < 6) {
    error.value = 'הסיסמה חייבת להכיל לפחות 6 תווים'
    return
  }

  loading.value = true
  try {
    await client.post('/auth/reset-password', {
      token: route.query.token,
      password: password.value,
    })
    done.value = true
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה באיפוס הסיסמה'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-split {
  min-height: 100vh;
  display: flex;
  direction: rtl;
  font-family: 'Heebo', sans-serif;
}

.auth-brand-panel {
  width: 45%;
  background: linear-gradient(135deg, #E65100 0%, #F57C00 40%, #FF9800 70%, #FFB74D 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden;
  padding: 60px 40px;
}

.brand-content {
  position: relative;
  z-index: 2;
  text-align: center;
  color: #fff;
  max-width: 380px;
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 40px;
}

.brand-icon {
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  backdrop-filter: blur(8px);
}

.brand-name {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.brand-heading {
  font-size: 42px;
  font-weight: 900;
  margin-bottom: 12px;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 18px;
  opacity: 0.85;
  font-weight: 400;
  line-height: 1.6;
}

.brand-wave {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  height: 120px;
  z-index: 1;
}

.brand-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  z-index: 1;
}

.brand-circle-1 {
  width: 200px;
  height: 200px;
  top: -40px;
  left: -60px;
  animation: floatCircle 8s ease-in-out infinite;
}

.brand-circle-2 {
  width: 140px;
  height: 140px;
  bottom: 80px;
  right: -30px;
  animation: floatCircle 6s ease-in-out infinite reverse;
}

.brand-circle-3 {
  width: 80px;
  height: 80px;
  top: 30%;
  right: 10%;
  background: rgba(255, 255, 255, 0.04);
  animation: floatCircle 10s ease-in-out infinite 2s;
}

@keyframes floatCircle {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

.auth-form-panel {
  width: 55%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 60px 40px;
}

.form-content {
  width: 100%;
  max-width: 400px;
  animation: slideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.form-heading {
  font-size: 32px;
  font-weight: 800;
  color: #181818;
  margin-bottom: 8px;
}

.form-subtitle {
  color: #888;
  font-size: 15px;
  margin-bottom: 36px;
}

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

.error {
  color: #d32f2f;
  font-size: 14px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: #FEF1EE;
  border-radius: 10px;
  border: 1px solid rgba(211, 47, 47, 0.15);
}

.success-state {
  text-align: center;
  padding: 20px 0;
}

.success-icon {
  margin-bottom: 20px;
}

.success-title {
  font-size: 24px;
  font-weight: 800;
  color: #181818;
  margin-bottom: 12px;
}

.success-text {
  font-size: 15px;
  color: #888;
  line-height: 1.7;
  margin-bottom: 28px;
}

.back-link {
  display: inline-block;
  padding: 12px 32px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border-radius: 50px;
  font-size: 15px;
  font-weight: 700;
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.25);
}

.back-link:hover {
  background: linear-gradient(135deg, #E65100, #F57C00);
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.35);
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .auth-split { flex-direction: column; }
  .auth-brand-panel { width: 100%; padding: 48px 24px 36px; min-height: auto; }
  .brand-heading { font-size: 28px; }
  .brand-subtitle { font-size: 15px; }
  .auth-form-panel { width: 100%; padding: 36px 24px 48px; }
  .form-content { max-width: 100%; }
  .brand-circle-1 { width: 120px; height: 120px; }
  .brand-circle-2 { width: 80px; height: 80px; }
  .brand-wave { height: 60px; }
}

@media (max-width: 480px) {
  .auth-brand-panel { padding: 36px 20px 28px; }
  .brand-heading { font-size: 24px; }
  .brand-logo { margin-bottom: 24px; }
  .auth-form-panel { padding: 28px 20px 40px; }
  .form-heading { font-size: 26px; }
}
</style>
