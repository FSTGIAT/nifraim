<template>
  <!-- React island for components/ui/thinking-orbs (ThinkingOrb, a canvas
       orb). Re-renders on prop change so the state can follow the AI. -->
  <span class="to" aria-hidden="true">
    <span v-if="reduced" class="to-static" :style="{ background: color }"></span>
    <span v-else ref="mountEl" class="to-mount"></span>
  </span>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  state: { type: String, default: 'working' }, // working | searching | solving | listening | composing | shaping | …
  size: { type: Number, default: 64 }, // 64 | 32 | 20 (tuned presets)
  color: { type: String, default: '#6A48C9' },
  theme: { type: String, default: 'light' }, // light ink-on-light; 'dark' for dark substrates
  speed: { type: Number, default: 1 },
  dotSize: { type: Number, default: 1 }, // >1 = bolder dots (small / light placements)
  dots: { type: Number, default: 1 },
})

const mountEl = ref(null)
const reduced = ref(false)
let root = null
let mods = null

function paint() {
  if (!root || !mods) return
  const { react, orb } = mods
  root.render(react.createElement(orb.ThinkingOrb, {
    state: props.state, size: props.size, color: props.color, theme: props.theme, speed: props.speed,
    dotSize: props.dotSize, dots: props.dots,
    'aria-label': 'Nifra AI',
  }))
}

onMounted(async () => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { reduced.value = true; return }
  try {
    const [rd, react, orb] = await Promise.all([
      import('react-dom/client'), import('react'), import('../ui/thinking-orbs'),
    ])
    if (!mountEl.value) return
    mods = { react, orb }
    root = rd.createRoot(mountEl.value)
    paint()
  } catch (e) {
    console.error('[ThinkingOrbIsland] render failed', e)
    reduced.value = true
  }
})
watch(() => [props.state, props.size, props.color, props.theme, props.speed, props.dotSize, props.dots], paint)
onBeforeUnmount(() => { try { root?.unmount() } catch { /* ignore */ } root = null })
</script>

<style scoped>
.to { display: inline-grid; place-items: center; line-height: 0; }
.to-mount { display: inline-grid; place-items: center; direction: ltr; }
.to-static { width: 60%; aspect-ratio: 1; border-radius: 50%; opacity: 0.35; }
</style>
