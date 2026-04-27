<template>
  <div ref="mountEl" class="shelf-reel-mount" aria-hidden="true"></div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  type: { type: String, required: true }, // 'lost' | 'agents' | 'upload' | 'bonus' | 'invites' | 'ai'
  width:  { type: Number, default: 280 },
  height: { type: Number, default: 140 },
})

const mountEl = ref(null)

// Module-scope cache so the React+Remotion chunk loads once for the whole page.
let reactStack = null
let reactRoot = null
let currentMountEl = null

async function ensureStack() {
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
    ShelfReel: remotion.ShelfReel,
  }
  return reactStack
}

async function render() {
  if (!mountEl.value) return
  const stack = await ensureStack()
  if (!mountEl.value) return

  // If the cached root points at a stale DOM node — e.g. v-if remounted us —
  // unmount it and bind a fresh root to the current element.
  if (reactRoot && currentMountEl !== mountEl.value) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
  if (!reactRoot) {
    reactRoot = stack.createRoot(mountEl.value)
    currentMountEl = mountEl.value
  }

  // Loop a 3-second decoration. No controls, no poster, transparent background.
  // Composition canvas is 400×240 (16:10) — Player scales it to fit the host
  // element. Shapes inside the composition are sized to fill that canvas, so
  // the visible animation matches the stage no matter how big the book is.
  const FPS = 30
  const SECONDS = 3
  const COMP_W = 400
  const COMP_H = 240
  const element = stack.createElement(stack.Player, {
    key: `shelf-${props.type}`,
    component: stack.ShelfReel,
    inputProps: { type: props.type },
    durationInFrames: FPS * SECONDS,
    fps: FPS,
    compositionWidth: COMP_W,
    compositionHeight: COMP_H,
    style: { width: '100%', height: '100%', background: 'transparent', display: 'block' },
    autoPlay: true,
    loop: true,
    controls: false,
    showPosterWhenUnplayed: false,
    showPosterWhenPaused: false,
    showPosterWhenEnded: false,
    showPosterWhenBuffering: false,
    acknowledgeRemotionLicense: true,
  })
  reactRoot.render(element)
}

watch(() => props.type, () => render())
watch(mountEl, () => render(), { flush: 'post' })

onBeforeUnmount(() => {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentMountEl = null
  }
})
</script>

<style scoped>
.shelf-reel-mount {
  width: 100%;
  height: 100%;
  background: transparent;
  pointer-events: none;
  border-radius: 12px;
  overflow: hidden;
}
.shelf-reel-mount :deep(div), .shelf-reel-mount :deep(canvas) {
  background: transparent !important;
}
</style>
