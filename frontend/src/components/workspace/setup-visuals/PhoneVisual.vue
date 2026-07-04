<template>
  <div class="sv sv-phone" aria-hidden="true">
    <svg viewBox="0 0 440 330" fill="none">
      <!-- phone (right, RTL start) -->
      <g class="svp-phone">
        <rect x="296" y="70" width="96" height="188" rx="20" fill="#fff" stroke="#EAD9C6" stroke-width="2.5"/>
        <rect x="308" y="92" width="72" height="144" rx="10" fill="#FDF1E3"/>
        <rect x="326" y="79" width="36" height="5" rx="2.5" fill="#EAD9C6"/>
        <!-- sms bubble with code dots -->
        <g class="svp-bubble">
          <rect x="314" y="108" width="60" height="34" rx="10" fill="#F57C00"/>
          <path d="M322 142l-4 8 12-8z" fill="#F57C00"/>
          <circle cx="326" cy="125" r="3.2" fill="#fff"/>
          <circle cx="337" cy="125" r="3.2" fill="#fff"/>
          <circle cx="348" cy="125" r="3.2" fill="#fff"/>
          <circle cx="359" cy="125" r="3.2" fill="#fff"/>
        </g>
        <rect x="316" y="160" width="56" height="9" rx="4.5" fill="#FFE2C4"/>
        <rect x="316" y="176" width="40" height="9" rx="4.5" fill="#FFE2C4" opacity="0.7"/>
      </g>

      <!-- arc phone -> laptop -->
      <path class="svp-arc" d="M300 130 C 240 84, 170 84, 128 128" stroke="#F5A957" stroke-width="2.5" stroke-dasharray="3 8" stroke-linecap="round"/>
      <!-- flying code chip along the arc -->
      <g class="svp-chip">
        <rect x="-23" y="-12" width="46" height="24" rx="8" fill="#fff" stroke="#F57C00" stroke-width="2"/>
        <circle cx="-11" cy="0" r="2.6" fill="#E65100"/>
        <circle cx="-1" cy="0" r="2.6" fill="#E65100"/>
        <circle cx="9" cy="0" r="2.6" fill="#E65100"/>
      </g>

      <!-- laptop (left) -->
      <g>
        <rect x="52" y="128" width="168" height="112" rx="12" fill="#fff" stroke="#EAD9C6" stroke-width="2.5"/>
        <rect x="64" y="142" width="144" height="84" rx="8" fill="#FDF1E3"/>
        <!-- otp slots filling -->
        <g>
          <rect class="svp-slot svp-slot-1" x="80" y="168" width="22" height="30" rx="6" fill="#fff" stroke="#F5C08A" stroke-width="2"/>
          <rect class="svp-slot svp-slot-2" x="108" y="168" width="22" height="30" rx="6" fill="#fff" stroke="#F5C08A" stroke-width="2"/>
          <rect class="svp-slot svp-slot-3" x="136" y="168" width="22" height="30" rx="6" fill="#fff" stroke="#F5C08A" stroke-width="2"/>
          <rect class="svp-slot svp-slot-4" x="164" y="168" width="22" height="30" rx="6" fill="#fff" stroke="#F5C08A" stroke-width="2"/>
          <circle class="svp-digit svp-digit-1" cx="91" cy="183" r="4" fill="#E65100"/>
          <circle class="svp-digit svp-digit-2" cx="119" cy="183" r="4" fill="#E65100"/>
          <circle class="svp-digit svp-digit-3" cx="147" cy="183" r="4" fill="#E65100"/>
          <circle class="svp-digit svp-digit-4" cx="175" cy="183" r="4" fill="#E65100"/>
        </g>
        <path d="M36 240h200l-14 22H50z" fill="#F3E3D2"/>
      </g>

      <!-- success check pops after digits land -->
      <g class="svp-check">
        <circle cx="136" cy="130" r="16" fill="#2E844A"/>
        <path d="M128 130l6 6 10-11" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      </g>

      <!-- hands-free hint: crossed-out keyboard hand... keep abstract sparkles -->
      <g class="svp-spark">
        <path d="M250 236l3.5 8 8 3.5-8 3.5-3.5 8-3.5-8-8-3.5 8-3.5z" fill="#FFB74D"/>
      </g>
    </svg>
  </div>
</template>

<script setup>
</script>

<style scoped>
.sv { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.sv svg { width: 100%; height: 100%; }

.svp-phone { animation: svp-bob 5.4s ease-in-out infinite; }
@keyframes svp-bob { 50% { transform: translateY(-5px); } }

.svp-bubble { animation: svp-bubble 5.6s ease infinite; transform-origin: 344px 142px; }
@keyframes svp-bubble {
  0% { transform: scale(0); }
  8% { transform: scale(1.12); }
  12%, 96% { transform: scale(1); }
  100% { transform: scale(0); }
}

.svp-arc { animation: svp-dash 1.4s linear infinite; }
@keyframes svp-dash { to { stroke-dashoffset: -22; } }

/* chip flies along the arc via offset-path */
.svp-chip {
  offset-path: path('M300 130 C 240 84, 170 84, 128 128');
  offset-rotate: 0deg;
  animation: svp-fly 5.6s ease-in-out infinite;
}
@keyframes svp-fly {
  0%, 14% { offset-distance: 0%; opacity: 0; }
  20% { opacity: 1; }
  46% { offset-distance: 100%; opacity: 1; }
  52%, 100% { offset-distance: 100%; opacity: 0; }
}

.svp-digit { opacity: 0; animation: svp-digit 5.6s ease infinite; }
.svp-digit-1 { animation-delay: 0s; }
.svp-digit-2 { animation-delay: 0.12s; }
.svp-digit-3 { animation-delay: 0.24s; }
.svp-digit-4 { animation-delay: 0.36s; }
@keyframes svp-digit {
  0%, 46% { opacity: 0; transform: translateY(-4px); }
  52%, 94% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; }
}

.svp-check { animation: svp-check 5.6s ease infinite; transform-origin: 136px 130px; }
@keyframes svp-check {
  0%, 58% { transform: scale(0); }
  66% { transform: scale(1.14); }
  70%, 94% { transform: scale(1); }
  100% { transform: scale(0); }
}

.svp-spark { animation: svp-spark 2.8s ease-in-out infinite; transform-origin: 253px 248px; }
@keyframes svp-spark { 0%, 100% { transform: scale(0.7); opacity: 0.5; } 50% { transform: scale(1.15); opacity: 1; } }

@media (prefers-reduced-motion: reduce) {
  .svp-phone, .svp-bubble, .svp-arc, .svp-chip, .svp-digit, .svp-check, .svp-spark { animation: none; }
  .svp-digit { opacity: 1; }
  .svp-chip { opacity: 0; }
}
</style>
