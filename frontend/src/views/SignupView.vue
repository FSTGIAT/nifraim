<template>
  <div class="signup-page">
    <nav class="landing-nav">
      <div class="nav-content">
        <router-link to="/" class="nav-brand">
          <div class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span class="nav-name">Nifraim</span>
        </router-link>
      </div>
    </nav>

    <div class="signup-content">
      <!-- Progress -->
      <div class="progress-bar">
        <div class="progress-step" v-for="(s, i) in stepLabels" :key="i" :class="{ active: currentStep >= i, done: currentStep > i }">
          <div class="step-dot ltr-number">{{ currentStep > i ? '&#10003;' : i + 1 }}</div>
          <span>{{ s }}</span>
        </div>
      </div>

      <!-- Step 1: Details -->
      <div v-if="currentStep === 0" class="step-card">
        <h2>פרטים אישיים</h2>
        <p class="step-desc">מלאו את הפרטים שלכם להרשמה</p>
        <form @submit.prevent="goToStep(1)" class="signup-form">
          <div class="form-group">
            <label>שם מלא *</label>
            <input type="text" v-model="form.fullName" required placeholder="ישראל ישראלי" />
          </div>
          <div class="form-group">
            <label>אימייל *</label>
            <input type="email" v-model="form.email" required placeholder="email@example.com" dir="ltr" />
          </div>
          <div class="form-group">
            <label>טלפון *</label>
            <input type="tel" v-model="form.phone" required placeholder="05X-XXXXXXX" dir="ltr" />
          </div>
          <div class="form-group">
            <label>שם חברה (אופציונלי)</label>
            <input type="text" v-model="form.companyName" placeholder="סוכנות ביטוח" />
          </div>
          <button type="submit" class="btn-next" :disabled="!isStep1Valid">המשך לבחירת מסלול</button>
        </form>
      </div>

      <!-- Step 2: Plan -->
      <div v-if="currentStep === 1" class="step-card">
        <h2>בחירת מסלול</h2>
        <p class="step-desc">בחרו את המסלול המתאים לכם</p>
        <div class="plan-options">
          <div class="plan-option" :class="{ selected: form.plan === 'monthly' }" @click="form.plan = 'monthly'">
            <div class="plan-option-radio">
              <div class="radio-dot" v-if="form.plan === 'monthly'"></div>
            </div>
            <div class="plan-option-info">
              <div class="plan-option-name">חודשי</div>
              <div class="plan-option-price"><span class="ltr-number">&#8362;295</span> / חודש</div>
            </div>
          </div>
          <div class="plan-option" :class="{ selected: form.plan === 'yearly' }" @click="form.plan = 'yearly'">
            <div class="plan-option-radio">
              <div class="radio-dot" v-if="form.plan === 'yearly'"></div>
            </div>
            <div class="plan-option-info">
              <div class="plan-option-name">
                שנתי
                <span class="plan-option-badge">חודש חינם!</span>
              </div>
              <div class="plan-option-price"><span class="ltr-number">&#8362;3,245</span> / שנה</div>
            </div>
          </div>
        </div>
        <div class="step-actions">
          <button class="btn-back" @click="currentStep = 0">חזרה</button>
          <button class="btn-next" @click="goToStep(2)">המשך לתשלום</button>
        </div>
      </div>

      <!-- Step 3: Payment -->
      <div v-if="currentStep === 2" class="step-card">
        <h2>תשלום</h2>
        <p class="step-desc">בחרו אמצעי תשלום</p>
        <div class="payment-methods">
          <button class="payment-method" :class="{ active: true }" @click="processPayment" :disabled="loading">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
              <line x1="1" y1="10" x2="23" y2="10"/>
            </svg>
            <span>כרטיס אשראי</span>
            <span v-if="loading" class="spinner"></span>
          </button>
          <div class="payment-method disabled">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
              <line x1="12" y1="18" x2="12.01" y2="18"/>
            </svg>
            <span>Bit</span>
            <span class="coming-soon">בקרוב</span>
          </div>
          <div class="payment-method disabled">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            </svg>
            <span>PayBox</span>
            <span class="coming-soon">בקרוב</span>
          </div>
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <div class="step-actions">
          <button class="btn-back" @click="currentStep = 1">חזרה</button>
        </div>
      </div>

      <!-- Step 4: Success -->
      <div v-if="currentStep === 3" class="step-card success-card">
        <div class="success-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <h2>!ההרשמה הושלמה בהצלחה</h2>
        <p class="step-desc">הסיסמא שלכם נשלחה ב-SMS למספר {{ form.phone }}</p>
        <p class="step-desc">בדקו את ההודעות והתחברו למערכת</p>
        <router-link to="/login" class="btn-next">כניסה למערכת</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client.js'

const route = useRoute()

const stepLabels = ['פרטים', 'מסלול', 'תשלום', 'סיום']
const currentStep = ref(0)
const loading = ref(false)
const error = ref('')

const form = ref({
  fullName: '',
  email: '',
  phone: '',
  companyName: '',
  plan: 'yearly',
})

const isStep1Valid = computed(() => {
  return form.value.fullName && form.value.email && form.value.phone
})

onMounted(() => {
  // Pre-select plan from query
  if (route.query.plan === 'monthly' || route.query.plan === 'yearly') {
    form.value.plan = route.query.plan
  }
  // Handle success redirect from Cardcom
  if (route.query.step === 'success') {
    currentStep.value = 3
  }
})

function goToStep(step) {
  currentStep.value = step
}

async function processPayment() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.post('/subscription/signup', {
      email: form.value.email,
      full_name: form.value.fullName,
      phone: form.value.phone,
      company_name: form.value.companyName || null,
      plan: form.value.plan,
    })
    // Redirect to Cardcom payment page
    window.location.href = res.data.payment_url
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בתהליך התשלום. נסו שוב.'
    loading.value = false
  }
}
</script>

<style scoped>
.signup-page {
  min-height: 100vh;
  background: var(--bg);
}

.landing-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}

.nav-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}

.nav-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.nav-name {
  font-size: 20px;
  font-weight: 800;
  color: var(--text);
}

.signup-content {
  max-width: 560px;
  margin: 0 auto;
  padding: 100px 24px 60px;
}

/* Progress */
.progress-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 40px;
  position: relative;
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
  position: relative;
  z-index: 1;
}

.step-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-surface);
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-muted);
  transition: all 0.3s;
}

.progress-step.active .step-dot {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

.progress-step.done .step-dot {
  background: var(--green);
  border-color: var(--green);
  color: white;
}

.progress-step span {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.progress-step.active span {
  color: var(--primary);
  font-weight: 600;
}

/* Step Card */
.step-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 40px 32px;
  animation: fadeInUp 0.4s var(--transition);
}

.step-card h2 {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 8px;
}

.step-desc {
  color: var(--text-muted);
  font-size: 15px;
  margin-bottom: 28px;
}

/* Form */
.signup-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-group input {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-family: inherit;
  color: var(--text);
  background: var(--bg-surface);
  transition: border-color 0.2s;
}

.form-group input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

.form-group input::placeholder {
  color: var(--text-muted);
}

/* Buttons */
.btn-next {
  display: block;
  width: 100%;
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
  text-align: center;
}

.btn-next:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(1, 118, 211, 0.3);
}

.btn-next:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-back {
  padding: 12px 24px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  background: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-back:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
}

/* Plans */
.plan-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 8px;
}

.plan-option {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border: 2px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.plan-option:hover {
  border-color: var(--primary);
}

.plan-option.selected {
  border-color: var(--primary);
  background: var(--primary-light);
}

.plan-option-radio {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.plan-option.selected .plan-option-radio {
  border-color: var(--primary);
}

.radio-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--primary);
}

.plan-option-name {
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.plan-option-badge {
  padding: 2px 8px;
  background: var(--green-light);
  color: var(--green);
  border-radius: 100px;
  font-size: 11px;
  font-weight: 600;
}

.plan-option-price {
  font-size: 14px;
  color: var(--text-muted);
}

/* Payment */
.payment-methods {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.payment-method {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  font-family: inherit;
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s;
}

.payment-method:hover:not(.disabled):not(:disabled) {
  border-color: var(--primary);
}

.payment-method.active {
  border-color: var(--primary);
  background: var(--primary-light);
}

.payment-method.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.coming-soon {
  margin-right: auto;
  margin-left: 0;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: auto;
  margin-left: 0;
}

.error-msg {
  color: var(--red);
  font-size: 14px;
  margin-top: 12px;
}

/* Success */
.success-card {
  text-align: center;
}

.success-icon {
  margin-bottom: 20px;
}
</style>
