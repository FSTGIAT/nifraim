<template>
  <!-- React island for components/ui/ruler-carousel. The active index and
       "open" (with the pressed item — the origin of the iPhone-style open)
       come back up as Vue events. -->
  <div ref="mountEl" class="rci"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  active: { type: Number, default: 0 },
  colors: { type: Object, default: null },
  itemWidth: { type: Number, default: 240 },
  gap: { type: Number, default: 48 },
  freshId: { type: String, default: null },
})
const emit = defineEmits(['active', 'open'])

const mountEl = ref(null)
const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
let root = null
let mods = null

function paint() {
  if (!root || !mods) return
  const { react, rc } = mods
  root.render(react.createElement(rc.RulerCarousel, {
    // a different list length = a fresh ruler anchored on `active` — never a stale
    // position measured against the old length
    key: props.items.length,
    items: props.items,
    active: props.active,
    colors: props.colors || undefined,
    itemWidth: props.itemWidth,
    gap: props.gap,
    reducedMotion: reduced,
    freshId: props.freshId,
    onActive: (i) => emit('active', i),
    onOpen: (i, el) => emit('open', i, el),
  }))
}

onMounted(async () => {
  try {
    const [rd, react, rc] = await Promise.all([
      import('react-dom/client'), import('react'), import('../ui/ruler-carousel'),
    ])
    if (!mountEl.value) return
    mods = { react, rc }
    root = rd.createRoot(mountEl.value)
    paint()
  } catch (e) {
    console.error('[RulerCarouselIsland] render failed', e)
  }
})
// Re-render the React tree ONLY when what it shows changes — a signature of
// the list, not the array's identity. The studio re-renders often while
// recording (timer); a new paint each time would nudge the springs.
const signature = () => JSON.stringify([props.items.map((i) => [i.id, i.label, !!i.live]), props.active,
  props.colors, props.itemWidth, props.gap, props.freshId])
watch(signature, paint)
onBeforeUnmount(() => { try { root?.unmount() } catch { /* ignore */ } root = null })
</script>

<style scoped>
.rci { width: 100%; }
</style>
