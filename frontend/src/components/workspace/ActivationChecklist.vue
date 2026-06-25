<template>
  <Transition name="activation-pop">
    <div v-if="visible" ref="mountEl" class="activation-mount"></div>
  </Transition>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { useNotificationsStore } from '../../stores/notifications.js'
import { activationState } from '../../utils/activationState.js'

const emit = defineEmits(['open-phone-forward', 'open-add-portal', 'run-automation'])
const store = usePortalAutomationStore()
const notifications = useNotificationsStore()

const CLOSED_KEY = 'activation_closed'   // set only when the user explicitly ✕-closes it
const DONE_KEY = 'activation_completed'
const REMINDER_ID = 'activation-setup'

const visible = ref(false)
let celebrated = false

// ── Step state (auto-detected from store) ─────────────────────────────────
const phoneDone = computed(() => !!store.phoneForward?.token)
const credsDone = computed(() => (store.credentials?.length || 0) > 0)
const runDone = computed(() => ['success', 'partial'].includes(store.latestBatch?.status))

const steps = computed(() => [
  { id: 'register', label: 'הרשמה הושלמה', hint: 'ברוך הבא ל-Nifraim', cta: '', done: true },
  { id: 'phone', label: 'חבר את הטלפון', hint: 'הטלפון מעביר את קוד האימות אוטומטית — בלי הקלדה', cta: 'חבר', done: phoneDone.value },
  { id: 'portal', label: 'הוסף פורטל חברה ראשון', hint: 'שם משתמש וסיסמה לפורטל הסוכן של חברת הביטוח', cta: 'הוסף', done: credsDone.value },
  { id: 'run', label: 'הרץ הורדה אוטומטית מכל החברות', hint: 'הורדה ואיחוד ל-2 קבצים: פרודוקציה + נפרעים', cta: 'הרץ עכשיו', done: runDone.value },
])
const completedCount = computed(() => steps.value.filter((s) => s.done).length)
const currentIndex = computed(() => steps.value.findIndex((s) => !s.done))
const allDone = computed(() => completedCount.value >= steps.value.length)

function pinReminder() {
  notifications.pinAlert({
    id: REMINDER_ID,
    kind: 'activation',
    severity: 'info',
    title: 'השלם את הפעלת האוטומציה',
    body: 'נותרו צעדים להפעלת ההורדה האוטומטית מכל החברות',
    createdAt: new Date().toISOString(),
    actions: ['reopen_activation'],
    meta: {},
  })
}

function onAction(id) {
  if (id === 'phone') emit('open-phone-forward')
  else if (id === 'portal') emit('open-add-portal')
  else if (id === 'run') emit('run-automation')
}

function onClose() {
  // Closing before finishing: don't auto-show again, but drop a bell reminder.
  localStorage.setItem(CLOSED_KEY, 'true')
  if (!allDone.value) pinReminder()
  hide()
}

function markCompleted() {
  localStorage.setItem(DONE_KEY, 'true')
  notifications.unpinAlert(REMINDER_ID)
  hide()
}

// ── React island (Ark UI ActivationCard) ──────────────────────────────────
const mountEl = ref(null)
let reactStack = null
let reactRoot = null
let currentMountEl = null

async function ensureReactStack() {
  if (reactStack) return reactStack
  const [rdClient, react, mod] = await Promise.all([
    import('react-dom/client'),
    import('react'),
    import('../../react/ActivationCard.jsx'),
  ])
  reactStack = {
    createRoot: rdClient.createRoot,
    createElement: react.createElement,
    ActivationCard: mod.ActivationCard,
  }
  return reactStack
}

async function render() {
  if (!visible.value || !mountEl.value) return
  try {
    const stack = await ensureReactStack()
    if (!mountEl.value) return
    if (reactRoot && currentMountEl !== mountEl.value) {
      try { reactRoot.unmount() } catch { /* ignore */ }
      reactRoot = null
    }
    if (!reactRoot) {
      reactRoot = stack.createRoot(mountEl.value)
      currentMountEl = mountEl.value
    }
    reactRoot.render(stack.createElement(stack.ActivationCard, {
      steps: steps.value,
      completedCount: completedCount.value,
      total: steps.value.length,
      currentIndex: currentIndex.value,
      allDone: allDone.value,
      onAction,
      onClose,
    }))
  } catch (e) {
    console.error('[ActivationChecklist] render failed', e)
    hide()
  }
}

function teardown() {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentMountEl = null
  }
}

function hide() {
  visible.value = false
  teardown()
}

function show() {
  if (localStorage.getItem(DONE_KEY) === 'true') return
  notifications.unpinAlert(REMINDER_ID)   // card is visible now — no duplicate bell nag
  visible.value = true
  nextTick(render)
}

// Re-render the island whenever step state changes; celebrate + close at 4/4.
watch([completedCount, currentIndex, allDone], () => {
  if (!visible.value) return
  render()
  if (allDone.value && !celebrated) {
    celebrated = true
    setTimeout(markCompleted, 2600)
  }
})

// Re-open from the notification-bell reminder (fires if already mounted).
watch(() => activationState.forceShow, (v) => {
  if (v) { activationState.forceShow = false; show() }
})

onMounted(async () => {
  if (localStorage.getItem(DONE_KEY) === 'true') return
  await Promise.all([
    store.fetchPhoneForward().catch(() => {}),
    store.fetchCredentials().catch(() => {}),
    store.fetchLatestBatch().catch(() => {}),
  ])
  // Already fully set up (returning power user) → mark done silently, no card.
  if (allDone.value) { markCompleted(); return }
  // Re-opened from the bell while on a content tab → home just mounted us.
  if (activationState.forceShow) { activationState.forceShow = false; show(); return }
  // Show on every login while setup is incomplete — until the user explicitly
  // closes it (✕). Once closed, stay hidden but keep a bell reminder as the way back.
  if (localStorage.getItem(CLOSED_KEY) !== 'true') show()
  else pinReminder()
})

onBeforeUnmount(teardown)
</script>

<style scoped>
.activation-mount {
  width: 100%;
  max-width: 640px;
  margin: 0 auto 18px;
  z-index: 2;
}

.activation-pop-enter-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.activation-pop-leave-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.activation-pop-enter-from, .activation-pop-leave-to { opacity: 0; transform: translateY(-8px); }

@media (prefers-reduced-motion: reduce) {
  .activation-pop-enter-active, .activation-pop-leave-active { transition: none; }
}
</style>
