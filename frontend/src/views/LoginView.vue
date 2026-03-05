<template>
  <div class="auth-split">
    <!-- Gradient Panel (Left) -->
    <div class="auth-brand-panel">
      <div class="brand-content">
        <div class="brand-logo">
          <div class="brand-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span class="brand-name">Nifraim</span>
        </div>
        <h1 class="brand-heading">!ברוכים הבאים</h1>
        <p class="brand-subtitle">מערכת ניהול עמלות מתקדמת</p>
        <div class="brand-toggle">
          <span>אין לך חשבון?</span>
          <router-link to="/register" class="brand-toggle-link">הרשם כאן</router-link>
        </div>
      </div>
      <!-- Wave decoration -->
      <svg class="brand-wave" viewBox="0 0 500 150" preserveAspectRatio="none">
        <path d="M0,60 C150,120 350,0 500,80 L500,150 L0,150 Z" fill="rgba(255,255,255,0.08)"/>
        <path d="M0,90 C120,140 380,30 500,100 L500,150 L0,150 Z" fill="rgba(255,255,255,0.05)"/>
      </svg>
      <!-- Floating circles -->
      <div class="brand-circle brand-circle-1"></div>
      <div class="brand-circle brand-circle-2"></div>
      <div class="brand-circle brand-circle-3"></div>
    </div>

    <!-- Form Panel (Right) -->
    <div class="auth-form-panel">
      <div class="form-content">
        <h2 class="form-heading">התחברות</h2>
        <p class="form-subtitle">הזינו את הפרטים שלכם</p>
        <LoginForm />
        <p class="mobile-toggle">
          אין לך חשבון? <router-link to="/register">הרשם כאן</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import LoginForm from '../components/auth/LoginForm.vue'
</script>

<style scoped>
.auth-split {
  min-height: 100vh;
  display: flex;
  direction: rtl;
  font-family: 'Heebo', sans-serif;
}

/* ── Brand Panel ── */
.auth-brand-panel {
  width: 45%;
  background: linear-gradient(135deg, #E65100 0%, #F57C00 40%, #FF9800 70%, #FFB74D 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden;
  padding: 60px 40px;
}

.brand-content {
  position: relative;
  z-index: 2;
  text-align: center;
  color: #fff;
  max-width: 380px;
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 40px;
}

.brand-icon {
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  backdrop-filter: blur(8px);
}

.brand-name {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.brand-heading {
  font-size: 42px;
  font-weight: 900;
  margin-bottom: 12px;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 18px;
  opacity: 0.85;
  font-weight: 400;
  margin-bottom: 48px;
  line-height: 1.6;
}

.brand-toggle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  opacity: 0.9;
}

.brand-toggle-link {
  display: inline-block;
  padding: 10px 32px;
  border: 2px solid rgba(255, 255, 255, 0.6);
  border-radius: 50px;
  color: #fff;
  font-weight: 700;
  font-size: 15px;
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.brand-toggle-link:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: #fff;
  transform: translateY(-1px);
}

/* Wave decoration */
.brand-wave {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  height: 120px;
  z-index: 1;
}

/* Floating circles */
.brand-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  z-index: 1;
}

.brand-circle-1 {
  width: 200px;
  height: 200px;
  top: -40px;
  left: -60px;
  animation: floatCircle 8s ease-in-out infinite;
}

.brand-circle-2 {
  width: 140px;
  height: 140px;
  bottom: 80px;
  right: -30px;
  animation: floatCircle 6s ease-in-out infinite reverse;
}

.brand-circle-3 {
  width: 80px;
  height: 80px;
  top: 30%;
  right: 10%;
  background: rgba(255, 255, 255, 0.04);
  animation: floatCircle 10s ease-in-out infinite 2s;
}

@keyframes floatCircle {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

/* ── Form Panel ── */
.auth-form-panel {
  width: 55%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 60px 40px;
}

.form-content {
  width: 100%;
  max-width: 400px;
  animation: slideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.form-heading {
  font-size: 32px;
  font-weight: 800;
  color: #181818;
  margin-bottom: 8px;
}

.form-subtitle {
  color: #888;
  font-size: 15px;
  margin-bottom: 36px;
}

.mobile-toggle {
  display: none;
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: #888;
}

.mobile-toggle a {
  color: #F57C00;
  font-weight: 600;
  text-decoration: none;
}

.mobile-toggle a:hover {
  color: #E65100;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .auth-split {
    flex-direction: column;
  }

  .auth-brand-panel {
    width: 100%;
    padding: 48px 24px 36px;
    min-height: auto;
  }

  .brand-heading {
    font-size: 28px;
  }

  .brand-subtitle {
    font-size: 15px;
    margin-bottom: 24px;
  }

  .brand-toggle {
    display: none;
  }

  .auth-form-panel {
    width: 100%;
    padding: 36px 24px 48px;
  }

  .form-content {
    max-width: 100%;
  }

  .mobile-toggle {
    display: block;
  }

  .brand-circle-1 {
    width: 120px;
    height: 120px;
  }

  .brand-circle-2 {
    width: 80px;
    height: 80px;
  }

  .brand-wave {
    height: 60px;
  }
}

@media (max-width: 480px) {
  .auth-brand-panel {
    padding: 36px 20px 28px;
  }

  .brand-heading {
    font-size: 24px;
  }

  .brand-logo {
    margin-bottom: 24px;
  }

  .auth-form-panel {
    padding: 28px 20px 40px;
  }

  .form-heading {
    font-size: 26px;
  }
}
</style>
