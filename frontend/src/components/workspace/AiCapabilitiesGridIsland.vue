<template>
  <div ref="mountEl" class="aicg-island"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const mountEl = ref(null)
let reactRoot = null

function hasWebGL2() {
  try {
    if (typeof document === 'undefined') return false
    const canvas = document.createElement('canvas')
    return !!canvas.getContext('webgl2')
  } catch {
    return false
  }
}

onMounted(async () => {
  if (!mountEl.value) return
  try {
    const [rdClient, react, mod] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('./AiCapabilitiesGrid.tsx'),
    ])
    if (!mountEl.value) return
    reactRoot = rdClient.createRoot(mountEl.value)
    reactRoot.render(
      react.createElement(mod.default, { webgl: hasWebGL2() }),
    )
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[AiCapabilitiesGridIsland] failed to mount React island', e)
  }
})

onBeforeUnmount(() => {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
})
</script>

<style scoped>
.aicg-island { width: 100%; }

/* Section sits on the app's light/cream surface so it matches the rest of the
   UI (the hero above is intentionally dark, but everything below should feel
   light and airy). Section bg is a very soft cream so the colorful shader
   cards pop without floating in raw white. */
:deep(.aicg-root) {
  width: 100%;
  padding: 28px 24px;
  border-radius: 24px;
  background: linear-gradient(180deg, #FBF7EE 0%, #F4EEDF 100%);
  border: 1px solid rgba(0, 0, 0, 0.04);
  font-family: 'Heebo', sans-serif;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

:deep(.aicg-head) {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 22px;
  text-align: right;
}
:deep(.aicg-title) {
  font-size: 22px;
  font-weight: 700;
  color: #1A1A1A;
  margin: 0;
  letter-spacing: -0.3px;
}
:deep(.aicg-sub) {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.56);
  margin: 0;
}

:deep(.aicg-grid) {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

/* Card shell — the colorful shader fills the background, a translucent dark
   veil sits over it for contrast, and the content rides on top in z=1. */
:deep(.aicg-card) {
  position: relative;
  display: flex;
  min-height: 240px;
  padding: 0;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: #1A1A1A; /* base color when shader/fallback hasn't painted yet */
  overflow: hidden;
  isolation: isolate;
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
  will-change: transform;
  box-shadow: 0 14px 30px -16px rgba(20, 16, 8, 0.35);
}
:deep(.aicg-card:hover) {
  border-color: rgba(255, 255, 255, 0.32);
  box-shadow: 0 20px 44px -18px rgba(20, 16, 8, 0.5);
}

:deep(.aicg-bg) {
  position: absolute;
  inset: 0;
  z-index: 0;
}
:deep(.aicg-bg-fallback) {
  width: 100%;
  height: 100%;
}
:deep(.aicg-veil) {
  position: absolute;
  inset: 0;
  /* Light veil — just enough to keep text legible without muddying the pastels. */
  background: linear-gradient(180deg, rgba(0,0,0,0.06) 0%, rgba(0,0,0,0.32) 65%, rgba(0,0,0,0.48) 100%);
  pointer-events: none;
}
/* On hover the veil nearly disappears so the shader colors pop. */
:deep(.aicg-card:hover) :deep(.aicg-veil),
:deep(.aicg-card:hover .aicg-veil) {
  background: linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.20) 65%, rgba(0,0,0,0.38) 100%);
}

:deep(.aicg-card-body) {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 24px 24px 22px;
  gap: 10px;
}

:deep(.aicg-icon) {
  width: 50px;
  height: 50px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.24);
  color: #ffffff;
  margin-bottom: 6px;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

:deep(.aicg-card-title) {
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
  margin: 0;
  line-height: 1.3;
  letter-spacing: -0.1px;
  /* Heavier shadow because the veil is now light — needed for AA contrast over pastels. */
  text-shadow: 0 1px 2px rgba(0,0,0,0.55), 0 2px 12px rgba(0,0,0,0.45);
}

:deep(.aicg-card-text) {
  font-size: 14px;
  line-height: 1.65;
  color: #ffffff;
  margin: 0;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5), 0 2px 10px rgba(0,0,0,0.4);
}

:deep(.aicg-tip) {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.35);
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  line-height: 1.55;
  color: #ffffff;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5), 0 2px 10px rgba(0,0,0,0.4);
}
:deep(.aicg-tip svg) {
  color: #FFE08A;
  flex-shrink: 0;
  margin-top: 2px;
}

/* Center card — slightly thicker glow ring to draw the eye to the marquee. */
:deep(.aicg-card--center) {
  border-color: rgba(255, 222, 153, 0.55);
  box-shadow:
    0 0 0 1px rgba(255, 222, 153, 0.18) inset,
    0 20px 44px -16px rgba(120, 70, 10, 0.45);
}

@media (max-width: 1100px) {
  :deep(.aicg-grid) { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 720px) {
  :deep(.aicg-grid) { grid-template-columns: 1fr; }
  :deep(.aicg-card) { min-height: 200px; }
  :deep(.aicg-title) { font-size: 18px; }
}

@media (prefers-reduced-motion: reduce) {
  :deep(.aicg-card) { transition: none; }
  :deep(.aicg-card:hover) { transform: none; }
}
</style>
