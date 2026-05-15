<template>
  <div class="auto-page">
    <!-- ─── Header ──────────────────────────────────────────── -->
    <header class="page-head">
      <div class="page-titles">
        <span class="eyebrow">תפעול / אוטומציה</span>
        <h2 class="page-title">פורטלי חברות הביטוח</h2>
        <p class="page-sub">חבר חברה אחת, גרור לתזמון, והדוח יוריד את עצמו.</p>
      </div>
      <div class="page-actions">
        <span
          v-if="store.twilioNumber"
          class="twilio-badge"
          :title="'מספר Twilio פעיל'"
        >
          <span class="ltr-number tp-num">{{ store.twilioNumber.phone_number }}</span>
          <button class="tp-release" @click="releaseNumber" title="שחרר את המספר">שחרר</button>
        </span>
        <button
          v-else
          class="btn-add btn-add--secondary"
          :disabled="provisioning"
          @click="provisionNumber"
        >
          {{ provisioning ? 'רוכש…' : 'הקצה מספר Twilio' }}
        </button>
        <button class="btn-add" @click="openAdd">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14"/><path d="M12 5v14"/>
          </svg>
          <span>הוסף פורטל</span>
        </button>
      </div>
    </header>

    <div v-if="store.error" class="error-banner">{{ store.error }}</div>

    <!-- ─── Schedule zones (drop targets) ───────────────────── -->
    <PortalScheduleZones
      :credentials="store.credentials"
      :portal-label="portalLabel"
      @drop="onZoneDrop"
      @remove="onZoneRemove"
    />

    <!-- ─── Manual section: cards not assigned to any schedule ─ -->
    <section class="manual-section">
      <div class="ms-head">
        <span class="ms-title">פורטלים — ידני</span>
        <span class="ms-meta">{{ manualCreds.length }} פורטל{{ manualCreds.length === 1 ? '' : 'ים' }}</span>
      </div>

      <div v-if="store.loading && !store.credentials.length" class="loading-strip">
        <span class="spinner" aria-hidden="true"></span>
        <span>טוען פורטלים…</span>
      </div>

      <div v-else-if="!store.credentials.length" class="empty-state">
        <p>עדיין לא הוגדרו פורטלים.</p>
        <button class="btn-add" @click="openAdd">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14"/><path d="M12 5v14"/>
          </svg>
          <span>הוסיף פורטל ראשון</span>
        </button>
      </div>

      <div v-else class="cards-grid">
        <PortalCard
          v-for="cred in manualCreds"
          :key="cred.id"
          :cred="cred"
          :is-running="isRunning(cred.id)"
          :is-synced="isSynced(cred)"
          :twilio-number="store.twilioNumber"
          :portal-label="portalLabel(cred.portal_kind)"
          :is-implemented="isImplemented(cred.portal_kind)"
          :active-run="store.activeRun"
          :draggable="true"
          @run="runNow(cred.id)"
          @edit="openEdit(cred)"
          @delete="deleteCred(cred.id)"
          @sync="syncPhone(cred.id)"
          @dragstart="onCardDragStart($event, cred.id)"
        />
      </div>

    </section>

    <!-- Cards in scheduled zones still need run/edit/delete affordances. We
         render a "scheduled" section listing those cards in detail below. -->
    <section v-if="scheduledCreds.length" class="scheduled-section">
      <div class="ms-head">
        <span class="ms-title">פורטלים מתוזמנים</span>
        <span class="ms-meta">פעולות ידניות זמינות גם להם</span>
      </div>
      <div class="cards-grid">
        <PortalCard
          v-for="cred in scheduledCreds"
          :key="cred.id"
          :cred="cred"
          :is-running="isRunning(cred.id)"
          :is-synced="isSynced(cred)"
          :twilio-number="store.twilioNumber"
          :portal-label="portalLabel(cred.portal_kind)"
          :is-implemented="isImplemented(cred.portal_kind)"
          :active-run="store.activeRun"
          :draggable="true"
          @run="runNow(cred.id)"
          @edit="openEdit(cred)"
          @delete="deleteCred(cred.id)"
          @sync="syncPhone(cred.id)"
          @dragstart="onCardDragStart($event, cred.id)"
        />
      </div>
    </section>

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
          <span class="otp-meta">SMS שהתקבלו בצינור Twilio (לאבחון בלבד)</span>
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

    <!-- OTP modal — shared for any card's active run.
         Close = cancel (mirrors the dock behavior on the comparison tab). -->
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
import PortalScheduleZones from './PortalScheduleZones.vue'
import PortalCard from './PortalCard.vue'
import PortalOtpModal from './PortalOtpModal.vue'

const store = usePortalAutomationStore()

const provisioning = ref(false)
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
function onModalSaved(cred) {
  // store.create/update already updates credentials[]; nothing else needed
}

// ─── Derived lists ────────────────────────────────────────
const manualCreds   = computed(() => store.credentials.filter((c) => !c.schedule_kind || c.schedule_kind === 'manual'))
const scheduledCreds = computed(() => store.credentials.filter((c) => c.schedule_kind && c.schedule_kind !== 'manual'))

function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || kind
}
function isImplemented(kind) {
  return !!store.portalKinds.find((k) => k.id === kind)?.implemented
}
function isRunning(credId) {
  return store.activeRunId && store.activeRun?.credential_id === credId
}
function isSynced(cred) {
  return store.twilioNumber && cred.contact_phone_synced_to === store.twilioNumber.phone_number
}

// ─── Twilio actions ───────────────────────────────────────
async function provisionNumber() {
  provisioning.value = true
  try { await store.provisionTwilio() } finally { provisioning.value = false }
}
async function releaseNumber() {
  if (!confirm('לשחרר את מספר ה-Twilio? כל הסנכרונים בפורטלים יפסיקו לעבוד.')) return
  await store.releaseTwilio()
}

// ─── Per-credential actions ───────────────────────────────
async function syncPhone(id)   { await store.syncContactPhone(id) }
async function runNow(id)      { await store.runNow(id) }
async function deleteCred(id)  {
  if (!confirm('למחוק את ההגדרה?')) return
  await store.deleteCredential(id)
}

// ─── Drag and drop wiring ─────────────────────────────────
function onCardDragStart(event, credId) {
  event.dataTransfer.setData('text/plain', credId)
  event.dataTransfer.effectAllowed = 'move'
}
async function onZoneDrop({ id, schedule_kind }) {
  await store.updateSchedule(id, schedule_kind)
}
async function onZoneRemove(id) {
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
  await store.fetchTwilioNumber()
  await store.fetchOtpInbox()
})
onUnmounted(() => {
  if (otpAutoTimer) clearInterval(otpAutoTimer)
  store.reset()
})
</script>

<style scoped>
.auto-page {
  max-width: 1180px;
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
}
.page-title { margin: 0; font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.3px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--text-muted); }
.page-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.btn-add {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border: none;
  border-radius: 9px;
  padding: 9px 16px;
  height: 36px;
  font-family: inherit;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.2px;
  cursor: pointer;
  box-shadow: 0 6px 14px rgba(245, 124, 0, 0.32);
  transition: transform 0.18s, box-shadow 0.18s, opacity 0.18s;
}
.btn-add:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(245, 124, 0, 0.4);
}
.btn-add:disabled { opacity: 0.55; cursor: not-allowed; box-shadow: none; }

/* Secondary primary — same dimensions, lighter visual weight */
.btn-add--secondary {
  background: var(--card-bg, #fff);
  color: var(--primary-deep, #c2410c);
  border: 1px solid rgba(245, 124, 0, 0.35);
  box-shadow: none;
}
.btn-add--secondary:hover:not(:disabled) {
  background: rgba(245, 124, 0, 0.06);
  border-color: var(--primary, #F57C00);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.16);
}

/* Twilio number badge (only shown when assigned) */
.twilio-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 6px 0 12px;
  background: var(--card-bg);
  border: 1px solid rgba(16, 185, 129, 0.32);
  border-radius: 9px;
  box-sizing: border-box;
}
.tp-num {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 12.5px;
  letter-spacing: 0.4px;
  color: #047857;
  font-weight: 700;
}
.tp-release {
  background: transparent;
  color: var(--text-muted);
  font-family: inherit;
  font-weight: 600;
  font-size: 11.5px;
  border: none;
  border-radius: 5px;
  padding: 4px 8px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.tp-release:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}

.error-banner {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #b91c1c;
  padding: 10px 14px;
  border-radius: var(--radius-sm, 8px);
  font-size: 13px;
}

/* Manual / scheduled sections */
.manual-section, .scheduled-section { display: flex; flex-direction: column; gap: 12px; }
.ms-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--border-subtle);
}
.ms-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--text);
}
.ms-meta { font-size: 12px; color: var(--text-muted); }

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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 28px 16px;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-lg, 16px);
  background: var(--bg);
  color: var(--text-muted);
  font-size: 13.5px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

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
