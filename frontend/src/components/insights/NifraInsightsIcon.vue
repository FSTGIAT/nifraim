<template>
  <button ref="btnEl" type="button" class="nii" :class="'nii--' + size" title="Nifra Insights · מה עולה בשיחות שלך"
          aria-label="Nifra Insights" @click="$emit('open', btnEl)">
  <!-- Nifra Insights — a line chart that draws itself in a glass ring (Hebrew: right → left), a dot
       lands at its end; a red count when something from the calls is due today. Click → the studio grows out of it. -->
    <span class="nii-ring">
      <svg class="nii-art" viewBox="0 0 64 64" aria-hidden="true">
        <line x1="10" y1="48" x2="54" y2="48" class="nii-base" />
        <path d="M54 40 C 47 40, 45 30, 38 31 S 29 40, 23 33 S 15 18, 10 19" class="nii-line" pathLength="1" />
        <circle cx="10" cy="19" r="3.2" class="nii-dot" />
      </svg>
      <span v-if="badge > 0" class="nii-badge ltr-number" :aria-label="badge + ' משימות להיום'">{{ badge > 9 ? '9+' : badge }}</span>
    </span>
    <span v-if="size === 'big'" class="nii-cap" dir="ltr">Nifra <b>Insights</b></span>
  </button>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  size: { type: String, default: 'big' },   // big (home spot) | small (corner stack)
  badge: { type: Number, default: 0 },
})
defineEmits(['open'])
const btnEl = ref(null)
</script>

<style scoped>
.nii { display: inline-flex; flex-direction: column; align-items: center; gap: 8px; padding: 0; border: none; background: none; cursor: pointer; font-family: 'Heebo', sans-serif; }
.nii:focus-visible { outline: 2px solid var(--tab-insights); outline-offset: 6px; border-radius: 50%; }
.nii-ring {
  position: relative; display: grid; place-items: center; border-radius: 50%;
  /* filled with Insights' own colour: light teal → deep teal (user 2026-10-10) */
  background: radial-gradient(circle at 35% 30%, #6FA3AE 0%, #3C7380 45%, #1F4650 100%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18), 0 10px 30px rgba(44, 95, 107, 0.34), 0 2px 6px rgba(24, 24, 24, 0.08);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.nii--big .nii-ring { width: 118px; height: 118px; }
.nii--small .nii-ring { width: 54px; height: 54px; }
.nii--big .nii-art { width: 64px; height: 64px; }
.nii--small .nii-art { width: 32px; height: 32px; }
.nii:hover .nii-ring { transform: scale(1.05); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.3), 0 14px 38px rgba(44, 95, 107, 0.44); }
.nii-base { stroke: rgba(255, 255, 255, 0.35); stroke-width: 1.2; stroke-linecap: round; }
.nii-line {
  fill: none; stroke: #fff; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round;
  stroke-dasharray: 1; stroke-dashoffset: 1; animation: niiDraw 6s cubic-bezier(0.4, 0.1, 0.2, 1) infinite;
}
.nii-dot { fill: #2C5F6B; stroke: #fff; stroke-width: 1.8; opacity: 0; transform-box: fill-box; transform-origin: center; animation: niiDot 6s ease infinite; }
.nii-badge {
  position: absolute; top: 4%; inset-inline-start: 4%; min-width: 22px; height: 22px; padding: 0 6px; border-radius: 999px;
  display: grid; place-items: center; background: var(--red); color: #fff; font-size: 12px; font-weight: 800;
  box-shadow: 0 0 0 2px #fff;
}
.nii--small .nii-badge { min-width: 17px; height: 17px; font-size: 10px; padding: 0 4px; top: -2px; inset-inline-start: -2px; }
.nii-cap {
  padding: 5px 13px; border-radius: 999px; background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(8px);
  box-shadow: 0 2px 10px rgba(24, 24, 24, 0.08); font-size: 13px; font-weight: 800; letter-spacing: -0.01em; color: #181818;
}
.nii-cap b { color: var(--tab-insights-ink); font-weight: 900; }
/* draw (0–35%) → hold → fade back (85–100%) — slow and calm, one stroke at a time */
@keyframes niiDraw { 0% { stroke-dashoffset: 1; opacity: 1; } 35%, 82% { stroke-dashoffset: 0; opacity: 1; } 96% { stroke-dashoffset: 0; opacity: 0; } 100% { stroke-dashoffset: 1; opacity: 0; } }
@keyframes niiDot { 0%, 33% { opacity: 0; transform: scale(0.4); } 40%, 82% { opacity: 1; transform: scale(1); } 96%, 100% { opacity: 0; transform: scale(1); } }
@media (prefers-reduced-motion: reduce) { .nii-line { animation: none; stroke-dashoffset: 0; } .nii-dot { animation: none; opacity: 1; } }
</style>
