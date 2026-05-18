<template>
  <div ref="mountEl" class="cm-island" :class="`cm-island--${layout}`"></div>
</template>

<script setup>
// Vue → React bridge for the CircleMenu component. Same pattern as
// ShaderHeroIsland.vue and AiVizPanel.vue — dynamic-import react + react-dom
// + the .tsx component, then createRoot(mountEl).render().
//
// Items prop shape: [{ key, label, iconName }] where iconName maps to a
// lucide-react component (resolved at mount time). The React component
// receives `onItemClick(key)` which we forward as a Vue `select` event.
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  items: { type: Array, required: true },
  layout: { type: String, default: 'circle' }, // 'circle' | 'across'
  itemGap: { type: Number, default: 10 },
})
const emit = defineEmits(['select'])

const mountEl = ref(null)
let reactRoot = null
let reactDeps = null // cached { React, ReactDOM, CircleMenu, lucideIcons }

function resolveIconNode(name) {
  if (!reactDeps) return null
  const Icon = reactDeps.lucideIcons[name]
  if (!Icon) return null
  return reactDeps.React.createElement(Icon, { size: 18 })
}

function renderTree() {
  if (!reactRoot || !reactDeps) return
  const reactItems = props.items.map((it) => ({
    key: it.key,
    label: it.label,
    icon: resolveIconNode(it.icon),
  }))
  reactRoot.render(
    reactDeps.React.createElement(reactDeps.CircleMenu, {
      items: reactItems,
      layout: props.layout,
      itemGap: props.itemGap,
      onItemClick: (key) => emit('select', key),
    }),
  )
}

onMounted(async () => {
  if (!mountEl.value) return
  try {
    const [reactMod, rdMod, cmMod, lucideMod] = await Promise.all([
      import('react'),
      import('react-dom/client'),
      import('./CircleMenu.tsx'),
      import('lucide-react'),
    ])
    reactDeps = {
      React: reactMod,
      ReactDOM: rdMod,
      CircleMenu: cmMod.default || cmMod.CircleMenu,
      lucideIcons: lucideMod,
    }
    reactRoot = rdMod.createRoot(mountEl.value)
    renderTree()
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[CircleMenuIsland] failed to mount React island', e)
  }
})

// Re-render the React tree if any incoming prop changes.
watch(
  () => [props.items, props.layout, props.itemGap],
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
/* ── Mount footprints per layout ──────────────────────────────────────
   - `circle`: the React component's natural 250×250 box; we scale to ~72%
     so it fits the top-left corner without orbit items clipping at edges.
   - `across`: trigger only (48×48); items extend outside the box via
     absolute positioning, so the strip flex layout stays unaffected. */

.cm-island {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  /* Items extend outside the mount footprint; never clip them. */
  overflow: visible;
}

.cm-island--circle {
  width: 250px;
  height: 250px;
  transform: scale(0.72);
  transform-origin: top left;
}

.cm-island--across,
.cm-island--down {
  width: 48px;
  height: 48px;
}
</style>
