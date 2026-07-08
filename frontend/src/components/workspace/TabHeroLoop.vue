<template>
  <!-- Reusable Remotion hero-loop island. Pass `scene` = a key from
       TAB_HERO_SCENES ('ai-library' | 'portal' | 'company-emails' |
       'recruits' | 'commission-shelf'). Decorative only; hidden entirely
       for prefers-reduced-motion or if the React stack fails to load. -->
  <div v-if="!hidden" class="tab-hero-loop" aria-hidden="true">
    <div ref="mountEl" class="tab-hero-mount"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  scene: { type: String, required: true },
})

const mountEl = ref(null)
const hidden = ref(false)
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
      import('../../remotion/TabHeroLoops'),
    ])
    const component = remotion.TAB_HERO_SCENES[props.scene]
    if (!component || !mountEl.value) {
      hidden.value = true
      return
    }
    reactRoot = rdClient.createRoot(mountEl.value)
    reactRoot.render(
      react.createElement(player.Player, {
        component,
        durationInFrames: remotion.TAB_HERO_LOOP_FRAMES,
        fps: 30,
        compositionWidth: 420,
        compositionHeight: 300,
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
      }),
    )
  } catch (e) {
    console.error('[TabHeroLoop] render failed', e)
    hidden.value = true
  }
}

onMounted(() => {
  if (prefersReducedMotion()) {
    hidden.value = true
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
/* Root stays in the host's writing mode so logical insets (inset-inline-end,
   flex order) on this element resolve RTL-correctly. */
.tab-hero-loop {
  width: 100%;
  height: 100%;
}

/* Player centers with LTR-assuming math — scope LTR to the INNER mount only,
   never the positioned root. See memory remotion-rtl-player.
   scaleX(-1): mirror the scene so directional motion (conveyor, plane, cards)
   flows right-to-left, matching the Hebrew RTL interface. */
.tab-hero-mount {
  width: 100%;
  height: 100%;
  direction: ltr;
  transform: scaleX(-1);
}
</style>
