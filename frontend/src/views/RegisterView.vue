<template>
  <div class="auth-page">
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

    <div class="auth-glow"></div>
    <div class="auth-card">
      <h1>הרשמה</h1>
      <p class="subtitle">צור חשבון חדש</p>
      <RegisterForm />
    </div>
  </div>
</template>

<script setup>
import RegisterForm from '../components/auth/RegisterForm.vue'
</script>

<style scoped>
.auth-page {
  --auth-bg: #0a0a0a;
  --auth-card: #141414;
  --auth-border: #2a2a2a;
  --auth-text: #F5F5F5;
  --auth-text-dim: #666666;
  --auth-orange: #F57C00;

  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: var(--auth-bg);
  font-family: 'Heebo', sans-serif;
}

.auth-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(10, 10, 10, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--auth-border);
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
  background: var(--auth-orange);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0a0a0a;
}

.nav-name {
  font-size: 20px;
  font-weight: 800;
  color: var(--auth-text);
}

.auth-glow {
  position: fixed;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(245, 124, 0, 0.08) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}

.auth-card {
  position: relative;
  z-index: 1;
  background: var(--auth-card);
  border: 1px solid var(--auth-border);
  border-radius: 16px;
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
  animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

h1 {
  font-size: 32px;
  font-weight: 800;
  margin-bottom: 8px;
  color: var(--auth-text);
}

.subtitle {
  color: var(--auth-text-dim);
  margin-bottom: 36px;
  font-size: 15px;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 480px) {
  .auth-card {
    padding: 36px 24px;
    margin: 0 16px;
  }

  h1 {
    font-size: 28px;
  }
}
</style>
