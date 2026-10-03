<template>
  <div class="auth-split">
    <div class="auth-form-panel">
      <div class="form-content">
        <template v-if="!done">
          <p class="form-kicker">כמעט שם</p>
        <h1 class="form-heading">הגדרת סיסמה חדשה</h1>
          <p class="form-subtitle">הזינו את הסיסמה החדשה שלכם</p>

          <form class="auth-form" @submit.prevent="handleSubmit">
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

        <!-- plain <a>: /privacy is served by the backend (api/legal.py), not the Vue router -->
        <a href="/privacy" class="auth-legal">מדיניות פרטיות</a>
      </div>
    </div>

    <!-- left: Kling video, opening out of a soft circle -->
    <AuthMedia class="auth-media" video="portal" />
  </div>
</template>

<script setup>
import AuthMedia from '../components/site/AuthMedia.vue'
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

<style scoped src="../components/site/auth-pages.css"></style>
