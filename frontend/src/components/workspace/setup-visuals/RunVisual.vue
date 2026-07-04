<template>
  <div class="sv sv-run" aria-hidden="true">
    <svg viewBox="0 0 440 330" fill="none">
      <!-- dashboard window -->
      <rect x="60" y="58" width="252" height="204" rx="14" fill="#fff" stroke="#EAD9C6" stroke-width="2.5"/>
      <rect x="60" y="58" width="252" height="32" rx="14" fill="#FDF1E3"/>
      <rect x="60" y="76" width="252" height="14" fill="#FDF1E3"/>
      <circle cx="294" cy="74" r="4" fill="#F57C00"/>
      <circle cx="280" cy="74" r="4" fill="#FFB74D"/>
      <circle cx="266" cy="74" r="4" fill="#F5C08A"/>

      <!-- growing bars -->
      <g>
        <rect class="svr-bar svr-bar-1" x="96" y="120" width="34" height="118" rx="8" fill="#FFB74D"/>
        <rect class="svr-bar svr-bar-2" x="146" y="120" width="34" height="118" rx="8" fill="#F57C00"/>
        <rect class="svr-bar svr-bar-3" x="196" y="120" width="34" height="118" rx="8" fill="#E65100"/>
        <rect class="svr-bar svr-bar-4" x="246" y="120" width="34" height="118" rx="8" fill="#FFCC80"/>
      </g>
      <line x1="84" y1="238" x2="292" y2="238" stroke="#EAD9C6" stroke-width="2.5" stroke-linecap="round"/>

      <!-- check pops above bars -->
      <g class="svr-check svr-check-1">
        <circle cx="113" cy="106" r="11" fill="#2E844A"/>
        <path d="M107.5 106l4.2 4.2 7-7.6" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <g class="svr-check svr-check-2">
        <circle cx="163" cy="94" r="11" fill="#2E844A"/>
        <path d="M157.5 94l4.2 4.2 7-7.6" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <g class="svr-check svr-check-3">
        <circle cx="213" cy="82" r="11" fill="#2E844A"/>
        <path d="M207.5 82l4.2 4.2 7-7.6" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <g class="svr-check svr-check-4">
        <circle cx="263" cy="112" r="11" fill="#2E844A"/>
        <path d="M257.5 112l4.2 4.2 7-7.6" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
      </g>

      <!-- big play button -->
      <g class="svr-play">
        <circle cx="352" cy="230" r="38" fill="#F57C00"/>
        <circle class="svr-play-ring" cx="352" cy="230" r="38" stroke="#F57C00" stroke-width="3"/>
        <path d="M341 212l32 18-32 18z" fill="#fff"/>
      </g>

      <!-- sparkles -->
      <g class="svr-spark svr-spark-1">
        <path d="M348 92l4 9 9 4-9 4-4 9-4-9-9-4 9-4z" fill="#FFB74D"/>
      </g>
      <g class="svr-spark svr-spark-2">
        <path d="M96 280l3 7 7 3-7 3-3 7-3-7-7-3 7-3z" fill="#F5C08A"/>
      </g>
    </svg>
  </div>
</template>

<script setup>
</script>

<style scoped>
.sv { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.sv svg { width: 100%; height: 100%; }

.svr-bar { transform-origin: center 238px; animation: svr-grow 6s ease infinite; }
.svr-bar-1 { animation-delay: 0.15s; }
.svr-bar-2 { animation-delay: 0.35s; }
.svr-bar-3 { animation-delay: 0.55s; }
.svr-bar-4 { animation-delay: 0.75s; }
@keyframes svr-grow {
  0% { transform: scaleY(0.06); }
  14% { transform: scaleY(1.05); }
  20%, 92% { transform: scaleY(1); }
  100% { transform: scaleY(0.06); }
}

.svr-check { animation: svr-pop 6s ease infinite; }
.svr-check-1 { animation-delay: 0.9s; transform-origin: 113px 106px; }
.svr-check-2 { animation-delay: 1.1s; transform-origin: 163px 94px; }
.svr-check-3 { animation-delay: 1.3s; transform-origin: 213px 82px; }
.svr-check-4 { animation-delay: 1.5s; transform-origin: 263px 112px; }
@keyframes svr-pop {
  0%, 14% { transform: scale(0); }
  22% { transform: scale(1.15); }
  27%, 88% { transform: scale(1); }
  96%, 100% { transform: scale(0); }
}

.svr-play { animation: svr-throb 2.4s ease-in-out infinite; transform-origin: 352px 230px; }
@keyframes svr-throb { 50% { transform: scale(1.05); } }
.svr-play-ring { fill: none; animation: svr-ring 2.4s ease-out infinite; transform-origin: 352px 230px; }
@keyframes svr-ring {
  0% { transform: scale(1); opacity: 0.7; }
  100% { transform: scale(1.5); opacity: 0; }
}

.svr-spark { animation: svr-spark 3.2s ease-in-out infinite; }
.svr-spark-1 { transform-origin: 352px 105px; }
.svr-spark-2 { animation-delay: 1.4s; transform-origin: 96px 290px; }
@keyframes svr-spark { 0%, 100% { transform: scale(0.65); opacity: 0.45; } 50% { transform: scale(1.15); opacity: 1; } }

@media (prefers-reduced-motion: reduce) {
  .svr-bar, .svr-check, .svr-play, .svr-play-ring, .svr-spark { animation: none; }
}
</style>
