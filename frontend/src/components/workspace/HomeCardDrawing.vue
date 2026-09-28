<template>
  <!-- Home card illustrations — hand-drawn line art in the same language as
       the cycle clock and Nifra Agent (round strokes, a thin secondary line,
       one small accent). Each draws itself in on mount and re-draws on hover;
       the automation gears turn. pathLength=1 on every stroke → one dash anim. -->
  <svg class="hcd" :class="['hcd--' + name, { 'is-hover': hover }]" viewBox="0 0 64 64" aria-hidden="true"
       :style="{ '--hcd-delay': delay + 'ms' }">
    <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
      <!-- פרודוקציה: the book of policies, growing -->
      <template v-if="name === 'production'">
        <path class="s thin" pathLength="1" d="M18 12h24l6 6v30" />
        <path class="s" pathLength="1" stroke-width="2.4" d="M12 18h24l7 7v29H12z" />
        <path class="s thin" pathLength="1" d="M36 18v7h7" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M17 46l7-7 5 4 8-10" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M33 33h4v4" />
        <circle class="dot" cx="17" cy="46" r="1.8" />
      </template>

      <!-- השוואת נפרעים: two sides on a balance -->
      <template v-else-if="name === 'comparison'">
        <path class="s" pathLength="1" stroke-width="2.4" d="M32 10v42M22 54h20" />
        <path class="s" pathLength="1" stroke-width="2.4" d="M13 18h38" />
        <circle class="dot" cx="32" cy="14" r="2.2" />
        <path class="s thin" pathLength="1" d="M13 18l-7 16M13 18l7 16M51 18l-7 16M51 18l7 16" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M5 34c2 5 14 5 16 0z" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M43 34c2 5 14 5 16 0z" />
        <path class="s acc" pathLength="1" stroke-width="2" d="M48.5 30.5l2 2 4-4.5" />
      </template>

      <!-- מדף ההסכמים: agreements standing on a shelf, a % tag -->
      <template v-else-if="name === 'commission-rates'">
        <path class="s" pathLength="1" stroke-width="2.6" d="M6 50h52" />
        <path class="s thin" pathLength="1" d="M10 50v5M54 50v5" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M11 50V20h9v30" />
        <path class="s thin" pathLength="1" d="M13.5 26h4M13.5 30h4" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M22 50V14h10v36" />
        <path class="s thin" pathLength="1" d="M24.5 20h5M24.5 24h5" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M35 50l6-27 8 2-6 25" />
        <path class="s acc" pathLength="1" stroke-width="1.6" d="M27 32v7" />
        <path class="s acc" pathLength="1" stroke-width="2" d="M22.5 39h9l-2 7h-9z" />
        <text class="pct" x="26" y="45" text-anchor="middle">%</text>
      </template>

      <!-- פורטל לקוחות: a customer's screen, shared by link -->
      <template v-else-if="name === 'portal'">
        <rect class="s" pathLength="1" x="8" y="12" width="40" height="30" rx="4" stroke-width="2.4" />
        <path class="s thin" pathLength="1" d="M8 19h40" />
        <circle class="s" pathLength="1" cx="21" cy="29" r="4" stroke-width="2" />
        <path class="s thin" pathLength="1" d="M29 27h13M29 32h9" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M20 48h16M28 42v6" />
        <path class="s acc" pathLength="1" stroke-width="2.2" d="M47 38l4-4a4 4 0 0 1 6 6l-4 4M52 45l-4 4a4 4 0 0 1-6-6l4-4M47.5 44.5l5-5" />
      </template>

      <!-- ספריית AI: an open book that knows things -->
      <template v-else-if="name === 'ai-library'">
        <path class="s" pathLength="1" stroke-width="2.4" d="M32 20c-6-5-15-5-22-2v30c7-3 16-3 22 2 6-5 15-5 22-2V18c-7-3-16-3-22 2z" />
        <path class="s thin" pathLength="1" d="M32 20v30" />
        <path class="s thin" pathLength="1" d="M15 26c4-1 8-1 12 1M15 32c4-1 8-1 12 1M37 27c4-2 8-2 12-1" />
        <path class="s acc" pathLength="1" stroke-width="2" d="M44 6v8M40 10h8M50 16v4M48 18h4" />
      </template>

      <!-- מסלקה פנסיונית: the clearinghouse → the customer's savings -->
      <template v-else-if="name === 'maslaka'">
        <path class="s" pathLength="1" stroke-width="2.4" d="M8 22L28 10l20 12z" />
        <path class="s thin" pathLength="1" d="M8 26h40" />
        <path class="s" pathLength="1" stroke-width="2.2" d="M13 28v16M23 28v16M33 28v16M43 28v16" />
        <path class="s" pathLength="1" stroke-width="2.6" d="M6 48h44" />
        <path class="s acc" pathLength="1" stroke-width="2.2" d="M54 20v18M49 33l5 5 5-5" />
        <circle class="s acc" pathLength="1" cx="54" cy="46" r="4" stroke-width="2" />
      </template>

      <!-- אוטומציה: gears that turn by themselves -->
      <template v-else-if="name === 'portal-automation'">
        <g class="gear-big">
          <path class="s" pathLength="1" stroke-width="2.3"
                d="M26.2 9.6h7.6l1.2 5.3 3.4 1.4 4.6-2.9 5.4 5.4-2.9 4.6 1.4 3.4 5.3 1.2v7.6l-5.3 1.2-1.4 3.4 2.9 4.6-5.4 5.4-4.6-2.9-3.4 1.4-1.2 5.3h-7.6l-1.2-5.3-3.4-1.4-4.6 2.9-5.4-5.4 2.9-4.6-1.4-3.4-5.3-1.2v-7.6l5.3-1.2 1.4-3.4-2.9-4.6 5.4-5.4 4.6 2.9 3.4-1.4z" />
          <circle class="s thin" pathLength="1" cx="30" cy="32" r="9" />
          <circle class="s" pathLength="1" cx="30" cy="32" r="3.5" stroke-width="2.2" />
        </g>
        <g class="gear-small">
          <path class="s acc" pathLength="1" stroke-width="2"
                d="M52 45l2.2.6.6 2.2 2.2.6-.6 2.2 1.6 1.6-1.6 1.6.6 2.2-2.2.6-.6 2.2-2.2-.6-1.6 1.6-1.6-1.6-2.2.6-.6-2.2-2.2-.6.6-2.2-1.6-1.6 1.6-1.6-.6-2.2 2.2-.6.6-2.2z" />
          <circle class="s acc" pathLength="1" cx="50.4" cy="52.6" r="2" stroke-width="1.8" />
        </g>
      </template>

      <!-- fallback -->
      <circle v-else class="s" pathLength="1" cx="32" cy="32" r="20" stroke-width="2.4" />
    </g>
  </svg>
</template>

<script setup>
defineProps({
  name: { type: String, required: true },
  hover: { type: Boolean, default: false },
  delay: { type: Number, default: 0 },
})
</script>

<style scoped>
.hcd { width: 56px; height: 56px; overflow: visible; color: var(--accent-ink, currentColor); }
.s { stroke-dasharray: 1; stroke-dashoffset: 1; animation: hcdDraw 0.9s cubic-bezier(.55, .1, .35, 1) var(--hcd-delay, 0ms) forwards; }
.thin { stroke-width: 1.3; opacity: 0.5; }
.acc { color: var(--accent, currentColor); stroke: var(--accent, currentColor); }
.dot { fill: var(--accent, currentColor); stroke: none; opacity: 0; animation: hcdPop .3s ease calc(var(--hcd-delay, 0ms) + 700ms) forwards; }
.pct { font: 800 6.5px 'Heebo', sans-serif; fill: var(--accent, currentColor); stroke: none; opacity: 0; animation: hcdPop .3s ease calc(var(--hcd-delay, 0ms) + 800ms) forwards; }
@keyframes hcdDraw { to { stroke-dashoffset: 0; } }
@keyframes hcdPop { to { opacity: 1; } }
/* hover: sketch it again, quicker */
.is-hover .s { animation: hcdRedraw 0.7s cubic-bezier(.55, .1, .35, 1) both; }
@keyframes hcdRedraw { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
/* the gears turn (slowly always, faster on hover), meshing in opposite directions */
.gear-big { transform-origin: 30px 32px; animation: hcdSpin 16s linear infinite; }
.gear-small { transform-origin: 50.4px 52.6px; animation: hcdSpin 8s linear infinite reverse; }
.is-hover .gear-big { animation-duration: 3s; }
.is-hover .gear-small { animation-duration: 1.5s; }
@keyframes hcdSpin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .s, .is-hover .s { animation: none; stroke-dashoffset: 0; }
  .dot, .pct { animation: none; opacity: 1; }
  .gear-big, .gear-small { animation: none; }
}
</style>
