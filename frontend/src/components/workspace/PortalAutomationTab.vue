<template>
  <div class="auto-page">
    <!-- ─── Header — Monday-style board header ─────────────── -->
    <header class="page-head">
      <div class="page-titles">
        <div class="title-row">
          <span class="title-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </span>
          <h2 class="page-title">פורטלי חברות הביטוח</h2>
        </div>
        <p class="page-sub">חבר חברה אחת, גרור לתזמון, והדוח יוריד את עצמו.</p>
      </div>
      <div v-if="store.credentials.length" class="page-stats" aria-label="סטטיסטיקה">
        <div class="stat-pill stat-pill--scheduled">
          <span class="stat-num ltr-number">{{ scheduledCount }}</span>
          <span class="stat-lbl">מתוזמן</span>
        </div>
        <div class="stat-pill stat-pill--total">
          <span class="stat-num ltr-number">{{ store.credentials.length }}</span>
          <span class="stat-lbl">סה״כ פורטלים</span>
        </div>
      </div>
    </header>

    <!-- Run all portals → aggregate to one production + one נפרעים file → compare. -->
    <PortalRunAllBar class="runall-block" @view-results="emit('go-to-comparison')" />

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
      @view-error="onViewError"
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
              <th>זמן</th><th>מאת</th><th>חברה</th><th>קוד</th><th>סטטוס</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="otp in store.otpInbox" :key="otp.id">
              <td class="otp-time">{{ formatOtpTime(otp.received_at) }}</td>
              <td><span class="ltr-number">{{ otp.from_number }}</span></td>
              <td>
                <span v-if="otp.matched_company" class="otp-company">{{ otp.matched_company }}</span>
                <span v-else class="otp-company otp-company--none">לא זוהתה</span>
              </td>
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

    <!-- ─── Error popup — replaces the inline error block on cards ─── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="errorModalOpen" class="err-overlay" @click="errorModalOpen = false">
          <div class="err-card" role="dialog" aria-modal="true" aria-label="פרטי שגיאה" @click.stop>
            <header class="err-head">
              <span class="err-icon" aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </span>
              <div class="err-titles">
                <h3 class="err-title">שגיאה בריצת אוטומציה</h3>
                <p v-if="errorContext" class="err-meta">{{ portalLabel(errorContext.portal_kind) }} · <span class="ltr-number">{{ errorContext.username }}</span></p>
              </div>
              <button class="err-x" type="button" aria-label="סגור" @click="errorModalOpen = false">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 6 6 18" /><path d="m6 6 12 12" />
                </svg>
              </button>
            </header>
            <div class="err-body">{{ errorMessage }}</div>
            <footer class="err-foot">
              <button class="err-btn err-btn--secondary" type="button" @click="errorModalOpen = false">סגור</button>
              <button v-if="errorContext" class="err-btn err-btn--primary" type="button" @click="rerunFromError">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <polygon points="6 4 20 12 6 20" />
                </svg>
                <span>נסה שוב</span>
              </button>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import PortalCredentialModal from './PortalCredentialModal.vue'
import PortalAutomationCanvas from './PortalAutomationCanvas.vue'
import PortalOtpModal from './PortalOtpModal.vue'
import PortalRunAllBar from './PortalRunAllBar.vue'

const props = defineProps({
  // When the activation checklist routes here, auto-open the add-credential modal.
  autoOpenAdd: { type: Boolean, default: false },
})
const emit = defineEmits(['go-to-comparison', 'opened'])
const store = usePortalAutomationStore()

const scheduledCount = computed(() =>
  store.credentials.filter((c) => c.schedule_kind && c.schedule_kind !== 'manual').length,
)

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

// ─── Error popup ──────────────────────────────────────────
const errorModalOpen = ref(false)
const errorMessage = ref('')
const errorContext = ref(null)
function onViewError({ cred, message }) {
  errorContext.value = cred
  errorMessage.value = message || 'שגיאה לא ידועה'
  errorModalOpen.value = true
}
async function rerunFromError() {
  const id = errorContext.value?.id
  errorModalOpen.value = false
  if (id) await runNow(id)
}

// ─── Per-credential actions ───────────────────────────────
async function runNow(id) {
  try {
    await store.runNow(id)
  } catch (_) {
    // 409 = a run is already in-flight for this credential. Hydrate the
    // store so the OTP modal / progress UI binds to the live run instead
    // of throwing. Mirrors PortalAutomationDock.onRun.
    await store.hydrateActiveRun()
  }
}
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
  // Same fix as PortalAutomationDock — close as soon as the run leaves
  // awaiting_otp so phone-forward delivery doesn't leave a stale modal
  // that 400s on submit. (See F3 in plan.)
  if (['downloading', 'parsing', 'success', 'failed', 'timeout'].includes(s)) {
    otpModalOpen.value = false
  }
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
  if (props.autoOpenAdd) {
    openAdd()
    emit('opened')
  }
})

// Activation checklist may set this after the tab is already mounted.
watch(() => props.autoOpenAdd, (v) => {
  if (v) {
    openAdd()
    emit('opened')
  }
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

/* Header — Monday-style board header */
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
  padding: 4px 0 18px;
  border-bottom: 1px solid var(--border-subtle);
}
.page-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.title-icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  color: #fff;
  display: grid;
  place-items: center;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.32),
              inset 0 1px 0 rgba(255, 255, 255, 0.25);
  flex-shrink: 0;
}
.page-title {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.4px;
  line-height: 1.1;
}
.page-sub {
  margin: 6px 0 0;
  font-size: 13.5px;
  color: var(--text-muted);
  padding-inline-start: 50px;
}

/* Right-side board stats — Monday "info cells" */
.page-stats {
  display: flex;
  gap: 10px;
  align-items: stretch;
  flex-shrink: 0;
}
.stat-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 8px 16px;
  border-radius: 12px;
  border: 1.5px solid var(--border-subtle);
  background: var(--card-bg);
  min-width: 84px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.stat-pill:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
.stat-pill--scheduled {
  border-color: color-mix(in srgb, var(--chart-10) 50%, transparent);
  background: linear-gradient(135deg, color-mix(in srgb, var(--chart-10) 12%, transparent) 0%, transparent 100%);
}
.stat-pill--scheduled .stat-num { color: var(--chart-10); }
.stat-pill--total {
  border-color: color-mix(in srgb, var(--chart-2) 50%, transparent);
  background: linear-gradient(135deg, color-mix(in srgb, var(--chart-2) 12%, transparent) 0%, transparent 100%);
}
.stat-pill--total .stat-num { color: var(--chart-2); }
.stat-num {
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: -0.5px;
}
.stat-lbl {
  font-size: 10.5px;
  color: var(--text-muted);
  font-weight: 700;
  letter-spacing: 0.3px;
  margin-top: 4px;
}

.error-banner {
  background: rgba(234, 0, 30, 0.08);
  border: 1px solid rgba(234, 0, 30, 0.3);
  color: var(--red-deep);
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
  border-top-color: var(--primary);
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
.otp-code { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-weight: 700; letter-spacing: 1px; color: var(--green-deep); }
.otp-company { font-weight: 600; color: var(--text-default); }
.otp-company--none { font-weight: 400; color: var(--text-muted); font-style: italic; }

.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.status-success { background: var(--green); color: #fff; box-shadow: 0 1px 4px rgba(46, 132, 74, 0.35); }
.status-pending { background: var(--primary); color: #fff; box-shadow: 0 1px 4px rgba(245, 124, 0, 0.35); }

/* ─── Error popup modal ────────────────────────────────── */
.err-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 18, 28, 0.55);
  backdrop-filter: blur(3px);
  z-index: 1010;
  display: grid;
  place-items: center;
  padding: 20px;
}
.err-card {
  background: var(--card-bg, #fff);
  border-radius: 16px;
  width: 100%;
  max-width: 520px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.32);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.err-head {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 14px;
  padding: 18px 20px 14px;
  background: linear-gradient(135deg, rgba(234, 0, 30, 0.10) 0%, transparent 70%);
  border-bottom: 1px solid var(--border-subtle);
}
.err-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--red);
  color: #fff;
  display: grid;
  place-items: center;
  box-shadow: 0 4px 12px rgba(234, 0, 30, 0.38),
              inset 0 1px 0 rgba(255, 255, 255, 0.25);
  flex-shrink: 0;
}
.err-titles { min-width: 0; }
.err-title { margin: 0; font-size: 17px; font-weight: 800; color: var(--text); letter-spacing: -0.2px; }
.err-meta { margin: 3px 0 0; font-size: 12.5px; color: var(--text-muted); }
.err-x {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--card-bg);
  display: grid;
  place-items: center;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.err-x:hover { background: var(--bg); color: var(--text); border-color: var(--text-muted); }
.err-body {
  padding: 16px 20px;
  font-size: 13px;
  color: var(--text);
  line-height: 1.55;
  max-height: 50vh;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  background: var(--bg);
  border-bottom: 1px solid var(--border-subtle);
}
.err-foot {
  display: flex;
  gap: 8px;
  padding: 14px 20px;
  justify-content: flex-end;
}
.err-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  border-radius: 8px;
  padding: 9px 16px;
  font-family: inherit;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}
.err-btn--secondary {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border-subtle);
}
.err-btn--secondary:hover { background: var(--card-bg); border-color: var(--text-muted); }
.err-btn--primary {
  background: linear-gradient(135deg, var(--primary), var(--accent-cyan));
  color: #fff;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.30);
}
.err-btn--primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(245, 124, 0, 0.42);
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active .err-card, .modal-leave-active .err-card { transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.22s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .err-card, .modal-leave-to .err-card { opacity: 0; transform: translateY(8px) scale(0.96); }

@media (prefers-reduced-motion: reduce) {
  .spinner { animation: none; }
  .stat-pill:hover,
  .err-btn--primary:hover { transform: none; }
}
</style>
