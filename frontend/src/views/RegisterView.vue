<template>
  <div class="auth-split" dir="rtl">
    <aside class="auth-brand-panel" aria-hidden="true">
      <span class="orb orb--a"></span>
      <span class="orb orb--b"></span>
      <span class="orb orb--c"></span>
      <span class="orb orb--d"></span>
      <span class="orb orb--e"></span>

      <span class="sweep"></span>
      <span class="grain"></span>

      <svg class="brand-wave" viewBox="0 0 500 150" preserveAspectRatio="none" aria-hidden="true">
        <path class="wave wave--1" d="M0,80 C150,140 350,20 500,90 L500,150 L0,150 Z" fill="rgba(232,102,10,0.22)" />
        <path class="wave wave--2" d="M0,100 C120,150 380,40 500,110 L500,150 L0,150 Z" fill="rgba(232,102,10,0.14)" />
        <path class="wave wave--3" d="M0,120 C160,150 340,80 500,130 L500,150 L0,150 Z" fill="rgba(45,37,34,0.08)" />
      </svg>

      <div class="brand-content">
        <div class="brand-logo">
          <div class="brand-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <span class="brand-name">Nifraim</span>
        </div>

        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          <span>סוכן AI לסוכני ביטוח</span>
        </div>

        <h1 class="brand-heading">
          הצטרפו <span class="accent">לסוכני AI</span>
        </h1>
        <p class="brand-subtitle">חשבון חדש בכמה שניות. בלי כרטיס אשראי.</p>

        <div class="brand-toggle">
          <span>כבר רשומים?</span>
          <router-link to="/login" class="brand-toggle-link">התחבר</router-link>
        </div>
      </div>
    </aside>

    <main class="auth-form-panel">
      <div class="form-content">
        <h2 class="form-heading">הרשמה</h2>
        <p class="form-subtitle">הזינו את הפרטים שלכם</p>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <div class="field">
            <label for="fullName">שם מלא</label>
            <div class="control">
              <svg class="control-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <input
                id="fullName"
                v-model="fullName"
                type="text"
                placeholder="שם מלא"
                autocomplete="name"
              />
            </div>
          </div>

          <div class="field">
            <label for="email">אימייל</label>
            <div class="control">
              <svg class="control-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="m3 7 9 6 9-6" />
              </svg>
              <input
                id="email"
                v-model="email"
                type="email"
                placeholder="your@email.com"
                dir="ltr"
                required
                autocomplete="email"
              />
            </div>
          </div>

          <div class="field">
            <label for="username">שם משתמש</label>
            <div class="control">
              <svg class="control-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-3.92 7.94" />
              </svg>
              <input
                id="username"
                v-model="username"
                type="text"
                placeholder="kiko"
                dir="ltr"
                required
                minlength="3"
                maxlength="32"
                autocomplete="username"
                @input="usernameTouched = true"
              />
            </div>
            <p class="hint">3–32 תווים · אותיות קטנות, ספרות וקו תחתון · כך יחפשו אתכם בצ'אט</p>
          </div>

          <div class="field">
            <label for="password">סיסמה</label>
            <div class="control">
              <svg class="control-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="4" y="11" width="16" height="10" rx="2" />
                <path d="M8 11V7a4 4 0 0 1 8 0v4" />
              </svg>
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="••••••••"
                dir="ltr"
                required
                minlength="6"
                autocomplete="new-password"
              />
              <button
                type="button"
                class="toggle-pw"
                :aria-label="showPassword ? 'הסתר סיסמה' : 'הצג סיסמה'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                  <path d="m1 1 22 22" />
                  <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M2 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
            </div>
            <p class="hint">לפחות 6 תווים</p>
          </div>

          <Transition name="fade">
            <p v-if="error" class="auth-error">{{ error }}</p>
          </Transition>

          <button type="submit" class="auth-submit" :disabled="loading">
            <span v-if="loading" class="spinner" aria-hidden="true"></span>
            <span>{{ loading ? 'נרשם...' : 'הרשם' }}</span>
          </button>
        </form>

        <p class="mobile-toggle">
          כבר רשומים?
          <router-link to="/login">התחברות</router-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()

const fullName = ref('')
const email = ref('')
const username = ref('')
const usernameTouched = ref(false)
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)

function suggestUsername (mail) {
  const local = (mail || '').split('@')[0].toLowerCase()
  const base = local.replace(/[^a-z0-9_]/g, '')
  return base.length < 3 ? `user${base}` : base.slice(0, 32)
}

// Suggest a handle from the email until the user edits the field themselves.
watch(email, (mail) => {
  if (!usernameTouched.value) username.value = suggestUsername(mail)
})

async function handleSubmit() {
  error.value = ''
  const handle = username.value.trim().replace(/^@/, '').toLowerCase()
  if (!/^[a-z0-9_]{3,32}$/.test(handle)) {
    error.value = 'שם משתמש יכול להכיל רק אותיות אנגליות קטנות, ספרות וקו תחתון (3–32 תווים)'
    return
  }
  loading.value = true
  try {
    await auth.register(email.value, password.value, fullName.value || null, handle)
    router.push('/workspace')
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בהרשמה'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-split {
  min-height: 100vh;
  display: flex;
  background: #f5f0eb;
  color: #2d2522;
  font-family: 'Heebo', sans-serif;
  overflow: hidden;
}

.auth-brand-panel {
  position: relative;
  flex: 0 0 45%;
  overflow: hidden;
  background:
    radial-gradient(circle at 30% 25%, rgba(255, 178, 120, 0.6) 0%, transparent 55%),
    radial-gradient(circle at 75% 75%, rgba(232, 102, 10, 0.32) 0%, transparent 55%),
    linear-gradient(135deg, #fff3e6 0%, #f5e5d3 50%, #ede1cc 100%);
  isolation: isolate;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  mix-blend-mode: multiply;
  will-change: transform;
  pointer-events: none;
}
.orb--a {
  width: 380px;
  height: 380px;
  top: -90px;
  right: -70px;
  background: rgba(232, 102, 10, 0.45);
  animation: orbA 9s ease-in-out infinite;
}
.orb--b {
  width: 300px;
  height: 300px;
  bottom: 60px;
  left: -70px;
  background: rgba(245, 124, 0, 0.4);
  animation: orbB 11s ease-in-out infinite;
}
.orb--c {
  width: 240px;
  height: 240px;
  top: 38%;
  left: 28%;
  background: rgba(255, 170, 100, 0.5);
  animation: orbC 13s ease-in-out infinite;
}
.orb--d {
  width: 180px;
  height: 180px;
  bottom: 30%;
  right: 16%;
  background: rgba(200, 90, 0, 0.35);
  animation: orbD 8s ease-in-out infinite;
}
.orb--e {
  width: 140px;
  height: 140px;
  top: 16%;
  left: 10%;
  background: rgba(232, 102, 10, 0.4);
  animation: orbE 7s ease-in-out infinite;
}

@keyframes orbA {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(-40px, 60px) scale(1.15); }
}
@keyframes orbB {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(50px, -40px) scale(1.1); }
}
@keyframes orbC {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(30px, -30px) scale(1.2); }
}
@keyframes orbD {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(-30px, -40px) scale(1.05); }
}
@keyframes orbE {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(40px, 30px) scale(1.1); }
}

.sweep {
  position: absolute;
  inset: -20%;
  background: linear-gradient(115deg, transparent 40%, rgba(255, 255, 255, 0.35) 50%, transparent 60%);
  animation: sweep 8s ease-in-out infinite;
  pointer-events: none;
  mix-blend-mode: overlay;
}
@keyframes sweep {
  0%   { transform: translateX(-30%); }
  50%  { transform: translateX(30%); }
  100% { transform: translateX(-30%); }
}

.grain {
  position: absolute;
  inset: 0;
  opacity: 0.06;
  pointer-events: none;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.brand-wave {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  height: 130px;
  z-index: 2;
  pointer-events: none;
}
.wave {
  transform-origin: center bottom;
  will-change: transform;
}
.wave--1 { animation: waveDrift 6s ease-in-out infinite; }
.wave--2 { animation: waveDrift 8s ease-in-out infinite reverse; }
.wave--3 { animation: waveDrift 10s ease-in-out infinite; }

@keyframes waveDrift {
  0%, 100% { transform: translateX(0) scaleY(1); }
  50%      { transform: translateX(-18px) scaleY(1.04); }
}

.brand-content {
  position: relative;
  z-index: 10;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 80px 48px;
  text-align: center;
  max-width: 480px;
  margin: 0 auto;
  color: #2d2522;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}
.brand-icon {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #e8660a;
  border-radius: 12px;
  box-shadow: 0 4px 14px rgba(232, 102, 10, 0.3);
}
.brand-name {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.4px;
  color: #2d2522;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 7px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(45, 37, 34, 0.1);
  font-size: 12.5px;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: rgba(45, 37, 34, 0.82);
  margin-bottom: 22px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #e8660a;
  box-shadow: 0 0 12px rgba(232, 102, 10, 0.5);
  animation: dotPulse 2s ease-in-out infinite;
}
@keyframes dotPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.4; transform: scale(0.7); }
}

.brand-heading {
  font-size: clamp(2.6rem, 4.4vw, 3.6rem);
  line-height: 1.05;
  letter-spacing: -1.2px;
  font-weight: 300;
  color: #2d2522;
  margin: 0 0 18px;
}
.brand-heading .accent {
  font-weight: 800;
  color: #e8660a;
  font-style: italic;
}

.brand-subtitle {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.7;
  color: rgba(45, 37, 34, 0.7);
  margin: 0 0 36px;
  max-width: 320px;
}

.brand-toggle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: rgba(45, 37, 34, 0.65);
}
.brand-toggle-link {
  display: inline-block;
  padding: 10px 28px;
  border: 1.5px solid rgba(45, 37, 34, 0.25);
  border-radius: 50px;
  color: #2d2522;
  font-weight: 600;
  font-size: 14px;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.55);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.brand-toggle-link:hover {
  background: #fff;
  border-color: #e8660a;
  color: #e8660a;
  transform: translateY(-1px);
}

.auth-form-panel {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
  position: relative;
  background: #f9f6f2;
  border-inline-start: 1px solid rgba(45, 37, 34, 0.06);
}

.form-content {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 420px;
  animation: slideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes slideIn {
  from { opacity: 0; transform: translateX(20px); }
  to   { opacity: 1; transform: translateX(0); }
}

.form-heading {
  font-size: 30px;
  font-weight: 700;
  color: #2d2522;
  margin: 0 0 6px;
  letter-spacing: -0.4px;
}
.form-subtitle {
  color: rgba(45, 37, 34, 0.6);
  font-size: 14px;
  margin: 0 0 32px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.field label {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(45, 37, 34, 0.75);
}

.control {
  position: relative;
}
.control-icon {
  position: absolute;
  top: 50%;
  right: 14px;
  width: 16px;
  height: 16px;
  transform: translateY(-50%);
  color: rgba(45, 37, 34, 0.45);
  pointer-events: none;
}
.control input {
  width: 100%;
  height: 46px;
  padding: 0 44px 0 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid rgba(45, 37, 34, 0.12);
  color: #2d2522;
  font-size: 15px;
  font-family: 'Heebo', sans-serif;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.control input::placeholder {
  color: rgba(45, 37, 34, 0.35);
}
.control input:focus {
  outline: none;
  border-color: #e8660a;
  box-shadow: 0 0 0 3px rgba(232, 102, 10, 0.15);
}
.control input[dir='ltr'] {
  padding: 0 44px 0 44px;
}

.toggle-pw {
  position: absolute;
  top: 50%;
  left: 12px;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 0;
  color: rgba(45, 37, 34, 0.5);
  cursor: pointer;
  border-radius: 8px;
  transition: color 0.2s, background 0.2s;
}
.toggle-pw:hover {
  color: #e8660a;
  background: rgba(232, 102, 10, 0.08);
}
.toggle-pw svg {
  width: 16px;
  height: 16px;
}

.hint {
  margin: -2px 4px 0;
  font-size: 12px;
  color: rgba(45, 37, 34, 0.5);
}

.auth-error {
  margin: 0;
  padding: 11px 14px;
  border-radius: 12px;
  background: #fef1ee;
  border: 1px solid rgba(211, 47, 47, 0.2);
  color: #c62828;
  font-size: 13px;
  font-weight: 500;
}

.auth-submit {
  margin-top: 6px;
  height: 48px;
  border-radius: 999px;
  border: 0;
  background: #e8660a;
  color: #fff;
  font-family: 'Heebo', sans-serif;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.01em;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  box-shadow: 0 8px 20px rgba(232, 102, 10, 0.25);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 0.2s, background 0.2s;
}
.auth-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  background: #c85a00;
  box-shadow: 0 12px 28px rgba(232, 102, 10, 0.35);
}
.auth-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.mobile-toggle {
  display: none;
  text-align: center;
  margin-top: 22px;
  font-size: 13px;
  color: rgba(45, 37, 34, 0.6);
}
.mobile-toggle a {
  margin-inline-start: 6px;
  color: #e8660a;
  font-weight: 600;
  text-decoration: none;
}
.mobile-toggle a:hover {
  text-decoration: underline;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 768px) {
  .auth-split {
    flex-direction: column;
  }
  .auth-brand-panel {
    flex: 0 0 auto;
    width: 100%;
    min-height: 320px;
  }
  .brand-content {
    padding: 56px 24px 80px;
  }
  .brand-heading {
    font-size: clamp(1.9rem, 7vw, 2.6rem);
  }
  .brand-toggle {
    display: none;
  }
  .auth-form-panel {
    padding: 40px 24px 56px;
  }
  .mobile-toggle {
    display: block;
  }
}

@media (max-width: 480px) {
  .brand-content {
    padding: 44px 20px 68px;
  }
  .auth-form-panel {
    padding: 32px 20px 48px;
  }
  .form-heading {
    font-size: 24px;
  }
}
</style>
