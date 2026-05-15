<template>
  <div
    ref="rootEl"
    class="shader-hero"
    :class="{ 'shader-hero--shader-off': !shaderActive || !inView }"
    aria-label="Nifraim AI agent hero"
  >
    <!-- Always-on CSS mesh fallback. Looks great on its own, becomes the
         "production" hero when WebGL2 is unavailable. -->
    <div class="shader-hero-fallback" aria-hidden="true">
      <div class="shader-hero-fallback-orb shader-hero-fallback-orb--1"></div>
      <div class="shader-hero-fallback-orb shader-hero-fallback-orb--2"></div>
      <div class="shader-hero-fallback-orb shader-hero-fallback-orb--3"></div>
      <div class="shader-hero-fallback-orb shader-hero-fallback-orb--4"></div>
      <div class="shader-hero-fallback-orb shader-hero-fallback-orb--5"></div>
      <div class="shader-hero-fallback-grain" aria-hidden="true"></div>
    </div>

    <!-- React island root. Only used when WebGL2 is verified available. -->
    <div ref="mountEl" class="shader-hero-react-root"></div>

    <!-- Hebrew content overlay — always visible, regardless of shader state.
         Uses Vue's <router-link> so SPA navigation works. -->
    <main class="shader-hero-content">
      <div class="shader-hero-eyebrow">
        <span class="shader-hero-eyebrow-dot"></span>
        <span>סוכן AI לסוכני ביטוח</span>
      </div>
      <h1 class="shader-hero-headline">
        בדיקת עמלות נפרעים והקפים<br/>
        <span class="shader-hero-headline-accent">מבוסס AI</span>
      </h1>
      <p class="shader-hero-sub">
        סוכני AI טוענים, סורקים ומשווים — אתם רואים רק את התובנות.
      </p>
      <div class="shader-hero-ctas">
        <router-link to="/login" class="shader-hero-cta shader-hero-cta--primary">
          התחברות
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </router-link>
        <a href="#automation" class="shader-hero-cta shader-hero-cta--ghost" @click.prevent="scrollToAutomation">
          אוטומציה
        </a>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const rootEl = ref(null)
const mountEl = ref(null)
const inView = ref(true)
const shaderActive = ref(false)

let reactRoot = null
let observer = null

function hasWebGL2() {
  try {
    if (typeof document === 'undefined') return false
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('webgl2')
    return !!ctx
  } catch {
    return false
  }
}

function scrollToAutomation() {
  const el = document.getElementById('automation')
  if (!el) return
  window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 72, behavior: 'smooth' })
}

onMounted(async () => {
  if (!rootEl.value) return

  const prefersReduced =
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (prefersReduced) return

  // Pause/resume the shader (display:none on the React root) based on whether
  // the hero is in the viewport. Cheap perf win — display:none stops WebGL rAF.
  observer = new IntersectionObserver(
    ([entry]) => {
      inView.value = entry.isIntersecting
    },
    { rootMargin: '25% 0px 25% 0px', threshold: 0 },
  )
  observer.observe(rootEl.value)

  // Gate: if WebGL2 isn't available (older drivers, no hardware accel, WSL
  // headless GPUs), don't even attempt to mount the React island. The CSS
  // fallback stays as the hero — looks great on its own.
  if (!hasWebGL2()) {
    // eslint-disable-next-line no-console
    console.info('[ShaderHero] WebGL2 not available — using CSS fallback')
    return
  }

  try {
    const [rdClient, react, shaderModule] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('./ShaderHero.tsx'),
    ])
    if (!mountEl.value) return
    reactRoot = rdClient.createRoot(mountEl.value)
    reactRoot.render(react.createElement(shaderModule.default))
    shaderActive.value = true
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[ShaderHeroIsland] failed to mount React island', e)
  }
})

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  if (reactRoot) {
    try {
      reactRoot.unmount()
    } catch {
      /* ignore */
    }
    reactRoot = null
  }
})
</script>

<style scoped>
.shader-hero {
  position: relative;
  width: 100%;
  min-height: 100dvh;
  overflow: hidden;
  background: #000;
  isolation: isolate;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
}

/* ── React mount layer ── */
.shader-hero-react-root {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.shader-hero--shader-off .shader-hero-react-root {
  display: none;
}

/* ── CSS fallback mesh (always rendered; the shader covers it when active) ── */
.shader-hero-fallback {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: radial-gradient(circle at 30% 70%, #1A1614 0%, #000000 100%);
  overflow: hidden;
}

.shader-hero-fallback-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  mix-blend-mode: screen;
  will-change: transform;
}

.shader-hero-fallback-orb--1 {
  width: 70vw;
  height: 70vw;
  top: -20vw;
  right: -15vw;
  background: rgba(232, 102, 10, 0.55); /* brand orange */
  animation: heroOrb1 18s ease-in-out infinite;
}
.shader-hero-fallback-orb--2 {
  width: 50vw;
  height: 50vw;
  bottom: -15vw;
  left: -10vw;
  background: rgba(93, 64, 55, 0.65); /* coffee */
  animation: heroOrb2 22s ease-in-out infinite;
}
.shader-hero-fallback-orb--3 {
  width: 35vw;
  height: 35vw;
  top: 25%;
  left: 35%;
  background: rgba(255, 255, 255, 0.06); /* ivory wash */
  animation: heroOrb3 26s ease-in-out infinite;
}
.shader-hero-fallback-orb--4 {
  width: 28vw;
  height: 28vw;
  top: 55%;
  right: 8%;
  background: rgba(62, 39, 35, 0.6); /* deep coffee */
  animation: heroOrb4 20s ease-in-out infinite;
}
.shader-hero-fallback-orb--5 {
  width: 22vw;
  height: 22vw;
  top: 15%;
  left: 12%;
  background: rgba(232, 102, 10, 0.3); /* brand orange small */
  animation: heroOrb5 16s ease-in-out infinite;
}

@keyframes heroOrb1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-4vw, 6vw) scale(1.08); }
}
@keyframes heroOrb2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(6vw, -4vw) scale(1.1); }
}
@keyframes heroOrb3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-3vw, -3vw) scale(1.15); }
}
@keyframes heroOrb4 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(4vw, -5vw) scale(1.05); }
}
@keyframes heroOrb5 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(5vw, 4vw) scale(1.1); }
}

/* Faint grain to texture the gradient — without it the fallback looks too clean */
.shader-hero-fallback-grain {
  position: absolute;
  inset: 0;
  opacity: 0.06;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* Soft fade into the cream Chapter 02 below — works for shader and fallback */
.shader-hero::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 18vh;
  z-index: 5;
  pointer-events: none;
  background: linear-gradient(to bottom, transparent 0%, rgba(232, 102, 10, 0.18) 70%, rgba(232, 102, 10, 0.45) 100%);
}

/* ── Hebrew content overlay (always visible) ── */
.shader-hero-content {
  position: absolute;
  bottom: 64px;
  right: 56px;
  z-index: 20;
  max-width: 640px;
  text-align: right;
  color: #fff;
}

.shader-hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 7px 16px 7px 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.14);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.92);
  margin-bottom: 22px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.shader-hero-eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #E8660A;
  box-shadow: 0 0 12px rgba(232, 102, 10, 0.7);
  animation: shaderHeroDotPulse 2s ease-in-out infinite;
}

@keyframes shaderHeroDotPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

.shader-hero-headline {
  font-size: clamp(2.4rem, 5.5vw, 5rem);
  line-height: 1.05;
  letter-spacing: -1.5px;
  font-weight: 300;
  color: #fff;
  margin: 0 0 18px;
}

.shader-hero-headline-accent {
  font-weight: 800;
  color: #E8660A;
  font-style: italic;
}

.shader-hero-sub {
  font-size: 15px;
  font-weight: 300;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.78);
  margin: 0 0 24px;
  max-width: 460px;
}

.shader-hero-ctas {
  display: flex;
  gap: 14px;
  align-items: center;
  flex-wrap: wrap;
}

.shader-hero-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 32px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  transition: all 0.2s ease;
  cursor: pointer;
}

.shader-hero-cta--primary {
  background: #fff;
  color: #0a0a0a;
}
.shader-hero-cta--primary:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
}
.shader-hero-cta--primary svg {
  width: 16px;
  height: 16px;
}

.shader-hero-cta--ghost {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: #fff;
  font-weight: 500;
}
.shader-hero-cta--ghost:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.6);
}

/* ── Mobile ── */
@media (max-width: 768px) {
  .shader-hero-content {
    bottom: 40px;
    right: 24px;
    left: 24px;
    max-width: none;
  }
  .shader-hero-headline {
    font-size: clamp(2rem, 8vw, 3rem);
  }
  .shader-hero-ctas {
    flex-direction: column;
    align-items: stretch;
  }
  .shader-hero-cta {
    justify-content: center;
  }
}
</style>
