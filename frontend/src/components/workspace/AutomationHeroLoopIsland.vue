<template>
  <!-- Remotion island: looping gears/conveyor scene for the automation hero.
       Decorative only. Falls back to the static illustration when the user
       prefers reduced motion or the React stack fails to load. -->
  <div class="hero-loop" aria-hidden="true">
    <img v-if="useStatic" class="hero-loop-fallback" :src="automationArt" alt="" />
    <div v-else ref="mountEl" class="hero-loop-mount"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import automationArt from '../../assets/kling/automation.webp'

const mountEl = ref(null)
const useStatic = ref(false)

let reactRoot = null

function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

async function render() {
  if (!mountEl.value) return
  try {
    const [rdClient, react, player, remotion] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion'),
    ])
    if (!mountEl.value) return
    reactRoot = rdClient.createRoot(mountEl.value)
    const element = react.createElement(player.Player, {
      component: remotion.AutomationHeroLoop,
      durationInFrames: remotion.AUTOMATION_HERO_LOOP_FRAMES,
      fps: 30,
      compositionWidth: 880,
      compositionHeight: 460,
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
      style: { width: '100%', height: '100%' },
    })
    reactRoot.render(element)
  } catch (e) {
    console.error('[AutomationHeroLoopIsland] render failed', e)
    useStatic.value = true
  }
}

onMounted(() => {
  if (prefersReducedMotion()) {
    useStatic.value = true
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
.hero-loop {
  width: 100%;
  height: 100%;
}

.hero-loop-mount {
  width: 100%;
  height: 100%;
  /* Remotion Player centers its composition with LTR-assuming math —
     under the app's RTL root it drifts ~half a scene off-box. Keep the
     LTR scope INSIDE the island so the host's logical insets stay RTL.
     NOT mirrored: the conveyor→gears→archive pipeline reads left-to-right
     by design (source → process → output). */
  direction: ltr;
}

.hero-loop-fallback {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>
