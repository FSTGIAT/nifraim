<template>
  <div class="sv sv-agree" aria-hidden="true">
    <svg viewBox="0 0 440 330" fill="none">
      <!-- a stack of agreements -->
      <rect x="120" y="70" width="150" height="196" rx="12" fill="#F3EAF7" stroke="#C7A8D6" stroke-width="2" transform="rotate(-6 195 168)" />
      <rect x="130" y="62" width="150" height="196" rx="12" fill="#fff" stroke="#8E44AD" stroke-width="2.5" />
      <rect x="152" y="88" width="80" height="10" rx="5" fill="#6B2F86" />
      <g stroke="#D9C6E3" stroke-width="7" stroke-linecap="round">
        <path d="M152 118 h104" /><path d="M152 138 h90" /><path d="M152 158 h100" />
      </g>
      <!-- the rates Nifraim reads out of it -->
      <g class="sva-rate sva-rate1"><rect x="246" y="176" width="92" height="30" rx="15" fill="#8E44AD" /><text x="292" y="196" text-anchor="middle" font-family="Heebo, sans-serif" font-size="15" font-weight="800" fill="#fff">25%</text></g>
      <g class="sva-rate sva-rate2"><rect x="266" y="216" width="92" height="30" rx="15" fill="#6B2F86" /><text x="312" y="236" text-anchor="middle" font-family="Heebo, sans-serif" font-size="15" font-weight="800" fill="#fff">0.3%</text></g>
      <!-- upload arrow -->
      <g class="sva-up">
        <circle cx="196" cy="222" r="24" fill="#8E44AD" />
        <path d="M196 234 v-22 M186 220 l10 -10 l10 10" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" />
      </g>
    </svg>
  </div>
</template>

<style scoped>
.sv { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.sv svg { width: 100%; height: 100%; }
.sva-up { animation: svaUp 2.4s ease-in-out infinite; }
@keyframes svaUp { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.sva-rate { opacity: 0; animation: svaRate 6s ease-in-out infinite; }
.sva-rate2 { animation-delay: 0.6s; }
@keyframes svaRate { 0%, 20% { opacity: 0; transform: translateX(-16px); } 35%, 85% { opacity: 1; transform: none; } 100% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .sva-up, .sva-rate { animation: none; opacity: 1; transform: none; } }
</style>
