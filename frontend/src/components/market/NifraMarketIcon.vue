<template>
  <button ref="btnEl" type="button" class="nmi" :class="'nmi--' + size" title="Nifra Market · הלקוחות שלך מול השוק"
          aria-label="Nifra Market" @click="$emit('open', btnEl)">
  <!-- Nifra Market — a living ladder in a glass ring: five bars keep re-ranking, one dot (your customer)
       climbs. Click → the studio grows out of it. -->
    <span class="nmi-ring">
      <span class="nmi-glow" aria-hidden="true"></span>
      <svg class="nmi-ladder" viewBox="0 0 64 64" aria-hidden="true">
        <rect v-for="i in 5" :key="i" class="nmi-bar" :style="{ '--k': i }" :x="6 + (i - 1) * 11.5" y="14" width="7" height="38" rx="3.5" />
        <circle class="nmi-dot" cx="43.5" cy="40" r="4.6" />
      </svg>
    </span>
    <span v-if="size === 'big'" class="nmi-cap" dir="ltr">Nifra <b>Market</b></span>
  </button>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ size: { type: String, default: 'big' } }) // big (home column) | small (corner stack)
defineEmits(['open'])
const btnEl = ref(null)
</script>

<style scoped>
.nmi { display: inline-flex; flex-direction: column; align-items: center; gap: 8px; padding: 0; border: none; background: none; cursor: pointer; font-family: 'Heebo', sans-serif; }
.nmi:focus-visible { outline: 2px solid #5E6320; outline-offset: 6px; border-radius: 50%; }
.nmi-ring {
  position: relative; display: grid; place-items: center; border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #FFFFFF 0%, #F5F6EA 55%, #E9EBD3 100%);
  box-shadow: inset 0 0 0 1px rgba(122, 127, 42, 0.2), 0 10px 30px rgba(122, 127, 42, 0.2), 0 2px 6px rgba(24, 24, 24, 0.06);
  animation: nmiBreathe 4.8s ease-in-out infinite; transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.nmi--big .nmi-ring { width: 118px; height: 118px; }
.nmi--small .nmi-ring { width: 54px; height: 54px; }
.nmi--big .nmi-ladder { width: 64px; height: 64px; }
.nmi--small .nmi-ladder { width: 32px; height: 32px; }
.nmi:hover .nmi-ring { transform: scale(1.06); box-shadow: inset 0 0 0 1px rgba(122, 127, 42, 0.32), 0 14px 38px rgba(122, 127, 42, 0.3); }
.nmi-glow {
  position: absolute; inset: -14px; border-radius: 50%; pointer-events: none;
  background: conic-gradient(from 0deg, rgba(122, 127, 42, 0), rgba(122, 127, 42, 0.26), rgba(201, 205, 140, 0.34), rgba(122, 127, 42, 0));
  filter: blur(14px); opacity: 0.7; animation: nmiSpin 9s linear infinite;
}
.nmi--small .nmi-glow { inset: -6px; filter: blur(7px); }
@media (max-width: 700px) { .nmi-glow { inset: -4px; filter: blur(8px); } }
.nmi-bar { fill: #7A7F2A; opacity: 0.28; transform-box: fill-box; transform-origin: bottom; animation: nmiBar 3.6s ease-in-out infinite; animation-delay: calc(var(--k) * -0.7s); }
.nmi-bar:nth-child(4) { opacity: 0.7; }
.nmi-dot { fill: #5E6320; stroke: #fff; stroke-width: 2; animation: nmiDot 3.6s ease-in-out infinite; }
.nmi-cap {
  padding: 5px 13px; border-radius: 999px; background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(8px);
  box-shadow: 0 2px 10px rgba(24, 24, 24, 0.08); font-size: 13px; font-weight: 800; letter-spacing: -0.01em; color: #181818;
}
.nmi-cap b { color: #5E6320; font-weight: 900; }
@keyframes nmiBreathe { 50% { transform: scale(1.035); } }
@keyframes nmiSpin { to { transform: rotate(360deg); } }
@keyframes nmiBar { 0%, 100% { transform: scaleY(0.45); } 50% { transform: scaleY(1); } }
@keyframes nmiDot { 0%, 100% { transform: translateY(8px); } 50% { transform: translateY(-14px); } }
@media (prefers-reduced-motion: reduce) { .nmi-ring, .nmi-glow, .nmi-bar, .nmi-dot { animation: none; } }
</style>
