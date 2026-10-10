<template>
  <div class="mw" aria-hidden="true">
    <!-- The tabs' bottom waves (CommissionUploader's pattern: 3 sliding layers + a shimmer masked to the waves),
         in Nifra Market's olive, inside the studio window. Unique gradient ids (mwg*) — ids are page-global. -->
    <div class="mw-shimmer"></div>
    <svg class="mw-wave mw-wave--1" viewBox="0 0 1440 200" preserveAspectRatio="none">
      <defs>
        <linearGradient id="mwg1" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#7A7F2A" stop-opacity="0.18" />
          <stop offset="30%" stop-color="#9DA243" stop-opacity="0.10" />
          <stop offset="60%" stop-color="#7A7F2A" stop-opacity="0.18" />
          <stop offset="100%" stop-color="#9DA243" stop-opacity="0.09" />
        </linearGradient>
      </defs>
      <path fill="url(#mwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z" />
    </svg>
    <svg class="mw-wave mw-wave--2" viewBox="0 0 1440 200" preserveAspectRatio="none">
      <defs>
        <linearGradient id="mwg2" x1="100%" y1="0%" x2="0%" y2="0%">
          <stop offset="0%" stop-color="#7A7F2A" stop-opacity="0.14" />
          <stop offset="40%" stop-color="#B9BD6A" stop-opacity="0.10" />
          <stop offset="70%" stop-color="#7A7F2A" stop-opacity="0.14" />
          <stop offset="100%" stop-color="#B9BD6A" stop-opacity="0.08" />
        </linearGradient>
      </defs>
      <path fill="url(#mwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z" />
    </svg>
    <svg class="mw-wave mw-wave--3" viewBox="0 0 1440 200" preserveAspectRatio="none">
      <defs>
        <linearGradient id="mwg3" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#7A7F2A" stop-opacity="0.12" />
          <stop offset="50%" stop-color="#C9CD8C" stop-opacity="0.10" />
          <stop offset="100%" stop-color="#7A7F2A" stop-opacity="0.14" />
        </linearGradient>
      </defs>
      <path fill="url(#mwg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z" />
    </svg>
    <!-- a small surfer rides the front wave once in a while (every 24s, ~6s on screen) -->
    <span class="mw-surfer-track">
      <span class="mw-surfer-bob">
        <svg class="mw-surfer" viewBox="0 0 64 56" width="52" height="46">
          <path d="M6 46 C 18 52, 46 52, 60 44 C 50 42, 20 42, 6 46 Z" class="mw-board" />
          <circle cx="33" cy="9" r="4.6" class="mw-ink-fill" />
          <path d="M33 14 L30 27 L22 35 M30 27 L38 34 L40 42 M22 35 L20 42" class="mw-ink" />
          <path d="M31 18 L19 14 M31 18 L44 21" class="mw-ink" />
          <path d="M8 49 C 3 50, 1 47, 4 45" class="mw-spray" />
        </svg>
      </span>
    </span>
    <span class="mw-blob mw-blob--a"></span>
    <span class="mw-blob mw-blob--b"></span>
  </div>
</template>

<style scoped>
.mw { position: absolute; left: 0; right: 0; bottom: 0; height: 240px; overflow: hidden; pointer-events: none; z-index: 0; }
.mw-shimmer {
  position: absolute; inset: 0; z-index: 1; overflow: hidden;
  mask-image: linear-gradient(to top, #000 30%, rgba(0, 0, 0, 0.3) 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to top, #000 30%, rgba(0, 0, 0, 0.3) 60%, transparent 100%);
}
.mw-shimmer::after {
  content: ''; position: absolute; top: 0; left: -80%; width: 50%; height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(214, 219, 140, 0.16) 35%, rgba(255, 255, 255, 0.28) 50%, rgba(214, 219, 140, 0.16) 65%, transparent 100%);
  animation: mwSweep 7s ease-in-out infinite;
}
.mw-wave { position: absolute; bottom: 0; left: 0; width: 200%; height: 100%; }
.mw-wave--1 { animation: mwSlide 14s linear infinite; }
.mw-wave--2 { animation: mwSlide 18s linear infinite reverse; }
.mw-wave--3 { animation: mwSlide 22s linear infinite; }
.mw-blob { position: absolute; border-radius: 50%; filter: blur(50px); opacity: 0.55; animation: mwBob 13s ease-in-out infinite; }
.mw-blob--a { width: 240px; height: 240px; bottom: 40px; right: 12%; background: rgba(157, 162, 67, 0.22); }
.mw-blob--b { width: 200px; height: 200px; bottom: 10px; left: 18%; background: rgba(201, 205, 140, 0.30); animation-delay: -6s; }
/* the surfer: crosses right→left over 6s of a 24s loop, invisible the rest; bobs and tilts with the swell */
.mw-surfer-track { position: absolute; z-index: 2; bottom: 112px; right: -70px; opacity: 0; animation: mwRide 24s linear infinite 3s; }
.mw-surfer-bob { display: block; animation: mwBobSurf 2.2s ease-in-out infinite; transform-origin: 50% 90%; }
.mw-surfer { display: block; overflow: visible; transform: scaleX(-1); }   /* drawn facing right; it rides leftward */
.mw-board { fill: rgba(122, 127, 42, 0.85); }
.mw-ink { fill: none; stroke: #5E6320; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.mw-ink-fill { fill: #5E6320; }
.mw-spray { fill: none; stroke: rgba(255, 255, 255, 0.9); stroke-width: 2; stroke-linecap: round; }
@keyframes mwRide {
  0% { transform: translateX(0); opacity: 0; }
  1.5% { opacity: 1; }
  24% { opacity: 1; }
  26% { transform: translateX(calc(-100vw - 140px)); opacity: 0; }
  100% { transform: translateX(calc(-100vw - 140px)); opacity: 0; }
}
@keyframes mwBobSurf { 0%, 100% { transform: translateY(0) rotate(-4deg); } 50% { transform: translateY(-9px) rotate(5deg); } }
@keyframes mwSweep { 0% { left: -80%; } 100% { left: 180%; } }
@keyframes mwSlide { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
@keyframes mwBob { 50% { transform: translate(-24px, -16px) scale(1.08); } }
@media (prefers-reduced-motion: reduce) { .mw-wave, .mw-shimmer::after, .mw-blob { animation: none; } .mw-surfer-track { display: none; } }
</style>
