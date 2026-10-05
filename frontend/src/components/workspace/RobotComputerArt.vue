<template>
  <!-- Nifra Robot's computer — line art in the HomeCardDrawing language.
       Connected: the screen glows softly and a small data pulse runs across it.
       Disconnected: the screen is dim and an unplugged cable hangs and sways. -->
  <svg class="rca" :class="online ? 'rca--on' : 'rca--off'" viewBox="0 0 160 120" :width="width" aria-hidden="true">
    <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
      <!-- screen glow (connected) -->
      <rect v-if="online" class="glow" x="30" y="14" width="100" height="62" rx="6" />
      <!-- monitor -->
      <rect class="s" pathLength="1" x="24" y="8" width="112" height="74" rx="9" stroke-width="2.6" />
      <rect class="s thin" pathLength="1" x="31" y="15" width="98" height="60" rx="5" />
      <!-- stand -->
      <path class="s" pathLength="1" d="M72 82l-4 16M88 82l4 16" stroke-width="2.4" />
      <path class="s" pathLength="1" d="M56 100h48" stroke-width="2.6" />
      <!-- connected: a data line running across the screen -->
      <template v-if="online">
        <path class="s thin" pathLength="1" d="M38 46h84" />
        <path class="s acc data" pathLength="1" stroke-width="2.4" d="M38 46h18l5-10 7 20 6-14 4 4h44" />
        <circle class="led" cx="122" cy="68" r="2.4" />
      </template>
      <!-- disconnected: dim screen, an unplugged cable hanging from the back -->
      <template v-else>
        <path class="s thin" pathLength="1" d="M66 45h28" />
        <g class="cable">
          <path class="s" pathLength="1" d="M136 60c10 0 14 8 12 18s-6 16-4 24" stroke-width="2.2" />
          <path class="s acc-off" pathLength="1" d="M139 102h10v6h-10zM141.5 108v4M146.5 108v4" stroke-width="2" />
        </g>
      </template>
    </g>
  </svg>
</template>

<script setup>
defineProps({
  online: { type: Boolean, default: false },
  width: { type: Number, default: 150 },
})
</script>

<style scoped>
.rca { display: block; margin: 0 auto; overflow: visible; color: var(--text-secondary, #3E3E3C); }
.rca--off { color: var(--text-muted, #706E6B); }
.s { stroke-dasharray: 1; stroke-dashoffset: 1; animation: rcaDraw 1s cubic-bezier(0.55, 0.1, 0.35, 1) forwards; }
.thin { stroke-width: 1.5; opacity: 0.5; }
.acc { stroke: var(--tab-automation, #0E8C8A); }
.acc-off { stroke: currentColor; }
@keyframes rcaDraw { to { stroke-dashoffset: 0; } }

/* connected */
.glow { fill: var(--tab-automation, #0E8C8A); stroke: none; opacity: 0; filter: blur(8px); animation: rcaGlow 3.6s ease-in-out 0.8s infinite; }
@keyframes rcaGlow { 0%, 100% { opacity: 0.08; } 50% { opacity: 0.2; } }
.data { stroke-dasharray: 0.3 0.7; animation: rcaDraw 1s ease forwards, rcaRun 2.4s linear 1s infinite; }
@keyframes rcaRun { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
.led { fill: var(--green, #2E844A); stroke: none; animation: rcaLed 2s ease-in-out infinite; }
@keyframes rcaLed { 50% { opacity: 0.3; } }

/* disconnected: the cable sways a little */
.cable { transform-origin: 136px 60px; animation: rcaSway 3.4s ease-in-out 1s infinite; }
@keyframes rcaSway { 0%, 100% { transform: rotate(0deg); } 50% { transform: rotate(4deg); } }

@media (prefers-reduced-motion: reduce) {
  .s, .data, .cable, .glow, .led { animation: none; stroke-dashoffset: 0; }
  .data { stroke-dasharray: none; }
  .glow { opacity: 0.12; }
}
</style>
