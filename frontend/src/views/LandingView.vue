<template>
  <div class="landing">
    <!-- Nav -->
    <nav class="land-nav">
      <div class="nav-content">
        <div class="nav-brand">
          <div class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span class="nav-name">Nifraim</span>
        </div>
        <div class="nav-links">
          <a href="#features">תכונות</a>
          <router-link to="/pricing">תמחור</router-link>
          <router-link to="/login" class="nav-btn-ghost">התחברות</router-link>
          <router-link to="/signup" class="nav-btn-solid">התחל עכשיו</router-link>
        </div>

        <!-- Mobile menu button -->
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

      <!-- Mobile menu -->
      <Transition name="mobile-menu">
        <div v-if="mobileMenuOpen" class="mobile-menu">
          <a href="#features" @click="mobileMenuOpen = false">תכונות</a>
          <router-link to="/pricing" @click="mobileMenuOpen = false">תמחור</router-link>
          <router-link to="/login" class="nav-btn-ghost" @click="mobileMenuOpen = false">התחברות</router-link>
          <router-link to="/signup" class="nav-btn-solid" @click="mobileMenuOpen = false">התחל עכשיו</router-link>
        </div>
      </Transition>
    </nav>

    <!-- Floating circles -->
    <div class="float-circle float-circle-1"></div>
    <div class="float-circle float-circle-2"></div>
    <div class="float-circle float-circle-3"></div>
    <div class="float-circle float-circle-4"></div>
    <div class="float-circle float-circle-5"></div>

    <!-- Hero Slider -->
    <section class="hero-slider" @mouseenter="pauseSlider" @mouseleave="resumeSlider">
      <div class="slider-track" :style="{ transform: `translateX(${currentSlide * -100}%)` }">
        <!-- Slide 1: Bold Statement -->
        <div class="slide slide-1">
          <div class="slide-glow"></div>
          <div class="slide-content">
            <h1 class="hero-headline">ניהול עמלות.<br><span class="text-orange">חכם.</span></h1>
            <p class="hero-subtitle">העלו קבצים, השוו נתונים, גלו פערים — תוך שניות</p>
            <router-link to="/signup" class="btn-primary">התחל עכשיו</router-link>
          </div>
        </div>

        <!-- Slide 2: Numbers Impact -->
        <div class="slide slide-2">
          <div class="slide-grid-bg"></div>
          <div class="slide-content">
            <div class="impact-number ltr-number">
              <span class="big-num">{{ currentSlide === 1 ? animatedPercent : 95 }}%</span>
              <span class="big-label">חיסכון בזמן</span>
            </div>
            <div class="impact-row">
              <div class="impact-item">
                <span class="impact-val ltr-number">7+</span>
                <span class="impact-lbl">פורמטים</span>
              </div>
              <div class="impact-divider"></div>
              <div class="impact-item">
                <span class="impact-val">דיוק מלא</span>
                <span class="impact-lbl">בהשוואה</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Slide 3: How It's Different -->
        <div class="slide slide-3">
          <div class="slide-content">
            <h2 class="slide-title">לא עוד בדיקות ידניות</h2>
            <div class="flow-steps">
              <div class="flow-step">
                <div class="flow-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </div>
                <span>העלאה</span>
              </div>
              <div class="flow-line"></div>
              <div class="flow-step">
                <div class="flow-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                  </svg>
                </div>
                <span>השוואה</span>
              </div>
              <div class="flow-line"></div>
              <div class="flow-step">
                <div class="flow-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12.01" y2="8"/>
                  </svg>
                </div>
                <span>תובנות</span>
              </div>
            </div>
            <a href="#how-it-works" class="btn-secondary">צפו איך זה עובד</a>
          </div>
        </div>
      </div>

      <!-- Slider dots -->
      <div class="slider-dots">
        <button
          v-for="i in 3"
          :key="i"
          class="dot"
          :class="{ active: currentSlide === i - 1 }"
          @click="goToSlide(i - 1)"
          :aria-label="'שקופית ' + i"
        ></button>
      </div>
    </section>

    <!-- Features -->
    <section id="features" class="features">
      <div class="section-wrap">
        <h2 class="section-title">למה <span class="text-orange">Nifraim</span> ?</h2>
        <div class="features-grid">
          <div class="feature-block" v-for="(f, i) in features" :key="i">
            <span class="feature-num ltr-number">{{ String(i + 1).padStart(2, '0') }}</span>
            <h3>{{ f.title }}</h3>
            <p>{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- How It Works -->
    <section id="how-it-works" class="how-section">
      <div class="section-wrap">
        <h2 class="section-title">איך זה <span class="text-orange">עובד</span> ?</h2>
        <div class="timeline">
          <div class="timeline-step" v-for="(s, i) in steps" :key="i">
            <div class="timeline-circle ltr-number">{{ i + 1 }}</div>
            <h3>{{ s.title }}</h3>
            <p>{{ s.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Numbers Strip -->
    <section class="numbers-strip" ref="numbersSection">
      <div class="section-wrap">
        <div class="numbers-grid">
          <div class="number-block" v-for="(n, i) in numbers" :key="i">
            <span class="number-val ltr-number">{{ numbersVisible ? n.animated.value : '0' }}{{ n.suffix }}</span>
            <span class="number-label">{{ n.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="cta-glow"></div>
      <div class="section-wrap">
        <h2 class="cta-title">מוכנים להתחיל?</h2>
        <router-link to="/signup" class="btn-primary btn-large">התחל עכשיו</router-link>
      </div>
    </section>

    <!-- Footer -->
    <footer class="land-footer">
      <div class="footer-wrap">
        <div class="footer-brand">
          <div class="nav-icon small">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span>Nifraim</span>
        </div>
        <p class="footer-tagline">מערכת ניהול עמלות מתקדמת</p>
        <div class="footer-links">
          <router-link to="/pricing">תמחור</router-link>
          <router-link to="/login">התחברות</router-link>
        </div>
        <p class="footer-copy ltr-number">&copy; 2026 Nifraim</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, reactive } from 'vue'

// Mobile menu
const mobileMenuOpen = ref(false)

// Slider
const currentSlide = ref(0)
let sliderInterval = null
const SLIDE_COUNT = 3
const SLIDE_DELAY = 5000

function goToSlide(index) {
  currentSlide.value = index
}

function nextSlide() {
  currentSlide.value = (currentSlide.value + 1) % SLIDE_COUNT
}

function pauseSlider() {
  if (sliderInterval) {
    clearInterval(sliderInterval)
    sliderInterval = null
  }
}

function resumeSlider() {
  if (!sliderInterval) {
    sliderInterval = setInterval(nextSlide, SLIDE_DELAY)
  }
}

// Slide 2 animated percent
const animatedPercent = ref(0)
function animatePercent() {
  const duration = 1200
  const start = performance.now()
  function tick(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedPercent.value = Math.round(95 * eased)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

// Features data
const features = [
  {
    title: 'זיהוי אוטומטי',
    desc: 'המערכת מזהה פורמטים מ-7+ חברות שונות, כולל קבצים מוגני סיסמא.',
  },
  {
    title: 'השוואה מדויקת',
    desc: 'התאמה אוטומטית בין פרודוקציה לנפרעים. זיהוי פערים וחסרים.',
  },
  {
    title: 'תוצאות מיידיות',
    desc: 'מה שלקח שעות — לוקח שניות. העלו קבצים וקבלו תשובות.',
  },
]

// Steps data
const steps = [
  { title: 'העלו קבצים', desc: 'גררו את הקבצים אל המערכת. זיהוי אוטומטי של הפורמט.' },
  { title: 'השוו נתונים', desc: 'המערכת מתאימה רשומות לפי ת.ז. ומספר פוליסה.' },
  { title: 'קבלו תובנות', desc: 'מי שולם, מי לא, היכן יש פערים — הכל במבט אחד.' },
]

// Numbers section
const numbersSection = ref(null)
const numbersVisible = ref(false)

function animateCounter(target, finalValue, duration = 1500) {
  const start = performance.now()
  function tick(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    target.value = Math.round(finalValue * eased).toLocaleString()
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

const numbers = reactive([
  { animated: ref('0'), suffix: '+', label: 'קבצים עובדו', final: 1000 },
  { animated: ref('0'), suffix: '+', label: 'חברות נתמכות', final: 50 },
  { animated: ref('0'), suffix: '%', label: 'חיסכון בזמן', final: 95 },
])

let numbersObserver = null

onMounted(() => {
  // Start slider
  sliderInterval = setInterval(nextSlide, SLIDE_DELAY)

  // Animate slide 2 percent on first visit
  setTimeout(animatePercent, 600)

  // Intersection observer for numbers
  numbersObserver = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && !numbersVisible.value) {
        numbersVisible.value = true
        numbers.forEach((n) => {
          animateCounter(n.animated, n.final)
        })
      }
    },
    { threshold: 0.3 }
  )
  if (numbersSection.value) {
    numbersObserver.observe(numbersSection.value)
  }
})

onBeforeUnmount(() => {
  pauseSlider()
  if (numbersObserver) numbersObserver.disconnect()
})
</script>

<style scoped>
/* ── Landing Theme Variables ── */
.landing {
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

.landing a {
  color: inherit;
  text-decoration: none;
}

.text-orange {
  color: var(--land-orange);
}

.section-wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
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

.nav-icon.small {
  width: 32px;
  height: 32px;
  border-radius: 8px;
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
  display: none;
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

/* ── Hero Slider ── */
.hero-slider {
  position: relative;
  height: 100vh;
  min-height: 600px;
  overflow: hidden;
  padding-top: 72px;
}

.slider-track {
  display: flex;
  flex-direction: row;
  direction: ltr;
  height: 100%;
  transition: transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide {
  min-width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  text-align: center;
  direction: rtl;
}

.slide-content {
  position: relative;
  z-index: 2;
  max-width: 800px;
  padding: 0 24px;
}

/* Slide 1 */
.slide-1 .slide-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(245, 124, 0, 0.12) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}

.hero-headline {
  font-size: 80px;
  font-weight: 900;
  line-height: 1.1;
  margin-bottom: 24px;
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.hero-subtitle {
  font-size: 22px;
  font-weight: 400;
  color: var(--land-text-secondary);
  margin-bottom: 40px;
  line-height: 1.6;
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.15s both;
}

/* Slide 2 */
.slide-2 .slide-grid-bg {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(245, 124, 0, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(245, 124, 0, 0.05) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}

.impact-number {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 48px;
}

.big-num {
  font-size: 140px;
  font-weight: 900;
  color: var(--land-orange);
  line-height: 1;
  letter-spacing: -4px;
}

.big-label {
  font-size: 28px;
  font-weight: 500;
  color: var(--land-text-secondary);
  margin-top: 8px;
}

.impact-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 40px;
}

.impact-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.impact-val {
  font-size: 32px;
  font-weight: 800;
  color: var(--land-orange);
}

.impact-lbl {
  font-size: 16px;
  color: var(--land-text-secondary);
}

.impact-divider {
  width: 1px;
  height: 48px;
  background: var(--land-border);
}

/* Slide 3 */
.slide-title {
  font-size: 56px;
  font-weight: 900;
  margin-bottom: 56px;
}

.flow-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 48px;
}

.flow-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.flow-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 2px solid var(--land-orange);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--land-orange);
}

.flow-step span {
  font-size: 18px;
  font-weight: 600;
  color: var(--land-text);
}

.flow-line {
  width: 80px;
  height: 2px;
  background: var(--land-orange);
  opacity: 0.4;
  margin-bottom: 32px;
}

/* Buttons */
.btn-primary {
  display: inline-block;
  padding: 16px 40px;
  background: var(--land-orange);
  color: #0a0a0a !important;
  border-radius: 12px;
  font-size: 18px;
  font-weight: 700;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  border: none;
  cursor: pointer;
}

.btn-primary:hover {
  background: var(--land-orange-bright);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(245, 124, 0, 0.3);
}

.btn-primary.btn-large {
  padding: 20px 56px;
  font-size: 22px;
  border-radius: 14px;
}

.btn-secondary {
  display: inline-block;
  padding: 14px 36px;
  border: 1px solid var(--land-orange);
  color: var(--land-orange) !important;
  border-radius: 12px;
  font-size: 17px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: var(--land-orange-glow);
}

/* Slider dots */
.slider-dots {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 12px;
  z-index: 10;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--land-text-dim);
  border: none;
  cursor: pointer;
  transition: all 0.3s;
  padding: 0;
}

.dot.active {
  background: var(--land-orange);
  box-shadow: 0 0 12px rgba(245, 124, 0, 0.5);
}

.dot:hover:not(.active) {
  background: var(--land-text-secondary);
}

/* ── Features ── */
.features {
  padding: 120px 24px;
  background: var(--land-bg-alt);
}

.section-title {
  font-size: 52px;
  font-weight: 800;
  text-align: center;
  margin-bottom: 72px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 48px;
}

.feature-block {
  padding: 40px 32px;
  border-bottom: 2px solid var(--land-border);
  transition: border-color 0.3s;
}

.feature-block:hover {
  border-color: var(--land-orange);
}

.feature-num {
  display: block;
  font-size: 48px;
  font-weight: 900;
  color: var(--land-orange);
  margin-bottom: 20px;
  opacity: 0.6;
}

.feature-block h3 {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--land-text);
}

.feature-block p {
  font-size: 17px;
  color: var(--land-text-secondary);
  line-height: 1.7;
}

/* ── How It Works ── */
.how-section {
  padding: 120px 24px;
  background: var(--land-bg);
}

.timeline {
  display: flex;
  justify-content: center;
  gap: 80px;
  position: relative;
}

.timeline::before {
  content: '';
  position: absolute;
  top: 32px;
  right: calc(50% - 300px);
  width: 600px;
  height: 2px;
  background: linear-gradient(to left, var(--land-orange), rgba(245, 124, 0, 0.2));
}

.timeline-step {
  text-align: center;
  position: relative;
  z-index: 1;
  max-width: 240px;
}

.timeline-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 2px solid var(--land-orange);
  background: var(--land-bg);
  color: var(--land-orange);
  font-size: 28px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}

.timeline-step h3 {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--land-text);
}

.timeline-step p {
  font-size: 16px;
  color: var(--land-text-secondary);
  line-height: 1.6;
}

/* ── Numbers Strip ── */
.numbers-strip {
  padding: 100px 24px;
  background: var(--land-bg-card);
}

.numbers-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 40px;
  text-align: center;
}

.number-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.number-val {
  font-size: 72px;
  font-weight: 900;
  color: var(--land-orange);
  line-height: 1;
}

.number-label {
  font-size: 18px;
  font-weight: 500;
  color: var(--land-text-secondary);
}

/* ── CTA ── */
.cta-section {
  padding: 140px 24px;
  text-align: center;
  position: relative;
  background: var(--land-bg);
}

.cta-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(245, 124, 0, 0.08) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}

.cta-title {
  font-size: 64px;
  font-weight: 900;
  margin-bottom: 48px;
  position: relative;
  z-index: 1;
}

.cta-section .btn-primary {
  position: relative;
  z-index: 1;
}

/* ── Footer ── */
.land-footer {
  padding: 48px 24px;
  border-top: 1px solid var(--land-border);
  background: var(--land-bg);
}

.footer-wrap {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
}

.footer-tagline {
  font-size: 14px;
  color: var(--land-text-dim);
}

.footer-links {
  display: flex;
  gap: 24px;
}

.footer-links a {
  font-size: 14px;
  color: var(--land-text-secondary);
  transition: color 0.2s;
}

.footer-links a:hover {
  color: var(--land-orange);
}

.footer-copy {
  font-size: 13px;
  color: var(--land-text-dim);
}

/* ── Floating Circles ── */
.float-circle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.float-circle-1 {
  width: 260px;
  height: 260px;
  top: -60px;
  right: -80px;
  background: rgba(245, 124, 0, 0.04);
  border: 1px solid rgba(245, 124, 0, 0.06);
  animation: floatCircle 8s ease-in-out infinite;
}

.float-circle-2 {
  width: 180px;
  height: 180px;
  bottom: 120px;
  left: -50px;
  background: rgba(245, 124, 0, 0.03);
  border: 1px solid rgba(245, 124, 0, 0.05);
  animation: floatCircle 6s ease-in-out infinite reverse;
}

.float-circle-3 {
  width: 100px;
  height: 100px;
  top: 35%;
  left: 8%;
  background: rgba(245, 124, 0, 0.05);
  animation: floatCircle 10s ease-in-out infinite 2s;
}

.float-circle-4 {
  width: 140px;
  height: 140px;
  top: 60%;
  right: 5%;
  background: rgba(245, 124, 0, 0.03);
  border: 1px solid rgba(245, 124, 0, 0.04);
  animation: floatCircle 9s ease-in-out infinite 1s;
}

.float-circle-5 {
  width: 70px;
  height: 70px;
  top: 15%;
  left: 20%;
  background: rgba(245, 124, 0, 0.06);
  animation: floatCircle 7s ease-in-out infinite 3s reverse;
}

@keyframes floatCircle {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-18px) rotate(2deg); }
  66% { transform: translateY(10px) rotate(-1deg); }
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

  .hero-headline {
    font-size: 44px;
  }

  .hero-subtitle {
    font-size: 18px;
  }

  .big-num {
    font-size: 80px;
  }

  .big-label {
    font-size: 20px;
  }

  .impact-row {
    gap: 24px;
  }

  .impact-val {
    font-size: 24px;
  }

  .slide-title {
    font-size: 36px;
  }

  .flow-steps {
    flex-direction: column;
    gap: 16px;
  }

  .flow-line {
    width: 2px;
    height: 32px;
    margin-bottom: 0;
  }

  .section-title {
    font-size: 36px;
    margin-bottom: 48px;
  }

  .features-grid {
    grid-template-columns: 1fr;
    gap: 32px;
  }

  .timeline {
    flex-direction: column;
    align-items: center;
    gap: 40px;
  }

  .timeline::before {
    display: none;
  }

  .numbers-grid {
    grid-template-columns: 1fr;
    gap: 32px;
  }

  .number-val {
    font-size: 56px;
  }

  .cta-title {
    font-size: 40px;
  }

  .footer-wrap {
    flex-direction: column;
    text-align: center;
  }

  .float-circle-1 { width: 140px; height: 140px; }
  .float-circle-2 { width: 100px; height: 100px; }
  .float-circle-4 { display: none; }
  .float-circle-5 { display: none; }
}

@media (max-width: 480px) {
  .hero-headline {
    font-size: 36px;
  }

  .big-num {
    font-size: 64px;
  }

  .section-title {
    font-size: 30px;
  }

  .cta-title {
    font-size: 32px;
  }

  .btn-primary.btn-large {
    padding: 16px 40px;
    font-size: 18px;
  }
}
</style>
