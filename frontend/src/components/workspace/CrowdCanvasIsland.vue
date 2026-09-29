<template>
  <!-- React island for components/ui/skiper39 (CrowdCanvas): Open Peeps walking
       along the bottom of a surface, redrawn in that surface's ink. -->
  <div ref="mountEl" class="crowd" aria-hidden="true"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import sprite from '../../assets/crowd/open-peeps.png'

const props = defineProps({
  ink: { type: String, default: '#2F6C94' },
  height: { type: String, default: '100%' },
  scale: { type: Number, default: 0.42 },
  crowd: { type: Number, default: 14 },
  opacity: { type: Number, default: 0.7 },
})

// cells of the sprite sheet holding a kitchen knife — not for an insurance app
const EXCLUDE = [17, 72, 92, 100]

const mountEl = ref(null)
let root = null

onMounted(async () => {
  try {
    const [rd, react, ui] = await Promise.all([import('react-dom/client'), import('react'), import('../ui/skiper39')])
    if (!mountEl.value) return
    root = rd.createRoot(mountEl.value)
    root.render(react.createElement(ui.CrowdCanvas, {
      src: sprite, rows: 15, cols: 7, ink: props.ink, exclude: EXCLUDE,
      scale: props.scale, maxCrowd: props.crowd,
      style: { height: props.height, opacity: props.opacity },
    }))
  } catch (e) {
    console.error('[CrowdCanvasIsland] render failed', e)
  }
})
onBeforeUnmount(() => { try { root?.unmount() } catch { /* ignore */ } root = null })
</script>

<style scoped>
.crowd { position: absolute; inset: 0; direction: ltr; pointer-events: none; }
</style>
