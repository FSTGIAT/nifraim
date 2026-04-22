<template>
  <div class="signup">
    <!-- Orange orbs -->
    <div class="hero-gradient" aria-hidden="true">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
    </div>

    <!-- Nav -->
    <nav class="land-nav nav--light">
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
        <div class="nav-aside">
          <router-link to="/pricing" class="nav-link-muted">תמחור</router-link>
          <router-link to="/login" class="nav-link-muted">יש לי חשבון</router-link>
        </div>
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
              <svg v-if="currentStep > i" class="step-check-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              <span v-else class="ltr-number">{{ i + 1 }}</span>
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
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
              <span>המשך לאישור המסלול</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
          </form>
        </div>

        <!-- Step 2: Plan confirmation (single tier) -->
        <div v-else-if="currentStep === 1" key="step1" class="step-card">
          <div class="step-header">
            <div class="step-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
            </div>
            <div>
              <h2>אישור מסלול</h2>
              <p class="step-desc">מסלול אחד. גישה מלאה.</p>
            </div>
          </div>

          <div class="plan-summary">
            <div class="plan-summary-head">
              <div class="ps-name">Nifraim</div>
              <div class="ps-price">
                <span class="ps-amount ltr-number">{{ monthlyPrice }}</span>
                <div class="ps-unit">
                  <span class="ps-currency">₪</span>
                  <span class="ps-period">לחודש</span>
                </div>
              </div>
              <div class="ps-vat">כולל מע״מ · חיוב חודשי אוטומטי</div>
            </div>
            <ul class="ps-bullets">
              <li>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                פורטל לקוחות ללא הגבלה
              </li>
              <li>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                עוזר AI אישי
              </li>
              <li>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                תמיכה מלאה
              </li>
            </ul>
          </div>

          <div class="step-actions">
            <button class="btn-back" @click="goBack(0)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
              חזרה
            </button>
            <button class="btn-next btn-next--inline" @click="goToStep(2)">
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
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
              חיוב אוטומטי חודשי —
              <strong class="ltr-number">₪{{ monthlyPrice }}</strong>
              בחודש
            </span>
          </div>

          <!-- Cardcom iframe or pre-payment state -->
          <div v-if="paymentUrl" class="cardcom-iframe-wrap">
            <iframe :src="paymentUrl" class="cardcom-iframe" frameborder="0" allowpaymentrequest></iframe>
          </div>
          <div v-else>
            <label class="terms-checkbox">
              <input type="checkbox" v-model="agreedToTerms" />
              <span class="checkmark"></span>
              <span>אני מסכים/ה לתנאי השימוש ולהוראת הקבע</span>
            </label>

            <button class="btn-next" style="margin-top: 20px" @click="processPayment" :disabled="loading || !agreedToTerms">
              <span v-if="!loading">המשך לתשלום</span>
              <span v-else>טוען טופס תשלום...</span>
              <span v-if="loading" class="spinner"></span>
            </button>
          </div>

          <p v-if="error" class="error-msg">{{ error }}</p>
          <div class="step-actions">
            <button class="btn-back" @click="paymentUrl ? (paymentUrl = '') : goBack(1)">
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
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
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
              <span class="detail-value ltr-number">Nifraim · ₪{{ monthlyPrice }} בחודש</span>
            </div>
            <div class="success-detail-row">
              <span class="detail-label">חיוב הבא:</span>
              <span class="detail-value">בעוד 30 יום</span>
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

const monthlyPrice = 220
const stepLabels = ['פרטים', 'מסלול', 'תשלום', 'סיום']
const currentStep = ref(0)
const stepDirection = ref('step-forward')
const loading = ref(false)
const error = ref('')
const agreedToTerms = ref(false)
const paymentUrl = ref('')

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
  plan: 'monthly',
})

const isStep1Valid = computed(() => {
  return form.value.fullName && form.value.email && form.value.phone
})

onMounted(() => {
  if (route.query.step === 'success') {
    currentStep.value = 3
  } else if (typeof route.query.step === 'string' && /^[0-3]$/.test(route.query.step)) {
    currentStep.value = Number(route.query.step)
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
      plan: 'monthly',
    })
    paymentUrl.value = res.data.payment_url
    loading.value = false
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בתהליך התשלום. נסו שוב.'
    loading.value = false
  }
}
</script>

<style scoped>
/* ── Theme tokens (mirrors LandingView / PricingView) ── */
.signup {
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
  --dark-section: #2D2522;
  --transition-fast: 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  min-height: 100vh;
  background: var(--cream-bg);
  color: var(--cream-text);
  font-family: 'Heebo', sans-serif;
  direction: rtl;
  position: relative;
  overflow: hidden;
}

.signup a { color: inherit; text-decoration: none; }

/* ── Orange orbs ── */
.hero-gradient {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.hero-gradient .orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  animation: orbFloat 9s ease-in-out infinite;
}

.hero-gradient .orb-1 {
  width: 720px;
  height: 720px;
  background: rgba(232, 102, 10, 0.28);
  top: -18%;
  left: -10%;
}

.hero-gradient .orb-2 {
  width: 520px;
  height: 520px;
  background: rgba(232, 102, 10, 0.22);
  bottom: 2%;
  right: -6%;
  animation-duration: 11s;
}

.hero-gradient .orb-3 {
  width: 460px;
  height: 460px;
  background: rgba(245, 124, 0, 0.2);
  top: 38%;
  left: 42%;
  animation-duration: 10s;
  animation-delay: -2s;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0); }
  50%      { transform: translate(30px, -24px); }
}

/* ── Nav (mirrors PricingView nav--light) ── */
.land-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(245, 240, 235, 0.9);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(45, 37, 34, 0.06);
}

.nav-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-icon {
  width: 40px;
  height: 40px;
  background: var(--cream-text);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--cream-bg);
}

.nav-name {
  font-size: 22px;
  font-weight: 800;
  color: var(--cream-text);
}

.nav-aside {
  display: flex;
  gap: 24px;
  align-items: center;
}

.nav-link-muted {
  font-size: 14px;
  font-weight: 500;
  color: var(--cream-text-muted);
  transition: color 0.2s;
}

.nav-link-muted:hover {
  color: var(--land-orange);
}

/* ── Content container ── */
.signup-content {
  max-width: 560px;
  margin: 0 auto;
  padding: 120px 24px 80px;
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
  background: rgba(45, 37, 34, 0.1);
  border-radius: 3px;
  z-index: 0;
}

.progress-line-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--land-orange), var(--land-orange-bright));
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 0 12px rgba(232, 102, 10, 0.35);
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
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid rgba(232, 102, 10, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 900;
  color: rgba(232, 102, 10, 0.55);
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  z-index: 2;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
  letter-spacing: -0.5px;
}

.step-dot-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid rgba(232, 102, 10, 0.35);
  animation: ringPulse 2s ease-in-out infinite;
  z-index: 1;
}

@keyframes ringPulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50%      { transform: scale(1.15); opacity: 0; }
}

.progress-step.active .step-dot {
  background: var(--land-orange);
  border-color: transparent;
  color: #fff;
  font-size: 20px;
  font-weight: 900;
  box-shadow: 0 4px 16px rgba(232, 102, 10, 0.4);
  transform: scale(1.05);
}

.progress-step.done .step-dot {
  background: var(--land-orange);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 4px 12px rgba(232, 102, 10, 0.3);
}

.progress-step.done .step-check-icon {
  color: #fff;
  stroke: #fff;
  filter: drop-shadow(0 1px 1.5px rgba(69, 26, 0, 0.3));
}

.progress-step.done .step-dot-ring {
  border-color: rgba(232, 102, 10, 0.25);
}

.progress-step > span {
  font-size: 13px;
  color: rgba(45, 37, 34, 0.45);
  font-weight: 500;
  transition: all 0.4s;
}

.progress-step.active > span {
  color: var(--land-orange);
  font-weight: 700;
}

.progress-step.done > span {
  color: var(--land-orange-deep);
  font-weight: 600;
}

.step-check-icon {
  display: block;
  flex-shrink: 0;
}

.step-check-enter-active { animation: checkPop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1); }
.step-check-leave-active { animation: checkPop 0.2s reverse; }
@keyframes checkPop {
  from { transform: scale(0) rotate(-45deg); opacity: 0; }
  to   { transform: scale(1) rotate(0); opacity: 1; }
}

/* ── Step Card ── */
.step-card {
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 24px;
  padding: 40px 36px;
  box-shadow:
    0 40px 80px -20px rgba(45, 37, 34, 0.15),
    0 0 0 1px rgba(232, 102, 10, 0.05);
  position: relative;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
}

.step-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--land-orange);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 8px 20px rgba(232, 102, 10, 0.25);
}

.step-card h2 {
  font-size: 24px;
  font-weight: 800;
  margin: 0 0 4px;
  color: var(--cream-text);
  letter-spacing: -0.3px;
}

.step-desc {
  color: var(--cream-text-muted);
  font-size: 14px;
  margin: 0;
}

/* ── Step transitions ── */
.step-forward-enter-active { animation: stepSlideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.step-forward-leave-active { animation: stepSlideOut 0.3s cubic-bezier(0.7, 0, 0.84, 0); }
.step-back-enter-active    { animation: stepSlideInBack 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.step-back-leave-active    { animation: stepSlideOutBack 0.3s cubic-bezier(0.7, 0, 0.84, 0); }

@keyframes stepSlideIn     { from { opacity: 0; transform: translateX(-30px) scale(0.97); } to { opacity: 1; transform: translateX(0) scale(1); } }
@keyframes stepSlideOut    { from { opacity: 1; transform: translateX(0) scale(1); }          to { opacity: 0; transform: translateX(30px) scale(0.97); } }
@keyframes stepSlideInBack { from { opacity: 0; transform: translateX(30px) scale(0.97); }    to { opacity: 1; transform: translateX(0) scale(1); } }
@keyframes stepSlideOutBack{ from { opacity: 1; transform: translateX(0) scale(1); }          to { opacity: 0; transform: translateX(-30px) scale(0.97); } }

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
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--cream-text-muted);
}

.input-wrap {
  position: relative;
}

.form-group input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(45, 37, 34, 0.12);
  border-radius: 12px;
  font-size: 15px;
  font-family: 'Heebo', sans-serif;
  color: var(--cream-text);
  background: var(--cream-surface-3);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.form-group input::placeholder {
  color: rgba(45, 37, 34, 0.3);
}

.form-group input:focus {
  border-color: var(--land-orange);
  box-shadow: 0 0 0 3px rgba(232, 102, 10, 0.15);
  outline: none;
  background: #fff;
}

/* ── Buttons ── */
.btn-next {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 16px;
  background: var(--land-orange);
  color: #fff;
  border: none;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 700;
  font-family: 'Heebo', sans-serif;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  text-align: center;
  text-decoration: none;
  box-shadow: 0 4px 20px rgba(232, 102, 10, 0.25);
}

.btn-next:hover:not(:disabled) {
  background: var(--land-orange-deep);
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(232, 102, 10, 0.3);
}

.btn-next:active:not(:disabled) {
  transform: translateY(0);
}

.btn-next:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-next--inline {
  width: auto;
  padding: 14px 28px;
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 22px;
  border: 1px solid rgba(45, 37, 34, 0.15);
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--cream-text-muted);
  background: transparent;
  font-family: 'Heebo', sans-serif;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-back:hover {
  border-color: var(--land-orange);
  color: var(--land-orange);
  background: rgba(232, 102, 10, 0.06);
}

.step-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 28px;
  align-items: center;
}

/* ── Plan summary card ── */
.plan-summary {
  border: 1px solid rgba(232, 102, 10, 0.2);
  border-radius: 18px;
  padding: 28px;
  background: linear-gradient(135deg, rgba(232, 102, 10, 0.06), rgba(255, 255, 255, 0.6));
  position: relative;
  overflow: hidden;
}

.plan-summary::before {
  content: '';
  position: absolute;
  top: -40%;
  right: -30%;
  width: 70%;
  height: 70%;
  background: radial-gradient(circle, rgba(232, 102, 10, 0.18), transparent 60%);
  pointer-events: none;
}

.plan-summary-head {
  position: relative;
}

.ps-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--cream-text);
  letter-spacing: -0.2px;
}

.ps-price {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-top: 6px;
}

.ps-amount {
  font-size: clamp(60px, 8vw, 88px);
  font-weight: 900;
  line-height: 0.95;
  color: var(--cream-text);
  letter-spacing: -2px;
  background: linear-gradient(135deg, var(--cream-text) 0%, var(--land-orange) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.ps-unit {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-bottom: 10px;
}

.ps-currency {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--cream-text);
  line-height: 1;
}

.ps-period {
  font-size: 0.9rem;
  color: var(--cream-text-muted);
}

.ps-vat {
  margin-top: 8px;
  font-size: 0.78rem;
  color: var(--cream-text-dim);
}

.ps-bullets {
  list-style: none;
  margin: 20px 0 0;
  padding: 20px 0 0;
  border-top: 1px solid rgba(45, 37, 34, 0.08);
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
}

.ps-bullets li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.92rem;
  color: var(--cream-text);
  font-weight: 500;
}

.ps-bullets svg {
  color: var(--land-orange);
  flex-shrink: 0;
}

/* ── Recurring notice ── */
.recurring-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(232, 102, 10, 0.06);
  border: 1px solid rgba(232, 102, 10, 0.18);
  border-radius: 12px;
  margin-bottom: 20px;
  color: var(--land-orange-deep);
  font-size: 13px;
  font-weight: 500;
  animation: fieldFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.recurring-notice svg {
  flex-shrink: 0;
  color: var(--land-orange);
}

.recurring-notice strong {
  font-weight: 800;
  color: var(--cream-text);
}

/* ── Cardcom iframe ── */
.cardcom-iframe-wrap {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(45, 37, 34, 0.1);
  background: #fff;
  margin-bottom: 16px;
}

.cardcom-iframe {
  width: 100%;
  min-height: 380px;
  border: none;
  display: block;
}

/* ── Terms checkbox ── */
.terms-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
  cursor: pointer;
  font-size: 14px;
  color: var(--cream-text-muted);
  user-select: none;
}

.terms-checkbox input { display: none; }

.checkmark {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(45, 37, 34, 0.2);
  border-radius: 6px;
  flex-shrink: 0;
  transition: all 0.3s;
  position: relative;
  background: #fff;
}

.terms-checkbox input:checked + .checkmark {
  background: var(--land-orange);
  border-color: var(--land-orange);
}

.terms-checkbox input:checked + .checkmark::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 2px;
  width: 5px;
  height: 10px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: auto;
  margin-left: 0;
}

.error-msg {
  color: #c23934;
  font-size: 14px;
  margin-top: 12px;
  padding: 12px 16px;
  background: rgba(234, 0, 30, 0.06);
  border: 1px solid rgba(234, 0, 30, 0.18);
  border-radius: 10px;
}

/* ── Success ── */
.success-card {
  text-align: center;
}

.success-card .step-desc {
  margin-bottom: 6px;
}

.success-icon {
  margin-bottom: 20px;
}

.success-circle {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--land-orange), var(--land-orange-bright));
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12px 32px rgba(232, 102, 10, 0.3);
  animation: successPop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes successPop {
  0%   { transform: scale(0) rotate(-45deg); opacity: 0; }
  60%  { transform: scale(1.1) rotate(5deg); }
  100% { transform: scale(1) rotate(0); opacity: 1; }
}

.success-card h2 {
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both;
}

.success-details {
  margin: 24px auto 28px;
  max-width: 360px;
  background: var(--cream-surface-3);
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 14px;
  padding: 16px 22px;
  text-align: right;
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.3s both;
}

.success-detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(45, 37, 34, 0.06);
}

.success-detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 13px;
  color: var(--cream-text-muted);
}

.detail-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--cream-text);
}

.success-card .btn-next {
  margin-top: 0;
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes spin { to { transform: rotate(360deg); } }

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .nav-aside { gap: 14px; }
  .nav-link-muted { font-size: 13px; }
  .signup-content { padding: 110px 20px 60px; }
}

@media (max-width: 480px) {
  .step-card {
    padding: 28px 22px;
    border-radius: 18px;
  }

  .step-card h2 { font-size: 21px; }

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
    flex-direction: row;
    text-align: start;
    gap: 12px;
  }

  .progress-bar {
    margin-bottom: 36px;
  }

  .recurring-notice {
    font-size: 12.5px;
    padding: 12px 14px;
  }

  .step-actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .btn-next--inline,
  .btn-back {
    width: 100%;
    justify-content: center;
  }

  .plan-summary {
    padding: 22px;
  }
}
</style>
