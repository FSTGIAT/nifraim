<template>
  <!-- Remotion orb for the assistant widget. Under prefers-reduced-motion we
       skip Remotion entirely and paint the orb's resting frame as CSS. -->
  <div class="orb" aria-hidden="true">
    <div v-if="reduced" class="orb-static" :style="staticStyle"></div>
    <div v-else ref="mountEl" class="orb-mount"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'

const props = defineProps({
  color: { type: String, default: '#7C4DBE' },
  // Mounted while the conversation is open: the orb spins up and the sparks
  // travel, so the widget reads as listening rather than decorative.
  active: { type: Boolean, default: false },
})

const mountEl = ref(null)
const reduced = ref(false)
let reactRoot = null
let playerProps = null

function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

const staticStyle = computed(() => ({
  background: `radial-gradient(circle, ${props.color} 0%, transparent 68%)`,
}))

async function render() {
  if (!mountEl.value) return
  try {
    const [rdClient, react, player, remotion] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/AiOrb'),
    ])
    if (!mountEl.value) return
    playerProps = { react, player, remotion }
    reactRoot = rdClient.createRoot(mountEl.value)
    paint()
  } catch (e) {
    console.error('[AiOrbIsland] render failed', e)
    reduced.value = true // fall back to the static orb
  }
}

function paint() {
  if (!reactRoot || !playerProps) return
  const { react, player, remotion } = playerProps
  reactRoot.render(
    react.createElement(player.Player, {
      component: remotion.AiOrb,
      inputProps: { color: props.color, active: props.active },
      durationInFrames: remotion.AI_ORB_FRAMES,
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
}

// Re-render on state change only — `active` is the one input that matters.
watch(() => props.active, () => { if (!reduced.value) paint() })

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
.orb { position: absolute; inset: 0; pointer-events: none; }
.orb-static {
  position: absolute; inset: 9%;
  border-radius: 50%; opacity: 0.28;
}
/* The Player centers with LTR-assuming math, so LTR is scoped to the INNER
   mount only — never a positioned root. See memory remotion-rtl-player. */
.orb-mount { width: 100%; height: 100%; direction: ltr; }
</style>
