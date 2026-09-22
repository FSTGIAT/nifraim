<template>
  <!-- Heartbeat rings behind the worker icon. Mounted ONLY while the worker is
       online (the parent gates with v-if), so no Player exists on the offline
       card — the stillness is the signal. Under prefers-reduced-motion we skip
       Remotion entirely and paint one static ring. -->
  <div class="wp" aria-hidden="true">
    <div v-if="reduced" class="wp-static" :style="staticStyle"></div>
    <div v-else ref="mountEl" class="wp-mount"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  color: { type: String, default: '#1B5E20' },
})

const mountEl = ref(null)
const reduced = ref(false)
let reactRoot = null

function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

const staticStyle = computed(() => ({
  border: `2px solid ${props.color}`,
  opacity: 0.28,
}))

async function render() {
  if (!mountEl.value) return
  try {
    const [rdClient, react, player, remotion] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/WorkerPulse'),
    ])
    if (!mountEl.value) return
    reactRoot = rdClient.createRoot(mountEl.value)
    reactRoot.render(
      react.createElement(player.Player, {
        component: remotion.WorkerPulse,
        inputProps: { color: props.color },
        durationInFrames: remotion.WORKER_PULSE_FRAMES,
        fps: 30,
        compositionWidth: 120,
        compositionHeight: 120,
        autoPlay: true,
        loop: true,
        controls: false,
        clickToPlay: false,
        doubleClickToFullscreen: false,
        showPosterWhenUnplayed: false,
        showPosterWhenPaused: false,
        showPosterWhenEnded: false,
        showPosterWhenBuffering: false,
        acknowledgeRemotionLicense: true,
        style: { width: '100%', height: '100%', backgroundColor: 'transparent' },
      }),
    )
  } catch (e) {
    console.error('[WorkerPulseIsland] render failed', e)
    reduced.value = true // fall back to the static ring
  }
}

onMounted(() => {
  if (prefersReducedMotion()) {
    reduced.value = true
    return
  }
  nextTick(render)
})

onBeforeUnmount(() => {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
})
</script>

<style scoped>
.wp { position: absolute; inset: 0; pointer-events: none; }
.wp-static {
  position: absolute; inset: 50% auto auto 50%;
  width: 54px; height: 54px; margin: -27px 0 0 -27px;
  border-radius: 50%;
}
/* The Player centers with LTR-assuming math, so LTR is scoped to the INNER
   mount only — never a positioned root. See memory remotion-rtl-player. */
.wp-mount { width: 100%; height: 100%; direction: ltr; }
</style>
