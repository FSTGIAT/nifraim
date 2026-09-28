<template>
  <!-- Generic looping Remotion scene. `component` / `framesKey` name exports of
       src/remotion/index.ts. Reduced motion or a load failure → the slot. -->
  <div class="rli" :style="{ aspectRatio: `${width} / ${height}` }">
    <div v-if="!useStatic" ref="mountEl" class="rli-mount" aria-hidden="true"></div>
    <slot v-else />
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  component: { type: String, required: true },
  framesKey: { type: String, required: true },
  width: { type: Number, required: true },
  height: { type: Number, required: true },
  inputProps: { type: Object, default: () => ({}) },
})
const mountEl = ref(null)
const useStatic = ref(false)
let root = null
let renderPlayer = null

onMounted(async () => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { useStatic.value = true; return }
  await nextTick()
  try {
    const [rd, react, player, remotion] = await Promise.all([
      import('react-dom/client'), import('react'), import('@remotion/player'), import('../../remotion'),
    ])
    if (!mountEl.value) return
    root = rd.createRoot(mountEl.value)
    renderPlayer = () => root?.render(react.createElement(player.Player, {
      component: remotion[props.component],
      inputProps: props.inputProps,
      durationInFrames: remotion[props.framesKey],
      fps: 30,
      compositionWidth: props.width,
      compositionHeight: props.height,
      autoPlay: true, loop: true, controls: false, clickToPlay: false,
      doubleClickToFullscreen: false, acknowledgeRemotionLicense: true,
      style: { width: '100%', height: '100%' },
    }))
    renderPlayer()
  } catch (e) {
    console.error('[RemotionLoopIsland] render failed', e)
    useStatic.value = true
  }
})
// New inputProps (e.g. hover) → re-render the same Player; it keeps its frame.
watch(() => props.inputProps, () => renderPlayer?.(), { deep: true })
onBeforeUnmount(() => { try { root?.unmount() } catch { /* ignore */ } root = null })
</script>

<style scoped>
.rli { width: 100%; }
.rli-mount { width: 100%; height: 100%; direction: ltr; } /* Player math assumes LTR */
</style>
