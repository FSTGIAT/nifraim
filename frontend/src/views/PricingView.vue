<template>
  <div class="pricing" ref="pricingRoot">
    <!-- Nav -->
    <nav class="land-nav" ref="landNav">
      <div class="nav-content">
        <router-link to="/" class="nav-brand">
          <div class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span class="nav-name">Nifraim</span>
        </router-link>
        <div class="nav-links">
          <router-link to="/">דף הבית</router-link>
          <router-link to="/pricing" class="active">תמחור</router-link>
          <router-link to="/login" class="nav-btn-ghost">התחברות</router-link>
          <router-link to="/signup" class="nav-btn-solid">התחל עכשיו</router-link>
        </div>

        <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen" aria-label="תפריט">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line v-if="!mobileMenuOpen" x1="3" y1="6" x2="21" y2="6"/>
            <line v-if="!mobileMenuOpen" x1="3" y1="12" x2="21" y2="12"/>
            <line v-if="!mobileMenuOpen" x1="3" y1="18" x2="21" y2="18"/>
            <line v-if="mobileMenuOpen" x1="18" y1="6" x2="6" y2="18"/>
            <line v-if="mobileMenuOpen" x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <Transition name="mobile-menu">
        <div v-if="mobileMenuOpen" class="mobile-menu">
          <router-link to="/" @click="mobileMenuOpen = false">דף הבית</router-link>
          <router-link to="/pricing" class="active" @click="mobileMenuOpen = false">תמחור</router-link>
          <router-link to="/login" class="nav-btn-ghost" @click="mobileMenuOpen = false">התחברות</router-link>
          <router-link to="/signup" class="nav-btn-solid" @click="mobileMenuOpen = false">התחל עכשיו</router-link>
        </div>
      </Transition>
    </nav>

    <!-- HERO -->
    <section class="chapter-hero" ref="heroSection">
      <div class="hero-gradient">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
      </div>
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
        </div>

        <div class="hero-visual" ref="heroVisual">
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

const contactEmail = 'nifraim@nifraim.com'

const pricingRoot = ref(null)
const landNav = ref(null)
const heroSection = ref(null)
const heroContent = ref(null)
const heroEyebrow = ref(null)
const heroHeadline = ref(null)
const heroSub = ref(null)
const heroCtaWrap = ref(null)
const heroVisual = ref(null)
const priceCard = ref(null)
const priceNumber = ref(null)

const mobileMenuOpen = ref(false)

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

  // Nav always light (hero is cream)
  landNav.value?.classList.add('nav--light')

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

  gsap.to('.orb-1', { y: -40, x: 20, duration: 8, repeat: -1, yoyo: true, ease: 'sine.inOut' })
  gsap.to('.orb-2', { y: 30, x: -15, duration: 10, repeat: -1, yoyo: true, ease: 'sine.inOut' })
  gsap.to('.orb-3', { y: -20, x: 25, duration: 9, repeat: -1, yoyo: true, ease: 'sine.inOut' })
})

onBeforeUnmount(() => {
  gsap.killTweensOf([heroEyebrow.value, heroHeadline.value, heroSub.value, heroCtaWrap.value, priceCard.value])
  gsap.killTweensOf(['.orb-1', '.orb-2', '.orb-3'])
})
</script>

<style scoped>
/* ── Pricing Theme Variables (mirrors LandingView tokens) ── */
.pricing {
  --land-bg: #4A4A4A;
  --land-orange: #E8660A;
  --land-orange-bright: #F57C00;
  --land-orange-deep: #C85A00;
  --land-orange-glow: rgba(232, 102, 10, 0.1);
  --land-text: #F5F5F5;
  --land-text-secondary: #A0A0A0;
  --land-border: #666666;

  --cream-bg: #F5F0EB;
  --cream-text: #2D2522;
  --cream-text-muted: rgba(45, 37, 34, 0.6);
  --cream-text-dim: rgba(45, 37, 34, 0.35);
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

.pricing a {
  color: inherit;
  text-decoration: none;
}

/* ── Navigation ── */
.land-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(74, 74, 74, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--land-border);
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.land-nav.nav--light {
  background: rgba(245, 240, 235, 0.9);
  border-bottom-color: rgba(45, 37, 34, 0.06);
}

.land-nav.nav--light .nav-name { color: var(--cream-text); }
.land-nav.nav--light .nav-icon { background: var(--cream-text); color: var(--cream-bg); }
.land-nav.nav--light .nav-links a { color: var(--cream-text-muted); }
.land-nav.nav--light .nav-links a:hover,
.land-nav.nav--light .nav-links a.active { color: var(--land-orange); }
.land-nav.nav--light .nav-btn-ghost {
  border-color: var(--cream-text) !important;
  color: var(--cream-text) !important;
}
.land-nav.nav--light .nav-btn-ghost:hover { background: rgba(45, 37, 34, 0.05) !important; }
.land-nav.nav--light .nav-btn-solid {
  background: var(--cream-text) !important;
  color: var(--cream-bg) !important;
}
.land-nav.nav--light .nav-btn-solid:hover { background: var(--dark-section) !important; }
.land-nav.nav--light .mobile-menu-btn { color: var(--cream-text); }

.nav-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-icon {
  width: 40px;
  height: 40px;
  background: var(--land-orange);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0a0a0a;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.nav-name {
  font-size: 22px;
  font-weight: 800;
  color: var(--land-text);
  transition: color var(--transition-fast);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-links a {
  font-size: 15px;
  font-weight: 500;
  color: var(--land-text-secondary);
  transition: color 0.2s;
}

.nav-links a:hover,
.nav-links a.active { color: var(--land-orange); }

.nav-btn-ghost {
  padding: 10px 24px;
  border-radius: 10px;
  border: 1px solid var(--land-orange) !important;
  color: var(--land-orange) !important;
  font-weight: 600 !important;
  transition: all 0.2s;
}

.nav-btn-ghost:hover { background: var(--land-orange-glow) !important; }

.nav-btn-solid {
  padding: 10px 24px;
  border-radius: 10px;
  background: var(--land-orange) !important;
  color: #0a0a0a !important;
  font-weight: 700 !important;
  transition: all 0.2s;
}

.nav-btn-solid:hover { background: var(--land-orange-bright) !important; }

.mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  color: var(--land-text);
  cursor: pointer;
  padding: 8px;
  transition: color var(--transition-fast);
}

.mobile-menu {
  display: none;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  border-top: 1px solid var(--land-border);
  background: rgba(74, 74, 74, 0.95);
}

.land-nav.nav--light .mobile-menu {
  background: rgba(245, 240, 235, 0.97);
  border-top-color: rgba(45, 37, 34, 0.06);
}

.mobile-menu a {
  font-size: 16px;
  font-weight: 500;
  color: var(--land-text-secondary);
  padding: 8px 0;
}

.mobile-menu-enter-active,
.mobile-menu-leave-active { transition: all 0.3s ease; }

.mobile-menu-enter-from,
.mobile-menu-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ── HERO (cream) ── */
.chapter-hero {
  position: relative;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  overflow: hidden;
  background: var(--cream-bg);
}

.hero-gradient {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.hero-gradient .orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  will-change: transform;
}

.hero-gradient .orb-1 {
  width: 720px;
  height: 720px;
  background: rgba(232, 102, 10, 0.28);
  top: -18%;
  left: -10%;
}

.hero-gradient .orb-2 {
  width: 520px;
  height: 520px;
  background: rgba(232, 102, 10, 0.22);
  bottom: 2%;
  right: -6%;
}

.hero-gradient .orb-3 {
  width: 460px;
  height: 460px;
  background: rgba(245, 124, 0, 0.2);
  top: 38%;
  left: 42%;
}

.hero-inner {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  width: 100%;
  min-height: 100dvh;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 32px;
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 110px 24px 80px 0;
  max-width: 560px;
}

.hero-eyebrow {
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  color: var(--land-orange);
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(232, 102, 10, 0.08);
  padding: 6px 16px 6px 12px;
  border-radius: 40px;
  border: 1px solid rgba(232, 102, 10, 0.15);
  width: fit-content;
  max-width: 100%;
}

.eyebrow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--land-orange);
  flex-shrink: 0;
  animation: dotPulse 2s ease-in-out infinite;
}

@keyframes dotPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.hero-headline {
  font-size: clamp(40px, 5.5vw, 72px);
  font-weight: 900;
  line-height: 1.08;
  letter-spacing: -1px;
  color: var(--cream-text);
}

.hero-headline .highlight {
  color: var(--land-orange);
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
  background: rgba(232, 102, 10, 0.15);
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
  background: var(--land-orange);
  color: #fff;
  padding: 16px 40px;
  border-radius: 40px;
  font-size: 1.05rem;
  font-weight: 700;
  transition: all var(--transition-fast);
  min-height: 54px;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(232, 102, 10, 0.25);
}

.hero-btn:hover {
  background: var(--land-orange-deep);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(232, 102, 10, 0.3);
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
  background: rgba(232, 102, 10, 0.06);
  border-color: var(--land-orange);
  color: var(--land-orange);
}

.ghost-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--land-orange-glow);
  color: var(--land-orange);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.hero-ghost:hover .ghost-icon {
  background: var(--land-orange);
  color: #fff;
}

/* ── Hero visual — price card ── */
.hero-visual {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100dvh;
  padding: 110px 20px 80px;
}

.price-card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 28px;
  padding: 36px 32px 32px;
  box-shadow:
    0 40px 80px -20px rgba(45, 37, 34, 0.18),
    0 0 0 1px rgba(232, 102, 10, 0.08),
    0 2px 0 rgba(232, 102, 10, 0.04) inset;
  position: relative;
  z-index: 2;
}

.price-card::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 30px;
  background: linear-gradient(135deg, rgba(232, 102, 10, 0.2), transparent 60%);
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
  background: linear-gradient(135deg, var(--cream-text) 0%, var(--land-orange) 100%);
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
  color: var(--land-orange);
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
    min-height: auto;
    padding: 0 0 100px;
  }
}

@media (max-width: 768px) {
  .nav-links { display: none; }
  .mobile-menu-btn { display: block; }
  .mobile-menu { display: flex; }

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
