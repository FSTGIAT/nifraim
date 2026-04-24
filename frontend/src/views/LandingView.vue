<template>
  <div class="landing" ref="landingRoot">
    <!-- Progress Bar -->
    <div class="progress-bar" ref="progressBar"></div>

    <!-- Grain overlay via CSS pseudo-element on .landing -->

    <!-- Nav -->
    <nav class="land-nav" ref="landNav">
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
          <a href="#how" @click.prevent="scrollToSection('how')">איך זה עובד</a>
          <a href="#features" @click.prevent="scrollToSection('features')">יכולות</a>
          <a href="#portal" @click.prevent="scrollToSection('portal')">פורטל לקוחות</a>
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
          <a href="#how" @click.prevent="scrollToSection('how')">איך זה עובד</a>
          <a href="#features" @click.prevent="scrollToSection('features')">יכולות</a>
          <a href="#portal" @click.prevent="scrollToSection('portal')">פורטל לקוחות</a>
          <router-link to="/pricing" @click="mobileMenuOpen = false">תמחור</router-link>
          <router-link to="/login" class="nav-btn-ghost" @click="mobileMenuOpen = false">התחברות</router-link>
          <router-link to="/signup" class="nav-btn-solid" @click="mobileMenuOpen = false">התחל עכשיו</router-link>
        </div>
      </Transition>
    </nav>

    <!-- ================================ -->
    <!-- CHAPTER 01: HERO — BENTO         -->
    <!-- ================================ -->
    <section class="chapter-hero" ref="heroSection">
      <div class="chapter-num" aria-hidden="true">01</div>
      <div class="hero-gradient">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
      </div>
      <div class="hero-inner">
        <div class="hero-content" ref="heroContent">
          <span class="hero-eyebrow" ref="heroEyebrow">
            <span class="eyebrow-dot"></span>
            מערכת AI לסוכני ביטוח
          </span>
          <h1 class="hero-headline" ref="heroHeadline">בדיקת עמלות נפרעים והקפים מבוסס <span class="highlight">AI</span></h1>
          <p class="hero-sub" ref="heroSub">העלו קבצים, השוו נתונים, גלו פערים - תוך שניות</p>
          <div class="hero-cta-wrap" ref="heroCtaWrap">
            <router-link to="/signup" class="hero-btn">
              התחל
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            </router-link>
            <a href="#how" class="hero-ghost" @click.prevent="scrollToSection('how')">
              <span class="ghost-play">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </span>
              איך זה עובד
            </a>
          </div>
          <div class="hero-stats-row" ref="heroStatsRow">
            <div class="hero-stat">
              <div class="hero-stat-num ltr-number">95%</div>
              <div class="hero-stat-label">חיסכון בזמן</div>
            </div>
            <div class="hero-stat-divider"></div>
            <div class="hero-stat">
              <div class="hero-stat-num ltr-number">3.2s</div>
              <div class="hero-stat-label">זמן עיבוד ממוצע</div>
            </div>
          </div>
          <!-- Trust strip removed -->
        </div>
        <div class="hero-visual" ref="heroVisual">
          <div class="hero-dashboard">
            <img src="/images/landing/success-man.jpg" alt="סוכן ביטוח מצליח עם Nifraim" width="768" height="1024" fetchpriority="high" decoding="async">
            <div class="hero-img-overlay"></div>
          </div>
          <!-- Floating stat cards -->
          <div class="float-card float-card-1" ref="floatCard1">
            <div class="fc-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <div class="fc-value ltr-number">₪54,300</div>
            <div class="fc-label">עמלות שנמצאו</div>
            <div class="fc-badge ltr-number">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M7 14l5-5 5 5H7z"/></svg>
              +12.5%
            </div>
          </div>
          <div class="float-card float-card-2" ref="floatCard2">
            <div class="fc-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            </div>
            <div class="fc-value ltr-number">3.2s</div>
            <div class="fc-label">זמן עיבוד ממוצע</div>
            <div class="fc-bar">
              <div class="fc-bar-fill"></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ================================ -->
    <!-- CHAPTER 02: PINNED STATS (dark)  -->
    <!-- ================================ -->
    <section class="chapter-stats chapter--dark" ref="chapterStats">
      <div class="chapter-num" aria-hidden="true">02</div>
      <div class="stats-wrapper" ref="statsWrapper">
        <div class="stat-slide" ref="stat1">
          <div class="stat-number"><span class="stat-accent ltr-number">0</span></div>
          <p class="stat-label">קבצים עובדו במערכת</p>
        </div>
        <div class="stat-slide" ref="stat2">
          <div class="stat-number"><span class="stat-accent ltr-number">0</span></div>
          <p class="stat-label">חברות ביטוח נתמכות</p>
        </div>
        <div class="stat-slide" ref="stat3">
          <div class="stat-number"><span class="stat-accent ltr-number">0</span></div>
          <p class="stat-label">חיסכון בזמן עבודה</p>
        </div>
        <div class="stats-conclusion" ref="statsConclusion">
          <h3>הכל אוטומטי.</h3>
          <span class="copper-line"></span>
        </div>
      </div>
    </section>

    <!-- ================================ -->
    <!-- CHAPTER 03: HOW IT WORKS (cream) -->
    <!-- ================================ -->
    <section class="chapter-how" id="how" ref="chapterHow">
      <div class="chapter-num" aria-hidden="true">03</div>
      <div class="how-header" ref="howHeader">
        <span class="how-label">איך זה עובד</span>
        <h2 class="how-title">שלושה צעדים פשוטים</h2>
      </div>
      <div class="how-steps">
        <div class="how-step" v-for="(s, i) in howSteps" :key="i" ref="howStepEls">
          <div v-if="i > 0" class="how-connector"></div>
          <div class="how-step-num ltr-number">{{ String(i + 1).padStart(2, '0') }}</div>
          <div class="how-step-icon" v-html="s.icon"></div>
          <h3>{{ s.title }}</h3>
          <p>{{ s.desc }}</p>
        </div>
      </div>
    </section>

    <!-- ================================ -->
    <!-- CHAPTER 04: FEATURES HORIZ (dark)-->
    <!-- ================================ -->
    <section class="chapter-features" id="features" ref="chapterFeatures">
      <div class="chapter-num" aria-hidden="true">04</div>
      <div class="features-header">
        <span class="features-label">יכולות המערכת</span>
        <h2 class="features-title">למה Nifraim?</h2>
      </div>
      <div class="features-track" ref="featuresTrack">
        <div class="feature-card" v-for="(f, i) in featureCards" :key="i">
          <div class="feature-card-bg">
            <img :src="f.image" :alt="f.title" loading="lazy" decoding="async" width="2752" height="1536">
          </div>
          <div class="feature-card-content">
            <div class="feature-card-number ltr-number">{{ f.num }}</div>
            <h3 class="feature-card-name">{{ f.title }}</h3>
            <p class="feature-card-desc">{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ================================ -->
    <!-- CHAPTER 05: PORTAL BENTO (cream) -->
    <!-- ================================ -->
    <section class="chapter-portal" id="portal" ref="chapterPortal">
      <div class="chapter-num" aria-hidden="true">05</div>
      <div class="portal-header">
        <span class="portal-label">פורטל לקוחות</span>
        <h2 class="portal-title">שתפו את תיק הביטוח</h2>
        <p class="portal-sub">חוויה מותאמת אישית, מאובטחת ומקצועית — הלקוחות שלכם רואים את הכל</p>
      </div>
      <div class="portal-grid">
        <!-- Featured card -->
        <div class="portal-card portal-card-featured" data-portal-card>
          <div>
            <div class="pc-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            </div>
            <h3>דשבורד אישי</h3>
            <p>מדדי KPI, גרפים וטבלאות — כל המידע במבט אחד. הלקוח רואה את התיק שלו בצורה ויזואלית ומסודרת.</p>
          </div>
          <div class="portal-card-img">
            <img src="/images/landing/hero-dashboard-v2.jpg" alt="דשבורד לקוח Nifraim" loading="lazy" decoding="async" width="2048" height="1152">
          </div>
        </div>

        <div class="portal-card" data-portal-card>
          <div class="pc-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
          </div>
          <h3>עוזר AI חכם</h3>
          <p>הלקוחות שואלים, הבינה המלאכותית עונה — על התיק שלהם</p>
        </div>

        <div class="portal-card" data-portal-card>
          <div class="pc-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
          </div>
          <h3>התראות שינויים</h3>
          <p>הלקוח מקבל התראה אוטומטית כשמשהו משתנה בתיק הביטוח</p>
        </div>

        <div class="portal-card" data-portal-card>
          <div class="pc-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </div>
          <h3>גישה מאובטחת</h3>
          <p>קישור ייחודי עם סיסמא, תוקף מוגבל והגנה מפני חדירה</p>
        </div>

        <div class="portal-card" data-portal-card>
          <div class="pc-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          </div>
          <h3>גרפים היסטוריים</h3>
          <p>מעקב פרמיה וצבירה לאורך זמן — תמונה ברורה</p>
        </div>

        <div class="portal-card" data-portal-card>
          <div class="pc-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
          </div>
          <h3>הדפסת דוחות</h3>
          <p>דוח מסודר של כל תיק הביטוח — מוכן להדפסה</p>
        </div>
      </div>
    </section>

    <!-- ================================ -->
    <!-- CHAPTER 06: CTA (dark)           -->
    <!-- ================================ -->
    <section class="chapter-cta chapter--dark" id="cta" ref="chapterCta">
      <div class="chapter-num" aria-hidden="true">06</div>
      <div class="cta-bg-visual">
        <img src="/images/landing/ai-network.jpg" alt="" aria-hidden="true" loading="lazy" decoding="async" width="2048" height="2048">
      </div>
      <div class="cta-overlay"></div>
      <div class="cta-content" ref="ctaContent">
        <h2 class="cta-headline">מוכנים <span>להתחיל?</span></h2>
        <p class="cta-sub">הצטרפו לעשרות סוכני ביטוח שכבר חוסכים שעות עבודה כל שבוע</p>
        <router-link to="/signup" class="cta-btn">התחל עכשיו</router-link>
      </div>
    </section>

    <!-- Footer -->
    <footer class="land-footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span class="fb-name">Nifraim</span>
          <span class="fb-tag">מערכת ניהול עמלות מתקדמת</span>
        </div>
        <div class="footer-links">
          <router-link to="/pricing">תמחור</router-link>
          <router-link to="/login">התחברות</router-link>
        </div>
        <p class="footer-copy ltr-number">&copy; 2026 Nifraim. כל הזכויות שמורות.</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

// Refs
const landingRoot = ref(null)
const landNav = ref(null)
const progressBar = ref(null)
const heroSection = ref(null)
const heroContent = ref(null)
const heroEyebrow = ref(null)
const heroHeadline = ref(null)
const heroSub = ref(null)
const heroCtaWrap = ref(null)
const heroStatsRow = ref(null)
const heroVisual = ref(null)
const floatCard1 = ref(null)
const floatCard2 = ref(null)
const heroTrust = ref(null)
const chapterStats = ref(null)
const statsWrapper = ref(null)
const stat1 = ref(null)
const stat2 = ref(null)
const stat3 = ref(null)
const statsConclusion = ref(null)
const chapterHow = ref(null)
const howHeader = ref(null)
const howStepEls = ref([])
const chapterFeatures = ref(null)
const featuresTrack = ref(null)
const chapterPortal = ref(null)
const chapterCta = ref(null)
const ctaContent = ref(null)

// Mobile menu
const mobileMenuOpen = ref(false)

// Motion preference — used to gate video autoplay + ScrollTrigger effects
const prefersReducedMotion = ref(
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches,
)

// Smooth scroll to anchor (native — CSS `scroll-behavior: smooth` handles the easing)
function scrollToSection(id) {
  const el = document.getElementById(id)
  if (!el) return
  const y = el.getBoundingClientRect().top + window.scrollY - 72
  window.scrollTo({ top: y, behavior: 'smooth' })
  mobileMenuOpen.value = false
}

// Data
const statData = [
  { target: 1000, suffix: '+' },
  { target: 50, suffix: '+' },
  { target: 95, suffix: '%' },
]

const howSteps = [
  {
    title: 'העלו קבצים',
    desc: 'גררו את הקבצים אל המערכת. זיהוי אוטומטי של הפורמט.',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>'
  },
  {
    title: 'השוו נתונים',
    desc: 'המערכת מתאימה רשומות לפי ת.ז. ומספר פוליסה. התאמה אוטומטית בין פרודוקציה לנפרעים.',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>'
  },
  {
    title: 'קבלו תובנות',
    desc: 'מי שולם, מי לא, היכן יש פערים — הכל במבט אחד. תוצאות מיידיות, ללא בדיקות ידניות.',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 118 2.83"/><path d="M22 12A10 10 0 0012 2v10z"/></svg>'
  },
]

const featureCards = [
  { num: 'יכולת 01', title: 'זיהוי אוטומטי', desc: 'המערכת מזהה פורמטים מחברות שונות באופן אוטומטי. ללא הגדרות מראש.', image: '/images/landing/ai-network.jpg' },
  { num: 'יכולת 02', title: 'השוואה מדויקת', desc: 'התאמה אוטומטית בין פרודוקציה לנפרעים. זיהוי פערים, חסרים ואי-התאמות בשניות.', image: '/images/landing/data-flow.jpg' },
  { num: 'יכולת 03', title: 'תוצאות מיידיות', desc: 'מה שלקח שעות — לוקח שניות. העלו קבצים וקבלו תשובות. ייצוא לאקסל בלחיצה.', image: '/images/landing/dashboard.jpg' },
  { num: 'יכולת 04', title: 'ניתוח AI חכם', desc: 'בינה מלאכותית שמבינה את הנתונים שלכם. שאלו שאלות — קבלו תובנות מהתיק.', image: '/images/landing/portal.jpg' },
]

// Scroll progress: rAF-throttled writer for a single CSS variable on the progress bar element
let scrollRafQueued = false
let progressBarEl = null
function updateProgressBar() {
  scrollRafQueued = false
  if (!progressBarEl) return
  const h = document.documentElement
  const max = h.scrollHeight - h.clientHeight
  const ratio = max > 0 ? h.scrollTop / max : 0
  progressBarEl.style.setProperty('--progress', ratio)
}
function onScrollThrottled() {
  if (scrollRafQueued) return
  scrollRafQueued = true
  requestAnimationFrame(updateProgressBar)
}

function animateStatCounter(el, target, suffix) {
  const obj = { val: 0 }
  gsap.to(obj, {
    val: target,
    duration: 1.5,
    ease: 'power2.out',
    onUpdate: () => {
      el.textContent = (target >= 100 ? Math.round(obj.val).toLocaleString() : Math.round(obj.val)) + suffix
    }
  })
}

onMounted(() => {
  const prefersReduced = prefersReducedMotion.value

  // Native smooth scroll — scoped to the landing page via a class on <html>
  document.documentElement.classList.add('landing-smooth')

  // Progress bar: single rAF-throttled listener, writes a CSS custom property
  progressBarEl = progressBar.value
  updateProgressBar()
  window.addEventListener('scroll', onScrollThrottled, { passive: true })

  // Nav starts light (hero is cream)
  landNav.value?.classList.add('nav--light')

  if (!prefersReduced) {
    // ---- CHAPTER 1: Hero Animations ----
    gsap.set([heroEyebrow.value, heroSub.value, heroCtaWrap.value, heroStatsRow.value], { opacity: 0, y: 20 })
    gsap.set(heroHeadline.value, { opacity: 0, y: 30 })
    gsap.set(heroVisual.value, { opacity: 0, clipPath: 'inset(0 100% 0 0)' })
    gsap.set([floatCard1.value, floatCard2.value], { opacity: 0, y: 30, scale: 0.9 })
    gsap.set(heroTrust.value, { opacity: 0, y: 15 })

    const heroTL = gsap.timeline({ delay: 0.3 })
    heroTL
      .to(heroEyebrow.value, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' })
      .to(heroHeadline.value, { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out' }, '-=0.3')
      .to(heroSub.value, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.3')
      .to(heroCtaWrap.value, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.2')
      .to(heroStatsRow.value, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.2')
      .to(heroVisual.value, { opacity: 1, clipPath: 'inset(0 0% 0 0)', duration: 1.2, ease: 'power3.inOut' }, '-=0.8')
      .to([floatCard1.value, floatCard2.value], { opacity: 1, y: 0, scale: 1, duration: 0.6, stagger: 0.2, ease: 'back.out(1.5)' }, '-=0.5')
      .to(heroTrust.value, { opacity: 1, y: 0, duration: 0.7, ease: 'power2.out' }, '-=0.3')

    // Gentle fade-out as hero leaves the viewport — one-shot transition instead of scrub:1 parallax.
    gsap.to(heroContent.value, {
      opacity: 0.4,
      y: -40,
      scrollTrigger: {
        trigger: heroSection.value,
        start: 'bottom 70%',
        end: 'bottom 20%',
        toggleActions: 'play none none reverse',
      },
    })

    // Orb gentle floating animation
    gsap.to('.orb-1', { y: -40, x: 20, duration: 8, repeat: -1, yoyo: true, ease: 'sine.inOut' })
    gsap.to('.orb-2', { y: 30, x: -15, duration: 10, repeat: -1, yoyo: true, ease: 'sine.inOut' })
    gsap.to('.orb-3', { y: -20, x: 25, duration: 9, repeat: -1, yoyo: true, ease: 'sine.inOut' })

    // Nav light/dark toggle per section
    // Hero (cream) + chapters 3, 5 → nav stays light (default)
    // Dark sections: chapters 2 (stats), 4 (features), 6 (cta) → nav--dark (remove nav--light)
    const setNavLight = () => landNav.value?.classList.add('nav--light')
    const setNavDark = () => landNav.value?.classList.remove('nav--light')

    // Chapter 2 (dark) → dark nav
    ScrollTrigger.create({
      trigger: chapterStats.value,
      start: 'top 50%',
      end: 'bottom 50%',
      onEnter: setNavDark,
      onLeaveBack: setNavLight,
      onLeave: setNavLight,
      onEnterBack: setNavDark,
    })

    // Chapter 4 is now cream/brand — no nav-dark trigger (section matches the light nav).

    // Chapter 6 (dark) → dark nav
    ScrollTrigger.create({
      trigger: chapterCta.value,
      start: 'top 50%',
      end: 'bottom 50%',
      onEnter: setNavDark,
      onLeaveBack: setNavLight,
      onLeave: setNavLight,
      onEnterBack: setNavDark,
    })

    // ---- CHAPTER 2: Pinned Stats ----
    const statSlides = [stat1.value, stat2.value, stat3.value]
    const conclusionEl = statsConclusion.value
    let conclusionShown = false
    const slideActive = [false, false, false]

    // Show first stat immediately when entering the section
    ScrollTrigger.create({
      trigger: chapterStats.value,
      start: 'top 80%',
      once: true,
      onEnter: () => {
        if (stat1.value) {
          slideActive[0] = true
          gsap.fromTo(stat1.value,
            { opacity: 0, y: 50, scale: 0.95 },
            { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: 'power3.out' }
          )
          const accentEl = stat1.value.querySelector('.stat-accent')
          if (accentEl) animateStatCounter(accentEl, statData[0].target, statData[0].suffix)
        }
      }
    })

    ScrollTrigger.create({
      trigger: chapterStats.value,
      start: 'top top',
      end: '+=100%',
      pin: true,
      pinSpacing: true,
      onUpdate: (self) => {
        const p = self.progress

        // 3 slides: 0–0.28, 0.28–0.56, 0.56–0.80, conclusion 0.80+
        statSlides.forEach((s, i) => {
          if (!s) return
          const start = i * 0.28
          const end = start + 0.28
          if (p >= start && p < end) {
            if (!slideActive[i]) {
              slideActive[i] = true
              gsap.killTweensOf(s)
              gsap.fromTo(s,
                { opacity: 0, y: 40, scale: 0.95 },
                { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: 'power3.out' }
              )
              const accentEl = s.querySelector('.stat-accent')
              if (accentEl) {
                animateStatCounter(accentEl, statData[i].target, statData[i].suffix)
              }
            }
          } else {
            if (slideActive[i]) {
              slideActive[i] = false
              gsap.killTweensOf(s)
              gsap.to(s, { opacity: 0, y: p > end ? -30 : 30, scale: 0.95, duration: 0.25, ease: 'power2.in' })
            }
          }
        })

        // Conclusion
        if (p >= 0.82) {
          if (!conclusionShown) {
            conclusionShown = true
            gsap.killTweensOf(conclusionEl)
            gsap.fromTo(conclusionEl,
              { opacity: 0, scale: 0.9 },
              { opacity: 1, scale: 1, duration: 0.5, ease: 'power3.out' }
            )
          }
        } else {
          if (conclusionShown) {
            conclusionShown = false
            gsap.killTweensOf(conclusionEl)
            gsap.to(conclusionEl, { opacity: 0, scale: 0.9, duration: 0.25, ease: 'power2.in' })
          }
        }
      }
    })

    // ---- CHAPTER 3: How It Works ----
    gsap.set(howHeader.value, { opacity: 0, y: 30 })
    ScrollTrigger.create({
      trigger: chapterHow.value,
      start: 'top 70%',
      once: true,
      onEnter: () => {
        gsap.to(howHeader.value, { opacity: 1, y: 0, duration: 0.7, ease: 'power2.out' })
      }
    })

    if (howStepEls.value) {
      howStepEls.value.forEach((step, i) => {
        gsap.set(step, { opacity: 0, y: 40 })
        ScrollTrigger.create({
          trigger: step,
          start: 'top 80%',
          once: true,
          onEnter: () => {
            gsap.to(step, { opacity: 1, y: 0, duration: 0.7, delay: i * 0.15, ease: 'power3.out' })
          }
        })
      })
    }

    // ---- CHAPTER 4: Features Horizontal Scroll ----
    const featTrack = featuresTrack.value
    if (featTrack) {
      ScrollTrigger.matchMedia({
        // Desktop: horizontal scroll
        '(min-width: 769px)': function() {
          const getScrollDist = () => featTrack.scrollWidth - window.innerWidth

          gsap.to(featTrack, {
            x: () => -getScrollDist(),
            ease: 'none',
            scrollTrigger: {
              trigger: chapterFeatures.value,
              start: 'top top',
              end: () => '+=' + (getScrollDist() + window.innerWidth * 0.3),
              pin: true,
              scrub: 1,
              invalidateOnRefresh: true
            }
          })
        },
        // Mobile: no pin, stack vertically (handled by CSS)
      })
    }

    // ---- CHAPTER 5: Portal Cards ----
    const portalCardEls = document.querySelectorAll('[data-portal-card]')
    portalCardEls.forEach((card, i) => {
      gsap.set(card, { opacity: 0, y: 40 })
      ScrollTrigger.create({
        trigger: card,
        start: 'top 85%',
        once: true,
        onEnter: () => {
          gsap.to(card, { opacity: 1, y: 0, duration: 0.6, delay: i * 0.1, ease: 'power3.out' })
        }
      })
    })

    // ---- CHAPTER 6: CTA ----
    gsap.set(ctaContent.value, { opacity: 0, y: 40 })
    ScrollTrigger.create({
      trigger: chapterCta.value,
      start: 'top 60%',
      once: true,
      onEnter: () => {
        gsap.to(ctaContent.value, { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out' })
      }
    })

    // CTA background image: one-shot rise on entrance (scrub:1 parallax was re-querying + transforming every scroll frame).
    gsap.from('.cta-bg-visual img', {
      y: 40,
      scale: 1.05,
      duration: 1.2,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: chapterCta.value,
        start: 'top 80%',
        once: true,
      },
    })

  } else {
    // ---- Reduced Motion Fallback ----
    // Stats: show all inline
    ;[stat1.value, stat2.value, stat3.value].forEach((s, i) => {
      if (!s) return
      s.style.position = 'relative'
      s.style.opacity = '1'
      s.style.marginBottom = '60px'
      const accentEl = s.querySelector('.stat-accent')
      if (accentEl) accentEl.textContent = statData[i].target + statData[i].suffix
    })
    if (statsConclusion.value) {
      statsConclusion.value.style.opacity = '1'
      statsConclusion.value.style.position = 'relative'
    }

    // How steps
    if (howHeader.value) {
      howHeader.value.style.opacity = '1'
      howHeader.value.style.transform = 'none'
    }
    if (howStepEls.value) {
      howStepEls.value.forEach(el => { el.style.opacity = '1'; el.style.transform = 'none' })
    }

    // Features: stack vertically
    if (featuresTrack.value) {
      featuresTrack.value.style.flexDirection = 'column'
      featuresTrack.value.style.width = '100%'
      featuresTrack.value.style.height = 'auto'
      featuresTrack.value.style.padding = '120px 24px'
    }
    document.querySelectorAll('.feature-card').forEach(c => {
      c.style.width = '100%'
      c.style.minWidth = 'auto'
      c.style.opacity = '1'
    })

    // Portal cards
    document.querySelectorAll('[data-portal-card]').forEach(el => {
      el.style.opacity = '1'; el.style.transform = 'none'
    })

    // CTA
    if (ctaContent.value) {
      ctaContent.value.style.opacity = '1'
      ctaContent.value.style.transform = 'none'
    }
  }
})

onBeforeUnmount(() => {
  ScrollTrigger.getAll().forEach(t => t.kill())
  window.removeEventListener('scroll', onScrollThrottled)
  document.documentElement.classList.remove('landing-smooth')
  progressBarEl = null
})
</script>

<style scoped>
/* ── Landing Theme Variables ── */
.landing {
  --land-bg: #4A4A4A;
  --land-bg-alt: #555555;
  --land-bg-card: #5C5C5C;
  --land-orange: #E8660A;
  --land-orange-bright: #F57C00;
  --land-orange-deep: #C85A00;
  --land-orange-glow: rgba(232, 102, 10, 0.1);
  --land-text: #F5F5F5;
  --land-text-secondary: #A0A0A0;
  --land-text-dim: #666666;
  --land-border: #666666;
  --land-border-hover: #777777;

  /* Cream palette (chapters 3, 5) */
  --cream-bg: #F5F0EB;
  --cream-surface: #EDE8E1;
  --cream-surface-2: #E8E2DA;
  --cream-surface-3: #F9F6F2;
  --cream-text: #2D2522;
  --cream-text-muted: rgba(45, 37, 34, 0.6);
  --cream-text-dim: rgba(45, 37, 34, 0.35);

  /* Dark section palette (chapters 2, 4, 6) */
  --dark-section: #2D2522;
  --dark-surface: #3A3330;
  --text-light: #F5F0EB;
  --text-light-muted: rgba(245, 240, 235, 0.6);

  --transition-fast: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-smooth: 0.6s cubic-bezier(0.16, 1, 0.3, 1);

  min-height: 100vh;
  background: var(--land-bg);
  color: var(--land-text);
  font-family: 'Heebo', sans-serif;
  direction: rtl;
  overflow-x: hidden;
  position: relative;
}

/* Grain overlay */
.landing::after {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.landing a {
  color: inherit;
  text-decoration: none;
}

::selection {
  background: var(--land-orange);
  color: #fff;
}

.section-wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ── Progress Bar ── */
/* Composited: scales a 100%-wide element via transform rather than animating `width` per scroll frame. */
.progress-bar {
  --progress: 0;
  position: fixed;
  top: 0;
  right: 0;
  left: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--land-orange), var(--land-orange-bright));
  z-index: 1000;
  transform: scaleX(var(--progress));
  transform-origin: right center;
  will-change: transform;
}

/* ── Chapter Numbers ── */
.chapter-num {
  position: absolute;
  top: 5%;
  left: 5%;
  font-family: 'Heebo', sans-serif;
  font-size: clamp(100px, 15vw, 200px);
  font-weight: 900;
  color: transparent;
  -webkit-text-stroke: 1px rgba(45, 37, 34, 0.04);
  line-height: 1;
  z-index: 0;
  pointer-events: none;
  user-select: none;
}

.chapter--dark .chapter-num {
  -webkit-text-stroke-color: rgba(245, 240, 235, 0.05);
}

/* ── Navigation ── */
/* Solid-with-alpha instead of backdrop-filter: blur over scrolling content forced a per-frame compositor repaint. */
.land-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(74, 74, 74, 0.92);
  border-bottom: 1px solid var(--land-border);
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

/* Nav light mode (after hero) */
.land-nav.nav--light {
  background: rgba(245, 240, 235, 0.95);
  border-bottom-color: rgba(45, 37, 34, 0.06);
}

.land-nav.nav--light .nav-name {
  color: var(--cream-text);
}

.land-nav.nav--light .nav-icon {
  background: var(--cream-text);
  color: var(--cream-bg);
}

.land-nav.nav--light .nav-links a {
  color: var(--cream-text-muted);
}

.land-nav.nav--light .nav-links a:hover {
  color: var(--land-orange);
}

.land-nav.nav--light .nav-btn-ghost {
  border-color: var(--cream-text) !important;
  color: var(--cream-text) !important;
}

.land-nav.nav--light .nav-btn-ghost:hover {
  background: rgba(45, 37, 34, 0.05) !important;
}

.land-nav.nav--light .nav-btn-solid {
  background: var(--cream-text) !important;
  color: var(--cream-bg) !important;
}

.land-nav.nav--light .nav-btn-solid:hover {
  background: var(--dark-section) !important;
}

.land-nav.nav--light .mobile-menu-btn {
  color: var(--cream-text);
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
  transition: color var(--transition-fast);
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
.mobile-menu-leave-active {
  transition: all 0.3s ease;
}

.mobile-menu-enter-from,
.mobile-menu-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ══════════════════════════════════════ */
/* CHAPTER 1: HERO — BENTO (cream)       */
/* ══════════════════════════════════════ */
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
  /* 60px blur is half the old cost; element scale 1.4x keeps the perceived softness the same. */
  filter: blur(60px);
  transform: translateZ(0) scale(1.4);
  will-change: transform;
}

.hero-gradient .orb-1 {
  width: 600px;
  height: 600px;
  background: rgba(232, 102, 10, 0.1);
  top: -20%;
  left: -10%;
}

.hero-gradient .orb-2 {
  width: 400px;
  height: 400px;
  background: rgba(232, 102, 10, 0.07);
  bottom: 10%;
  right: -5%;
}

.hero-gradient .orb-3 {
  width: 350px;
  height: 350px;
  background: rgba(180, 140, 100, 0.08);
  top: 40%;
  left: 50%;
}

.hero-inner {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  width: 100%;
  min-height: 100dvh;
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 110px 48px 80px 32px;
  max-width: 640px;
  margin-inline-start: auto;
  margin-top: -100px;
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
  font-size: clamp(36px, 5.5vw, 68px);
  font-weight: 900;
  line-height: 1.15;
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
  bottom: 2px;
  right: 0;
  width: 100%;
  height: 6px;
  background: rgba(232, 102, 10, 0.15);
  border-radius: 3px;
}

.hero-sub {
  font-size: clamp(15px, 1.1vw, 18px);
  color: var(--cream-text-muted);
  line-height: 1.7;
  max-width: 460px;
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

.hero-ghost {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  border: none;
  color: #fff;
  background: #1a1a1a;
  padding: 16px 28px;
  border-radius: 40px;
  font-size: 0.95rem;
  font-weight: 700;
  transition: all var(--transition-fast);
  min-height: 52px;
}

.ghost-play {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--land-orange);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.ghost-play svg {
  margin-right: -1px;
}

.hero-ghost:hover {
  background: var(--land-orange);
  color: #fff;
}

.hero-ghost:hover .ghost-play {
  background: #fff;
  color: var(--land-orange);
}

.hero-stats-row {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-top: 16px;
  padding: 16px 24px;
  background: rgba(45, 37, 34, 0.03);
  border-radius: 14px;
  border: 1px solid rgba(45, 37, 34, 0.05);
  width: fit-content;
}

.hero-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: center;
}

.hero-stat-divider {
  width: 1px;
  height: 32px;
  background: rgba(45, 37, 34, 0.1);
}

.hero-stat-num {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--land-orange);
  letter-spacing: -0.5px;
}

.hero-stat-label {
  font-size: 0.72rem;
  color: var(--cream-text-dim);
  letter-spacing: 0.02em;
}

/* Hero Visual — Edge bleed to left */
.hero-visual {
  position: relative;
  height: 100%;
  min-height: 100dvh;
  padding: 24px;
}

.hero-dashboard {
  position: absolute;
  top: 96px;
  bottom: 24px;
  left: 24px;
  right: 24px;
  overflow: hidden;
  border-radius: 32px;
  box-shadow: 0 8px 40px rgba(45, 37, 34, 0.12);
}

.hero-dashboard img,
.hero-dashboard .hero-dashboard-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: #FFF8F0;
}

.hero-img-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to right, rgba(245, 240, 235, 0.3) 0%, transparent 30%),
              linear-gradient(to top, rgba(45, 37, 34, 0.2) 0%, transparent 30%);
  pointer-events: none;
}

/* Floating stat cards — dropped backdrop-filter (cards are animated; per-frame blur is wasted) */
.float-card {
  position: absolute;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 14px;
  padding: 16px 20px;
  z-index: 3;
  box-shadow: 0 16px 40px rgba(45, 37, 34, 0.1);
}

.float-card-1 {
  top: 18%;
  right: 8%;
  animation: float1 6s ease-in-out infinite;
}

.float-card-2 {
  bottom: 15%;
  left: 8%;
  animation: float2 7s ease-in-out infinite;
}

@keyframes float1 { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-12px); } }
@keyframes float2 { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(10px); } }

.float-card .fc-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--land-orange-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.float-card .fc-icon svg {
  width: 18px;
  height: 18px;
  color: var(--land-orange);
}

.float-card .fc-value {
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--cream-text);
  letter-spacing: -0.5px;
}

.float-card .fc-label {
  font-size: 0.72rem;
  color: var(--cream-text-dim);
  margin-top: 2px;
}

.float-card .fc-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(76, 175, 80, 0.1);
  color: #2E7D32;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 20px;
  margin-top: 6px;
}

.float-card .fc-bar {
  width: 100%;
  height: 4px;
  background: rgba(45, 37, 34, 0.06);
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.float-card .fc-bar-fill {
  width: 85%;
  height: 100%;
  background: linear-gradient(90deg, var(--land-orange), var(--land-orange-bright));
  border-radius: 2px;
  transform-origin: right center; /* RTL — grow from the right edge */
  animation: barFill 2s ease-out 1.5s both;
  will-change: transform;
}

/* scaleX on a fixed-width element is composited; the old `width: 0→85%` triggered layout every keyframe. */
@keyframes barFill {
  from { transform: scaleX(0); }
  to   { transform: scaleX(1); }
}

/* Trust strip */
.hero-trust {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.trust-label {
  font-size: 0.72rem;
  color: var(--cream-text-dim);
  letter-spacing: 0.03em;
}

.trust-logos {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.trust-logos span {
  font-size: 0.78rem;
  font-weight: 700;
  color: rgba(45, 37, 34, 0.22);
  letter-spacing: 0.01em;
  transition: color 0.3s;
}

.trust-logos span:hover {
  color: var(--land-orange);
}

/* Scroll indicator */
.scroll-indicator {
  position: absolute;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  z-index: 5;
}

.scroll-indicator span {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: var(--cream-text-dim);
}

.scroll-arrow {
  width: 1px;
  height: 40px;
  background: linear-gradient(to bottom, var(--land-orange), transparent);
  position: relative;
  overflow: hidden;
}

.scroll-arrow::after {
  content: '';
  position: absolute;
  top: 0;
  width: 100%;
  height: 50%;
  background: var(--land-orange);
  animation: scrollPulse 2s ease-in-out infinite;
  will-change: transform;
}

/* Composited transform replaces the old `top: -50% → 150%` reflow-triggering keyframe. */
@keyframes scrollPulse {
  0%   { transform: translateY(-100%); }
  100% { transform: translateY(300%); }
}

/* ══════════════════════════════════════ */
/* CHAPTER 2: PINNED STATS (dark)        */
/* ══════════════════════════════════════ */
.chapter-stats {
  position: relative;
  min-height: 100vh;
  background: var(--dark-section);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.stats-wrapper {
  position: relative;
  width: 100%;
  min-height: 100vh;
}

.stat-slide {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  opacity: 0;
  padding: 0 24px;
  pointer-events: none;
}

.stat-number {
  font-size: clamp(64px, 15vw, 160px);
  font-weight: 900;
  color: var(--text-light);
  letter-spacing: -3px;
  line-height: 1;
  margin-bottom: 16px;
}

.stat-accent {
  color: var(--land-orange);
}

.stat-label {
  font-size: clamp(1rem, 2vw, 1.5rem);
  color: var(--text-light-muted);
  max-width: 500px;
  line-height: 1.6;
}

.stats-conclusion {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  z-index: 5;
  pointer-events: none;
}

.stats-conclusion h3 {
  font-size: clamp(2rem, 5vw, 3.5rem);
  font-weight: 800;
  color: var(--text-light);
  letter-spacing: -1px;
}

.copper-line {
  display: block;
  width: 60px;
  height: 3px;
  background: var(--land-orange);
  margin-top: 20px;
  border-radius: 2px;
}

/* ══════════════════════════════════════ */
/* CHAPTER 3: HOW IT WORKS (cream)       */
/* ══════════════════════════════════════ */
.chapter-how {
  position: relative;
  min-height: 100vh;
  background: var(--cream-surface);
  overflow: hidden;
  padding: 120px 24px;
}

.how-header {
  text-align: center;
  margin-bottom: 80px;
  position: relative;
  z-index: 2;
}

.how-label {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--land-orange);
  font-weight: 600;
  margin-bottom: 16px;
  display: block;
}

.how-title {
  font-size: clamp(28px, 4vw, 48px);
  font-weight: 800;
  color: var(--cream-text);
  letter-spacing: -1px;
}

.how-steps {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 40px;
  position: relative;
  z-index: 2;
}

.how-step {
  position: relative;
  padding: 40px 32px;
  border-radius: 20px;
  background: var(--cream-surface-3);
  border: 1px solid rgba(45, 37, 34, 0.06);
  transition: all var(--transition-smooth);
}

.how-step:hover {
  border-color: rgba(232, 102, 10, 0.15);
  transform: translateY(-4px);
  box-shadow: 0 20px 60px rgba(45, 37, 34, 0.08);
}

.how-step-num {
  font-size: 4rem;
  font-weight: 900;
  color: transparent;
  -webkit-text-stroke: 1px rgba(45, 37, 34, 0.08);
  line-height: 1;
  margin-bottom: 20px;
}

.how-step-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  background: var(--land-orange-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.how-step-icon :deep(svg) {
  width: 24px;
  height: 24px;
  color: var(--land-orange);
}

.how-step h3 {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--cream-text);
  margin-bottom: 12px;
}

.how-step p {
  font-size: 0.95rem;
  color: var(--cream-text-muted);
  line-height: 1.7;
}

.how-connector {
  position: absolute;
  top: 50%;
  width: 40px;
  right: calc(100% + 0px);
  height: 1px;
  background: linear-gradient(to right, rgba(232, 102, 10, 0.2), transparent);
}

/* ══════════════════════════════════════ */
/* CHAPTER 4: FEATURES HORIZONTAL (dark) */
/* ══════════════════════════════════════ */
.chapter-features {
  position: relative;
  min-height: 100vh;
  background: linear-gradient(180deg, var(--cream-bg) 0%, #FFF2E0 100%);
  overflow: hidden;
}

/* Soft brand orbs — echoes the hero's decoration to keep the section on-brand */
.chapter-features::before,
.chapter-features::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
}
.chapter-features::before {
  width: 520px;
  height: 520px;
  background: rgba(232, 102, 10, 0.10);
  top: -120px;
  right: -140px;
}
.chapter-features::after {
  width: 380px;
  height: 380px;
  background: rgba(255, 183, 77, 0.14);
  bottom: -100px;
  left: -100px;
}

.features-header {
  position: absolute;
  top: 60px;
  right: 0;
  left: 0;
  text-align: center;
  z-index: 5;
  padding: 0 24px;
}

.features-label {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--land-orange);
  font-weight: 600;
  margin-bottom: 12px;
  display: block;
}

.features-title {
  font-size: clamp(28px, 4vw, 48px);
  font-weight: 800;
  color: var(--cream-text);
  letter-spacing: -1px;
}

.features-track {
  display: flex;
  gap: 32px;
  padding: 160px 48px 60px 48px;
  will-change: transform;
  direction: ltr;
}

.features-track::after {
  content: '';
  min-width: 120px;
  flex-shrink: 0;
}

.feature-card {
  min-width: clamp(340px, 55vw, 640px);
  height: clamp(380px, 50vh, 480px);
  border-radius: 24px;
  padding: 40px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
  background: #ffffff;
  border: 1px solid rgba(45, 37, 34, 0.06);
  box-shadow: 0 20px 50px rgba(232, 102, 10, 0.10), 0 4px 12px rgba(45, 37, 34, 0.04);
  transition: border-color var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
  direction: rtl;
}

.feature-card:hover {
  border-color: rgba(232, 102, 10, 0.25);
  transform: translateY(-4px);
  box-shadow: 0 28px 60px rgba(232, 102, 10, 0.14), 0 6px 16px rgba(45, 37, 34, 0.06);
}

/* Cream gradient overlay replaces the old dark 0.95 one — text sits cleanly while the photo stays visible */
.feature-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(255, 248, 240, 0.96) 28%, rgba(255, 248, 240, 0.55) 60%, rgba(255, 248, 240, 0.15) 100%);
  z-index: 1;
}

.feature-card-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.feature-card-bg img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  /* Warm-tint the stock photos so they read as brand rather than generic AI imagery */
  filter: saturate(0.85) brightness(1.05) sepia(0.15);
}

.feature-card-content {
  position: relative;
  z-index: 2;
}

.feature-card-number {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: var(--land-orange);
  font-weight: 700;
  margin-bottom: 12px;
}

.feature-card-name {
  font-size: clamp(1.5rem, 3vw, 2.2rem);
  font-weight: 800;
  color: var(--cream-text);
  line-height: 1.1;
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}

.feature-card-desc {
  font-size: 0.92rem;
  color: var(--cream-text-dim);
  line-height: 1.7;
  max-width: 380px;
}

/* ══════════════════════════════════════ */
/* CHAPTER 5: PORTAL BENTO GRID (cream)  */
/* ══════════════════════════════════════ */
.chapter-portal {
  position: relative;
  padding: 120px 24px;
  background: var(--cream-bg);
  overflow: hidden;
}

.portal-header {
  text-align: center;
  margin-bottom: 60px;
  position: relative;
  z-index: 2;
}

.portal-label {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--land-orange);
  font-weight: 600;
  margin-bottom: 16px;
  display: block;
}

.portal-title {
  font-size: clamp(28px, 4vw, 48px);
  font-weight: 800;
  color: var(--cream-text);
  letter-spacing: -1px;
  margin-bottom: 16px;
}

.portal-sub {
  font-size: 1rem;
  color: var(--cream-text-muted);
  max-width: 560px;
  margin: 0 auto;
  line-height: 1.7;
}

.portal-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: auto auto;
  gap: 20px;
  position: relative;
  z-index: 2;
}

.portal-card {
  padding: 32px;
  border-radius: 20px;
  background: var(--cream-surface-3);
  border: 1px solid rgba(45, 37, 34, 0.05);
  transition: all var(--transition-smooth);
  position: relative;
  overflow: hidden;
}

.portal-card:hover {
  border-color: rgba(232, 102, 10, 0.12);
  transform: translateY(-4px);
  box-shadow: 0 20px 60px rgba(45, 37, 34, 0.08);
}

.portal-card::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(232, 102, 10, 0.04), transparent);
  border-radius: 50%;
  pointer-events: none;
}

.portal-card-featured {
  grid-column: span 2;
  grid-row: span 2;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.portal-card-featured .portal-card-img {
  margin-top: 24px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(45, 37, 34, 0.06);
  flex: 1;
  min-height: 200px;
}

.portal-card-featured .portal-card-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.portal-card .pc-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--land-orange-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.portal-card .pc-icon :deep(svg) {
  width: 20px;
  height: 20px;
  color: var(--land-orange);
}

.portal-card h3 {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--cream-text);
  margin-bottom: 8px;
}

.portal-card p {
  font-size: 0.88rem;
  color: var(--cream-text-muted);
  line-height: 1.7;
}

/* ══════════════════════════════════════ */
/* CHAPTER 6: CTA (dark)                 */
/* ══════════════════════════════════════ */
.chapter-cta {
  position: relative;
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--dark-section);
}

.cta-bg-visual {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}

.cta-bg-visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.1;
  filter: blur(2px);
}

.chapter-cta .cta-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, rgba(45, 37, 34, 0.6), rgba(45, 37, 34, 0.95));
  z-index: 1;
}

.cta-content {
  position: relative;
  z-index: 3;
  text-align: center;
  padding: 0 24px;
  max-width: 700px;
}

.cta-headline {
  font-size: clamp(2.5rem, 7vw, 5rem);
  font-weight: 900;
  color: var(--text-light);
  line-height: 1.05;
  margin-bottom: 20px;
  letter-spacing: -2px;
}

.cta-headline span {
  color: var(--land-orange);
}

.cta-sub {
  font-size: 1.1rem;
  color: var(--text-light-muted);
  margin-bottom: 36px;
  line-height: 1.7;
}

.cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: var(--land-orange);
  color: #fff !important;
  padding: 20px 52px;
  border-radius: 40px;
  font-size: 1.1rem;
  font-weight: 700;
  transition: all var(--transition-fast);
  min-height: 56px;
  border: none;
  cursor: pointer;
  box-shadow: 0 0 40px rgba(232, 102, 10, 0.2);
}

.cta-btn:hover {
  background: var(--land-orange-deep);
  transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(232, 102, 10, 0.4);
}

/* ══════════════════════════════════════ */
/* FOOTER                                */
/* ══════════════════════════════════════ */
.land-footer {
  background: var(--dark-section);
  border-top: 1px solid rgba(245, 240, 235, 0.04);
  padding: 60px 24px 40px;
}

.footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 24px;
}

.footer-brand {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fb-name {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--land-orange);
}

.fb-tag {
  font-size: 0.82rem;
  color: var(--text-light-muted);
}

.footer-links {
  display: flex;
  gap: 28px;
}

.footer-links a {
  font-size: 0.85rem;
  color: var(--text-light-muted);
  transition: color var(--transition-fast);
}

.footer-links a:hover {
  color: var(--land-orange);
}

.footer-copy {
  font-size: 0.75rem;
  color: rgba(245, 240, 235, 0.3);
  width: 100%;
  text-align: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(245, 240, 235, 0.04);
}

/* ══════════════════════════════════════ */
/* RESPONSIVE                            */
/* ══════════════════════════════════════ */
@media (max-width: 1024px) {
  .hero-inner {
    grid-template-columns: 1fr;
    gap: 40px;
    padding-top: 120px;
  }

  .hero-visual {
    max-width: 320px;
    margin: 0 auto;
  }

  .portal-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .portal-card-featured {
    grid-column: span 2;
    grid-row: span 1;
  }
}

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

  .how-steps {
    grid-template-columns: 1fr;
    max-width: 500px;
  }

  .how-connector {
    display: none !important;
  }

  /* Features: stack vertically on mobile */
  .chapter-features {
    min-height: auto;
  }

  .features-header {
    position: relative;
    top: auto;
    padding-top: 60px;
    padding-bottom: 20px;
  }

  .features-track {
    flex-direction: column;
    padding: 24px;
    direction: rtl;
  }

  .features-track::after {
    display: none;
  }

  .feature-card {
    min-width: auto;
    width: 100%;
    height: 380px;
  }

  .portal-grid {
    grid-template-columns: 1fr;
  }

  .portal-card-featured {
    grid-column: span 1;
    grid-row: span 1;
  }

  .hero-inner {
    grid-template-columns: 1fr;
  }

  .hero-content {
    padding: 120px 24px 40px;
    max-width: 100%;
    margin: 0;
  }

  .hero-visual {
    position: relative;
    height: 400px;
    min-height: auto;
  }

  .hero-dashboard {
    border-radius: 0;
  }

  .hero-headline {
    font-size: clamp(28px, 7vw, 42px);
  }

  .hero-stats-row {
    gap: 16px;
    padding: 14px 18px;
  }

  .trust-logos {
    gap: 12px;
  }

  .trust-logos span {
    font-size: 0.72rem;
  }

  .float-card {
    display: none;
  }

  .chapter-num {
    font-size: clamp(60px, 16vw, 120px);
  }

  .footer-inner {
    flex-direction: column;
    text-align: center;
  }

  .footer-links {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .hero-cta-wrap {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-btn,
  .hero-ghost {
    justify-content: center;
  }

  .hero-stats-row {
    flex-direction: column;
    gap: 12px;
    width: 100%;
  }

  .hero-stat-divider {
    width: 40px;
    height: 1px;
  }

  .hero-trust .trust-logos {
    gap: 8px;
  }

  .scroll-indicator {
    display: none;
  }

  .cta-headline {
    font-size: clamp(2rem, 8vw, 3rem);
  }

  .cta-btn {
    padding: 16px 36px;
    font-size: 1rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>

<!-- Global styles — not scoped to .landing because they target <html> and have to survive Vue's attribute scoping. -->
<style>
html.landing-smooth {
  scroll-behavior: smooth;
}
@media (prefers-reduced-motion: reduce) {
  html.landing-smooth {
    scroll-behavior: auto;
  }
}
</style>