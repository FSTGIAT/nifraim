<template>
  <div class="pricing" ref="pricingRoot">
    <!-- Nav lives in App.vue (shared SiteNav across marketing routes) -->

    <!-- HERO -->
    <section class="chapter-hero" ref="heroSection">
      <div class="hero-inner">
        <div class="hero-content" ref="heroContent">
          <span class="hero-eyebrow" ref="heroEyebrow">
            <span class="eyebrow-dot"></span>
            מחיר אחד
          </span>
          <h1 class="hero-headline" ref="heroHeadline">
            תמחור שקוף.<br><span class="highlight">מחיר אחד.</span>
          </h1>
          <p class="hero-sub" ref="heroSub">
            גישה מלאה לכל היכולות של Nifraim — ב-₪220 לחודש.
          </p>
          <div class="hero-cta-wrap" ref="heroCtaWrap">
            <router-link to="/signup?plan=monthly" class="hero-btn">
              התחל עכשיו
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            </router-link>
            <a :href="`mailto:${contactEmail}?subject=${encodeURIComponent('שאלה על תמחור Nifraim')}`" class="hero-ghost">
              <span class="ghost-icon">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
              </span>
              שוחחו איתנו
            </a>
          </div>
          <!-- plain <a>: /privacy is a backend page -->
          <a href="/privacy" class="site-legal">מדיניות פרטיות</a>
        </div>

        <div class="hero-visual" ref="heroVisual">
          <!-- the arch video behind the glass price card -->
          <AuthMedia class="pv-media" video="portal" />
          <div class="price-card" ref="priceCard">
            <div class="pc-name">Nifraim</div>
            <div class="pc-price">
              <span class="pc-amount ltr-number" ref="priceNumber">0</span>
              <div class="pc-unit">
                <span class="pc-currency">₪</span>
                <span class="pc-period">לחודש</span>
              </div>
            </div>
            <div class="pc-vat">כולל מע״מ · חיוב חודשי</div>
            <ul class="pc-bullets">
              <li>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                פורטל לקוחות ללא הגבלה
              </li>
              <li>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                עוזר AI אישי
              </li>
              <li>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                תמיכה מלאה
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { gsap } from 'gsap'
import AuthMedia from '../components/site/AuthMedia.vue'

const contactEmail = 'nifraim@nifraim.com'

const pricingRoot = ref(null)
const heroSection = ref(null)
const heroContent = ref(null)
const heroEyebrow = ref(null)
const heroHeadline = ref(null)
const heroSub = ref(null)
const heroCtaWrap = ref(null)
const heroVisual = ref(null)
const priceCard = ref(null)
const priceNumber = ref(null)

function animateNumber(el, target, duration = 1.4) {
  const obj = { val: 0 }
  gsap.to(obj, {
    val: target,
    duration,
    ease: 'power2.out',
    onUpdate: () => {
      el.textContent = Math.round(obj.val)
    }
  })
}

onMounted(() => {
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (prefersReduced) {
    if (priceNumber.value) priceNumber.value.textContent = '220'
    return
  }

  gsap.set([heroEyebrow.value, heroSub.value, heroCtaWrap.value], { opacity: 0, y: 20 })
  gsap.set(heroHeadline.value, { opacity: 0, y: 30 })
  gsap.set(priceCard.value, { opacity: 0, y: 40, scale: 0.96 })

  const heroTL = gsap.timeline({ delay: 0.25 })
  heroTL
    .to(heroEyebrow.value, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' })
    .to(heroHeadline.value, { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out' }, '-=0.3')
    .to(heroSub.value, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.3')
    .to(heroCtaWrap.value, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.2')
    .to(priceCard.value, { opacity: 1, y: 0, scale: 1, duration: 0.9, ease: 'power3.out' }, '-=0.6')
    .add(() => {
      if (priceNumber.value) animateNumber(priceNumber.value, 220, 1.4)
    }, '-=0.3')

})

onBeforeUnmount(() => {
  gsap.killTweensOf([heroEyebrow.value, heroHeadline.value, heroSub.value, heroCtaWrap.value, priceCard.value])
})
</script>

<style scoped>
/* ── Pricing Theme Variables (mirrors LandingView tokens) ── */
.pricing {
  --land-bg: #4A4A4A;
  /* Orange retired 2026-09-26: actions = ink, accents = cobalt/teal (CHART_PALETTE). */
  --land-action: #181818;
  --land-action-deep: #000000;
  --land-accent: #2F73C4;          /* cobalt — fills, icons, decoration */
  --land-accent-ink: #245C9E;      /* deeper cobalt — small text on cream (≥4.5:1) */
  --land-accent-bright: #0E8C8A;   /* teal — gradient partner */
  --land-accent-glow: rgba(47, 115, 196, 0.1);
  --land-text: #F5F5F5;
  --land-text-secondary: #A0A0A0;
  --land-border: #666666;

  --cream-bg: #FFFFFF;
  --cream-text: #2A2E35;
  --cream-text-muted: rgba(42, 46, 53, 0.62);
  --cream-text-dim: rgba(42, 46, 53, 0.36);
  --dark-section: #2D2522;

  --transition-fast: 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  min-height: 100vh;
  background: var(--cream-bg);
  color: var(--cream-text);
  font-family: 'Heebo', sans-serif;
  direction: rtl;
  overflow-x: hidden;
  position: relative;
}

.pricing a:not(.hero-btn) { /* the CTA keeps its white label (this rule used to out-rank it) */
  color: inherit;
  text-decoration: none;
}

/* Navigation lives in App.vue (shared SiteNav). */

/* ── HERO (cream) ── */
.chapter-hero {
  position: relative;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  overflow: hidden;
  background: var(--cream-bg);
}

.hero-inner {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.12fr);
  align-items: center;
  width: 100%;
  min-height: 100dvh;
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 110px clamp(24px, 6vw, 96px) 60px;
  max-width: 640px;
  justify-self: center;
}

.hero-eyebrow {
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  color: var(--land-accent-ink);
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(47, 115, 196, 0.08);
  padding: 6px 16px 6px 12px;
  border-radius: 40px;
  border: 1px solid rgba(47, 115, 196, 0.15);
  width: fit-content;
  max-width: 100%;
}

.eyebrow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--land-accent);
  flex-shrink: 0;
  animation: dotPulse 2s ease-in-out infinite;
}

@keyframes dotPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.hero-headline {
  font-size: clamp(44px, 5.4vw, 84px);
  font-weight: 900;
  line-height: 1.02;
  letter-spacing: -0.04em;
  color: var(--cream-text);
}

.hero-headline .highlight {
  color: var(--land-accent);
  position: relative;
  display: inline-block;
}

.hero-headline .highlight::after {
  content: '';
  position: absolute;
  bottom: 4px;
  right: 0;
  width: 100%;
  height: 8px;
  background: rgba(47, 115, 196, 0.15);
  border-radius: 3px;
  z-index: -1;
}

.hero-sub {
  font-size: clamp(15px, 1.15vw, 19px);
  color: var(--cream-text-muted);
  line-height: 1.7;
  max-width: 480px;
}

.hero-cta-wrap {
  display: flex;
  gap: 14px;
  align-items: center;
  flex-wrap: wrap;
}

.hero-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--land-action);
  color: #fff;
  padding: 16px 40px;
  border-radius: 40px;
  font-size: 1.05rem;
  font-weight: 700;
  transition: all var(--transition-fast);
  min-height: 54px;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(24, 24, 24, 0.25);
}

.hero-btn:hover {
  background: var(--land-action-deep);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(24, 24, 24, 0.3);
}

.hero-btn svg {
  width: 18px;
  height: 18px;
  transition: transform var(--transition-fast);
}

.hero-btn:hover svg {
  transform: translateX(-4px);
}

/* Ghost CTA — cream/light styling to match hero background (no dark-on-cream) */
.hero-ghost {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: transparent;
  color: var(--cream-text);
  border: 1px solid rgba(45, 37, 34, 0.18);
  padding: 15px 28px;
  border-radius: 40px;
  font-size: 0.95rem;
  font-weight: 700;
  transition: all var(--transition-fast);
  min-height: 52px;
}

.hero-ghost:hover {
  background: rgba(24, 24, 24, 0.06);
  border-color: var(--land-action);
  color: var(--land-action);
}

.ghost-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(24, 24, 24, 0.08);
  color: var(--land-action);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.hero-ghost:hover .ghost-icon {
  background: var(--land-action);
  color: #fff;
}

/* ── Hero visual — price card ── */
.hero-visual {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  height: calc(100dvh - 24px);
  margin: 12px 0 12px 12px;
  border-radius: 28px;
  overflow: hidden;
  isolation: isolate;
  padding: 90px 24px 40px;
}
.pv-media { position: absolute; inset: 0; z-index: 0; }
.pricing a.site-legal { align-self: flex-start; font-size: 13px; color: var(--cream-text-muted); }
.pricing a.site-legal:hover { color: var(--cream-text); text-decoration: underline; }

.price-card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(22px) saturate(1.3);
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 28px;
  padding: 36px 32px 32px;
  box-shadow:
    0 40px 80px -20px rgba(45, 37, 34, 0.18),
    0 0 0 1px rgba(47, 115, 196, 0.08),
    0 2px 0 rgba(47, 115, 196, 0.04) inset;
  position: relative;
  z-index: 2;
}

.price-card::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 30px;
  background: linear-gradient(135deg, rgba(47, 115, 196, 0.2), transparent 60%);
  z-index: -1;
  pointer-events: none;
}

.pc-name {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--cream-text);
  letter-spacing: -0.2px;
}

.pc-price {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.pc-amount {
  font-size: clamp(72px, 9vw, 108px);
  font-weight: 900;
  line-height: 0.95;
  color: var(--cream-text);
  letter-spacing: -3px;
  background: linear-gradient(135deg, var(--cream-text) 0%, var(--land-accent) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.pc-unit {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-bottom: 14px;
}

.pc-currency {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--cream-text);
  line-height: 1;
}

.pc-period {
  font-size: 0.95rem;
  color: var(--cream-text-muted);
}

.pc-vat {
  margin-top: 10px;
  font-size: 0.78rem;
  color: var(--cream-text-dim);
  letter-spacing: 0.02em;
}

.pc-bullets {
  list-style: none;
  margin: 22px 0 0;
  padding: 22px 0 0;
  border-top: 1px solid rgba(45, 37, 34, 0.06);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pc-bullets li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.94rem;
  color: var(--cream-text);
  font-weight: 500;
}

.pc-bullets svg {
  color: var(--land-accent);
  flex-shrink: 0;
}

/* ── Responsive ── */
@media (max-width: 1024px) {
  .hero-inner {
    grid-template-columns: 1fr;
    gap: 32px;
  }

  .hero-content {
    padding: 120px 0 20px;
    max-width: 100%;
    text-align: start;
    margin-inline: auto;
  }

  .hero-visual {
    height: auto;
    min-height: 560px;
    margin: 0 12px 24px;
    padding: 48px 20px;
  }
}

@media (max-width: 768px) {
  .chapter-hero {
    padding-left: 20px;
    padding-right: 20px;
  }

  .price-card {
    padding: 28px 24px 24px;
  }

  .hero-btn {
    padding: 14px 28px;
    font-size: 0.98rem;
  }
}

@media (max-width: 480px) {
  .hero-cta-wrap {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-btn,
  .hero-ghost {
    width: 100%;
    justify-content: center;
  }
}
</style>
