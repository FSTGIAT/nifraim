<template>
  <div ref="hostEl" class="unpaid-trend-host">
    <div ref="mountEl" class="unpaid-trend-mount" aria-hidden="true"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  periods: { type: Array, required: true },
  series: { type: Array, required: true },
  insight: { type: String, default: '' },
})

const hostEl = ref(null)
const mountEl = ref(null)

// Measured container width drives the composition dimensions so internal
// pixel coordinates match the rendered size 1:1 — no sub-pixel scaling and
// no overflow when the card is narrower than a fixed reference width.
const measuredWidth = ref(720)
let resizeObserver = null

// Aspect: ~3:1 reads well on a single-row monitor without dwarfing the rest
const ASPECT = 3

// Module-scope cache so the React+Remotion chunk loads only once per session.
let reactStack = null
let reactRoot = null
let currentMountEl = null
let renderCounter = 0

async function ensureReactStack() {
  if (reactStack) return reactStack
  const [rdClient, react, player, remotion] = await Promise.all([
    import('react-dom/client'),
    import('react'),
    import('@remotion/player'),
    import('../../remotion'),
  ])
  reactStack = {
    createRoot: rdClient.createRoot,
    createElement: react.createElement,
    Player: player.Player,
    UnpaidTrendComposition: remotion.UnpaidTrendComposition,
  }
  return reactStack
}

async function render() {
  if (!mountEl.value) return
  try {
    const stack = await ensureReactStack()
    if (!mountEl.value) return

    if (reactRoot && currentMountEl !== mountEl.value) {
      try { reactRoot.unmount() } catch { /* ignore */ }
      reactRoot = null
    }
    if (!reactRoot) {
      reactRoot = stack.createRoot(mountEl.value)
      currentMountEl = mountEl.value
    }

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    // ~3s intro at 30fps + long still-tail so the final frame stays put.
    const introFrames = prefersReducedMotion ? 1 : 90
    const restFrames = prefersReducedMotion ? 0 : 108000
    const totalFrames = introFrames + restFrames

    // Pixel-snap so internal layout matches the rendered size — avoids the
    // sub-pixel scaling that pushes content past the card border.
    const w = Math.max(360, Math.round(measuredWidth.value))
    const h = Math.max(200, Math.round(w / ASPECT))

    renderCounter += 1
    const element = stack.createElement(stack.Player, {
      key: `unpaid-trend-${renderCounter}-${w}`,
      component: stack.UnpaidTrendComposition,
      inputProps: {
        title: props.title,
        periods: props.periods,
        series: props.series,
        insight: props.insight,
      },
      durationInFrames: totalFrames,
      fps: 30,
      compositionWidth: w,
      compositionHeight: h,
      autoPlay: true,
      loop: false,
      controls: false,
      clickToPlay: false,
      doubleClickToFullscreen: false,
      showPosterWhenUnplayed: false,
      showPosterWhenPaused: false,
      showPosterWhenEnded: false,
      showPosterWhenBuffering: false,
      acknowledgeRemotionLicense: true,
      style: {
        width: `${w}px`,
        height: `${h}px`,
        borderRadius: 14,
        overflow: 'hidden',
        display: 'block',
      },
    })
    reactRoot.render(element)
  } catch (e) {
    console.error('[UnpaidTrendCinematic] render failed', e)
  }
}

// Debounced re-render when the host width changes so resizing the window
// (or expanding/collapsing the monitor card) re-fits the chart.
let resizeRaf = null
function scheduleRender() {
  if (resizeRaf) cancelAnimationFrame(resizeRaf)
  resizeRaf = requestAnimationFrame(() => {
    resizeRaf = null
    render()
  })
}

watch(
  () => [props.periods, props.series, props.title, props.insight],
  () => nextTick(scheduleRender),
  { deep: true, immediate: false },
)

onMounted(() => {
  if (!hostEl.value) return
  const initial = hostEl.value.clientWidth || 720
  measuredWidth.value = initial
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver((entries) => {
      for (const e of entries) {
        const w = Math.round(e.contentRect.width)
        if (Math.abs(w - measuredWidth.value) >= 4) {
          measuredWidth.value = w
          scheduleRender()
        }
      }
    })
    resizeObserver.observe(hostEl.value)
  }
  nextTick(render)
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (resizeRaf) cancelAnimationFrame(resizeRaf)
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentMountEl = null
  }
})
</script>

<style scoped>
.unpaid-trend-host {
  width: 100%;
  display: block;
  position: relative;
  overflow: hidden;
  border-radius: 14px;
}
.unpaid-trend-mount {
  width: 100%;
  display: block;
  line-height: 0;
}
.unpaid-trend-mount > * {
  max-width: 100% !important;
  display: block;
}
</style>
