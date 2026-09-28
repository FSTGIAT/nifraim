<template>
  <!-- סוכן המשרד's mark, line art like the cycle clock: an envelope sealed with
       ₪ and a magnifier checking it. currentColor; used as icon and avatar. -->
  <svg viewBox="0 0 120 112" width="100%" height="100%" aria-hidden="true">
    <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
      <rect x="22" y="34" width="72" height="50" rx="7" stroke-width="2.6" fill="var(--card-bg, #fff)" />
      <path d="M23 37 L58 62 L93 37" stroke-width="2.6" />
      <path d="M24 82 L48 60 M92 82 L68 60" stroke-width="1.4" opacity="0.45" />
      <circle cx="58" cy="66" r="10" stroke-width="2" fill="var(--card-bg, #fff)" />
      <text x="58" y="70.5" text-anchor="middle" font-family="Heebo, sans-serif" font-size="12" font-weight="800" fill="currentColor" stroke="none">₪</text>
      <g class="oag-lens">
        <circle cx="92" cy="28" r="11" stroke-width="2.4" fill="var(--card-bg, #fff)" />
        <path d="M100 36 l8 8" stroke-width="3" />
        <path d="M87 28 l3.5 3.5 l6 -7" stroke-width="2" />
      </g>
    </g>
  </svg>
</template>
