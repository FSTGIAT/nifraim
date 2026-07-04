<template>
  <div class="sv sv-worker" aria-hidden="true">
    <svg viewBox="0 0 440 330" fill="none">
      <!-- cloud -->
      <g class="svw-cloud">
        <path d="M290 66c0-16 13-28 29-28 12 0 22 7 26 17 2-.6 5-1 8-1 13 0 24 11 24 24s-11 24-24 24h-58c-13 0-24-11-24-24 0-11 8-20 19-23z" fill="#FFF3E0" stroke="#F5C08A" stroke-width="2"/>
        <circle cx="322" cy="72" r="4" fill="#F57C00" opacity="0.55"/>
        <circle cx="338" cy="72" r="4" fill="#F57C00" opacity="0.35"/>
        <circle cx="354" cy="72" r="4" fill="#F57C00" opacity="0.2"/>
      </g>

      <!-- dashed link cloud -> monitor -->
      <path class="svw-link" d="M322 104 C 322 138, 250 130, 232 158" stroke="#F5A957" stroke-width="2.5" stroke-dasharray="3 8" stroke-linecap="round"/>

      <!-- monitor -->
      <rect x="88" y="118" width="240" height="152" rx="14" fill="#fff" stroke="#EAD9C6" stroke-width="2"/>
      <rect x="88" y="118" width="240" height="30" rx="14" fill="#FDF1E3"/>
      <rect x="88" y="134" width="240" height="14" fill="#FDF1E3"/>
      <circle cx="310" cy="133" r="4" fill="#F57C00"/>
      <circle cx="296" cy="133" r="4" fill="#FFB74D"/>
      <circle cx="282" cy="133" r="4" fill="#F5C08A"/>
      <!-- screen content: file rows appearing -->
      <g class="svw-row svw-row-1">
        <rect x="110" y="166" width="130" height="12" rx="6" fill="#FFE2C4"/>
        <rect x="250" y="166" width="24" height="12" rx="6" fill="#F57C00" opacity="0.8"/>
      </g>
      <g class="svw-row svw-row-2">
        <rect x="110" y="190" width="152" height="12" rx="6" fill="#FFE2C4"/>
        <rect x="272" y="190" width="24" height="12" rx="6" fill="#F57C00" opacity="0.55"/>
      </g>
      <g class="svw-row svw-row-3">
        <rect x="110" y="214" width="110" height="12" rx="6" fill="#FFE2C4"/>
        <rect x="230" y="214" width="24" height="12" rx="6" fill="#F57C00" opacity="0.35"/>
      </g>
      <!-- descending file -->
      <g class="svw-file">
        <rect x="192" y="150" width="34" height="42" rx="6" fill="#fff" stroke="#F57C00" stroke-width="2.4"/>
        <path d="M200 164h18M200 172h18M200 180h11" stroke="#F5A957" stroke-width="2.4" stroke-linecap="round"/>
        <path d="M209 186v14M203 195l6 6 6-6" stroke="#E65100" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" transform="translate(0,-58)"/>
      </g>
      <!-- stand -->
      <path d="M196 270h24v18h-24z" fill="#F3E3D2"/>
      <rect x="164" y="288" width="88" height="9" rx="4.5" fill="#EAD9C6"/>

      <!-- shield badge -->
      <g class="svw-shield">
        <path d="M78 178c0-4 22-12 22-12s22 8 22 12c0 22-8 34-22 42-14-8-22-20-22-42z" fill="#F57C00"/>
        <path d="M91 196l7 7 13-14" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>
      </g>

      <!-- live dot -->
      <g class="svw-live">
        <circle cx="336" cy="250" r="7" fill="#2E844A"/>
        <circle class="svw-live-ring" cx="336" cy="250" r="7" stroke="#2E844A" stroke-width="2"/>
      </g>
    </svg>
  </div>
</template>

<script setup>
</script>

<style scoped>
.sv { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.sv svg { width: 100%; height: 100%; }

.svw-cloud { animation: svw-bob 5s ease-in-out infinite; }
@keyframes svw-bob { 50% { transform: translateY(-6px); } }

.svw-link { animation: svw-dash 1.6s linear infinite; }
@keyframes svw-dash { to { stroke-dashoffset: -22; } }

.svw-file { animation: svw-drop 3.2s ease-in-out infinite; transform-origin: 209px 171px; }
@keyframes svw-drop {
  0%   { transform: translateY(-34px); opacity: 0; }
  18%  { transform: translateY(0);     opacity: 1; }
  62%  { transform: translateY(28px);  opacity: 1; }
  80%, 100% { transform: translateY(44px); opacity: 0; }
}

.svw-row { opacity: 0; animation: svw-row-in 6.4s ease infinite; }
.svw-row-2 { animation-delay: 0.5s; }
.svw-row-3 { animation-delay: 1s; }
@keyframes svw-row-in {
  0% { opacity: 0; transform: translateX(8px); }
  12%, 88% { opacity: 1; transform: translateX(0); }
  100% { opacity: 0; }
}

.svw-shield { animation: svw-pop 6.4s ease infinite; transform-origin: 100px 196px; }
@keyframes svw-pop {
  0%, 20% { transform: scale(0); }
  30% { transform: scale(1.12); }
  36%, 92% { transform: scale(1); }
  100% { transform: scale(0); }
}

.svw-live-ring { fill: none; animation: svw-pulse 2s ease-out infinite; transform-origin: 336px 250px; }
@keyframes svw-pulse {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(2.4); opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .svw-cloud, .svw-link, .svw-file, .svw-row, .svw-shield, .svw-live-ring { animation: none; }
  .svw-row { opacity: 1; }
}
</style>
