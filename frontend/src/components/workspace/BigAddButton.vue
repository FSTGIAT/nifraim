<template>
  <button
    class="bigadd"
    type="button"
    :title="label"
    :aria-label="label"
    @click="$emit('click')"
    @mouseenter="hover = true"
    @mouseleave="hover = false"
    @focus="hover = true"
    @blur="hover = false"
  >
    <span class="bigadd-ring" :style="{ width: size + 'px', height: size + 'px' }">
      <!-- Remotion supplies the ring and halo; the plus itself is static SVG
           on top, because the target you are aiming at should not move. -->
      <span v-if="reduced" class="bigadd-static" :style="{ borderColor: color }"></span>
      <span v-else ref="mountEl" class="bigadd-mount"></span>
      <!-- Default glyph is the plus; a caller can slot its own (still static). -->
      <span class="bigadd-glyph" :style="{ color }">
        <slot>
          <svg class="bigadd-plus" width="34" height="34" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">
            <path d="M5 12h14" /><path d="M12 5v14" />
          </svg>
        </slot>
      </span>
    </span>
  </button>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'

const props = defineProps({
  label: { type: String, default: 'הוסף' },
  color: { type: String, default: '#D6336C' },
  // Ring diameter in px.
  size: { type: Number, default: 76 },
})
defineEmits(['click'])

const hover = ref(false)
const mountEl = ref(null)
const reduced = ref(false)
let reactRoot = null
let mods = null

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
      import('../../remotion/PlusPulse'),
    ])
    if (!mountEl.value) return
    mods = { react, player, remotion }
    reactRoot = rdClient.createRoot(mountEl.value)
    paint()
  } catch (e) {
    console.error('[BigAddButton] render failed', e)
    reduced.value = true // fall back to a plain ring
  }
}

function paint() {
  if (!reactRoot || !mods) return
  const { react, player, remotion } = mods
  reactRoot.render(
    react.createElement(player.Player, {
      component: remotion.PlusPulse,
      inputProps: { color: props.color, active: hover.value },
      durationInFrames: remotion.PLUS_PULSE_FRAMES,
      fps: 30,
      compositionWidth: 140,
      compositionHeight: 140,
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

watch(hover, () => { if (!reduced.value) paint() })

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
.bigadd {
  display: flex; align-items: center; justify-content: center;
  width: 100%; padding: 12px 0 6px;
  border: none; background: none; cursor: pointer; font-family: inherit;
}
.bigadd-ring {
  position: relative;
  display: grid; place-items: center;
}
.bigadd-mount { position: absolute; inset: 0; direction: ltr; }
.bigadd-static {
  position: absolute; inset: 12%;
  border: 2px dashed currentColor; border-radius: 50%; opacity: 0.5;
}
.bigadd-glyph { position: relative; z-index: 1; display: grid; place-items: center; }
.bigadd:focus-visible { outline: none; }
.bigadd:focus-visible .bigadd-ring {
  outline: 2px solid currentColor; outline-offset: 4px; border-radius: 50%;
}
</style>
