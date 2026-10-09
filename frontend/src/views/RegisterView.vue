<template>
  <div class="auth-split" dir="rtl">
    <main class="auth-form-panel">
      <div class="form-content">
        <div class="form-lockup" dir="ltr">
          <NifraimIcon :size="108" />
          <p class="form-lockup-word">Nifraim<span>.com</span></p>
        </div>

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

        <!-- plain <a>: /privacy is served by the backend (api/legal.py), not the Vue router -->
        <a href="/privacy" class="auth-legal">מדיניות פרטיות</a>
      </div>
    </main>

    <!-- left: Kling video, opening out of a soft circle -->
    <AuthMedia class="auth-media" video="dusk" />
  </div>
</template>

<script setup>
import AuthMedia from '../components/site/AuthMedia.vue'
import NifraimIcon from '../components/common/NifraimIcon.vue'
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

<style scoped src="../components/site/auth-pages.css"></style>
