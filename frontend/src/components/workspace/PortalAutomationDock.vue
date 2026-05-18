<template>
  <section class="dock-section">
    <div v-if="store.error" class="dock-error">{{ store.error }}</div>

    <Motion
      v-if="dockKinds.length"
      as="div"
      class="dock"
      @mousemove="onMouseMove"
      @mouseleave="onMouseLeave"
    >
      <PortalAutomationDockItem
        v-for="kind in dockKinds"
        :key="kind.id"
        :cred="credentialFor(kind.id)"
        :has-credential="!!credentialFor(kind.id)"
        :mouse-x="mouseX"
        :portal-label="kind.label"
        :is-implemented="kind.implemented"
        :is-running="isRunningForKind(kind.id)"
        :any-running="anyRunning"
        :brand="brandFor(kind.id)"
        @click="onTileClick(kind)"
      />
    </Motion>

    <div v-else class="dock-empty">
      <p>טוען רשימת חברות…</p>
    </div>

    <PortalCredentialModal
      :open="addModalOpen"
      mode="add"
      :default-portal-kind="addModalKind"
      @close="addModalOpen = false"
      @saved="onCredentialSaved"
    />

    <PortalOtpModal
      :open="otpModalOpen"
      :run="store.activeRun"
      :company-name="activeCompanyLabel"
      :credential-otp-method="activeCredential?.otp_method || 'twilio'"
      @submit="onSubmitOtp"
      @close="closeOtpModal"
      @open-phone-forward="phoneForwardOpen = true"
    />

    <PhoneForwardModal :open="phoneForwardOpen" @close="phoneForwardOpen = false" />
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Motion, useMotionValue } from 'motion-v'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { brandFor } from '../../utils/companyBrand.js'
import PortalAutomationDockItem from './PortalAutomationDockItem.vue'
import PortalCredentialModal from './PortalCredentialModal.vue'
import PortalOtpModal from './PortalOtpModal.vue'
import PhoneForwardModal from './PhoneForwardModal.vue'

const emit = defineEmits(['success', 'failure', 'navigate-to-credentials'])
const store = usePortalAutomationStore()

const mouseX = useMotionValue(Infinity)
function onMouseMove(e) { mouseX.set(e.pageX) }
function onMouseLeave() { mouseX.set(Infinity) }

function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || brandFor(kind).label
}
function isImplemented(kind) {
  return !!store.portalKinds.find((k) => k.id === kind)?.implemented
}
function credentialFor(kind) {
  return store.credentials.find((c) => c.portal_kind === kind) || null
}
function isRunning(credId) {
  return store.activeRunId && store.activeRun?.credential_id === credId
}
function isRunningForKind(kind) {
  const c = credentialFor(kind)
  return !!c && isRunning(c.id)
}
const anyRunning = computed(() => !!store.activeRunId)

// Show EVERY company in the catalog — discovery matters even when the
// backend automation for a specific portal hasn't shipped yet (the user
// can pre-add credentials and the run will surface the error if it can't
// complete). Configured-with-credentials come first; unconfigured (the
// "+" tiles) follow. Stable alphabetical sort within each group so the
// dock layout doesn't shuffle on every fetch.
const dockKinds = computed(() => {
  const all = [...(store.portalKinds || [])]
  return all.sort((a, b) => {
    const aHas = !!credentialFor(a.id)
    const bHas = !!credentialFor(b.id)
    if (aHas !== bHas) return Number(bHas) - Number(aHas)
    return (a.label || a.id).localeCompare(b.label || b.id, 'he')
  })
})

const addModalOpen = ref(false)
const addModalKind = ref('')

function onTileClick(kind) {
  // Uniform behavior — implemented vs not is irrelevant for the click path.
  // The runner surfaces "not implemented" naturally via the error banner.
  const existing = credentialFor(kind.id)
  if (existing) {
    return runNow(existing.id)
  }
  // No credential yet → open the add modal pre-filled with this portal.
  addModalKind.value = kind.id
  addModalOpen.value = true
}

async function onCredentialSaved(cred) {
  addModalOpen.value = false
  // Refresh credentials list so the dock tile flips from "+ add" to active.
  await store.fetchCredentials()
  // Auto-trigger the run the user came here for.
  if (cred?.id) await runNow(cred.id)
}

async function runNow(credId) {
  // Don't bubble the axios error — store.error feeds the banner already.
  // Common case: 409 because another run is still in-flight (we hydrate it
  // on mount, but a stale state may slip through).
  try {
    await store.runNow(credId)
  } catch (_) {
    // The store has already populated `error`. If it's a 409 stale-run case,
    // try one more hydrate so the dock picks up the live run automatically.
    await store.hydrateActiveRun()
  }
}

// ───── OTP modal ─────
const otpModalOpen = ref(false)
const phoneForwardOpen = ref(false)
const activeCredential = computed(() => {
  const cid = store.activeRun?.credential_id
  return store.credentials.find((c) => c.id === cid) || null
})
const activeCompanyLabel = computed(() => {
  const cred = activeCredential.value
  return cred ? portalLabel(cred.portal_kind) : ''
})

watch(() => store.activeRun?.status, (s) => {
  if (s === 'awaiting_otp') otpModalOpen.value = true
  if (['success', 'failed', 'timeout'].includes(s)) {
    otpModalOpen.value = false
    if (s === 'success') emit('success', { credential: activeCredential.value, run: store.activeRun })
    else emit('failure', { credential: activeCredential.value, run: store.activeRun })
  }
})

async function onSubmitOtp(otp) {
  if (!store.activeRun?.id) return
  try { await store.submitOtp(store.activeRun.id, otp) } catch (_) {}
}
async function closeOtpModal() {
  // Close = cancel. The run is awaiting an OTP; without one it would just
  // time out. Mark it failed now so the dock unfreezes immediately.
  const id = store.activeRun?.id
  otpModalOpen.value = false
  if (id) await store.cancelRun(id)
}

onMounted(async () => {
  if (!store.portalKinds.length) await store.fetchPortalKinds()
  if (!store.credentials.length) await store.fetchCredentials()
  // Pick up any portal run that's still in-flight on the server, so a page
  // reload mid-OTP doesn't leave the user without a way to enter the code.
  await store.hydrateActiveRun()
})
</script>

<style scoped>
.dock-section {
  font-family: 'Heebo', sans-serif;
  display: flex;
  flex-direction: column;
  align-items: stretch;      /* dock spans the full section width */
  gap: 56px;                 /* leave clear room for icons that lift above the dock */
  padding: 12px 0 36px;
  width: 100%;
  overflow: visible;
}

.dock-error {
  margin: 0 auto;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.24);
  color: #b91c1c;
  border-radius: 8px;
  font-size: 12.5px;
  max-width: 540px;
}

/* ───── Dock — unchromed ─────
   No background / border / shadow / radius. Items float free against
   the page so the magnify behaviour reads as the focal interaction.
   IMPORTANT: overflow MUST stay visible — dock items grow from 40 → 80px
   on hover and need to "lift" upward outside the dock bounds. */
.dock {
  margin: 0;                  /* anchored to the parent's flex-start (right in RTL) */
  display: flex;
  align-items: flex-end;
  justify-content: space-between; /* distribute items across the available width */
  gap: 16px;
  height: 64px;
  padding: 0 8px 12px;
  width: 100%;                /* span the page */
  max-width: 100%;
  overflow: visible;          /* let lifted icons show above the dock */
}

.dock-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
}
.dock-empty p { margin: 0; }
.dock-cta {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border: none;
  border-radius: 9px;
  padding: 8px 16px;
  font-family: inherit;
  font-weight: 700;
  font-size: 12.5px;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(245, 124, 0, 0.28);
  transition: transform 0.15s, box-shadow 0.15s;
}
.dock-cta:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(245, 124, 0, 0.4); }
</style>
