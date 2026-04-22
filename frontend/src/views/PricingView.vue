<template>
  <div class="pricing-page">
    <!-- Nav -->
    <nav class="land-nav">
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
          <router-link to="/login" class="nav-btn-ghost" @click="mobileMenuOpen = false">התחברות</router-link>
          <router-link to="/signup" class="nav-btn-solid" @click="mobileMenuOpen = false">התחל עכשיו</router-link>
        </div>
      </Transition>
    </nav>

    <!-- Hero -->
    <section class="pricing-hero">
      <div class="hero-glow"></div>
      <h1><span class="text-orange">תמחור</span></h1>
    </section>

    <!-- Plans -->
    <section class="plans-section" ref="plansSection">
      <div class="plans">
        <div class="plan-card featured" :class="{ visible: plansVisible }" style="--delay: 0.1s">
          <div class="plan-name">חודשי</div>
          <div class="plan-price">
            <span class="price-amount ltr-number">{{ formattedMonthly }}</span>
            <span class="price-currency">₪</span>
            <span class="price-period">/ חודש</span>
          </div>
          <ul class="plan-features">
            <li v-for="(f, i) in planFeatures" :key="f" :style="{ '--fi': i }">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="check-icon">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ f }}
            </li>
          </ul>
          <router-link to="/signup?plan=monthly" class="plan-btn primary">בחירת מסלול</router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const mobileMenuOpen = ref(false)
const plansSection = ref(null)
const plansVisible = ref(false)
const monthlyPrice = ref(0)
const pricesAnimated = ref(false)

const formattedMonthly = computed(() => monthlyPrice.value)

const planFeatures = [
  'העלאת קבצי פרודוקציה ללא הגבלה',
  'השוואת נפרעים מכל חברות הביטוח',
  'זיהוי אוטומטי של 7+ פורמטים',
  'ניהול טבלת עמלות',
  'שליחת בירורים במייל',
  'תמיכה טכנית מלאה',
]

function animatePrice(targetRef, finalValue, duration = 1200) {
  const start = performance.now()
  const tick = (now) => {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    targetRef.value = Math.round(eased * finalValue)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

let observer = null

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && entry.target === plansSection.value) {
          plansVisible.value = true
          if (!pricesAnimated.value) {
            pricesAnimated.value = true
            setTimeout(() => {
              animatePrice(monthlyPrice, 220, 1200)
            }, 300)
          }
          observer.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.15 }
  )

  if (plansSection.value) observer.observe(plansSection.value)
})

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
})
</script>

<style scoped>
/* ── Theme Variables ── */
.pricing-page {
  --land-bg: #4A4A4A;
  --land-bg-alt: #555555;
  --land-bg-card: #5C5C5C;
  --land-orange: #F57C00;
  --land-orange-bright: #FF9800;
  --land-orange-deep: #E65100;
  --land-orange-glow: rgba(245, 124, 0, 0.15);
  --land-text: #F5F5F5;
  --land-text-secondary: #A0A0A0;
  --land-text-dim: #666666;
  --land-border: #666666;
  --land-border-hover: #777777;

  min-height: 100vh;
  background: var(--land-bg);
  color: var(--land-text);
  font-family: 'Heebo', sans-serif;
  direction: rtl;
  overflow-x: hidden;
}

.pricing-page a {
  color: inherit;
  text-decoration: none;
}

.text-orange {
  color: var(--land-orange);
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
}

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
}

.nav-name {
  font-size: 22px;
  font-weight: 800;
  color: var(--land-text);
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

.nav-links a:hover {
  color: var(--land-orange);
}

.nav-btn-ghost {
  padding: 10px 24px;
  border-radius: 10px;
  border: 1px solid var(--land-orange) !important;
  color: var(--land-orange) !important;
  font-weight: 600 !important;
  transition: all 0.2s;
}

.nav-btn-ghost:hover {
  background: var(--land-orange-glow) !important;
}

.nav-btn-solid {
  padding: 10px 24px;
  border-radius: 10px;
  background: var(--land-orange) !important;
  color: #0a0a0a !important;
  font-weight: 700 !important;
  transition: all 0.2s;
}

.nav-btn-solid:hover {
  background: var(--land-orange-bright) !important;
}

/* Mobile menu button */
.mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  color: var(--land-text);
  cursor: pointer;
  padding: 8px;
}

/* Mobile menu */
.mobile-menu {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  border-top: 1px solid var(--land-border);
  background: rgba(74, 74, 74, 0.95);
}

.mobile-menu a {
  font-size: 16px;
  font-weight: 500;
  color: var(--land-text-secondary);
  padding: 8px 0;
}

.mobile-menu-enter-active,
.mobile-menu-leave-active {
  transition: all 0.3s ease;
}

.mobile-menu-enter-from,
.mobile-menu-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ── Hero Section ── */
.pricing-hero {
  padding: 180px 24px 80px;
  text-align: center;
  position: relative;
}

.hero-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(245, 124, 0, 0.08) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
  animation: glowPulse 4s ease-in-out infinite;
}

.pricing-hero h1 {
  font-size: 80px;
  font-weight: 900;
  line-height: 1.1;
  position: relative;
  z-index: 1;
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

/* ── Plans Section ── */
.plans-section {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 24px 120px;
}

.plans {
  display: flex;
  justify-content: center;
}

.plan-card {
  width: 100%;
  max-width: 420px;
  background: var(--land-bg-alt);
  border: 1px solid var(--land-border);
  border-radius: 20px;
  padding: 44px 32px;
  position: relative;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.plan-card.visible {
  opacity: 1;
  transform: translateY(0);
  transition-delay: var(--delay, 0s);
}

.plan-card:hover {
  transform: translateY(-6px);
  border-color: var(--land-border-hover);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}

.plan-card.visible:hover {
  transition-delay: 0s;
}

/* Featured card glow */
.plan-card.featured {
  border-color: var(--land-orange);
  box-shadow: 0 0 0 1px var(--land-orange), 0 0 40px rgba(245, 124, 0, 0.08);
}

.plan-card.featured::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.15), transparent 60%);
  z-index: 0;
  animation: pulseGlow 3s ease-in-out infinite;
  pointer-events: none;
}

.plan-card.featured:hover {
  box-shadow: 0 0 0 1px var(--land-orange), 0 24px 64px rgba(245, 124, 0, 0.15);
}

.plan-badge {
  position: absolute;
  top: -14px;
  right: 24px;
  padding: 6px 20px;
  background: linear-gradient(135deg, var(--land-orange) 0%, var(--land-orange-bright) 100%);
  color: #0a0a0a;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 700;
  z-index: 1;
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.3);
  background-size: 200% 100%;
  animation: shimmer 3s ease-in-out infinite;
}

.plan-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--land-text);
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.plan-price {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 8px;
  position: relative;
  z-index: 1;
}

.price-amount {
  font-size: 60px;
  font-weight: 900;
  color: var(--land-text);
  line-height: 1;
}

.plan-card.featured .price-amount {
  color: var(--land-orange);
}

.price-currency {
  font-size: 26px;
  font-weight: 700;
  color: var(--land-text-secondary);
}

.price-period {
  font-size: 16px;
  color: var(--land-text-dim);
}

.plan-savings {
  display: inline-block;
  padding: 5px 14px;
  background: rgba(76, 175, 80, 0.12);
  color: #4caf50;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
}

.plan-features {
  list-style: none;
  margin: 28px 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: relative;
  z-index: 1;
}

.plan-features li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  color: var(--land-text-secondary);
  opacity: 0;
  transform: translateY(10px);
}

.plan-card.visible .plan-features li {
  animation: fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: calc(var(--fi) * 0.08s + 0.4s);
}

.check-icon {
  color: var(--land-orange);
  flex-shrink: 0;
}

.plan-btn {
  display: block;
  text-align: center;
  padding: 15px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 700;
  border: 1px solid var(--land-border);
  color: var(--land-text);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  z-index: 1;
}

.plan-btn:hover {
  border-color: var(--land-orange);
  color: var(--land-orange);
  transform: translateY(-2px);
}

.plan-btn.primary {
  background: var(--land-orange);
  color: #0a0a0a;
  border: none;
}

.plan-btn.primary:hover {
  background: var(--land-orange-bright);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(245, 124, 0, 0.3);
}

/* ── Animations ── */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulseGlow {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.6; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.05); }
}

@keyframes shimmer {
  0% { background-position: 200% center; }
  50% { background-position: -200% center; }
  100% { background-position: 200% center; }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .nav-links {
    display: none;
  }

  .mobile-menu-btn {
    display: block;
  }

  .mobile-menu {
    display: flex;
  }

  .pricing-hero {
    padding: 140px 24px 60px;
  }

  .pricing-hero h1 {
    font-size: 52px;
  }

  .plans {
    display: flex;
  }
}

@media (max-width: 480px) {
  .pricing-hero h1 {
    font-size: 42px;
  }

  .price-amount {
    font-size: 48px;
  }
}
</style>
