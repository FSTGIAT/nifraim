<template>
  <div class="expired-page">
    <div class="expired-card">
      <div class="expired-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      </div>
      <h1>המנוי שלכם לא פעיל</h1>
      <p>כדי לגשת למערכת Nifraim, יש לחדש את המנוי.</p>
      <div class="expired-actions">
        <router-link to="/pricing" class="btn-renew">חידוש מנוי</router-link>
        <button class="btn-logout" @click="logout">התנתקות</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
.expired-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.expired-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 60px 48px;
  text-align: center;
  max-width: 460px;
  width: 100%;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.6s var(--transition);
}

.expired-icon {
  margin-bottom: 24px;
}

.expired-card h1 {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 12px;
  color: var(--text);
}

.expired-card p {
  font-size: 16px;
  color: var(--text-muted);
  margin-bottom: 32px;
  line-height: 1.5;
}

.expired-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-renew {
  display: block;
  padding: 14px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  color: white;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 700;
  transition: all 0.2s;
}

.btn-renew:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.3);
}

.btn-logout {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  background: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-logout:hover {
  border-color: var(--red);
  color: var(--red);
}
</style>
