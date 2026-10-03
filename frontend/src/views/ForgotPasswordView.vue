<template>
  <div class="auth-split">
    <div class="auth-form-panel">
      <div class="form-content">
        <template v-if="!sent">
        <p class="form-kicker">שכחתם סיסמה?</p>
        <h1 class="form-heading">איפוס סיסמה</h1>
        <p class="form-subtitle">הזינו את האימייל שלכם ונשלח לכם קישור לאיפוס</p>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <div class="field">
            <label>אימייל</label>
            <input type="email" v-model="email" required placeholder="your@email.com" dir="ltr" />
          </div>
          <Transition name="fade">
            <p class="error" v-if="error">{{ error }}</p>
          </Transition>
          <button type="submit" class="btn-submit" :disabled="loading">
            <template v-if="loading">
              <div class="btn-spinner"></div>
              <span>שולח...</span>
            </template>
            <template v-else>שלח קישור לאיפוס</template>
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
          <h3 class="success-title">הקישור נשלח!</h3>
          <p class="success-text">קישור לאיפוס סיסמה נשלח לאימייל שלכם. בדקו את תיבת הדואר.</p>
          <router-link to="/login" class="back-link">חזרה להתחברות</router-link>
        </div>

        <p class="mobile-toggle">
          נזכרת בסיסמה? <router-link to="/login">התחבר</router-link>
        </p>

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
import client from '../api/client.js'

const email = ref('')
const error = ref('')
const loading = ref(false)
const sent = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    await client.post('/auth/forgot-password', { email: email.value })
    sent.value = true
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בשליחת הבקשה'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="../components/site/auth-pages.css"></style>
