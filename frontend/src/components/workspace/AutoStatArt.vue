<template>
  <!-- Bespoke line art for the automation tab — the HomeCardDrawing language:
       round strokes, a thin secondary line, one accent, pathLength=1 draw-in,
       and one small living loop each.
         portals  — three portal windows that slide into a stack
         pulse    — a heartbeat line running through a small node
         clock    — the hand sweeps once, then a check draws
         doc      — a document; the arrow drops in (on hover again) -->
  <svg class="asa" :class="['asa--' + name, { 'is-hover': hover }]" :width="size" :height="size" viewBox="0 0 48 48" aria-hidden="true">
    <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
      <template v-if="name === 'portals'">
        <g class="win win3"><rect class="s thin" pathLength="1" x="15" y="6" width="26" height="18" rx="3" /></g>
        <g class="win win2"><rect class="s thin" pathLength="1" x="11" y="13" width="26" height="18" rx="3" /></g>
        <g class="win win1">
          <rect class="s" pathLength="1" x="7" y="20" width="26" height="20" rx="3.5" stroke-width="2.4" />
          <path class="s" pathLength="1" d="M7 26.5h26" stroke-width="1.8" />
          <circle class="dot" cx="11" cy="23.3" r="1.1" /><circle class="dot" cx="14.5" cy="23.3" r="1.1" />
          <path class="s acc" pathLength="1" d="M13 33.5h9" stroke-width="2.2" />
        </g>
      </template>

      <template v-else-if="name === 'pulse'">
        <path class="s thin" pathLength="1" d="M4 30h40" />
        <path class="s acc beat" pathLength="1" stroke-width="2.4" d="M4 30h9l3.5-9 5 18 4.5-14 3 5H44" />
        <circle class="node" cx="24" cy="30" r="3.4" />
      </template>

      <template v-else-if="name === 'clock'">
        <circle class="s" pathLength="1" cx="24" cy="24" r="17" stroke-width="2.4" />
        <path class="s thin" pathLength="1" d="M24 9v3M39 24h-3M24 39v-3M9 24h3" />
        <g class="hand"><path class="s" pathLength="1" d="M24 24V14" stroke-width="2.4" /></g>
        <path class="s check acc" pathLength="1" d="m18 26 4.5 4.5L31 21" stroke-width="2.6" />
      </template>

      <template v-else-if="name === 'doc'">
        <path class="s" pathLength="1" d="M28 6H14a4 4 0 0 0-4 4v28a4 4 0 0 0 4 4h20a4 4 0 0 0 4-4V16z" stroke-width="2.4" />
        <path class="s thin" pathLength="1" d="M28 6v10h10" />
        <g class="arrow"><path class="s acc" pathLength="1" d="M24 19v13M18.5 27l5.5 5.5 5.5-5.5" stroke-width="2.4" /></g>
      </template>
    </g>
  </svg>
</template>

<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 44 },
  hover: { type: Boolean, default: false },
})
</script>

<style scoped>
.asa { display: block; flex: none; overflow: visible; color: var(--text-secondary, #3E3E3C); }
.s { stroke-dasharray: 1; stroke-dashoffset: 1; animation: asaDraw 0.9s cubic-bezier(0.55, 0.1, 0.35, 1) forwards; }
.thin { stroke-width: 1.4; opacity: 0.5; }
.acc { stroke: var(--tab-automation, #0E8C8A); }
.dot { fill: currentColor; opacity: 0; animation: asaPop 0.3s ease 0.8s forwards; }
@keyframes asaDraw { to { stroke-dashoffset: 0; } }
@keyframes asaPop { to { opacity: 0.55; } }

/* portals: the windows slide into their stack, the front one last */
.win { animation: asaSlide 0.7s cubic-bezier(0.34, 1.4, 0.5, 1) both; }
.win3 { animation-delay: 0.1s; } .win2 { animation-delay: 0.25s; } .win1 { animation-delay: 0.4s; }
@keyframes asaSlide { from { transform: translate(6px, -6px); opacity: 0; } to { transform: none; opacity: 1; } }
.asa--portals .win3 { animation: asaSlide 0.7s cubic-bezier(0.34, 1.4, 0.5, 1) 0.1s both, asaFloat 5s ease-in-out 1.4s infinite; }
@keyframes asaFloat { 50% { transform: translate(1px, -1.5px); } }

/* pulse: the beat keeps running, the node breathes */
.asa--pulse .beat { stroke-dasharray: 0.35 0.65; animation: asaDraw 0.9s ease forwards, asaRun 2.2s linear 0.9s infinite; }
@keyframes asaRun { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
.node { fill: var(--tab-automation, #0E8C8A); transform-box: fill-box; transform-origin: center; animation: asaNode 2.2s ease-in-out infinite; }
@keyframes asaNode { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.35); opacity: 0.7; } }

/* clock: the hand sweeps once, then the check draws */
.hand { transform-origin: 24px 24px; animation: asaSweep 1.1s cubic-bezier(0.32, 0.72, 0, 1) 0.4s both; }
@keyframes asaSweep { from { transform: rotate(-200deg); } to { transform: rotate(0deg); } }
.check { animation-delay: 1.4s; }

/* doc: the arrow drops in; again on hover */
.arrow { animation: asaDrop 0.6s cubic-bezier(0.34, 1.5, 0.5, 1) 0.7s both; }
.is-hover .arrow { animation: asaDrop 0.5s cubic-bezier(0.34, 1.5, 0.5, 1) both; }
@keyframes asaDrop { from { transform: translateY(-7px); opacity: 0; } to { transform: none; opacity: 1; } }

@media (prefers-reduced-motion: reduce) {
  .s, .win, .hand, .arrow, .node, .asa--pulse .beat, .asa--portals .win3 { animation: none !important; stroke-dashoffset: 0; opacity: 1; transform: none; }
  .asa--pulse .beat { stroke-dasharray: none; }
  .dot { animation: none; opacity: 0.55; }
}
</style>
