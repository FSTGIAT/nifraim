<template>
  <!-- Nifra Agent "made it" — a line drawing that draws itself, stroke by stroke,
       the moment the agent creates something: a calendar page whose date gets
       circled (meeting) or an envelope with the letter being written (email).
       On send it re-draws as a paper plane flying off a dashed trail, and a
       check is drawn. Every path uses pathLength=1 → one dash animation. -->
  <svg :key="kind + state" class="acd" :class="'acd--' + state" viewBox="0 0 120 84" aria-hidden="true">
    <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
      <template v-if="state === 'sent'">
        <path class="acd-trail" stroke-width="1.4" stroke-dasharray="3 4"
              d="M10 72 C 30 70, 38 52, 58 50 S 84 40, 92 24" />
        <g class="acd-plane">
          <path class="d" style="--d:.35s;--t:.55s" pathLength="1" stroke-width="2.4" d="M78 30 L112 12 L96 44 L90 32 Z" />
          <path class="d" style="--d:.7s;--t:.3s" pathLength="1" stroke-width="2" d="M90 32 L112 12" />
        </g>
        <circle class="d" style="--d:.9s;--t:.5s" pathLength="1" cx="30" cy="36" r="14" stroke-width="2.2" />
        <path class="d" style="--d:1.25s;--t:.35s" pathLength="1" stroke-width="2.8" d="M23 36.5 l5 5 l9 -10" />
      </template>

      <template v-else-if="kind === 'meeting'">
        <rect class="d" style="--d:0s;--t:.6s" pathLength="1" x="22" y="14" width="76" height="62" rx="8" stroke-width="2.4" />
        <path class="d" style="--d:.45s;--t:.3s" pathLength="1" stroke-width="2.4" d="M22 30 H98" />
        <path class="d" style="--d:.6s;--t:.2s" pathLength="1" stroke-width="2.6" d="M40 8 V20" />
        <path class="d" style="--d:.7s;--t:.2s" pathLength="1" stroke-width="2.6" d="M80 8 V20" />
        <g stroke-width="1.3" opacity=".5">
          <path class="d" style="--d:.85s;--t:.35s" pathLength="1" d="M22 45 H98 M22 60 H98" />
          <path class="d" style="--d:.95s;--t:.35s" pathLength="1" d="M41 30 V76 M60 30 V76 M79 30 V76" />
        </g>
        <!-- the date, circled by hand -->
        <path class="d acd-accent" style="--d:1.25s;--t:.55s" pathLength="1" stroke-width="2.4"
              d="M70.5 44.5 c 6 -5, 15 -3, 16 3 c 1 7, -8 11, -14 8.5 c -5 -2, -6 -8, -1 -12.5" />
        <path class="d acd-accent" style="--d:1.7s;--t:.25s" pathLength="1" stroke-width="2.6" d="M75 52 l3 3 l6 -7" />
      </template>

      <template v-else>
        <!-- the letter, written, then slid into the envelope -->
        <g class="acd-letter">
          <rect class="d" style="--d:0s;--t:.45s" pathLength="1" x="34" y="6" width="52" height="46" rx="4" stroke-width="2" />
          <path class="d" style="--d:.4s;--t:.3s" pathLength="1" stroke-width="1.6" opacity=".6" d="M42 18 H78" />
          <path class="d" style="--d:.6s;--t:.3s" pathLength="1" stroke-width="1.6" opacity=".6" d="M42 26 H74" />
          <path class="d" style="--d:.8s;--t:.25s" pathLength="1" stroke-width="1.6" opacity=".6" d="M42 34 H66" />
        </g>
        <rect class="d acd-fill" style="--d:.9s;--t:.55s" pathLength="1" x="20" y="34" width="80" height="44" rx="6" stroke-width="2.4" fill="var(--acd-bg, #fff)" />
        <path class="d" style="--d:1.25s;--t:.4s" pathLength="1" stroke-width="2.4" d="M21 36 L60 60 L99 36" />
        <circle class="d acd-accent acd-fill" style="--d:1.55s;--t:.4s" pathLength="1" cx="60" cy="60" r="6" stroke-width="2.2" fill="var(--acd-bg, #fff)" />
      </template>
    </g>
  </svg>
</template>

<script setup>
defineProps({
  kind: { type: String, default: 'email' },   // email | meeting
  state: { type: String, default: 'open' },   // open (just created) | sent
})
</script>

<style scoped>
.acd { width: 104px; height: auto; flex-shrink: 0; color: #10201F; overflow: visible; }
.acd-accent { color: #0E8C8A; stroke: #0E8C8A; }
.d {
  stroke-dasharray: 1; stroke-dashoffset: 1;
  animation: acdDraw var(--t, .5s) cubic-bezier(.55, .1, .35, 1) var(--d, 0s) forwards;
}
.acd-trail { opacity: .45; animation: acdTrail .7s linear both; }
@keyframes acdDraw { to { stroke-dashoffset: 0; } }
/* a filled shape shows its fill only as its outline is drawn */
.acd-fill { fill-opacity: 0; animation: acdDraw var(--t, .5s) cubic-bezier(.55, .1, .35, 1) var(--d, 0s) forwards, acdFill .3s ease calc(var(--d, 0s) + var(--t, .5s) * .5) forwards; }
@keyframes acdFill { to { fill-opacity: 1; } }
@keyframes acdTrail { from { opacity: 0; clip-path: inset(0 100% 0 0); } to { opacity: .45; clip-path: inset(0 0 0 0); } }
/* the letter slips down into the envelope once it's written */
.acd-letter { animation: acdSlip .45s ease-in 1.05s both; }
@keyframes acdSlip { to { transform: translateY(20px); } }
/* the plane keeps going */
.acd-plane { animation: acdFly 1.1s cubic-bezier(.5, 0, .7, .4) 1.6s forwards; }
@keyframes acdFly { to { transform: translate(26px, -22px) rotate(-6deg); opacity: 0; } }
@media (prefers-reduced-motion: reduce) {
  .d { animation: none; stroke-dashoffset: 0; }
  .acd-fill { fill-opacity: 1; }
  .acd-letter, .acd-plane, .acd-trail { animation: none; }
}
</style>
