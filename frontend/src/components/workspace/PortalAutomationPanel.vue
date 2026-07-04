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
        :style="{ '--brand': brandFor(cred.portal_kind).color }"
      >
        <div class="cred-head">
          <span class="cred-ico" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <path :d="brandFor(cred.portal_kind).iconPath" />
            </svg>
          </span>
          <div class="cred-head-txt">
            <strong>{{ portalLabel(cred.portal_kind) }}</strong>
            <span class="cred-user ltr-number">{{ cred.username }}</span>
          </div>
        </div>

        <button
          class="btn-run"
          :disabled="isRunning(cred.id) || anyRunning"
          @click="runNow(cred.id)"
        >
          <span v-if="isRunning(cred.id)" class="btn-run-spin" aria-hidden="true"></span>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="7 4 20 12 7 20" /></svg>
          <span>{{ isRunning(cred.id) ? 'רץ…' : 'הרץ אוטומציה' }}</span>
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
import { brandFor } from '../../utils/companyBrand.js'
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
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.cred-card:hover { border-color: color-mix(in srgb, var(--brand) 40%, transparent); box-shadow: 0 6px 18px color-mix(in srgb, var(--brand) 12%, transparent); }

.cred-head {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}
.cred-ico {
  flex-shrink: 0;
  width: 38px; height: 38px; border-radius: 11px;
  display: grid; place-items: center;
  background: color-mix(in srgb, var(--brand) 12%, transparent);
  color: var(--brand);
}
.cred-head-txt { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.cred-head-txt strong {
  font-size: 13.5px; font-weight: 700; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cred-user {
  font-size: 12px; color: var(--text-muted);
  direction: ltr; text-align: right;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.btn-run {
  display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  background: var(--brand);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.15s, opacity 0.15s;
}
.btn-run:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.btn-run:not(:disabled):hover {
  box-shadow: 0 6px 16px color-mix(in srgb, var(--brand) 35%, transparent);
  transform: translateY(-1px);
}
.btn-run-spin {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4); border-top-color: #fff;
  animation: btn-run-spin 0.8s linear infinite;
}
@keyframes btn-run-spin { to { transform: rotate(360deg); } }
</style>
