<template>
  <div class="auth-page">
    <div class="bg-mesh"></div>
    <div class="auth-card">
      <div class="brand-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
          <path d="M2 17l10 5 10-5"/>
          <path d="M2 12l10 5 10-5"/>
        </svg>
      </div>
      <h1>התחברות</h1>
      <p class="subtitle">InsureFlow - מערכת ניהול עמלות ביטוח</p>
      <LoginForm />
    </div>
  </div>
</template>

<script setup>
import LoginForm from '../components/auth/LoginForm.vue'
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.bg-mesh {
  position: fixed;
  inset: 0;
  z-index: 0;
  background:
    radial-gradient(ellipse 80% 60% at 20% 10%, var(--primary-light) 0%, transparent 60%),
    radial-gradient(ellipse 60% 50% at 80% 20%, rgba(34, 211, 238, 0.1) 0%, transparent 50%),
    radial-gradient(ellipse 70% 60% at 50% 90%, rgba(127, 86, 217, 0.08) 0%, transparent 50%);
  pointer-events: none;
}

.auth-card {
  position: relative;
  z-index: 1;
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
  box-shadow: var(--shadow-lg), var(--shadow-glow);
  animation: slideUp 0.6s var(--transition);
}

.brand-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 24px;
}

h1 {
  font-size: 28px;
  font-weight: 800;
  margin-bottom: 6px;
  color: var(--text);
  letter-spacing: -0.5px;
}

.subtitle {
  color: var(--text-muted);
  margin-bottom: 32px;
  font-size: 14px;
}
</style>
