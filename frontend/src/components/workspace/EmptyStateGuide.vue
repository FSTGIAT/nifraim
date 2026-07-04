<template>
  <!-- FULL: whole-tab empty state — floating circles + waves + centered guide -->
  <div v-if="variant === 'full'" class="esg esg--full">
    <div class="float-circle fc-1"></div>
    <div class="float-circle fc-2"></div>
    <div class="float-circle fc-3"></div>
    <div class="float-circle fc-4"></div>
    <div class="float-circle fc-5"></div>
    <div class="float-circle fc-6"></div>
    <div class="float-circle fc-7"></div>

    <div class="wave-bg">
      <div class="shimmer"></div>
      <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient :id="gid + 'a'" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
            <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path :fill="`url(#${gid}a)`" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient :id="gid + 'b'" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
            <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
            <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
            <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
          </linearGradient>
        </defs>
        <path :fill="`url(#${gid}b)`" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient :id="gid + 'c'" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/>
          </linearGradient>
        </defs>
        <path :fill="`url(#${gid}c)`" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
      </svg>
    </div>

    <div class="esg-content">
      <div class="esg-illustration">
        <slot name="illustration">
          <div class="esg-icon">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>
            </svg>
          </div>
        </slot>
      </div>
      <h3 class="esg-title">{{ title }}</h3>
      <p class="esg-body">{{ body }}</p>
      <button v-if="ctaLabel" class="esg-cta" @click="onCta">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4l14 8-14 8z"/></svg>
        {{ ctaLabel }}
      </button>
    </div>
  </div>

  <!-- INLINE: slim guide strip above existing content -->
  <div v-else class="esg esg--inline">
    <div class="esg-inline-icon">
      <slot name="illustration">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
        </svg>
      </slot>
    </div>
    <div class="esg-inline-texts">
      <strong v-if="title" class="esg-inline-title">{{ title }}</strong>
      <span class="esg-inline-body">{{ body }}</span>
    </div>
    <button v-if="ctaLabel" class="esg-cta esg-cta--ghost" @click="onCta">
      {{ ctaLabel }}
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
    </button>
  </div>
</template>

<script setup>
import { openSetup } from '../../utils/setupState.js'

const props = defineProps({
  title: { type: String, default: '' },
  body: { type: String, required: true },
  ctaLabel: { type: String, default: '' },
  // When set, the CTA deep-links into the setup wizard at this step
  // ('worker' | 'phone' | 'portal' | 'run'). Without it, `cta` is emitted.
  ctaStep: { type: String, default: '' },
  variant: { type: String, default: 'full' }, // 'full' | 'inline'
})

const emit = defineEmits(['cta'])

// SVG gradient ids are document-global — every mounted instance needs its own.
const gid = `esgw-${Math.random().toString(36).slice(2, 8)}`

function onCta() {
  if (props.ctaStep) openSetup(props.ctaStep)
  else emit('cta')
}
</script>

<style scoped>
/* ── FULL variant ── */
.esg--full {
  position: relative;
  text-align: center;
  padding: 80px 24px 100px;
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.esg-content { position: relative; z-index: 1; max-width: 460px; }

.esg-illustration { margin-bottom: 16px; }
.esg-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto;
  background: var(--primary-light, #FFF3E0);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary, #F57C00);
}

.esg-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text, #181818);
  margin: 0 0 8px;
}

.esg-body {
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-secondary, #3E3E3C);
  margin: 0 0 18px;
}

.esg-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 10px;
  background: var(--primary, #F57C00);
  color: #fff;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 3px 10px rgba(245, 124, 0, 0.28);
  transition: transform 0.15s, background 0.15s, box-shadow 0.15s;
}
.esg-cta:hover { background: var(--primary-deep, #E65100); transform: translateY(-1px); box-shadow: 0 5px 14px rgba(245, 124, 0, 0.34); }
.esg-cta:active { transform: translateY(0); }

/* ── INLINE variant ── */
.esg--inline {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 14px;
  background: linear-gradient(135deg, #F5FAFD 0%, #E7F2FA 100%);
  border: 1px solid rgba(78, 157, 208, 0.2);
  border-radius: var(--radius-md, 12px);
}

.esg-inline-icon {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #fff;
  color: #2C6E9E;
  border: 1px solid rgba(78, 157, 208, 0.18);
}

.esg-inline-texts { flex: 1; min-width: 0; font-size: 13px; line-height: 1.55; color: var(--text-secondary, #3E3E3C); }
.esg-inline-title { display: block; font-weight: 700; color: var(--text, #181818); margin-bottom: 1px; }

.esg-cta--ghost {
  flex-shrink: 0;
  background: #fff;
  color: #2C6E9E;
  border: 1px solid rgba(78, 157, 208, 0.35);
  box-shadow: none;
  padding: 8px 14px;
  font-size: 12.5px;
}
.esg-cta--ghost:hover { background: #E7F2FA; transform: none; box-shadow: none; }

/* ── Floating blur circles (shared with home hero motif) ── */
.float-circle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}
.fc-1 { width: 220px; height: 220px; top: 10%; right: -60px; background: rgba(245, 124, 0, 0.045); border: 1px solid rgba(245, 124, 0, 0.06); animation: esgFloatBob 8s ease-in-out infinite; }
.fc-2 { width: 160px; height: 160px; bottom: 25%; left: -40px; background: rgba(245, 124, 0, 0.035); border: 1px solid rgba(245, 124, 0, 0.05); animation: esgFloatBob 6.5s ease-in-out infinite reverse; }
.fc-3 { width: 90px; height: 90px; top: 30%; left: 8%; background: rgba(245, 124, 0, 0.05); animation: esgFloatBob 10s ease-in-out infinite 2s; }
.fc-4 { width: 120px; height: 120px; top: 55%; right: 6%; background: rgba(245, 124, 0, 0.03); border: 1px solid rgba(245, 124, 0, 0.04); animation: esgFloatBob 9s ease-in-out infinite 1s; }
.fc-5 { width: 50px; height: 50px; top: 18%; right: 22%; background: rgba(255, 152, 0, 0.055); animation: esgFloatBob 7s ease-in-out infinite 3s; }
.fc-6 { width: 280px; height: 280px; bottom: 8%; right: -90px; background: rgba(245, 124, 0, 0.025); border: 1px solid rgba(245, 124, 0, 0.035); animation: esgFloatBob 12s ease-in-out infinite 0.5s; }
.fc-7 { width: 65px; height: 65px; bottom: 35%; left: 18%; background: rgba(255, 183, 77, 0.06); border: 1px solid rgba(255, 183, 77, 0.05); animation: esgFloatBob 8.5s ease-in-out infinite reverse 1.5s; }

@keyframes esgFloatBob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-16px) rotate(2deg); }
  66% { transform: translateY(8px) rotate(-1deg); }
}

/* ── Waves fixed to bottom ── */
.wave-bg {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 200px;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.shimmer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100%;
  z-index: 1;
  overflow: hidden;
  mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
}
.shimmer::after {
  content: '';
  position: absolute;
  top: 0;
  left: -80%;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(255, 200, 100, 0.1) 35%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 200, 100, 0.1) 65%, transparent 100%);
  animation: esgShimmerSweep 7s ease-in-out infinite;
}
@keyframes esgShimmerSweep {
  0%   { left: -80%; }
  100% { left: 180%; }
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 200%;
  height: 100%;
}
.wave-1 { animation: esgWaveSlide 14s linear infinite; }
.wave-2 { animation: esgWaveSlide 18s linear infinite reverse; }
.wave-3 { animation: esgWaveSlide 22s linear infinite; }
@keyframes esgWaveSlide {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

@media (prefers-reduced-motion: reduce) {
  .float-circle, .wave, .shimmer::after { animation: none; }
}
</style>
