<template>
  <div class="auto-page">
    <!-- ─── Header ──────────────────────────────────────────── -->
    <header class="page-head">
      <div class="page-titles">
        <span class="eyebrow">תפעול / אוטומציה</span>
        <h2 class="page-title">פורטלי חברות הביטוח</h2>
        <p class="page-sub">חבר חברה אחת, גרור לתזמון, והדוח יוריד את עצמו.</p>
      </div>
    </header>

    <div v-if="store.error" class="error-banner">{{ store.error }}</div>

    <div v-if="store.loading && !store.credentials.length" class="loading-strip">
      <span class="spinner" aria-hidden="true"></span>
      <span>טוען פורטלים…</span>
    </div>

    <!-- ─── Main canvas: vertical schedule rail + cards pane ─── -->
    <PortalAutomationCanvas
      v-else
      :credentials="store.credentials"
      :portal-label="portalLabel"
      :active-run="store.activeRun"
      :active-run-id="store.activeRunId"
      @run="runNow"
      @edit="openEdit"
      @delete="deleteCred"
      @schedule="onSchedule"
      @unschedule="onUnschedule"
      @add="openAdd"
    />

    <!-- ─── Debug disclosure ────────────────────────────────── -->
    <details class="debug-block">
      <summary>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        </svg>
        <span>דיבאג / OTP inbox</span>
      </summary>
      <div class="otp-card">
        <div class="otp-card-head">
          <strong>OTPs אחרונים</strong>
          <span class="otp-meta">SMS שהתקבלו (Twilio + העברת SMS)</span>
          <button class="btn-refresh" @click="refreshOtps" :disabled="otpRefreshing">
            {{ otpRefreshing ? '⏳' : '↻' }} רענן
          </button>
        </div>
        <div v-if="!store.otpInbox.length" class="otp-empty">לא התקבלו SMS בינתיים.</div>
        <table v-else class="otp-table">
          <thead>
            <tr>
              <th>זמן</th><th>מאת</th><th>אל</th><th>קוד</th><th>סטטוס</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="otp in store.otpInbox" :key="otp.id">
              <td class="otp-time">{{ formatOtpTime(otp.received_at) }}</td>
              <td><span class="ltr-number">{{ otp.from_number }}</span></td>
              <td><span class="ltr-number">{{ otp.to_number }}</span></td>
              <td class="otp-code"><span class="ltr-number">{{ otp.otp_code || '—' }}</span></td>
              <td>
                <span v-if="otp.consumed_at" class="status-pill status-success">נוצל</span>
                <span v-else class="status-pill status-pending">חדש</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

    <PortalCredentialModal
      :open="modalOpen"
      :mode="modalMode"
      :credential="modalCred"
      @close="modalOpen = false"
      @saved="onModalSaved"
    />

    <!-- OTP modal — shared for any card's active run. -->
    <PortalOtpModal
      :open="otpModalOpen"
      :run="store.activeRun"
      :company-name="activeCredentialLabel"
      @submit="onSubmitOtp"
      @close="closeOtpModal"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import PortalCredentialModal from './PortalCredentialModal.vue'
import PortalAutomationCanvas from './PortalAutomationCanvas.vue'
import PortalOtpModal from './PortalOtpModal.vue'

const store = usePortalAutomationStore()

const otpRefreshing = ref(false)
let otpAutoTimer = null

// ─── Modal state ──────────────────────────────────────────
const modalOpen = ref(false)
const modalMode = ref('add')
const modalCred = ref(null)

function openAdd() {
  modalMode.value = 'add'
  modalCred.value = null
  modalOpen.value = true
}
function openEdit(cred) {
  modalMode.value = 'edit'
  modalCred.value = cred
  modalOpen.value = true
}
function onModalSaved() {
  // store.create/update already updates credentials[]; nothing else needed
}

function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || kind
}

// ─── Per-credential actions ───────────────────────────────
async function runNow(id) { await store.runNow(id) }
async function deleteCred(id) {
  if (!confirm('למחוק את ההגדרה?')) return
  await store.deleteCredential(id)
}

// ─── Schedule drag results ────────────────────────────────
async function onSchedule({ id, schedule_kind }) {
  await store.updateSchedule(id, schedule_kind)
}
async function onUnschedule(id) {
  await store.updateSchedule(id, 'manual')
}

// ─── OTP modal (shared across all card runs) ──────────────
const otpModalOpen = ref(false)
const activeCredential = computed(() => {
  const cid = store.activeRun?.credential_id
  return store.credentials.find((c) => c.id === cid) || null
})
const activeCredentialLabel = computed(() => {
  const cred = activeCredential.value
  return cred ? portalLabel(cred.portal_kind) : ''
})
watch(() => store.activeRun?.status, (s) => {
  if (s === 'awaiting_otp') otpModalOpen.value = true
  if (['success', 'failed', 'timeout'].includes(s)) otpModalOpen.value = false
})
async function onSubmitOtp(otp) {
  if (!store.activeRun?.id) return
  try { await store.submitOtp(store.activeRun.id, otp) } catch (_) {}
}
async function closeOtpModal() {
  // Close = cancel the run. Same flow as the dock OTP modal.
  const id = store.activeRun?.id
  otpModalOpen.value = false
  if (id) await store.cancelRun(id)
}

// ─── OTP inbox ────────────────────────────────────────────
async function refreshOtps() {
  otpRefreshing.value = true
  try { await store.fetchOtpInbox() } finally { otpRefreshing.value = false }
}
function formatOtpTime(iso) {
  const d = new Date(iso)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) return d.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  return d.toLocaleString('he-IL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
watch(() => store.activeRunId, (newVal) => {
  if (otpAutoTimer) { clearInterval(otpAutoTimer); otpAutoTimer = null }
  if (newVal) otpAutoTimer = setInterval(() => store.fetchOtpInbox(), 5000)
})

onMounted(async () => {
  await store.fetchPortalKinds()
  await store.fetchCredentials()
  await store.fetchOtpInbox()
})
onUnmounted(() => {
  if (otpAutoTimer) clearInterval(otpAutoTimer)
  store.reset()
})
</script>

<style scoped>
.auto-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 20px 40px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Header */
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}
.page-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.eyebrow {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
  letter-spacing: 0.4px;
}
.page-title { margin: 0; font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.3px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--text-muted); }

.error-banner {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #b91c1c;
  padding: 10px 14px;
  border-radius: var(--radius-sm, 8px);
  font-size: 13px;
}

.loading-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  color: var(--text-muted);
  font-size: 13px;
}
.spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border-subtle);
  border-top-color: var(--primary, #F57C00);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Debug disclosure */
.debug-block {
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--bg);
  padding: 10px 14px;
}
.debug-block summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary, var(--text-muted));
  padding: 4px 2px;
  list-style: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.debug-block summary::-webkit-details-marker { display: none; }
.debug-block summary:hover { color: var(--text); }
.debug-block[open] summary { color: var(--text); }

.otp-card { padding: 8px 0 0; }
.otp-card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.otp-card-head strong { font-size: 13px; color: var(--text); }
.otp-meta { font-size: 11px; color: var(--text-muted); flex: 1; }
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
.btn-refresh:hover:not(:disabled) { color: var(--text); border-color: var(--text-muted); }
.btn-refresh:disabled { cursor: not-allowed; opacity: 0.6; }
.otp-empty { padding: 12px; text-align: center; color: var(--text-muted); font-size: 12px; }
.otp-table { font-size: 12px; width: 100%; border-collapse: collapse; }
.otp-table th, .otp-table td { padding: 5px 8px; border-bottom: 1px dashed var(--border-subtle); text-align: start; }
.otp-time { color: var(--text-muted); white-space: nowrap; }
.otp-code { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-weight: 700; letter-spacing: 1px; color: var(--accent-emerald, #047857); }

.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.status-success { background: rgba(16, 185, 129, 0.15); color: #047857; }
.status-pending { background: rgba(59, 130, 246, 0.15); color: #1d4ed8; }
</style>
