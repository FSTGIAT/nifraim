<template>
  <Teleport to="body">
    <div ref="mountEl" class="notif-host" aria-hidden="true"></div>
  </Teleport>
</template>

<script setup>
/**
 * WorkspaceNotificationHost
 * Mounts the third-party React SplashedPushNotifications component once and
 * pipes Pinia store events into its imperative handle. Bottom-LEFT corner
 * (the component's own RTL CSS handles positioning).
 *
 * React-island lifecycle copied from AiVizPanel.vue + WelcomeOverlay.vue —
 * see ai_viz_remotion.md for the stale-root gotcha that necessitates the
 * currentMountEl bookkeeping.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useNotificationsStore } from '../../stores/notifications.js'
import { useProductionStore } from '../../stores/production.js'

const notifStore = useNotificationsStore()
const productionStore = useProductionStore()
const { comparisonResult, currentFile } = storeToRefs(productionStore)

const mountEl = ref(null)

let reactStack = null
let reactRoot = null
let currentMountEl = null
let handleObj = null   // React imperative handle exposed by the component

async function ensureReactStack() {
  if (reactStack) return reactStack
  const [rdClient, react, island] = await Promise.all([
    import('react-dom/client'),
    import('react'),
    import('../../react/notifications-island.tsx'),
  ])
  reactStack = {
    createRoot: rdClient.createRoot,
    createElement: react.createElement,
    createRef: react.createRef,
    SplashedPushNotifications: island.SplashedPushNotifications,
  }
  return reactStack
}

async function renderRoot() {
  if (!mountEl.value) {
    console.warn('[notif-host] mountEl missing at render time')
    return
  }
  try {
    const stack = await ensureReactStack()
    if (!mountEl.value) return
    if (reactRoot && currentMountEl !== mountEl.value) {
      try { reactRoot.unmount() } catch { /* ignore */ }
      reactRoot = null
      handleObj = null
      notifStore.setSink(null)
    }
    if (!reactRoot) {
      reactRoot = stack.createRoot(mountEl.value)
      currentMountEl = mountEl.value
    }
    // Callback ref — fires as soon as React commits the handle, on each render.
    const ref = (h) => {
      handleObj = h
      if (h && typeof h.createRtlNotification === 'function') {
        notifStore.setSink((type, title, body) => h.createRtlNotification(type, title, body))
        console.log('[notif-host] React handle ready, sink registered')
      } else {
        notifStore.setSink(null)
      }
    }
    const element = stack.createElement(stack.SplashedPushNotifications, {
      ref,
      durationMs: 9000,
      timerColor: 'var(--clr)',
      timerBgColor: 'rgba(26, 20, 16, 0.08)',
    })
    reactRoot.render(element)
    console.log('[notif-host] React island mounted')
  } catch (e) {
    console.warn('[notif-host] React mount failed', e)
  }
}

// Comparison-result watcher → churn + per-company gap toasts.
watch(comparisonResult, (result) => {
  if (!result) return
  const fileId = currentFile.value?.id
  notifStore.reportChurn(result, fileId)
  notifStore.reportGap(result)
})

onMounted(() => {
  console.log('[notif-host] mounted, kicking off React island + poll')
  nextTick(() => {
    renderRoot()
    notifStore.startPolling()
    if (typeof window !== 'undefined') {
      window.__notif = (type, title, body) => notifStore.enqueue(type, title, body)
    }
    // Fire-once welcome toast so the user always sees confirmation the
    // system is live, even if there are no overnight events.
    const WELCOME_KEY = 'notif.welcomeShown.v3'
    if (!localStorage.getItem(WELCOME_KEY)) {
      // Small delay so the React handle has a chance to register first.
      setTimeout(() => {
        notifStore.enqueue('help', 'מערכת התראות פעילה', 'תקבל התראה על אוטומציות, קבצים חדשים וירידות בלקוחות')
        try { localStorage.setItem(WELCOME_KEY, '1') } catch { /* ignore */ }
      }, 1200)
    }
  })
})
onBeforeUnmount(() => {
  notifStore.stopPolling()
  notifStore.setSink(null)
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentMountEl = null
    handleObj = null
  }
})
</script>

<style scoped>
/* The React component manages its own positioning via the .notificationContainer
 * styles it injects on first mount. The host div is just an anchor; the actual
 * rendered .notificationContainer divs live inside it and pin themselves to
 * `position: fixed; bottom: 10px; left: 10px` (RTL container). */
.notif-host {
  position: absolute;
  inset: 0;
  pointer-events: none;
  width: 0;
  height: 0;
}
.notif-host > * { pointer-events: auto; }
</style>
