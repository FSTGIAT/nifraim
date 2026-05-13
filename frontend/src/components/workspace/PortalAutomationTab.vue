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

    <!-- Twilio number card: provision / show / release -->
    <div class="twilio-card">
      <div class="twilio-info">
        <strong>מספר Twilio לאוטומציה</strong>
        <span v-if="store.twilioNumber" class="twilio-number ltr-number">{{ store.twilioNumber.phone_number }}</span>
        <span v-else class="twilio-empty">לא הוקצה — חברות הפורטל ישלחו OTP לטלפון האישי שלך עד שתקצה מספר.</span>
      </div>
      <div class="twilio-actions">
        <button v-if="!store.twilioNumber" class="btn-primary" :disabled="provisioning" @click="provisionNumber">
          {{ provisioning ? '⏳ רוכש...' : 'רכוש מספר Twilio' }}
        </button>
        <button v-else class="btn-cancel" @click="releaseNumber">שחרר מספר</button>
      </div>
    </div>

    <div v-if="store.loading && !store.credentials.length" class="loading">
      <div class="spinner"></div>
    </div>

    <!-- Add form -->
    <div v-if="showAddForm" class="add-form">
      <div v-if="formError" class="error-banner">{{ formError }}</div>
      <div class="form-row">
        <label>פורטל <span class="req">*</span></label>
        <select v-model="addForm.portal_kind" class="edit-input" :class="{ invalid: formError && !addForm.portal_kind }">
          <option value="" disabled>בחר חברה</option>
          <option v-for="k in store.portalKinds" :key="k.id" :value="k.id">
            {{ k.label }}{{ k.implemented ? '' : ' (לא ממומש)' }}
          </option>
        </select>
      </div>
      <div class="form-row">
        <label>שם משתמש <span class="req">*</span></label>
        <input v-model="addForm.username" class="edit-input" :class="{ invalid: formError && !addForm.username }" />
      </div>
      <div class="form-row">
        <label>סיסמה <span class="req">*</span></label>
        <input v-model="addForm.password" type="password" class="edit-input" :class="{ invalid: formError && !addForm.password }" />
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
        <button class="btn-save" :disabled="saving" @click="createCredential">
          {{ saving ? '⏳ שומר...' : 'שמור' }}
        </button>
        <button class="btn-cancel" @click="cancelAddForm">ביטול</button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!store.loading && !store.credentials.length && !showAddForm" class="empty">
      <p>לא הוגדרו פורטלים. לחץ "הוסף פורטל" כדי להתחיל.</p>
    </div>

    <!-- Recent OTPs panel -->
    <div class="otp-card">
      <div class="otp-card-head">
        <strong>OTPs אחרונים</strong>
        <span class="otp-meta">SMS שהתקבלו בצינור Twilio (לאבחון בלבד)</span>
        <button class="btn-refresh" @click="refreshOtps" :disabled="otpRefreshing">
          {{ otpRefreshing ? '⏳' : '↻' }} רענן
        </button>
      </div>
      <div v-if="!store.otpInbox.length" class="otp-empty">לא התקבלו SMS בינתיים.</div>
      <table v-else class="otp-table">
        <thead>
          <tr>
            <th>זמן</th>
            <th>מאת</th>
            <th>אל</th>
            <th>קוד</th>
            <th>סטטוס</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="otp in store.otpInbox" :key="otp.id">
            <td class="otp-time">{{ formatOtpTime(otp.received_at) }}</td>
            <td class="ltr-number">{{ otp.from_number }}</td>
            <td class="ltr-number">{{ otp.to_number }}</td>
            <td class="otp-code ltr-number">{{ otp.otp_code || '—' }}</td>
            <td>
              <span v-if="otp.consumed_at" class="status-pill status-success">נוצל</span>
              <span v-else class="status-pill status-pending">חדש</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Credentials table -->
    <table v-if="store.credentials.length > 0">
      <thead>
        <tr>
          <th>חברה</th>
          <th>משתמש</th>
          <th>סנכרון טלפון</th>
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
              <td>
                <span v-if="isSynced(cred)" class="status-pill status-success">✓ מסונכרן</span>
                <button
                  v-else-if="store.twilioNumber"
                  class="btn-sync"
                  :disabled="isRunning(cred.id)"
                  @click="syncPhone(cred.id)"
                  :title="`עדכן את הטלפון בפורטל ל-${store.twilioNumber.phone_number}`"
                >
                  סנכרן
                </button>
                <span v-else class="muted">דורש מספר Twilio</span>
              </td>
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
          <!-- Active run progress (shared component) -->
          <tr v-if="store.activeRun?.credential_id === cred.id" class="run-progress-row">
            <td colspan="7">
              <PortalRunProgress :runId="store.activeRun.id" />
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import PortalRunProgress from './PortalRunProgress.vue'

const store = usePortalAutomationStore()

const showAddForm = ref(false)
const editingId = ref(null)
const otpRefreshing = ref(false)
let otpAutoTimer = null

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

function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || kind
}

function statusLabel(status) {
  return STATUS_LABELS[status || 'none']
}

function isRunning(credId) {
  return store.activeRunId && store.activeRun?.credential_id === credId
}

function isSynced(cred) {
  return store.twilioNumber && cred.contact_phone_synced_to === store.twilioNumber.phone_number
}

const provisioning = ref(false)

async function provisionNumber() {
  provisioning.value = true
  try {
    await store.provisionTwilio()
  } finally {
    provisioning.value = false
  }
}

async function releaseNumber() {
  if (!confirm('לשחרר את מספר ה-Twilio? כל הסנכרונים בפורטלים יפסיקו לעבוד.')) return
  await store.releaseTwilio()
}

async function syncPhone(credId) {
  await store.syncContactPhone(credId)
}

async function refreshOtps() {
  otpRefreshing.value = true
  try {
    await store.fetchOtpInbox()
  } finally {
    otpRefreshing.value = false
  }
}

function formatOtpTime(iso) {
  const d = new Date(iso)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) return d.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  return d.toLocaleString('he-IL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// Auto-refresh OTP inbox every 5s while a run is active
watch(() => store.activeRunId, (newVal) => {
  if (otpAutoTimer) {
    clearInterval(otpAutoTimer)
    otpAutoTimer = null
  }
  if (newVal) {
    otpAutoTimer = setInterval(() => store.fetchOtpInbox(), 5000)
  }
})

const formError = ref('')
const saving = ref(false)

function openAddForm() {
  Object.assign(addForm, {
    portal_kind: '', username: '', password: '',
    twilio_to_number: '', schedule_enabled: false,
  })
  formError.value = ''
  showAddForm.value = true
}

function cancelAddForm() {
  showAddForm.value = false
  formError.value = ''
}

async function createCredential() {
  formError.value = ''
  const missing = []
  if (!addForm.portal_kind) missing.push('פורטל')
  if (!addForm.username) missing.push('שם משתמש')
  if (!addForm.password) missing.push('סיסמה')
  if (missing.length) {
    formError.value = 'חסרים שדות חובה: ' + missing.join(', ')
    return
  }

  saving.value = true
  try {
    await store.createCredential({
      portal_kind: addForm.portal_kind,
      username: addForm.username,
      password: addForm.password,
      twilio_to_number: addForm.twilio_to_number || null,
      schedule_enabled: addForm.schedule_enabled,
    })
    showAddForm.value = false
  } catch (e) {
    formError.value = store.error || e.response?.data?.detail || 'שגיאה בשמירה'
  } finally {
    saving.value = false
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

onMounted(async () => {
  await store.fetchPortalKinds()
  await store.fetchCredentials()
  await store.fetchTwilioNumber()
  await store.fetchOtpInbox()
})

onUnmounted(() => {
  if (otpAutoTimer) clearInterval(otpAutoTimer)
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

.edit-input.invalid {
  border-color: #ef4444;
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.1);
}

.req {
  color: #ef4444;
  font-weight: 700;
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.twilio-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 14px;
  margin-bottom: 14px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  flex-wrap: wrap;
}

.twilio-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.twilio-info strong {
  font-size: 13px;
  color: var(--text);
}

.twilio-number {
  font-size: 14px;
  color: var(--accent-emerald, #047857);
  font-weight: 700;
}

.twilio-empty {
  font-size: 12px;
  color: var(--text-muted);
}

.btn-primary {
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 7px 14px;
  font-family: inherit;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}

.btn-primary:disabled {
  background: var(--text-muted);
  cursor: not-allowed;
}

.btn-sync {
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 4px 10px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-sync:disabled {
  background: var(--text-muted);
  cursor: not-allowed;
}

.muted {
  color: var(--text-muted);
  font-size: 12px;
}

.otp-card {
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 16px;
}

.otp-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.otp-card-head strong {
  font-size: 13px;
  color: var(--text);
}

.otp-meta {
  font-size: 11px;
  color: var(--text-muted);
  flex: 1;
}

.btn-refresh {
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 3px 10px;
  font-family: inherit;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
}

.btn-refresh:hover:not(:disabled) {
  color: var(--text);
  border-color: var(--text-muted);
}

.btn-refresh:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.otp-empty {
  padding: 12px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}

.otp-table {
  font-size: 12px;
  width: 100%;
}

.otp-table th, .otp-table td {
  padding: 5px 8px;
  border-bottom: 1px dashed var(--border-subtle);
}

.otp-time {
  color: var(--text-muted);
  white-space: nowrap;
}

.otp-code {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--accent-emerald, #047857);
}

.status-pill.status-pending {
  background: rgba(59, 130, 246, 0.15);
  color: #1d4ed8;
}
</style>
