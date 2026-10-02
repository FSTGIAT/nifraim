<template>
  <!-- The calls orb — one hue (the calls orchid), soft light, no rainbow.
       All motion lives inside it: a slow breath when idle, the live
       microphone level while recording (--lvl swells the light and the
       rings), a thinking pulse while processing. Pure CSS: calm, cheap. -->
  <span ref="rootEl" class="co" :class="'co--' + state" :style="{ '--co-size': size + 'px', '--lvl': 0 }" aria-hidden="true">
    <span class="co-ring co-ring--1"></span>
    <span class="co-ring co-ring--2"></span>
    <span class="co-ball">
      <span class="co-light"></span>
      <span class="co-sheen"></span>
    </span>
  </span>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  size: { type: Number, default: 118 },
  state: { type: String, default: 'idle' }, // idle | recording | processing | done
  level: { type: Function, default: null }, // () => 0..1.2, read each frame while recording
  still: { type: Boolean, default: false },
})

const rootEl = ref(null)
const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
let raf = 0
let lvl = 0
function loop() {
  const target = props.level ? Math.min(1.2, props.level() || 0) : 0
  lvl += (target - lvl) * (target > lvl ? 0.35 : 0.08)
  rootEl.value?.style.setProperty('--lvl', lvl.toFixed(3))
  raf = requestAnimationFrame(loop)
}
function sync() {
  cancelAnimationFrame(raf)
  raf = 0
  if (props.state === 'recording' && !reduced && !props.still) raf = requestAnimationFrame(loop)
  else { lvl = 0; rootEl.value?.style.setProperty('--lvl', '0') }
}
watch(() => [props.state, props.still], sync)
onMounted(sync)
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<style scoped>
.co {
  position: relative; display: inline-grid; place-items: center; flex: none;
  width: var(--co-size); height: var(--co-size);
}
.co-ball {
  position: relative; width: 100%; height: 100%; border-radius: 50%; overflow: hidden;
  background: radial-gradient(circle at 50% 45%, #F7E6F1 0%, #E7B5D6 38%, #C76AA9 72%, #A63A86 100%);
  box-shadow: inset 0 -12px 30px rgba(110, 30, 85, 0.28), 0 18px 50px rgba(110, 30, 85, 0.22);
  transform: scale(calc(1 + var(--lvl) * 0.06));
  transition: transform 0.08s linear;
  animation: coBreathe 5s ease-in-out infinite;
}
/* the soft inner light — the thing that "lives" */
.co-light {
  position: absolute; inset: 18%; border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.35) 45%, rgba(255, 255, 255, 0) 70%);
  opacity: calc(0.55 + var(--lvl) * 0.4);
  transform: scale(calc(0.85 + var(--lvl) * 0.35));
  animation: coGlow 5s ease-in-out infinite;
}
.co-sheen {
  position: absolute; inset: 0; border-radius: 50%;
  background: radial-gradient(circle at 35% 25%, rgba(255, 255, 255, 0.55), transparent 35%);
}
.co-ring {
  position: absolute; inset: 0; border-radius: 50%; border: 1px solid rgba(199, 106, 169, 0.45); opacity: 0; pointer-events: none;
}
@keyframes coBreathe { 50% { transform: scale(1.025); } }
@keyframes coGlow { 50% { opacity: 0.8; transform: scale(0.95); } }

/* recording: the mic drives it; two rings ripple out */
.co--recording .co-ball { animation: none; }
.co--recording .co-light { animation: none; }
.co--recording .co-ring { animation: coRipple 2.2s ease-out infinite; }
.co--recording .co-ring--2 { animation-delay: 1.1s; }
@keyframes coRipple { 0% { transform: scale(1); opacity: 0.7; } 100% { transform: scale(1.35); opacity: 0; } }

/* processing: a slow thinking pulse of the inner light */
.co--processing .co-light { animation: coThink 1.8s ease-in-out infinite; }
.co--processing .co-ring--1 { animation: coRipple 3.6s ease-out infinite; }
@keyframes coThink { 0%, 100% { opacity: 0.45; transform: scale(0.75); } 50% { opacity: 0.95; transform: scale(1.05); } }

@media (prefers-reduced-motion: reduce) {
  .co-ball, .co-light, .co-ring { animation: none !important; }
}
</style>
