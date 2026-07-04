<template>
  <div class="auto-page">
    <!-- Aurora backdrop — the app's decorative motif in cool tones, giving the
         tab depth so it reads premium, not flat. Content layers above it. -->
    <div class="auto-bg" aria-hidden="true">
      <span class="aurora aurora--1"></span>
      <span class="aurora aurora--2"></span>
      <span class="aurora aurora--3"></span>
    </div>

    <div class="auto-inner">
    <!-- Hero: title + one-click run-all + add portal, aggregating to one
         production + one נפרעים file → compare. -->
    <PortalRunAllBar class="runall-block" @view-results="emit('go-to-comparison')" @add="openAdd" />

    <!-- KPI stat band -->
    <PortalStatBand v-if="store.credentials.length" />

    <div v-if="store.error" class="error-banner">{{ store.error }}</div>

    <div v-if="store.loading && !store.credentials.length" class="loading-strip">
      <span class="spinner" aria-hidden="true"></span>
      <span>טוען פורטלים…</span>
    </div>

    <!-- ─── Dashboard: company panels + activity sidebar ────── -->
    <div v-else class="dash" :class="{ 'dash--empty': !store.credentials.length }">
      <EmptyStateGuide
        v-if="!store.credentials.length"
        class="dash__guide"
        variant="inline"
        title="הורדה אוטומטית"
        body="מגדירים פעם אחת שם משתמש וסיסמה לכל פורטל חברה, מחברים את הטלפון להעברת קוד האימות — ומכאן והלאה לחיצה אחת מורידה את כל הדוחות ומשווה אותם."
        cta-label="פתח את אשף ההגדרה"
        cta-step="portal"
      />
      <PortalAutomationCanvas
        class="dash__main"
        :credentials="store.credentials"
        :portal-label="portalLabel"
        :active-run="store.activeRun"
        :active-run-id="store.activeRunId"
        @run="runNow"
        @edit="openEdit"
        @delete="deleteCred"
        @add="openAdd"
        @view-error="onViewError"
      />
      <PortalActivityPanel
        v-if="store.credentials.length"
        class="dash__aside"
        @view-results="emit('go-to-comparison')"
      />
    </div>

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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import PortalCredentialModal from './PortalCredentialModal.vue'
import PortalAutomationCanvas from './PortalAutomationCanvas.vue'
import PortalOtpModal from './PortalOtpModal.vue'
import PortalRunAllBar from './PortalRunAllBar.vue'
import PortalStatBand from './PortalStatBand.vue'
import PortalActivityPanel from './PortalActivityPanel.vue'
import EmptyStateGuide from './EmptyStateGuide.vue'

const props = defineProps({
  // When the activation checklist routes here, auto-open the add-credential modal.
  autoOpenAdd: { type: Boolean, default: false },
})
const emit = defineEmits(['go-to-comparison', 'opened'])
const store = usePortalAutomationStore()

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

onMounted(async () => {
  await store.fetchPortalKinds()
  await store.fetchCredentials()
  store.fetchLatestBatch()
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
  // Soft reset — an in-flight run-all batch must keep polling in the
  // background so its completion still refreshes the whole app.
  store.reset({ keepBatch: true })
})
</script>

<style scoped>
.auto-page {
  position: relative;
  min-height: 100%;
  padding: 26px 20px 48px;
  overflow: hidden;
  background:
    linear-gradient(180deg, #F7F8FD 0%, #F4F8FC 55%, #F2FAF8 100%);
}
.auto-bg { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
.aurora { position: absolute; border-radius: 50%; filter: blur(72px); }
.aurora--1 { width: 460px; height: 460px; background: rgba(91, 110, 225, 0.16); top: -140px; inset-inline-end: -90px; }
.aurora--2 { width: 400px; height: 400px; background: rgba(31, 168, 140, 0.14); bottom: -150px; inset-inline-start: -70px; }
.aurora--3 { width: 320px; height: 320px; background: rgba(142, 111, 214, 0.12); top: 42%; inset-inline-start: 34%; }
.auto-inner {
  position: relative;
  z-index: 1;
  max-width: 1400px;
  margin: 0 auto;
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

/* Add-portal button — sits at the inline-end of the page header */
.head-add {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: linear-gradient(135deg, #4E9DD0, #1FA88C);  /* pastel sky → teal */
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px 18px;
  height: 40px;
  font-family: inherit;
  font-weight: 700;
  font-size: 13.5px;
  cursor: pointer;
  box-shadow: 0 5px 13px rgba(31, 168, 140, 0.26);
  transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease;
  flex-shrink: 0;
}
.head-add:hover {
  transform: translateY(-1px);
  filter: brightness(1.04);
  box-shadow: 0 9px 20px rgba(31, 168, 140, 0.34);
}
.head-add:focus-visible { outline: 2px solid #1FA88C; outline-offset: 2px; }

/* ─── Dashboard grid: main panels + activity sidebar ────── */
.dash {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  align-items: start;
}
@media (min-width: 1024px) {
  .dash:not(.dash--empty) {
    grid-template-columns: minmax(0, 1fr) 320px;
  }
}

.dash__guide { margin-bottom: 0; } /* grid gap already spaces it */

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
  .err-btn--primary:hover { transform: none; }
}
</style>
