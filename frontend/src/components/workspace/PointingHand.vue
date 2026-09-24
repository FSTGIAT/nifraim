<template>
  <!-- First-run hint beside an empty-state CTA: every 10s a hand glides in from
       a screen corner, taps the target with a ripple, and glides back out.
       Decorative; never intercepts clicks. Place inside a position:relative
       wrapper around the target. -->
  <span class="pth" :class="`pth--${from}`" :style="{ '--pth-color': color }" aria-hidden="true">
    <span class="pth-ripple"></span>
    <svg viewBox="0 0 24 24" width="64" height="64" fill="#fff" stroke="currentColor" stroke-width="1.6"
         stroke-linecap="round" stroke-linejoin="round">
      <!-- Lucide "pointer": index finger raised -->
      <path d="M18 11a2 2 0 1 1 4 0v3a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15V4a2 2 0 0 1 4 0v5.5V9a2 2 0 0 1 4 0v1a2 2 0 0 1 4 0Z" />
      <path d="M14 10V9" fill="none" /><path d="M18 11v-1" fill="none" /><path d="M10 9.5V9" fill="none" />
    </svg>
  </span>
</template>

<script setup>
defineProps({
  // Which screen corner the hand comes from.
  from: { type: String, default: 'bottom-right' },   // 'bottom-right' | 'bottom-left'
  color: { type: String, default: 'var(--tab-production)' },   // ripple colour
})
</script>

<style scoped>
.pth {
  position: absolute; top: 60%; z-index: 20; pointer-events: none;
  color: var(--text); filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.18));
  transform-origin: 30% 10%;
  transform: translate(var(--dx), 48vh);
  animation: pth-cycle 10s infinite;
}
.pth--bottom-right { left: 62%; --dx: 52vw; }
.pth--bottom-left { right: 62%; --dx: -52vw; transform-origin: 70% 10%; }
.pth svg { display: block; transform: rotate(-28deg); }
.pth--bottom-left svg { transform: scaleX(-1) rotate(-28deg); }

.pth-ripple {
  position: absolute; top: -6px; width: 26px; height: 26px; border-radius: 50%;
  border: 2.5px solid var(--pth-color); opacity: 0;
  animation: pth-ripple 10s ease-out infinite;
}
.pth--bottom-right .pth-ripple { left: 2px; }
.pth--bottom-left .pth-ripple { right: 2px; }

/* 0–2.2s in · tap ~2.6s · hold · out by 5.2s · off-screen to 10s */
@keyframes pth-cycle {
  0%   { transform: translate(var(--dx), 48vh); animation-timing-function: cubic-bezier(0.22, 0.8, 0.3, 1); }
  22%  { transform: translate(0, 0) scale(1); animation-timing-function: ease-in-out; }
  26%  { transform: translate(0, 0) scale(0.84); }
  30%  { transform: translate(0, 0) scale(1); }
  34%  { transform: translate(0, 0) scale(1); animation-timing-function: cubic-bezier(0.6, 0, 0.8, 0.4); }
  52%, 100% { transform: translate(var(--dx), 48vh); }
}
@keyframes pth-ripple {
  0%, 25% { transform: scale(0.4); opacity: 0; }
  27% { opacity: 0.9; }
  40%, 100% { transform: scale(2.4); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .pth { animation: none; transform: none; }       /* resting beside the target */
  .pth-ripple { display: none; }
}
</style>
