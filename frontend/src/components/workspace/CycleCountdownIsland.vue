<template>
  <!-- Remotion island: live countdown to a cycle moment (+ the hand-drawn
       "how it works" strip unless compact). Reduced motion / load failure →
       a plain text countdown with the same numbers. -->
  <div class="ccd" :style="{ aspectRatio: `${size.width} / ${size.height}` }">
    <div v-if="useStatic" class="ccd-static" role="timer">
      <span class="ccd-static-head">{{ heading }}</span>
      <span class="ccd-static-digits ltr-number">{{ staticText }}</span>
    </div>
    <div v-else ref="mountEl" class="ccd-mount" aria-hidden="true"></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { cycleNow, cycleSkewMs } from '../../stores/cycle.js'

const props = defineProps({
  targetIso: { type: String, required: true },
  heading: { type: String, default: 'לשונית הפרודוקציה נפתחת בעוד' },
  periodName: { type: String, default: '' },
  compact: { type: Boolean, default: false },
  alignRight: { type: Boolean, default: false },
  color: { type: String, default: '#2F73C4' }, // resolved hex — Remotion can't read CSS vars
})

const size = computed(() => (props.compact ? { width: 800, height: 210 } : { width: 960, height: 440 }))
const mountEl = ref(null)
const useStatic = ref(false)
let reactRoot = null
let mods = null

// Reduced-motion fallback ticks once a minute (no seconds shown).
const now = ref(cycleNow())
let staticTimer = null
const staticText = computed(() => {
  const ms = Math.max(0, new Date(props.targetIso).getTime() - now.value)
  const mins = Math.floor(ms / 60000)
  const d = Math.floor(mins / 1440)
  const h = String(Math.floor((mins % 1440) / 60)).padStart(2, '0')
  const m = String(mins % 60).padStart(2, '0')
  return `${d} ימים · ${h}:${m}`
})

function draw() {
  if (!reactRoot || !mods) return
  const { react, player, remotion } = mods
  reactRoot.render(react.createElement(player.Player, {
    component: remotion.CycleCountdown,
    inputProps: {
      targetMs: new Date(props.targetIso).getTime(),
      skewMs: cycleSkewMs(),
      color: props.color,
      ink: '#181818',
      periodName: props.periodName,
      heading: props.heading,
      compact: props.compact,
      alignRight: props.alignRight,
    },
    durationInFrames: remotion.CYCLE_COUNTDOWN_FRAMES,
    fps: 30,
    compositionWidth: size.value.width,
    compositionHeight: size.value.height,
    autoPlay: true,
    loop: true,
    controls: false,
    clickToPlay: false,
    doubleClickToFullscreen: false,
    acknowledgeRemotionLicense: true,
    style: { width: '100%', height: '100%' },
  }))
}

async function mount() {
  if (!mountEl.value) return
  try {
    const [rdClient, react, player, remotion] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion'),
    ])
    if (!mountEl.value) return
    mods = { react, player, remotion }
    reactRoot = rdClient.createRoot(mountEl.value)
    draw()
  } catch (e) {
    console.error('[CycleCountdownIsland] render failed', e)
    useStatic.value = true
  }
}

watch(() => [props.targetIso, props.heading, props.periodName, props.color, props.compact], draw)

onMounted(() => {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduced) {
    useStatic.value = true
    staticTimer = setInterval(() => { now.value = cycleNow() }, 30000)
    return
  }
  nextTick(mount)
})

onBeforeUnmount(() => {
  clearInterval(staticTimer)
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
})
</script>

<style scoped>
.ccd { width: 100%; }
/* Player centering math assumes LTR — keep the LTR scope INSIDE the island. */
.ccd-mount { width: 100%; height: 100%; direction: ltr; }
.ccd-static {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  font-family: 'Heebo', sans-serif;
}
.ccd-static-head { font-size: 14px; font-weight: 700; color: var(--text-secondary, #706E6B); }
.ccd-static-digits { font-size: 34px; font-weight: 900; color: var(--tab-production, #2F73C4); }
</style>
