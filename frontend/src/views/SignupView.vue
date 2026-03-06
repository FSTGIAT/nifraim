<template>
  <div class="signup-page">
    <!-- Animated background -->
    <div class="bg-glow bg-glow-1"></div>
    <div class="bg-glow bg-glow-2"></div>
    <div class="bg-glow bg-glow-3"></div>

    <nav class="auth-nav">
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
        <div class="progress-line">
          <div class="progress-line-fill" :style="{ width: (currentStep / (stepLabels.length - 1)) * 100 + '%' }"></div>
        </div>
        <div class="progress-step" v-for="(s, i) in stepLabels" :key="i" :class="{ active: currentStep >= i, done: currentStep > i }">
          <div class="step-dot-wrap">
            <div class="step-dot ltr-number">
              <Transition name="step-check" mode="out-in">
                <svg v-if="currentStep > i" key="check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span v-else :key="i">{{ i + 1 }}</span>
              </Transition>
            </div>
            <div v-if="currentStep >= i" class="step-dot-ring"></div>
          </div>
          <span>{{ s }}</span>
        </div>
      </div>

      <!-- Animated step transitions -->
      <Transition :name="stepDirection" mode="out-in">
        <!-- Step 1: Details -->
        <div v-if="currentStep === 0" key="step0" class="step-card">
          <div class="step-header">
            <div class="step-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div>
              <h2>פרטים אישיים</h2>
              <p class="step-desc">מלאו את הפרטים שלכם להרשמה</p>
            </div>
          </div>
          <form @submit.prevent="goToStep(1)" class="signup-form">
            <div class="form-group" v-for="(field, fi) in step1Fields" :key="field.key" :style="{ animationDelay: fi * 80 + 'ms' }">
              <label>{{ field.label }}</label>
              <div class="input-wrap">
                <input :type="field.type" v-model="form[field.key]" :required="field.required" :placeholder="field.placeholder" :dir="field.dir || 'rtl'" />
              </div>
            </div>
            <button type="submit" class="btn-next" :disabled="!isStep1Valid">
              <span>המשך לבחירת מסלול</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
          </form>
        </div>

        <!-- Step 2: Plan -->
        <div v-else-if="currentStep === 1" key="step1" class="step-card">
          <div class="step-header">
            <div class="step-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
            </div>
            <div>
              <h2>בחירת מסלול</h2>
              <p class="step-desc">בחרו את המסלול המתאים לכם</p>
            </div>
          </div>
          <div class="plan-options">
            <div class="plan-option" :class="{ selected: form.plan === 'monthly' }" @click="form.plan = 'monthly'" style="animation-delay: 0ms">
              <div class="plan-option-radio">
                <Transition name="radio-pop">
                  <div class="radio-dot" v-if="form.plan === 'monthly'"></div>
                </Transition>
              </div>
              <div class="plan-option-info">
                <div class="plan-option-name">חודשי</div>
                <div class="plan-option-price"><span class="ltr-number">&#8362;295</span> / חודש</div>
              </div>
            </div>
            <div class="plan-option" :class="{ selected: form.plan === 'yearly' }" @click="form.plan = 'yearly'" style="animation-delay: 100ms">
              <div class="plan-option-radio">
                <Transition name="radio-pop">
                  <div class="radio-dot" v-if="form.plan === 'yearly'"></div>
                </Transition>
              </div>
              <div class="plan-option-info">
                <div class="plan-option-name">
                  שנתי
                  <span class="plan-option-badge">חודש חינם!</span>
                </div>
                <div class="plan-option-price"><span class="ltr-number">&#8362;3,245</span> / שנה</div>
              </div>
              <div class="plan-popular">מומלץ</div>
            </div>
          </div>
          <div class="step-actions">
            <button class="btn-back" @click="goBack(0)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
              חזרה
            </button>
            <button class="btn-next" @click="goToStep(2)">
              <span>המשך לתשלום</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Step 3: Payment -->
        <div v-else-if="currentStep === 2" key="step2" class="step-card">
          <div class="step-header">
            <div class="step-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
                <line x1="1" y1="10" x2="23" y2="10"/>
              </svg>
            </div>
            <div>
              <h2>תשלום</h2>
              <p class="step-desc">בחרו אמצעי תשלום</p>
            </div>
          </div>
          <div class="payment-methods">
            <button class="payment-method" :class="{ active: true }" @click="processPayment" :disabled="loading" style="animation-delay: 0ms">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
                <line x1="1" y1="10" x2="23" y2="10"/>
              </svg>
              <span>כרטיס אשראי</span>
              <span v-if="loading" class="spinner"></span>
            </button>
            <div class="payment-method disabled" style="animation-delay: 80ms">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
                <line x1="12" y1="18" x2="12.01" y2="18"/>
              </svg>
              <span>Bit</span>
              <span class="coming-soon">בקרוב</span>
            </div>
            <div class="payment-method disabled" style="animation-delay: 160ms">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              </svg>
              <span>PayBox</span>
              <span class="coming-soon">בקרוב</span>
            </div>
          </div>
          <p v-if="error" class="error-msg">{{ error }}</p>
          <div class="step-actions">
            <button class="btn-back" @click="goBack(1)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
              חזרה
            </button>
          </div>
        </div>

        <!-- Step 4: Success -->
        <div v-else-if="currentStep === 3" key="step3" class="step-card success-card">
          <div class="success-icon">
            <div class="success-circle">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#4caf50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
          </div>
          <h2>!ההרשמה הושלמה בהצלחה</h2>
          <p class="step-desc">הסיסמא שלכם נשלחה ב-SMS למספר {{ form.phone }}</p>
          <p class="step-desc">בדקו את ההודעות והתחברו למערכת</p>
          <router-link to="/login" class="btn-next">
            <span>כניסה למערכת</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </router-link>
        </div>
      </Transition>
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
const stepDirection = ref('step-forward')
const loading = ref(false)
const error = ref('')

const step1Fields = [
  { key: 'fullName', label: 'שם מלא *', type: 'text', required: true, placeholder: 'ישראל ישראלי' },
  { key: 'email', label: 'אימייל *', type: 'email', required: true, placeholder: 'email@example.com', dir: 'ltr' },
  { key: 'phone', label: 'טלפון *', type: 'tel', required: true, placeholder: '05X-XXXXXXX', dir: 'ltr' },
  { key: 'companyName', label: 'שם חברה (אופציונלי)', type: 'text', required: false, placeholder: 'סוכנות ביטוח' },
]

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
  if (route.query.plan === 'monthly' || route.query.plan === 'yearly') {
    form.value.plan = route.query.plan
  }
  if (route.query.step === 'success') {
    currentStep.value = 3
  }
})

function goToStep(step) {
  stepDirection.value = 'step-forward'
  currentStep.value = step
}

function goBack(step) {
  stepDirection.value = 'step-back'
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
  background: linear-gradient(145deg, #3a3a3a 0%, #4a4a4a 40%, #525252 100%);
  color: #F5F5F5;
  font-family: 'Heebo', sans-serif;
  position: relative;
  overflow: hidden;
}

/* Animated background glows */
.bg-glow {
  position: fixed;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.15;
  pointer-events: none;
  z-index: 0;
}

.bg-glow-1 {
  width: 500px;
  height: 500px;
  background: #F57C00;
  top: -150px;
  right: -100px;
  animation: glowFloat 12s ease-in-out infinite;
}

.bg-glow-2 {
  width: 400px;
  height: 400px;
  background: #FF9800;
  bottom: -100px;
  left: -100px;
  animation: glowFloat 10s ease-in-out infinite reverse;
}

.bg-glow-3 {
  width: 300px;
  height: 300px;
  background: #E65100;
  top: 50%;
  left: 50%;
  animation: glowFloat 14s ease-in-out infinite 3s;
}

@keyframes glowFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -40px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

/* Nav */
.auth-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(58, 58, 58, 0.7);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
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
  background: #F57C00;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1a1a1a;
}

.nav-name {
  font-size: 20px;
  font-weight: 800;
  color: #F5F5F5;
}

/* Content */
.signup-content {
  max-width: 560px;
  margin: 0 auto;
  padding: 100px 24px 60px;
  position: relative;
  z-index: 1;
}

/* ── Progress Bar ── */
.progress-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 48px;
  position: relative;
}

.progress-line {
  position: absolute;
  top: 22px;
  left: 40px;
  right: 40px;
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  z-index: 0;
}

.progress-line-fill {
  height: 100%;
  background: linear-gradient(90deg, #F57C00, #FF9800);
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 0 12px rgba(245, 124, 0, 0.4);
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  flex: 1;
  position: relative;
  z-index: 1;
}

.step-dot-wrap {
  position: relative;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-dot {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  border: 2px solid rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.35);
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  z-index: 2;
}

.step-dot-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid rgba(245, 124, 0, 0.3);
  animation: ringPulse 2s ease-in-out infinite;
  z-index: 1;
}

@keyframes ringPulse {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.15); opacity: 0; }
}

.progress-step.active .step-dot {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  border-color: transparent;
  color: #1a1a1a;
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.4);
  transform: scale(1.05);
}

.progress-step.done .step-dot {
  background: linear-gradient(135deg, #43A047, #66BB6A);
  border-color: transparent;
  color: white;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.progress-step.done .step-dot-ring {
  border-color: rgba(76, 175, 80, 0.3);
}

.progress-step span {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.35);
  font-weight: 500;
  transition: all 0.4s;
}

.progress-step.active span {
  color: #FF9800;
  font-weight: 700;
}

.progress-step.done span {
  color: #66BB6A;
  font-weight: 600;
}

/* Step check transition */
.step-check-enter-active { animation: checkPop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1); }
.step-check-leave-active { animation: checkPop 0.2s reverse; }
@keyframes checkPop {
  from { transform: scale(0) rotate(-45deg); opacity: 0; }
  to { transform: scale(1) rotate(0); opacity: 1; }
}

/* ── Step Card ── */
.step-card {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 40px 36px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.step-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
}

.step-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.15), rgba(255, 152, 0, 0.08));
  border: 1px solid rgba(245, 124, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #FF9800;
  flex-shrink: 0;
  animation: iconBreathe 3s ease-in-out infinite;
}

@keyframes iconBreathe {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 124, 0, 0); }
  50% { box-shadow: 0 0 20px 4px rgba(245, 124, 0, 0.1); }
}

.step-card h2 {
  font-size: 26px;
  font-weight: 800;
  margin-bottom: 4px;
  color: #F5F5F5;
}

.step-desc {
  color: rgba(255, 255, 255, 0.5);
  font-size: 15px;
  margin-bottom: 0;
}

/* ── Step Transitions ── */
.step-forward-enter-active {
  animation: stepSlideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.step-forward-leave-active {
  animation: stepSlideOut 0.3s cubic-bezier(0.7, 0, 0.84, 0);
}
.step-back-enter-active {
  animation: stepSlideInBack 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.step-back-leave-active {
  animation: stepSlideOutBack 0.3s cubic-bezier(0.7, 0, 0.84, 0);
}

@keyframes stepSlideIn {
  from { opacity: 0; transform: translateX(-40px) scale(0.97); }
  to { opacity: 1; transform: translateX(0) scale(1); }
}
@keyframes stepSlideOut {
  from { opacity: 1; transform: translateX(0) scale(1); }
  to { opacity: 0; transform: translateX(40px) scale(0.97); }
}
@keyframes stepSlideInBack {
  from { opacity: 0; transform: translateX(40px) scale(0.97); }
  to { opacity: 1; transform: translateX(0) scale(1); }
}
@keyframes stepSlideOutBack {
  from { opacity: 1; transform: translateX(0) scale(1); }
  to { opacity: 0; transform: translateX(-40px) scale(0.97); }
}

/* ── Form ── */
.signup-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  animation: fieldFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes fieldFadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.form-group label {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.6);
}

.input-wrap {
  position: relative;
}

.form-group input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  font-size: 15px;
  font-family: 'Heebo', sans-serif;
  color: #F5F5F5;
  background: rgba(255, 255, 255, 0.06);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.form-group input:focus {
  border-color: #F57C00;
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.15), 0 4px 16px rgba(245, 124, 0, 0.1);
  outline: none;
  background: rgba(255, 255, 255, 0.08);
}

.form-group input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

/* ── Buttons ── */
.btn-next {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 15px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #1a1a1a;
  border: none;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 700;
  font-family: 'Heebo', sans-serif;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  text-align: center;
  text-decoration: none;
  position: relative;
  overflow: hidden;
}

.btn-next::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.2), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.btn-next:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(245, 124, 0, 0.35);
}

.btn-next:hover:not(:disabled)::before {
  opacity: 1;
}

.btn-next:active:not(:disabled) {
  transform: translateY(0);
}

.btn-next:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 24px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.04);
  font-family: 'Heebo', sans-serif;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-back:hover {
  border-color: #F57C00;
  color: #F57C00;
  background: rgba(245, 124, 0, 0.06);
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 28px;
}

/* ── Plans ── */
.plan-options {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 8px;
}

.plan-option {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 22px;
  border: 2px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  animation: fieldFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.plan-option:hover {
  border-color: rgba(245, 124, 0, 0.4);
  background: rgba(245, 124, 0, 0.04);
  transform: translateY(-1px);
}

.plan-option.selected {
  border-color: #F57C00;
  background: rgba(245, 124, 0, 0.08);
  box-shadow: 0 4px 20px rgba(245, 124, 0, 0.15);
}

.plan-popular {
  position: absolute;
  top: -10px;
  left: 16px;
  padding: 2px 12px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #1a1a1a;
  font-size: 11px;
  font-weight: 800;
  border-radius: 100px;
  letter-spacing: 0.5px;
}

.plan-option-radio {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.3s;
}

.plan-option.selected .plan-option-radio {
  border-color: #F57C00;
}

.radio-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #F57C00;
}

.radio-pop-enter-active { animation: radioPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.radio-pop-leave-active { animation: radioPop 0.15s reverse; }
@keyframes radioPop {
  from { transform: scale(0); }
  to { transform: scale(1); }
}

.plan-option-name {
  font-weight: 700;
  font-size: 17px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #F5F5F5;
}

.plan-option-badge {
  padding: 3px 10px;
  background: rgba(76, 175, 80, 0.15);
  color: #66BB6A;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
}

.plan-option-price {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 2px;
}

/* ── Payment ── */
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
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  font-family: 'Heebo', sans-serif;
  font-size: 15px;
  font-weight: 600;
  color: #F5F5F5;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  animation: fieldFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.payment-method:hover:not(.disabled):not(:disabled) {
  border-color: #F57C00;
  background: rgba(245, 124, 0, 0.06);
  transform: translateY(-1px);
}

.payment-method.active {
  border-color: #F57C00;
  background: rgba(245, 124, 0, 0.08);
}

.payment-method.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.coming-soon {
  margin-right: auto;
  margin-left: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  font-weight: 500;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-top-color: #F57C00;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: auto;
  margin-left: 0;
}

.error-msg {
  color: #ef5350;
  font-size: 14px;
  margin-top: 12px;
  padding: 12px 16px;
  background: rgba(239, 83, 80, 0.08);
  border: 1px solid rgba(239, 83, 80, 0.2);
  border-radius: 10px;
}

/* ── Success ── */
.success-card {
  text-align: center;
}

.success-card .step-desc {
  margin-bottom: 8px;
}

.success-icon {
  margin-bottom: 24px;
}

.success-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(76, 175, 80, 0.1);
  border: 2px solid rgba(76, 175, 80, 0.2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  animation: successPop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes successPop {
  0% { transform: scale(0) rotate(-45deg); opacity: 0; }
  60% { transform: scale(1.1) rotate(5deg); }
  100% { transform: scale(1) rotate(0); opacity: 1; }
}

.success-card h2 {
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both;
}

.success-card .btn-next {
  margin-top: 24px;
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Responsive ── */
@media (max-width: 480px) {
  .step-card {
    padding: 28px 20px;
    border-radius: 16px;
  }

  .step-card h2 {
    font-size: 22px;
  }

  .step-dot {
    width: 38px;
    height: 38px;
    font-size: 13px;
  }

  .step-dot-wrap {
    width: 38px;
    height: 38px;
  }

  .step-header {
    flex-direction: column;
    text-align: center;
  }

  .progress-bar {
    margin-bottom: 36px;
  }
}
</style>
