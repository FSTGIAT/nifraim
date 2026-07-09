<template>
  <!-- Ambient color-matched Remotion loop for a card background. Decorative,
       mounted only while its card is hovered (parent gates with v-if), so at
       most one Player is ever alive. For prefers-reduced-motion we skip Remotion
       and paint a static tint instead. -->
  <div class="card-anim" aria-hidden="true">
    <div v-if="reduced" class="card-anim-static" :style="staticStyle"></div>
    <div v-else ref="mountEl" class="card-anim-mount"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  color: { type: String, default: '#2F73C4' },
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
  background: `radial-gradient(circle at 30% 35%, ${props.color}33 0%, ${props.color}00 70%)`,
}))

async function render() {
  if (!mountEl.value) return
  try {
    const [rdClient, react, player, remotion] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/CardAmbientLoop'),
    ])
    if (!mountEl.value) return
    reactRoot = rdClient.createRoot(mountEl.value)
    reactRoot.render(
      react.createElement(player.Player, {
        component: remotion.CardAmbientLoop,
        inputProps: { color: props.color },
        durationInFrames: remotion.CARD_AMBIENT_LOOP_FRAMES,
        fps: 30,
        compositionWidth: 220,
        compositionHeight: 170,
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
    console.error('[CardAmbientIsland] render failed', e)
    reduced.value = true // fall back to the static tint
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
.card-anim {
  width: 100%;
  height: 100%;
}

.card-anim-static {
  width: 100%;
  height: 100%;
}

/* Player centers with LTR-assuming math — scope LTR to the INNER mount only,
   never a positioned root. See memory remotion-rtl-player. No scaleX mirror:
   the motion is non-directional (drifting blobs), so RTL flow is moot. */
.card-anim-mount {
  width: 100%;
  height: 100%;
  direction: ltr;
}
</style>
