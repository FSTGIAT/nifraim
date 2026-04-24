<template>
  <Teleport to="body">
    <Transition name="welcome-fade">
      <div
        v-if="visible"
        class="welcome-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="ברוכים הבאים"
        @click="dismiss"
      >
        <div ref="mountEl" class="welcome-mount" aria-hidden="true"></div>
        <button
          type="button"
          class="welcome-skip"
          @click.stop="dismiss"
          aria-label="דלג"
        >
          דלג
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  userName: { type: String, default: '' },
  durationMs: { type: Number, default: 5000 },
})
const emit = defineEmits(['done'])

const mountEl = ref(null)
const visible = ref(true)

let reactStack = null
let reactRoot = null
let currentMountEl = null
let renderCounter = 0
let doneTimer = null
let doneEmitted = false

function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

async function ensureReactStack() {
  if (reactStack) return reactStack
  const [rdClient, react, player, remotion] = await Promise.all([
    import('react-dom/client'),
    import('react'),
    import('@remotion/player'),
    import('../../remotion'),
  ])
  reactStack = {
    createRoot: rdClient.createRoot,
    createElement: react.createElement,
    Player: player.Player,
    WelcomeComposition: remotion.WelcomeComposition,
  }
  return reactStack
}

async function render() {
  if (!mountEl.value) return
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

    renderCounter += 1
    const vw = Math.max(320, Math.round(window.innerWidth))
    const vh = Math.max(400, Math.round(window.innerHeight))
    const element = stack.createElement(stack.Player, {
      key: `welcome-${renderCounter}-${vw}x${vh}`,
      component: stack.WelcomeComposition,
      inputProps: { userName: props.userName },
      durationInFrames: 150,
      fps: 30,
      compositionWidth: vw,
      compositionHeight: vh,
      autoPlay: true,
      loop: false,
      controls: false,
      clickToPlay: false,
      doubleClickToFullscreen: false,
      showPosterWhenUnplayed: false,
      showPosterWhenPaused: false,
      showPosterWhenEnded: false,
      showPosterWhenBuffering: false,
      acknowledgeRemotionLicense: true,
      style: { width: '100%', height: '100%' },
    })
    reactRoot.render(element)
  } catch (e) {
    console.error('[WelcomeOverlay] render failed', e)
    dismiss()
  }
}

function emitDoneOnce() {
  if (doneEmitted) return
  doneEmitted = true
  emit('done')
}

function dismiss() {
  if (doneTimer) {
    clearTimeout(doneTimer)
    doneTimer = null
  }
  visible.value = false
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentMountEl = null
  }
  // Wait for leave transition before notifying the host.
  setTimeout(emitDoneOnce, 220)
}

function onEscape(e) {
  if (e.key === 'Escape') dismiss()
}

onMounted(() => {
  if (prefersReducedMotion()) {
    visible.value = false
    nextTick(emitDoneOnce)
    return
  }
  window.addEventListener('keydown', onEscape)
  nextTick(() => {
    render()
    // +120ms tail so the final frame is visible before the fade.
    doneTimer = setTimeout(dismiss, props.durationMs + 120)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEscape)
  if (doneTimer) {
    clearTimeout(doneTimer)
    doneTimer = null
  }
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentMountEl = null
  }
})
</script>

<style scoped>
.welcome-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
  background: #FFF8F0;
  cursor: pointer;
  overflow: hidden;
}

.welcome-mount {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.welcome-skip {
  position: absolute;
  top: 20px;
  inset-inline-end: 24px;
  background: rgba(255, 255, 255, 0.85);
  color: #E65100;
  border: 1px solid rgba(230, 81, 0, 0.25);
  backdrop-filter: blur(8px);
  border-radius: 999px;
  padding: 8px 18px;
  font-family: 'Heebo', sans-serif;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  letter-spacing: 0.02em;
  transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
  z-index: 1;
  box-shadow: 0 4px 12px rgba(230, 81, 0, 0.15);
}

.welcome-skip:hover {
  background: #fff;
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(230, 81, 0, 0.25);
}

.welcome-fade-enter-active {
  transition: opacity 0.25s ease;
}
.welcome-fade-leave-active {
  transition: opacity 0.2s ease;
}
.welcome-fade-enter-from,
.welcome-fade-leave-to {
  opacity: 0;
}
</style>
