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

    <!-- Floating circles (hero only) -->
    <div class="float-circle float-circle-1" ref="fc1"></div>
    <div class="float-circle float-circle-2" ref="fc2"></div>
    <div class="float-circle float-circle-3" ref="fc3"></div>
    <div class="float-circle float-circle-4" ref="fc4"></div>
    <div class="float-circle float-circle-5" ref="fc5"></div>

    <!-- ================================ -->
    <!-- HERO (unchanged)                 -->
    <!-- ================================ -->
    <section class="hero" ref="heroSection">
      <div class="hero-bg-image"></div>
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <router-link to="/signup" class="btn-primary hero-cta">התחל עכשיו</router-link>
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
    <section class="chapter-features chapter--dark" id="features" ref="chapterFeatures">
      <div class="chapter-num" aria-hidden="true">04</div>
      <div class="features-header">
        <span class="features-label">יכולות המערכת</span>
        <h2 class="features-title">למה Nifraim?</h2>
      </div>
      <div class="features-track" ref="featuresTrack">
        <div class="feature-card" v-for="(f, i) in featureCards" :key="i">
          <div class="feature-card-bg">
            <img :src="f.image" :alt="f.title" loading="lazy">
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
            <img src="/images/landing/hero-dashboard.jpg" alt="Customer dashboard" loading="lazy">
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
        <img src="/images/landing/ai-network.jpg" alt="" aria-hidden="true">
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
import Lenis from 'lenis'

gsap.registerPlugin(ScrollTrigger)

// Refs
const landingRoot = ref(null)
const landNav = ref(null)
const progressBar = ref(null)
const heroSection = ref(null)
const fc1 = ref(null)
const fc2 = ref(null)
const fc3 = ref(null)
const fc4 = ref(null)
const fc5 = ref(null)
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

// Smooth scroll to anchor
function scrollToSection(id) {
  const el = document.getElementById(id)
  if (!el) return
  if (lenis) {
    lenis.scrollTo(el, { offset: -72 })
  } else {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
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
    desc: 'גררו את הקבצים אל המערכת. זיהוי אוטומטי של הפורמט — כולל קבצים מוגני סיסמא מ-7+ חברות.',
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
  { num: 'יכולת 01', title: 'זיהוי אוטומטי', desc: 'המערכת מזהה פורמטים מ-7+ חברות שונות, כולל קבצים מוגני סיסמא. ללא הגדרות מראש.', image: '/images/landing/ai-network.jpg' },
  { num: 'יכולת 02', title: 'השוואה מדויקת', desc: 'התאמה אוטומטית בין פרודוקציה לנפרעים. זיהוי פערים, חסרים ואי-התאמות בשניות.', image: '/images/landing/data-flow.jpg' },
  { num: 'יכולת 03', title: 'תוצאות מיידיות', desc: 'מה שלקח שעות — לוקח שניות. העלו קבצים וקבלו תשובות. ייצוא לאקסל בלחיצה.', image: '/images/landing/dashboard.jpg' },
  { num: 'יכולת 04', title: 'ניתוח AI חכם', desc: 'בינה מלאכותית שמבינה את הנתונים שלכם. שאלו שאלות — קבלו תובנות מהתיק.', image: '/images/landing/portal.jpg' },
]

// Lenis + GSAP setup
let lenis = null
let lenisTickerFn = null
let rafId = null

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
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  // Lenis smooth scroll
  if (!prefersReduced) {
    lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      smoothWheel: true,
    })
    lenis.on('scroll', ScrollTrigger.update)
    lenisTickerFn = (time) => { if (lenis) lenis.raf(time * 1000) }
    gsap.ticker.add(lenisTickerFn)
    gsap.ticker.lagSmoothing(0)
  }

  // Progress bar
  const onScroll = () => {
    if (!progressBar.value) return
    const h = document.documentElement
    progressBar.value.style.width = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100 + '%'
  }
  window.addEventListener('scroll', onScroll, { passive: true })

  // Floating circles fade out after hero
  if (!prefersReduced) {
    ScrollTrigger.create({
      trigger: heroSection.value,
      start: 'top top',
      end: 'bottom top',
      onLeave: () => {
        gsap.to([fc1.value, fc2.value, fc3.value, fc4.value, fc5.value], {
          opacity: 0, duration: 0.5
        })
      },
      onEnterBack: () => {
        gsap.to([fc1.value, fc2.value, fc3.value, fc4.value, fc5.value], {
          opacity: 1, duration: 0.5
        })
      }
    })

    // Nav light/dark toggle per section
    // Light sections (cream): chapters 3 (how), 5 (portal) → nav--light
    // Dark sections: hero, chapters 2 (stats), 4 (features), 6 (cta) → no nav--light
    const setNavLight = () => landNav.value?.classList.add('nav--light')
    const setNavDark = () => landNav.value?.classList.remove('nav--light')

    // After hero → chapter 2 (dark) — nav stays dark
    // Chapter 3 (cream) → light nav
    ScrollTrigger.create({
      trigger: chapterHow.value,
      start: 'top 50%',
      end: 'bottom 50%',
      onEnter: setNavLight,
      onLeaveBack: setNavDark,
      onLeave: setNavDark,
      onEnterBack: setNavLight,
    })

    // Chapter 5 (cream) → light nav
    ScrollTrigger.create({
      trigger: chapterPortal.value,
      start: 'top 50%',
      end: 'bottom 50%',
      onEnter: setNavLight,
      onLeaveBack: setNavDark,
      onLeave: setNavDark,
      onEnterBack: setNavLight,
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

    // CTA parallax
    gsap.to('.cta-bg-visual img', {
      y: -40,
      scrollTrigger: {
        trigger: chapterCta.value,
        start: 'top bottom',
        end: 'bottom top',
        scrub: 1
      }
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
  if (lenisTickerFn) {
    gsap.ticker.remove(lenisTickerFn)
    lenisTickerFn = null
  }
  if (lenis) {
    lenis.destroy()
    lenis = null
  }
  if (rafId) {
    cancelAnimationFrame(rafId)
  }
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
.progress-bar {
  position: fixed;
  top: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--land-orange), var(--land-orange-bright));
  z-index: 1000;
  width: 0;
  will-change: width;
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

/* Nav light mode (after hero) */
.land-nav.nav--light {
  background: rgba(245, 240, 235, 0.9);
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

/* ── Hero ── */
.hero {
  position: relative;
  height: 100vh;
  min-height: 600px;
  overflow: hidden;
  padding-top: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.hero-bg-image {
  position: absolute;
  inset: 0;
  background: url('/images/hero-bg.png') center center / cover no-repeat;
  z-index: 0;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: rgba(10, 10, 10, 0.15);
  z-index: 1;
  pointer-events: none;
}

.hero-content {
  position: absolute;
  inset: 0;
  z-index: 2;
}

.hero-cta {
  position: absolute;
  bottom: 18%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 1.25rem;
  font-weight: 700;
  padding: 16px 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f57c00, #ff9800);
  color: #fff !important;
  text-decoration: none;
  box-shadow: 0 8px 32px rgba(245, 124, 0, 0.4);
  cursor: pointer;
  letter-spacing: 0.5px;
}

/* Use a wrapper approach: keep translateX(-50%) stable, animate via filter/box-shadow only */
.hero-cta:hover {
  box-shadow: 0 12px 40px rgba(245, 124, 0, 0.5);
  filter: brightness(1.1);
}

.hero-cta:active {
  filter: brightness(0.95);
}

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
  box-shadow: 0 8px 32px rgba(245, 124, 0, 0.3);
}

.btn-primary:not(.hero-cta):hover {
  transform: translateY(-2px);
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
  background: var(--dark-section);
  overflow: hidden;
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
  color: var(--text-light);
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
  border-radius: 20px;
  padding: 40px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
  border: 1px solid rgba(245, 240, 235, 0.08);
  transition: border-color var(--transition-fast);
  direction: rtl;
}

.feature-card:hover {
  border-color: rgba(245, 240, 235, 0.15);
}

.feature-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(45, 37, 34, 0.95) 30%, rgba(45, 37, 34, 0.2));
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
  font-weight: 600;
  margin-bottom: 12px;
}

.feature-card-name {
  font-size: clamp(1.5rem, 3vw, 2.2rem);
  font-weight: 800;
  color: var(--text-light);
  line-height: 1.1;
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}

.feature-card-desc {
  font-size: 0.92rem;
  color: var(--text-light-muted);
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

  .float-circle-1 { width: 140px; height: 140px; }
  .float-circle-2 { width: 100px; height: 100px; }
  .float-circle-4 { display: none; }
  .float-circle-5 { display: none; }
}

@media (max-width: 480px) {
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