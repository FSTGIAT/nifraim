<template>
  <div class="ag-shell-decor" aria-hidden="true">
    <!-- Orange floating blur circles -->
    <div class="float-circle fc-1"></div>
    <div class="float-circle fc-2"></div>
    <div class="float-circle fc-3"></div>
    <div class="float-circle fc-4"></div>
    <div class="float-circle fc-5"></div>
    <div class="float-circle fc-6"></div>
    <div class="float-circle fc-7"></div>

    <!-- Animated SVG waves at page bottom -->
    <div class="wave-bg">
      <div class="shimmer"></div>
      <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="agshellwg1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stop-color="#F57C00" stop-opacity="0.10"/>
            <stop offset="30%"  stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="60%"  stop-color="#FFB74D" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path fill="url(#agshellwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="agshellwg2" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%"   stop-color="#FFB74D" stop-opacity="0.08"/>
            <stop offset="40%"  stop-color="#F57C00" stop-opacity="0.05"/>
            <stop offset="70%"  stop-color="#FF9800" stop-opacity="0.08"/>
            <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
          </linearGradient>
        </defs>
        <path fill="url(#agshellwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="agshellwg3" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="50%"  stop-color="#F57C00" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path fill="url(#agshellwg3)" d="M0,140L60,143.3C120,147,240,153,360,156.7C480,160,600,160,720,153.3C840,147,960,133,1080,133.3C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
      </svg>
    </div>
  </div>
</template>

<script setup></script>

<style scoped>
.ag-shell-decor {
  position: fixed; inset: 0;
  pointer-events: none; z-index: 0;
  overflow: hidden;
}
.float-circle { position: fixed; border-radius: 50%; pointer-events: none; filter: blur(40px); }
.fc-1 { width: 260px; height: 260px; top: 60px;  left: -60px;  background: rgba(245, 124, 0, 0.10); animation: floatBob 14s ease-in-out infinite; }
.fc-2 { width: 200px; height: 200px; bottom: 80px; right: -40px; background: rgba(255, 152, 0, 0.12); animation: floatBob 12s ease-in-out infinite reverse; }
.fc-3 { width: 140px; height: 140px; top: 35%; left: 12%;  background: rgba(255, 183, 77, 0.10); animation: floatBob 17s ease-in-out infinite; }
.fc-4 { width: 110px; height: 110px; top: 22%; right: 28%; background: rgba(245, 124, 0, 0.08); animation: floatBob 9s ease-in-out infinite reverse; }
.fc-5 { width: 90px;  height: 90px;  bottom: 30%; left: 32%; background: rgba(255, 152, 0, 0.10); animation: floatBob 11s ease-in-out infinite; }
.fc-6 { width: 160px; height: 160px; top: 60%; right: 6%;  background: rgba(255, 183, 77, 0.08); animation: floatBob 15s ease-in-out infinite reverse; }
.fc-7 { width: 60px;  height: 60px;  top: 16%; left: 52%;  background: rgba(245, 124, 0, 0.12); animation: floatBob 8s ease-in-out infinite; }
@keyframes floatBob {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(15px, -20px) scale(1.05); }
}

.wave-bg {
  position: fixed; bottom: 0; left: 0; right: 0; height: 200px;
  pointer-events: none; overflow: hidden;
}
.wave { position: absolute; bottom: 0; left: 0; width: 100%; height: 100%; }
.wave-1 { animation: waveSlide 18s linear infinite; }
.wave-2 { animation: waveSlide 22s linear infinite reverse; }
.wave-3 { animation: waveSlide 26s linear infinite; }
@keyframes waveSlide { 0% { transform: translateX(0); } 100% { transform: translateX(-100px); } }
.shimmer {
  position: absolute; bottom: 0; left: -100%; width: 200%; height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(255, 224, 178, 0.18) 50%, transparent 100%);
  animation: shimmerSweep 8s linear infinite;
}
@keyframes shimmerSweep { 0% { transform: translateX(-50%); } 100% { transform: translateX(50%); } }
</style>
