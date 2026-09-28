<template>
  <div class="sv sv-maslaka" aria-hidden="true">
    <svg viewBox="0 0 440 330" fill="none">
      <!-- the שיוך form -->
      <rect x="92" y="44" width="178" height="236" rx="14" fill="#fff" stroke="#A7BDC2" stroke-width="2.5"/>
      <rect x="116" y="74" width="96" height="10" rx="5" fill="#2C5F6B"/>
      <rect x="116" y="100" width="130" height="8" rx="4" fill="#C9D8DB"/>
      <rect x="116" y="118" width="116" height="8" rx="4" fill="#C9D8DB"/>
      <rect x="116" y="136" width="124" height="8" rx="4" fill="#C9D8DB"/>
      <rect x="116" y="154" width="92" height="8" rx="4" fill="#C9D8DB"/>
      <line x1="116" y1="232" x2="246" y2="232" stroke="#A7BDC2" stroke-width="2" stroke-linecap="round"/>
      <!-- signature draws itself -->
      <path class="svm-sign" d="M122 222c10-18 18-20 22-8s8 12 16-4 14-10 16 2 10 6 22-10"
            stroke="#2C5F6B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>

      <!-- calendar: 15th -->
      <g class="svm-cal">
        <rect x="262" y="150" width="112" height="112" rx="16" fill="#fff" stroke="#2C5F6B" stroke-width="2.5"/>
        <rect x="262" y="150" width="112" height="30" rx="16" fill="#2C5F6B"/>
        <rect x="262" y="166" width="112" height="14" fill="#2C5F6B"/>
        <line x1="290" y1="140" x2="290" y2="160" stroke="#2C5F6B" stroke-width="5" stroke-linecap="round"/>
        <line x1="346" y1="140" x2="346" y2="160" stroke="#2C5F6B" stroke-width="5" stroke-linecap="round"/>
        <text x="318" y="238" text-anchor="middle" font-family="Heebo, sans-serif" font-size="48" font-weight="800" fill="#2C5F6B">15</text>
      </g>

      <!-- approved check -->
      <g class="svm-check">
        <circle cx="262" cy="70" r="20" fill="#2E844A"/>
        <path d="M252 70l7 7 12-13" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.sv { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.sv svg { width: 100%; height: 100%; }

.svm-sign { stroke-dasharray: 220; stroke-dashoffset: 220; animation: svm-draw 6s ease infinite; }
@keyframes svm-draw {
  0%, 8% { stroke-dashoffset: 220; }
  34%, 92% { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: 220; }
}
.svm-check { transform-origin: 262px 70px; animation: svm-pop 6s ease infinite; }
@keyframes svm-pop {
  0%, 36% { transform: scale(0); }
  44% { transform: scale(1.15); }
  50%, 92% { transform: scale(1); }
  100% { transform: scale(0); }
}
.svm-cal { transform-origin: 318px 206px; animation: svm-float 6s ease-in-out infinite; }
@keyframes svm-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
@media (prefers-reduced-motion: reduce) {
  .svm-sign, .svm-check, .svm-cal { animation: none; stroke-dashoffset: 0; transform: none; }
}
</style>
