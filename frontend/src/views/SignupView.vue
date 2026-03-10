<template>
  <div class="signup-page">
    <!-- Floating blur circles -->
    <div class="float-circle fc-1"></div>
    <div class="float-circle fc-2"></div>
    <div class="float-circle fc-3"></div>
    <div class="float-circle fc-4"></div>

    <!-- Animated waves at bottom -->
    <div class="wave-bg">
      <div class="shimmer"></div>
      <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="swg1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
            <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path fill="url(#swg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="swg2" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
            <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
            <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
            <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
          </linearGradient>
        </defs>
        <path fill="url(#swg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="swg3" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/>
          </linearGradient>
        </defs>
        <path fill="url(#swg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
      </svg>
    </div>

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
            <div class="step-dot">
              <Transition name="step-check" mode="out-in">
                <svg v-if="currentStep > i" key="check" class="step-check-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span v-else :key="i" class="ltr-number">{{ i + 1 }}</span>
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
              <p class="step-desc">מנוי חודשי עם הוראת קבע</p>
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
                <div class="plan-option-recur">הוראת קבע — חיוב אוטומטי מדי חודש</div>
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
                <div class="plan-option-recur">הוראת קבע — חיוב אוטומטי מדי שנה</div>
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
              <p class="step-desc">הכרטיס יחויב אוטומטית מדי חודש</p>
            </div>
          </div>

          <div class="recurring-notice">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            <span>
              חיוב אוטומטי {{ form.plan === 'monthly' ? 'חודשי' : 'שנתי' }} —
              <strong class="ltr-number">&#8362;{{ form.plan === 'monthly' ? '295' : '3,245' }}</strong>
              {{ form.plan === 'monthly' ? 'בחודש' : 'בשנה' }}
            </span>
          </div>

          <div class="payment-methods">
            <button class="payment-method" :class="{ active: true }" @click="processPayment" :disabled="loading || !agreedToTerms" style="animation-delay: 0ms">
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

          <label class="terms-checkbox">
            <input type="checkbox" v-model="agreedToTerms" />
            <span class="checkmark"></span>
            <span>אני מסכים/ה לתנאי השימוש ולהוראת הקבע</span>
          </label>

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

          <div class="success-details">
            <div class="success-detail-row">
              <span class="detail-label">מסלול:</span>
              <span class="detail-value">{{ form.plan === 'monthly' ? 'חודשי' : 'שנתי' }}</span>
            </div>
            <div class="success-detail-row">
              <span class="detail-label">חיוב הבא:</span>
              <span class="detail-value">{{ form.plan === 'monthly' ? 'בעוד 30 יום' : 'בעוד שנה' }}</span>
            </div>
            <div class="success-detail-row">
              <span class="detail-label">סוג מנוי:</span>
              <span class="detail-value">הוראת קבע — חידוש אוטומטי</span>
            </div>
          </div>

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
const agreedToTerms = ref(false)

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
  if (!agreedToTerms.value) return
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
    if (res.data.demo_mode) {
      // Dev mode: no Cardcom configured, user auto-activated
      goToStep(3)
      loading.value = false
    } else {
      window.location.href = res.data.payment_url
    }
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

/* ─── Floating blur circles ─── */
.float-circle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.fc-1 {
  width: 260px;
  height: 260px;
  top: 5%;
  right: -80px;
  background: rgba(245, 124, 0, 0.06);
  border: 1px solid rgba(245, 124, 0, 0.08);
  animation: floatBob 8s ease-in-out infinite;
}

.fc-2 {
  width: 180px;
  height: 180px;
  bottom: 30%;
  left: -50px;
  background: rgba(245, 124, 0, 0.045);
  border: 1px solid rgba(245, 124, 0, 0.06);
  animation: floatBob 6.5s ease-in-out infinite reverse;
}

.fc-3 {
  width: 100px;
  height: 100px;
  top: 35%;
  left: 10%;
  background: rgba(245, 124, 0, 0.06);
  animation: floatBob 10s ease-in-out infinite 2s;
}

.fc-4 {
  width: 140px;
  height: 140px;
  top: 60%;
  right: 8%;
  background: rgba(245, 124, 0, 0.04);
  border: 1px solid rgba(245, 124, 0, 0.05);
  animation: floatBob 9s ease-in-out infinite 1s;
}

@keyframes floatBob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-16px) rotate(2deg); }
  66% { transform: translateY(8px) rotate(-1deg); }
}

/* ─── Waves fixed to bottom ─── */
.wave-bg {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 200px;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.shimmer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100%;
  z-index: 1;
  overflow: hidden;
  mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
}

.shimmer::after {
  content: '';
  position: absolute;
  top: 0;
  left: -80%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 200, 100, 0.08) 35%,
    rgba(255, 255, 255, 0.12) 50%,
    rgba(255, 200, 100, 0.08) 65%,
    transparent 100%
  );
  animation: shimmerSweep 7s ease-in-out infinite;
}

@keyframes shimmerSweep {
  0%   { left: -80%; }
  100% { left: 180%; }
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 200%;
  height: 100%;
}

.wave-1 { animation: waveSlide 14s linear infinite; }
.wave-2 { animation: waveSlide 18s linear infinite reverse; }
.wave-3 { animation: waveSlide 22s linear infinite; }

@keyframes waveSlide {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
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

/* Step check icon */
.step-check-icon {
  display: block;
  flex-shrink: 0;
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

.plan-option-recur {
  font-size: 12px;
  color: rgba(255, 152, 0, 0.7);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ── Recurring notice ── */
.recurring-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(245, 124, 0, 0.08);
  border: 1px solid rgba(245, 124, 0, 0.15);
  border-radius: 12px;
  margin-bottom: 20px;
  color: #FFB74D;
  font-size: 14px;
  animation: fieldFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.recurring-notice svg {
  flex-shrink: 0;
  color: #FF9800;
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

/* ── Terms checkbox ── */
.terms-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
  cursor: pointer;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  user-select: none;
}

.terms-checkbox input {
  display: none;
}

.checkmark {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  flex-shrink: 0;
  transition: all 0.3s;
  position: relative;
}

.terms-checkbox input:checked + .checkmark {
  background: #F57C00;
  border-color: #F57C00;
}

.terms-checkbox input:checked + .checkmark::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 2px;
  width: 5px;
  height: 10px;
  border: solid #1a1a1a;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
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

.success-details {
  margin: 24px auto 28px;
  max-width: 320px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 18px 22px;
  text-align: right;
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.3s both;
}

.success-detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.success-detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}

.detail-value {
  font-size: 13px;
  font-weight: 600;
  color: #FFB74D;
}

.success-card h2 {
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both;
}

.success-card .btn-next {
  margin-top: 0;
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
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

  .recurring-notice {
    font-size: 13px;
    padding: 12px 14px;
  }
}
</style>
