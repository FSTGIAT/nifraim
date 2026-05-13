<template>
  <div class="run-progress">
    <div class="progress-stages">
      <span :class="['stage', stageClass('login')]">🔐 כניסה</span>
      <span :class="['stage', stageClass('otp')]">📲 קוד</span>
      <span :class="['stage', stageClass('download')]">📥 הורדה</span>
      <span :class="['stage', stageClass('parse')]">📊 עיבוד</span>
    </div>
    <div class="stage-label">{{ stageLabel }}</div>

    <div v-if="showManualOtp" class="manual-otp">
      <input
        v-model="manualOtp"
        placeholder="הזן קוד מה-SMS"
        maxlength="8"
        class="otp-input"
        dir="ltr"
      />
      <button class="btn-save" @click="submitManualOtp">שלח קוד</button>
    </div>

    <div v-if="run?.status === 'success'" class="success-banner">
      ✅ הסתיים בהצלחה — הדוח נוסף להעלאות.
    </div>
    <div
      v-if="run?.status === 'failed' || run?.status === 'timeout'"
      class="failure-banner"
    >
      ❌ הריצה נכשלה: {{ run?.error_message || 'שגיאה לא ידועה' }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'

const props = defineProps({
  runId: { type: String, required: true },
})
const emit = defineEmits(['success', 'failure'])

const store = usePortalAutomationStore()

const manualOtp = ref('')

const STAGE_LABELS = {
  login: '🔐 מתחבר לפורטל...',
  otp: '📲 ממתין לקוד SMS...',
  download: '📥 מוריד דוח...',
  parse: '📊 מעבד את הקובץ...',
}
const STAGE_ORDER = ['login', 'otp', 'download', 'parse']

const run = computed(() =>
  store.activeRun && store.activeRun.id === props.runId ? store.activeRun : null
)

const stageLabel = computed(() => {
  if (!run.value) return ''
  if (run.value.status === 'success') return '✅ הסתיים'
  if (run.value.status === 'failed') return `❌ נכשל: ${run.value.error_message || ''}`
  if (run.value.status === 'timeout') return '⏱ פסק זמן'
  return STAGE_LABELS[run.value.stage] || 'ממתין...'
})

function stageClass(name) {
  if (!run.value || !run.value.stage) return ''
  const cur = STAGE_ORDER.indexOf(run.value.stage)
  const idx = STAGE_ORDER.indexOf(name)
  if (idx < cur) return 'stage-done'
  if (idx === cur) return 'stage-active'
  return ''
}

const showManualOtp = computed(() => run.value?.status === 'awaiting_otp')

watch(
  () => run.value?.status,
  (s) => {
    if (s === 'success') emit('success', run.value)
    if (s === 'failed' || s === 'timeout') emit('failure', run.value)
  }
)

async function submitManualOtp() {
  if (!manualOtp.value) return
  try {
    await store.submitOtp(props.runId, manualOtp.value)
    manualOtp.value = ''
  } catch (_) { /* surfaced via store.error */ }
}
</script>

<style scoped>
.run-progress {
  padding: 12px;
  background: rgba(16, 185, 129, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: 10px;
}

.progress-stages {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.stage {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--bg, #f8fafc);
  font-size: 12px;
  color: var(--text-muted, #64748b);
  border: 1px solid var(--border-subtle, #e2e8f0);
}

.stage-done {
  background: rgba(16, 185, 129, 0.15);
  color: #047857;
  border-color: rgba(16, 185, 129, 0.3);
}

.stage-active {
  background: rgba(59, 130, 246, 0.15);
  color: #1d4ed8;
  border-color: rgba(59, 130, 246, 0.3);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.stage-label {
  font-size: 13px;
  color: var(--text, #0f172a);
  font-weight: 500;
}

.manual-otp {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  align-items: center;
}

.otp-input {
  max-width: 200px;
  text-align: center;
  letter-spacing: 4px;
  font-size: 16px;
  padding: 6px 10px;
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 6px;
  font-family: inherit;
  background: var(--card-bg, #fff);
  color: var(--text, #0f172a);
}

.btn-save {
  background: var(--primary, #f57c00);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 5px 12px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.success-banner {
  margin-top: 10px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #047857;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.failure-banner {
  margin-top: 10px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #b91c1c;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
}
</style>
