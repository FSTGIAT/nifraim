<template>
  <div class="auto-card">
    <div class="auto-header">
      <div>
        <h3>אוטומציה לפורטלים</h3>
        <p class="subtitle">התחברות אוטומטית לפורטלים, קבלת קוד SMS, והורדת דוחות</p>
      </div>
      <button v-if="!showAddForm" class="btn-add" @click="openAddForm">+ הוסף פורטל</button>
    </div>

    <div v-if="store.error" class="error-banner">{{ store.error }}</div>

    <div v-if="store.loading && !store.credentials.length" class="loading">
      <div class="spinner"></div>
    </div>

    <!-- Add form -->
    <div v-if="showAddForm" class="add-form">
      <div class="form-row">
        <label>פורטל</label>
        <select v-model="addForm.portal_kind" class="edit-input">
          <option value="" disabled>בחר חברה</option>
          <option v-for="k in store.portalKinds" :key="k.id" :value="k.id">
            {{ k.label }}{{ k.implemented ? '' : ' (לא ממומש)' }}
          </option>
        </select>
      </div>
      <div class="form-row">
        <label>שם משתמש</label>
        <input v-model="addForm.username" class="edit-input" />
      </div>
      <div class="form-row">
        <label>סיסמה</label>
        <input v-model="addForm.password" type="password" class="edit-input" />
      </div>
      <div class="form-row">
        <label>מספר Twilio (אופציונלי)</label>
        <input v-model="addForm.twilio_to_number" class="edit-input" placeholder="+972..." dir="ltr" />
      </div>
      <div class="form-row">
        <label>הרצה אוטומטית יומית</label>
        <input v-model="addForm.schedule_enabled" type="checkbox" />
      </div>
      <div class="form-actions">
        <button class="btn-save" @click="createCredential">שמור</button>
        <button class="btn-cancel" @click="showAddForm = false">ביטול</button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!store.loading && !store.credentials.length && !showAddForm" class="empty">
      <p>לא הוגדרו פורטלים. לחץ "הוסף פורטל" כדי להתחיל.</p>
    </div>

    <!-- Credentials table -->
    <table v-if="store.credentials.length > 0">
      <thead>
        <tr>
          <th>חברה</th>
          <th>משתמש</th>
          <th>מספר Twilio</th>
          <th>תזמון</th>
          <th>סטטוס אחרון</th>
          <th>פעולה</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <template v-for="cred in store.credentials" :key="cred.id">
          <tr>
            <template v-if="editingId === cred.id">
              <td>{{ portalLabel(cred.portal_kind) }}</td>
              <td><input v-model="editForm.username" class="edit-input" /></td>
              <td><input v-model="editForm.twilio_to_number" class="edit-input" dir="ltr" /></td>
              <td><input v-model="editForm.schedule_enabled" type="checkbox" /></td>
              <td>
                <input v-model="editForm.password" type="password" placeholder="חדש (אופציונלי)" class="edit-input" />
              </td>
              <td colspan="2" class="actions">
                <button class="btn-save" @click="saveEdit(cred.id)">שמור</button>
                <button class="btn-cancel" @click="editingId = null">ביטול</button>
              </td>
            </template>
            <template v-else>
              <td><strong>{{ portalLabel(cred.portal_kind) }}</strong></td>
              <td>{{ cred.username }}</td>
              <td class="ltr-number">{{ cred.twilio_to_number || '—' }}</td>
              <td>{{ cred.schedule_enabled ? '✓ יומי' : '—' }}</td>
              <td>
                <span class="status-pill" :class="`status-${cred.last_run_status || 'none'}`">
                  {{ statusLabel(cred.last_run_status) }}
                </span>
                <div v-if="cred.last_error" class="last-error" :title="cred.last_error">
                  {{ cred.last_error.slice(0, 60) }}
                </div>
              </td>
              <td class="actions">
                <button
                  class="btn-run"
                  :disabled="isRunning(cred.id)"
                  @click="runNow(cred.id)"
                >
                  {{ isRunning(cred.id) ? '⏳ רץ...' : '▶ הרץ עכשיו' }}
                </button>
              </td>
              <td class="actions">
                <button class="btn-edit" @click="startEdit(cred)" title="ערוך">&#9998;</button>
                <button class="btn-del" @click="deleteCred(cred.id)" title="מחק">&#10005;</button>
              </td>
            </template>
          </tr>
          <!-- Active run progress card -->
          <tr v-if="isRunning(cred.id) && store.activeRun" class="run-progress-row">
            <td colspan="7">
              <div class="run-progress">
                <div class="progress-stages">
                  <span :class="['stage', stageClass(store.activeRun, 'login')]">🔐 כניסה</span>
                  <span :class="['stage', stageClass(store.activeRun, 'otp')]">📲 קוד</span>
                  <span :class="['stage', stageClass(store.activeRun, 'download')]">📥 הורדה</span>
                  <span :class="['stage', stageClass(store.activeRun, 'parse')]">📊 עיבוד</span>
                </div>
                <div class="stage-label">{{ stageLabel(store.activeRun) }}</div>

                <!-- Manual OTP fallback (after 60s of awaiting_otp) -->
                <div v-if="showManualOtp" class="manual-otp">
                  <input v-model="manualOtp" placeholder="הזן קוד מה-SMS" maxlength="8" class="edit-input otp-input" dir="ltr" />
                  <button class="btn-save" @click="submitManualOtp">שלח קוד</button>
                </div>
              </div>
            </td>
          </tr>
          <!-- Result line after a finished run -->
          <tr v-if="cred.last_run_status === 'success' && !isRunning(cred.id) && store.activeRun?.credential_id === cred.id" class="result-row">
            <td colspan="7">
              <div class="success-banner">
                ✅ הסתיים בהצלחה — הדוח נוסף להעלאות.
                <button class="btn-link" @click="$emit('go-to-uploads')">פתח</button>
              </div>
            </td>
          </tr>
          <tr v-if="(cred.last_run_status === 'failed' || cred.last_run_status === 'timeout') && !isRunning(cred.id) && store.activeRun?.credential_id === cred.id" class="result-row">
            <td colspan="7">
              <div class="failure-banner">
                ❌ הריצה נכשלה: {{ store.activeRun?.error_message || cred.last_error || 'שגיאה לא ידועה' }}
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'

const store = usePortalAutomationStore()

const showAddForm = ref(false)
const editingId = ref(null)
const manualOtp = ref('')
const otpWaitStartedAt = ref(null)
const now = ref(Date.now())
let nowTicker = null

const addForm = reactive({
  portal_kind: '',
  username: '',
  password: '',
  twilio_to_number: '',
  schedule_enabled: false,
})

const editForm = reactive({
  username: '',
  password: '',
  twilio_to_number: '',
  schedule_enabled: false,
})

const STATUS_LABELS = {
  success: '✓ הצליח',
  failed: '✗ נכשל',
  timeout: '⏱ פסק זמן',
  pending: 'ממתין',
  running: 'רץ',
  awaiting_otp: 'ממתין לקוד',
  downloading: 'מוריד',
  parsing: 'מעבד',
  none: '—',
}
const STAGE_LABELS = {
  login: '🔐 מתחבר לפורטל...',
  otp: '📲 ממתין לקוד SMS...',
  download: '📥 מוריד דוח...',
  parse: '📊 מעבד את הקובץ...',
}

function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || kind
}

function statusLabel(status) {
  return STATUS_LABELS[status || 'none']
}

function stageLabel(run) {
  if (!run) return ''
  if (run.status === 'success') return '✅ הסתיים'
  if (run.status === 'failed') return `❌ נכשל: ${run.error_message || ''}`
  if (run.status === 'timeout') return '⏱ פסק זמן'
  return STAGE_LABELS[run.stage] || 'ממתין...'
}

function stageClass(run, name) {
  if (!run || !run.stage) return ''
  const order = ['login', 'otp', 'download', 'parse']
  const cur = order.indexOf(run.stage)
  const idx = order.indexOf(name)
  if (idx < cur) return 'stage-done'
  if (idx === cur) return 'stage-active'
  return ''
}

function isRunning(credId) {
  return store.activeRunId && store.activeRun?.credential_id === credId
}

const showManualOtp = computed(() => {
  if (!store.activeRun || store.activeRun.status !== 'awaiting_otp') return false
  if (!otpWaitStartedAt.value) return false
  return now.value - otpWaitStartedAt.value > 60000
})

watch(() => store.activeRun?.status, (s) => {
  if (s === 'awaiting_otp' && !otpWaitStartedAt.value) {
    otpWaitStartedAt.value = Date.now()
  } else if (s !== 'awaiting_otp') {
    otpWaitStartedAt.value = null
  }
})

function openAddForm() {
  Object.assign(addForm, {
    portal_kind: '', username: '', password: '',
    twilio_to_number: '', schedule_enabled: false,
  })
  showAddForm.value = true
}

async function createCredential() {
  if (!addForm.portal_kind || !addForm.username || !addForm.password) return
  try {
    await store.createCredential({
      portal_kind: addForm.portal_kind,
      username: addForm.username,
      password: addForm.password,
      twilio_to_number: addForm.twilio_to_number || null,
      schedule_enabled: addForm.schedule_enabled,
    })
    showAddForm.value = false
  } catch (_) {
    // store.error already set
  }
}

function startEdit(cred) {
  editingId.value = cred.id
  editForm.username = cred.username
  editForm.password = ''
  editForm.twilio_to_number = cred.twilio_to_number || ''
  editForm.schedule_enabled = cred.schedule_enabled
}

async function saveEdit(id) {
  const payload = {
    username: editForm.username,
    twilio_to_number: editForm.twilio_to_number || null,
    schedule_enabled: editForm.schedule_enabled,
  }
  if (editForm.password) payload.password = editForm.password
  await store.updateCredential(id, payload)
  editingId.value = null
}

async function deleteCred(id) {
  if (!confirm('למחוק את ההגדרה?')) return
  await store.deleteCredential(id)
}

async function runNow(id) {
  await store.runNow(id)
}

async function submitManualOtp() {
  if (!store.activeRunId || !manualOtp.value) return
  try {
    await store.submitOtp(store.activeRunId, manualOtp.value)
    manualOtp.value = ''
  } catch (e) {
    // ignore
  }
}

onMounted(async () => {
  await store.fetchPortalKinds()
  await store.fetchCredentials()
  nowTicker = setInterval(() => { now.value = Date.now() }, 1000)
})

onUnmounted(() => {
  if (nowTicker) clearInterval(nowTicker)
  store.reset()
})
</script>

<style scoped>
.auto-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  max-width: 1100px;
  margin: 0 auto;
}

.auto-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
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

.btn-add {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-family: inherit;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-add:hover {
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
  transform: translateY(-1px);
}

.error-banner {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #b91c1c;
  padding: 8px 12px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 32px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty {
  padding: 32px;
  text-align: center;
  color: var(--text-muted);
}

.add-form {
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 14px;
  display: grid;
  gap: 8px;
}

.form-row {
  display: grid;
  grid-template-columns: 180px 1fr;
  align-items: center;
  gap: 12px;
}

.form-row label {
  font-size: 13px;
  color: var(--text-muted);
}

.edit-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  font-family: inherit;
  font-size: 13px;
  background: var(--card-bg);
  color: var(--text);
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 4px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

thead {
  background: var(--bg);
}

th {
  padding: 8px 10px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  font-size: 12px;
  border-bottom: 1px solid var(--border-subtle);
}

td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}

.actions {
  display: flex;
  gap: 4px;
}

.btn-run, .btn-save, .btn-cancel, .btn-edit, .btn-del {
  border: none;
  border-radius: 6px;
  padding: 5px 10px;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  font-weight: 600;
}

.btn-run {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.btn-run:disabled {
  background: var(--text-muted);
  cursor: not-allowed;
}

.btn-save { background: var(--primary); color: white; }
.btn-cancel { background: var(--text-muted); color: white; }
.btn-edit, .btn-del { background: transparent; color: var(--text-muted); padding: 4px 8px; }
.btn-edit:hover { color: var(--primary); }
.btn-del:hover { color: #ef4444; }

.btn-link {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  font: inherit;
  text-decoration: underline;
  margin-right: 8px;
}

.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.status-success { background: rgba(16, 185, 129, 0.15); color: #047857; }
.status-failed, .status-timeout { background: rgba(239, 68, 68, 0.15); color: #b91c1c; }
.status-running, .status-pending, .status-awaiting_otp,
.status-downloading, .status-parsing { background: rgba(59, 130, 246, 0.15); color: #1d4ed8; }
.status-none { background: var(--bg); color: var(--text-muted); }

.last-error {
  margin-top: 4px;
  font-size: 11px;
  color: #b91c1c;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-progress-row td {
  background: rgba(16, 185, 129, 0.05);
}

.run-progress {
  padding: 10px 4px;
}

.progress-stages {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.stage {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--bg);
  font-size: 12px;
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
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
  color: var(--text);
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
}

.success-banner {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #047857;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.failure-banner {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #b91c1c;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
}
</style>
