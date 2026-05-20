<template>
  <div ref="mountEl" class="radial-orbital-island"></div>
</template>

<script setup>
// Vue → React bridge for the RadialOrbital launcher. Same chunk-split pattern
// as CircleMenuIsland.vue + AiVizPanel.vue: dynamic-import react + the .tsx
// component + lucide-react, mount once on mountEl, forward clicks via @select.
//
// Each item in `items` has shape: { id, title, iconName, energy? }. iconName
// must be a valid lucide-react export (e.g. 'BarChart3', 'TrendingUp').
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  items: { type: Array, required: true },
  size: { type: Number, default: 300 },
  orbitRadius: { type: Number, default: 96 },
})
const emit = defineEmits(['select'])

const mountEl = ref(null)
let reactRoot = null
let reactDeps = null

function buildReactItems() {
  if (!reactDeps) return []
  return props.items.map((it) => ({
    id: it.id,
    title: it.title,
    description: it.description,
    energy: typeof it.energy === 'number' ? it.energy : 60,
    icon: reactDeps.lucideIcons[it.iconName] || reactDeps.lucideIcons.Circle,
  }))
}

function renderTree() {
  if (!reactRoot || !reactDeps) return
  reactRoot.render(
    reactDeps.React.createElement(reactDeps.RadialOrbital, {
      items: buildReactItems(),
      size: props.size,
      orbitRadius: props.orbitRadius,
      onSelect: (id) => emit('select', id),
    }),
  )
}

onMounted(async () => {
  if (!mountEl.value) return
  try {
    const [reactMod, rdMod, orbitalMod, lucideMod] = await Promise.all([
      import('react'),
      import('react-dom/client'),
      import('./RadialOrbital.tsx'),
      import('lucide-react'),
    ])
    reactDeps = {
      React: reactMod,
      ReactDOM: rdMod,
      RadialOrbital: orbitalMod.default || orbitalMod.RadialOrbital,
      lucideIcons: lucideMod,
    }
    reactRoot = rdMod.createRoot(mountEl.value)
    renderTree()
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[RadialOrbitalIsland] failed to mount React island', e)
  }
})

watch(
  () => [props.items, props.size, props.orbitRadius],
  () => { renderTree() },
  { deep: true },
)

onBeforeUnmount(() => {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
  reactDeps = null
})
</script>

<style scoped>
.radial-orbital-island {
  display: inline-block;
  /* Width/height inherited from the React root which renders a sized container. */
}
</style>
