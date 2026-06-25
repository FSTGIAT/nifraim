<template>
  <div class="auto-panel">
    <div class="panel-header">
      <div>
        <h3>{{ title }}</h3>
        <p class="subtitle">לחץ על חברה להפעלת אוטומציה — כניסה, קוד SMS, הורדת דוח, עיבוד</p>
      </div>
    </div>

    <div v-if="store.error" class="error-banner">{{ store.error }}</div>

    <div v-if="!store.credentials.length && !store.loading" class="empty">
      <p>לא הוגדרו פורטלים. עבור ללשונית "אוטומציה" כדי להוסיף משתמש וסיסמה לכל חברה.</p>
      <button class="btn-secondary" @click="$emit('navigate-to-credentials')">
        עבור להגדרות אוטומציה
      </button>
    </div>

    <div v-else class="cred-grid">
      <div
        v-for="cred in store.credentials"
        :key="cred.id"
        class="cred-card"
      >
        <div class="cred-head">
          <strong>{{ portalLabel(cred.portal_kind) }}</strong>
        </div>
        <div class="cred-user">{{ cred.username }}</div>
        <button
          class="btn-run"
          :disabled="isRunning(cred.id) || anyRunning"
          @click="runNow(cred.id)"
        >
          {{ isRunning(cred.id) ? '⏳ רץ...' : '▶ הרץ אוטומציה' }}
        </button>

        <PortalRunProgress
          v-if="store.activeRun?.credential_id === cred.id"
          :runId="store.activeRun.id"
          @success="onSuccess(cred, $event)"
          @failure="onFailure(cred, $event)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import PortalRunProgress from './PortalRunProgress.vue'

const props = defineProps({
  title: { type: String, default: 'אוטומציה — הורדה ישירה מהפורטל' },
})
const emit = defineEmits(['success', 'failure', 'navigate-to-credentials'])

const store = usePortalAutomationStore()

const anyRunning = computed(() => !!store.activeRunId)

function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || kind
}

function isRunning(credId) {
  return store.activeRunId && store.activeRun?.credential_id === credId
}

async function runNow(credId) {
  await store.runNow(credId)
}

function onSuccess(cred, run) {
  emit('success', { credential: cred, run })
}

function onFailure(cred, run) {
  emit('failure', { credential: cred, run })
}

onMounted(async () => {
  if (!store.portalKinds.length) await store.fetchPortalKinds()
  if (!store.credentials.length) await store.fetchCredentials()
})
</script>

<style scoped>
.auto-panel {
  background: var(--card-bg);
  border: 1px solid var(--glass-border, var(--border-subtle));
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
}

.panel-header {
  margin-bottom: 16px;
}

h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}

.subtitle {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 12px;
}

.error-banner {
  background: rgba(194, 57, 52, 0.1);
  border: 1px solid rgba(194, 57, 52, 0.3);
  color: #C23934;
  padding: 8px 12px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
}

.empty {
  text-align: center;
  padding: 32px 16px;
  color: var(--text-muted);
  font-size: 14px;
}

.btn-secondary {
  margin-top: 12px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  font-family: inherit;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}

.btn-secondary:hover {
  background: var(--primary-deep, var(--primary));
  transform: translateY(-1px);
}

.cred-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.cred-card {
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cred-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 14px;
  color: var(--text);
}

.cred-user {
  font-size: 12px;
  color: var(--text-muted);
}

.btn-run {
  background: linear-gradient(135deg, #2E844A, #1B5E20);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-run:disabled {
  background: var(--text-muted);
  cursor: not-allowed;
  opacity: 0.7;
}

.btn-run:not(:disabled):hover {
  box-shadow: 0 4px 12px rgba(46, 132, 74, 0.3);
  transform: translateY(-1px);
}
</style>
