<template>
  <div class="password-card">
    <div class="card-icon">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0110 0v4"/>
      </svg>
    </div>
    <h2>תיק הביטוח האישי שלך</h2>
    <p class="subtitle">הזן את הסיסמה שקיבלת מהסוכן שלך</p>

    <form @submit.prevent="onSubmit">
      <div class="input-group">
        <input
          ref="passwordInput"
          :type="showPassword ? 'text' : 'password'"
          v-model="password"
          placeholder="סיסמה"
          dir="ltr"
          :disabled="loading"
          autocomplete="off"
        />
        <button type="button" class="toggle-vis" @click="showPassword = !showPassword" tabindex="-1">
          <svg v-if="showPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
            <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
            <line x1="1" y1="1" x2="23" y2="23"/>
          </svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
      </div>

      <Transition name="fade">
        <p v-if="error" class="error-text">{{ error }}</p>
      </Transition>

      <button type="submit" class="submit-btn" :disabled="!password || loading">
        <template v-if="loading">
          <div class="btn-spinner"></div>
          <span>מתחבר...</span>
        </template>
        <template v-else>
          <span>כניסה</span>
        </template>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePortalStore } from '../../stores/portal.js'

const props = defineProps({
  token: String,
  loading: Boolean,
  error: String,
})

const emit = defineEmits(['submit'])
const portalStore = usePortalStore()
const password = ref('')
const showPassword = ref(false)
const passwordInput = ref(null)

onMounted(() => {
  passwordInput.value?.focus()
})

async function onSubmit() {
  if (!password.value) return
  try {
    await portalStore.accessPortal(props.token, password.value)
    emit('submit')
  } catch {
    // error shown in store
  }
}
</script>

<style scoped>
.password-card {
  max-width: 400px;
  margin: 60px auto 0;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 40px 32px;
  text-align: center;
  box-shadow: var(--shadow-lg);
  animation: fadeInUp 0.5s var(--transition);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.card-icon {
  color: var(--primary);
  margin-bottom: 16px;
}

h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 6px;
}

.subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0 0 28px;
}

form { display: flex; flex-direction: column; gap: 16px; }

.input-group {
  position: relative;
}

.input-group input {
  width: 100%;
  padding: 14px 44px 14px 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 16px;
  font-family: inherit;
  background: var(--bg-surface);
  color: var(--text);
  transition: all 0.25s var(--transition);
  text-align: center;
  letter-spacing: 2px;
}

.input-group input:focus {
  border-color: var(--primary);
  box-shadow: var(--shadow-glow);
}

.toggle-vis {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  padding: 4px;
}

.toggle-vis:hover { color: var(--text-secondary); }

.error-text {
  font-size: 13px;
  color: var(--red);
  background: var(--red-light);
  padding: 8px 12px;
  border-radius: 6px;
  margin: 0;
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 14px;
  background: var(--primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: 16px;
  font-weight: 700;
  font-family: inherit;
  transition: all 0.3s var(--transition);
}

.submit-btn:hover:not(:disabled) {
  background: var(--primary-deep);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.3);
}

.submit-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
