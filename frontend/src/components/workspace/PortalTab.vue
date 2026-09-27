<template>
  <div class="portal-tab">
    <!-- Remotion: the agent connected to their customers — calm, very faint,
         decorative only. Once there are links (the empty state has its own
         picture). -->
    <div v-if="portalStore.links.length && !reducedMotion" class="portal-bg" aria-hidden="true">
      <div ref="bgEl" class="portal-bg-mount"></div>
    </div>
    <PortalLinksManager class="portal-fg" :show="true" :embedded="true" @close="() => {}" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import PortalLinksManager from './PortalLinksManager.vue'
import { usePortalStore } from '../../stores/portal.js'

const portalStore = usePortalStore()
const bgEl = ref(null)
const reducedMotion =
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
let bgRoot = null

function cssVar(name, fallback) {
  try { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback } catch { return fallback }
}

async function mountBg() {
  if (!bgEl.value || bgRoot) return
  try {
    const [rdClient, react, player, comp] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/PortalConnectionsBackdrop'),
    ])
    if (!bgEl.value || bgRoot) return
    bgRoot = rdClient.createRoot(bgEl.value)
    bgRoot.render(
      react.createElement(player.Player, {
        component: comp.PortalConnectionsBackdrop,
        // Remotion can't read CSS variables — resolve the portal tab's colours here.
        inputProps: { color: cssVar('--tab-portal', '#4E9DD0'), ink: cssVar('--tab-portal-ink', '#35719A') },
        durationInFrames: comp.PORTAL_CONN_FRAMES,
        fps: 30,
        compositionWidth: comp.PORTAL_CONN_W,
        compositionHeight: comp.PORTAL_CONN_H,
        autoPlay: true,
        loop: true,
        controls: false,
        clickToPlay: false,
        doubleClickToFullscreen: false,
        showPosterWhenUnplayed: false,
        acknowledgeRemotionLicense: true,
        style: { width: '100%', height: '100%', backgroundColor: 'transparent' },
      }),
    )
  } catch (e) {
    console.error('[PortalTab] background failed', e) // decorative — tab works without it
  }
}
function unmountBg() {
  if (bgRoot) {
    try { bgRoot.unmount() } catch { /* ignore */ }
    bgRoot = null
  }
}
watch(bgEl, (el) => { if (el) mountBg(); else unmountBg() })
onBeforeUnmount(unmountBg)
</script>

<style scoped>
.portal-tab {
  position: relative;
  min-height: 400px;
}
.portal-bg { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
/* "cover" for the 16:9 composition: at least the viewport's width AND height. */
.portal-bg-mount {
  position: absolute; left: 50%; top: 50%;
  width: max(100vw, calc(100vh * 16 / 9));
  aspect-ratio: 1600 / 900;
  transform: translate(-50%, -50%);
  direction: ltr; /* RTL root would shift the Remotion composition */
}
.portal-fg { position: relative; z-index: 1; }
</style>
