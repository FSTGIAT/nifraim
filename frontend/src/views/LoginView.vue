<template>
  <div class="auth-split" dir="rtl">

    <main class="auth-form-panel">
      <div class="form-content">
        <p class="form-kicker">ברוכים השבים</p>
        <h1 class="form-heading">התחברות</h1>
        <p class="form-subtitle">הזינו את הפרטים שלכם</p>

        <form class="auth-form" @submit.prevent="handleSubmit">
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
                autocomplete="current-password"
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
          </div>

          <div class="auth-form-row">
            <router-link to="/forgot-password" class="forgot">שכחתי סיסמה</router-link>
          </div>

          <Transition name="fade">
            <p v-if="error" class="auth-error">{{ error }}</p>
          </Transition>

          <button type="submit" class="auth-submit" :disabled="loading">
            <span v-if="loading" class="spinner" aria-hidden="true"></span>
            <span>{{ loading ? 'מתחבר...' : 'התחבר' }}</span>
          </button>
        </form>

        <p class="mobile-toggle">
          אין לכם חשבון?
          <router-link to="/signup">הרשמה</router-link>
        </p>

        <!-- plain <a>: /privacy is served by the backend (api/legal.py), not the Vue router -->
        <a href="/privacy" class="auth-legal">מדיניות פרטיות</a>
      </div>
    </main>

    <!-- left: the lighthouse pulling back from its lantern window -->
    <AuthMedia class="auth-media" video="hero" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import AuthMedia from '../components/site/AuthMedia.vue'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
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

<style scoped src="../components/site/auth-pages.css"></style>
