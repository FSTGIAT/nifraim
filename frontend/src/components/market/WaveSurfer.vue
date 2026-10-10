<template>
  <!-- A small line-art surfer that rides a wave layer once in a while: every `every` seconds one ride of
       `ride` seconds across the parent (which must be positioned + overflow hidden, like the wave bands). -->
  <span v-if="riding" :key="n" class="ws-track" :style="{ bottom: bottom + 'px', '--ride': ride + 's' }" aria-hidden="true"
        @animationend.self="riding = false">
    <span class="ws-bob">
      <svg class="ws-svg" viewBox="0 0 64 56" :width="size" :height="Math.round(size * 0.875)">
        <path d="M6 46 C 18 52, 46 52, 60 44 C 50 42, 20 42, 6 46 Z" :fill="colors.board" />
        <circle cx="33" cy="9" r="4.6" :fill="colors.ink" />
        <path d="M33 14 L30 27 L22 35 M30 27 L38 34 L40 42 M22 35 L20 42" class="ws-ink" :stroke="colors.ink" />
        <path d="M31 18 L19 14 M31 18 L44 21" class="ws-ink" :stroke="colors.ink" />
        <path d="M8 49 C 3 50, 1 47, 4 45" class="ws-spray" />
      </svg>
    </span>
  </span>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'

const props = defineProps({
  bottom: { type: Number, default: 110 },   // px from the band's bottom — the front wave's crest
  every: { type: Number, default: 24 },     // seconds between rides
  delay: { type: Number, default: 3 },      // seconds before the first ride
  ride: { type: Number, default: 6 },       // seconds on screen
  size: { type: Number, default: 52 },
  ink: { type: String, default: '#5E6320' },
  board: { type: String, default: 'rgba(122, 127, 42, 0.85)' },
  // 'canvas': on the workspace page, read the agent's page colour (Settings → מראה) — a dark canvas gets a light surfer
  tone: { type: String, default: 'fixed' },
})
const colors = reactive({ ink: props.ink, board: props.board })
function fromCanvas() {
  const c = getComputedStyle(document.documentElement).getPropertyValue('--app-canvas').trim()
  const m = c.match(/^#?([0-9a-f]{6})$/i)
  if (!m) return
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255)
  if (0.2126 * r + 0.7152 * g + 0.0722 * b < 0.45) { colors.ink = '#E3E7A4'; colors.board = 'rgba(214, 219, 140, 0.92)' }
  else { colors.ink = props.ink; colors.board = props.board }
}
const riding = ref(false)
const n = ref(0)
let first = null
let timer = null
function go() { if (document.hidden) return; if (props.tone === 'canvas') fromCanvas(); n.value++; riding.value = true }
onMounted(() => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  first = setTimeout(() => { go(); timer = setInterval(go, props.every * 1000) }, props.delay * 1000)
})
onBeforeUnmount(() => { clearTimeout(first); clearInterval(timer) })
</script>

<style scoped>
.ws-track { position: absolute; z-index: 2; right: -80px; animation: wsRide var(--ride, 6s) linear both; pointer-events: none; }
.ws-bob { display: block; animation: wsBob 2.2s ease-in-out infinite; transform-origin: 50% 90%; }
.ws-svg { display: block; overflow: visible; transform: scaleX(-1); }   /* drawn facing right; it rides leftward */
.ws-ink { fill: none; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.ws-spray { fill: none; stroke: rgba(255, 255, 255, 0.9); stroke-width: 2; stroke-linecap: round; }
@keyframes wsRide {
  0% { transform: translateX(0); opacity: 0; }
  6% { opacity: 1; }
  92% { opacity: 1; }
  100% { transform: translateX(calc(-100vw - 160px)); opacity: 0; }
}
@keyframes wsBob { 0%, 100% { transform: translateY(0) rotate(-4deg); } 50% { transform: translateY(-9px) rotate(5deg); } }
</style>
