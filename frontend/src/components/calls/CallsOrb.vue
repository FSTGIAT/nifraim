<template>
  <!-- The calls orb — one hue (the calls orchid), soft light, no rainbow.
       All motion lives inside it: a slow breath when idle, the live
       microphone level while recording (--lvl swells the light and the
       rings), a thinking pulse while processing. Pure CSS: calm, cheap. -->
  <span ref="rootEl" class="co" :class="'co--' + state" :style="{ '--co-size': size + 'px', '--lvl': 0 }" aria-hidden="true">
    <span class="co-halo"></span>
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
  /* --hov (0|1) is set by the parent button on hover: the orb leans in */
  transform: scale(calc(1 + var(--hov, 0) * 0.055));
  transition: transform 0.5s cubic-bezier(0.34, 1.45, 0.5, 1);
}
/* the glow behind the ball — beats with it, brightens on hover */
.co-halo {
  position: absolute; inset: -16%; border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle, rgba(217, 106, 181, 0.55) 0%, rgba(217, 106, 181, 0.18) 45%, rgba(217, 106, 181, 0) 70%);
  opacity: calc(0.35 + var(--hov, 0) * 0.45 + var(--lvl) * 0.4);
  transition: opacity 0.4s ease;
  animation: coHaloBeat 2.6s ease-in-out infinite;
}
.co-ball {
  position: relative; width: 100%; height: 100%; border-radius: 50%; overflow: hidden;
  background: radial-gradient(circle at 50% 45%, #F7E6F1 0%, #E7B5D6 38%, #C76AA9 72%, #A63A86 100%);
  box-shadow: inset 0 -12px 30px rgba(110, 30, 85, 0.28), 0 18px 50px rgba(110, 30, 85, 0.22);
  transform: scale(calc(1 + var(--lvl) * 0.06));
  transition: transform 0.08s linear;
  animation: coBeat 2.6s ease-in-out infinite;
}
/* the soft inner light — the thing that "lives" */
.co-light {
  position: absolute; inset: 18%; border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.35) 45%, rgba(255, 255, 255, 0) 70%);
  opacity: calc(0.55 + var(--lvl) * 0.4);
  transform: scale(calc(0.85 + var(--lvl) * 0.35));
  animation: coGlow 2.6s ease-in-out infinite;
}
.co-sheen {
  position: absolute; inset: 0; border-radius: 50%;
  background: radial-gradient(circle at 35% 25%, rgba(255, 255, 255, 0.55), transparent 35%);
}
.co-ring {
  position: absolute; inset: 0; border-radius: 50%; border: 1px solid rgba(199, 106, 169, 0.45); opacity: 0; pointer-events: none;
}
/* lub-dub: a visible double beat, then rest */
@keyframes coBeat {
  0%, 40%, 100% { transform: scale(1); }
  8% { transform: scale(1.06); }
  16% { transform: scale(0.995); }
  24% { transform: scale(1.035); }
}
@keyframes coGlow {
  0%, 40%, 100% { opacity: 0.6; transform: scale(0.88); }
  8% { opacity: 1; transform: scale(1.04); }
  24% { opacity: 0.85; transform: scale(0.98); }
}
@keyframes coHaloBeat {
  0%, 45%, 100% { transform: scale(0.96); }
  9% { transform: scale(1.1); }
  25% { transform: scale(1.03); }
}
/* idle: one soft ring leaves the orb on each beat */
.co--idle .co-ring--1, .co--done .co-ring--1 { animation: coBeatRing 2.6s ease-out infinite; }
@keyframes coBeatRing { 0%, 6% { transform: scale(1); opacity: 0; } 9% { opacity: 0.5; } 45% { transform: scale(1.28); opacity: 0; } 100% { opacity: 0; } }

/* recording: the mic drives it; two rings ripple out */
.co--recording .co-ball { animation: none; }
.co--recording .co-light { animation: none; }
.co--recording .co-halo { animation: none; }
.co--recording .co-ring { animation: coRipple 2.2s ease-out infinite; }
.co--recording .co-ring--2 { animation-delay: 1.1s; }
@keyframes coRipple { 0% { transform: scale(1); opacity: 0.7; } 100% { transform: scale(1.35); opacity: 0; } }

/* processing: a slow thinking pulse of the inner light */
.co--processing .co-light { animation: coThink 1.8s ease-in-out infinite; }
.co--processing .co-ring--1 { animation: coRipple 3.6s ease-out infinite; }
@keyframes coThink { 0%, 100% { opacity: 0.45; transform: scale(0.75); } 50% { opacity: 0.95; transform: scale(1.05); } }

@media (prefers-reduced-motion: reduce) {
  .co-ball, .co-light, .co-ring, .co-halo { animation: none !important; }
  .co { transition: none; }
}
</style>
