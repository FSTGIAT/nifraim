<template>
  <div class="landing" ref="landingRoot">
    <!-- Progress Bar -->
    <div class="progress-bar" ref="progressBar"></div>

    <!-- Centered slide-tabs nav is rendered at the app shell (App.vue) -->


    <!-- Grain overlay via CSS pseudo-element on .landing -->

    <!-- ================================ -->
    <!-- CHAPTER 01: HERO — SHADER         -->
    <!-- Live @paper-design/shaders-react WebGL mesh + Hebrew RTL overlay. -->
    <!-- Bottom edge fades into Chapter 02 cream story stack. -->
    <!-- ================================ -->
    <section class="chapter-hero chapter-hero--shader" ref="heroSection">
      <div class="chapter-num chapter-num--on-shader" aria-hidden="true">01</div>
      <ShaderHeroIsland />
    </section>

    <!-- ================================ -->
    <!-- CHAPTER 02: STORY STACK          -->
    <!-- Sticky cards rotate in from below. Each pins, the next slides over. -->
    <!-- ================================ -->
    <section class="chapter-stack" id="automation" ref="chapterStack" aria-label="הבטחות המערכת">
      <div
        v-for="(card, i) in storyCards"
        :key="card.label"
        class="story-card"
        :class="['story-card--' + card.theme]"
        :ref="(el) => { if (el) storyCardEls[i] = el }"
        data-story-card
      >
        <div class="story-inner">
          <div class="story-top">
            <span class="story-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="story-label">{{ card.label }}</span>
          </div>
          <hr class="story-divider" />
          <h2 class="story-headline" v-html="card.headline"></h2>
          <hr class="story-divider" />
          <p class="story-body">{{ card.body }}</p>
          <div v-if="card.cta" class="story-cta-row">
            <router-link :to="card.cta.to" class="story-cta">
              {{ card.cta.label }}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            </router-link>
          </div>
          <div class="story-meta" v-else>
            <span class="story-accent-dot"></span>
            <span class="story-meta-text">{{ card.meta }}</span>
          </div>
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
            <video :src="f.video" :poster="f.poster" :aria-label="f.title"
                   autoplay muted loop playsinline preload="metadata"
                   width="1376" height="768"></video>
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
      <!-- Background = animated boxes grid (replaces the static AI-network image) -->
      <FooterAnimatedBoxes class="cta-boxes" />
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
import { useRoute } from 'vue-router'
import ShaderHeroIsland from '../components/landing/ShaderHeroIsland.vue'
import FooterAnimatedBoxes from '../components/landing/FooterAnimatedBoxes.vue'

gsap.registerPlugin(ScrollTrigger)

// Refs
const landingRoot = ref(null)
const progressBar = ref(null)
const heroSection = ref(null)
const chapterStack = ref(null)
const storyCardEls = ref([])
const chapterHow = ref(null)
const howHeader = ref(null)
const howStepEls = ref([])
const chapterFeatures = ref(null)
const featuresTrack = ref(null)
const chapterPortal = ref(null)
const chapterCta = ref(null)
const ctaContent = ref(null)

// SlideTabs and its navTabs config now live in App.vue so the nav persists
// across the public marketing routes (landing/pricing/signup/login/...).

const route = useRoute()

// Motion preference — used to gate video autoplay + ScrollTrigger effects
const prefersReducedMotion = ref(
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches,
)

// Data — Chapter 02 story stack: 5 sticky cards stacking with rotation
const storyCards = [
  {
    label: 'אוטומציה',
    theme: 'peach',
    headline: 'לא להעלות.<br/>לא לגרור.<br/>לא לחפש.',
    body: 'סוכני AI טוענים, סורקים ומשווים בעצמם. אתם פנויים לעבודה האמיתית.',
    meta: 'ללא העלאות. ללא גרירה.',
  },
  {
    label: 'דיוק',
    theme: 'sage',
    headline: 'כל שקל.<br/>נמצא.',
    body: 'הסכמים, פוליסות ועמלות מתעדכנים אוטומטית לכל חברה ולכל מוצר.',
    meta: 'כל מוצר. כל חברה. כל חודש.',
  },
  {
    label: 'מהירות',
    theme: 'slate',
    headline: 'שניות.<br/>לא שעות.',
    body: 'בדיקה רציפה של עמלות נפרעים. המערכת מאתרת פערים לפני שאתם שמים לב.',
    meta: 'מבדיקות ידניות — להתראות אוטומטיות.',
  },
  {
    label: 'תובנות',
    theme: 'mauve',
    headline: 'הסיפור<br/>המלא של<br/>התיק.',
    body: 'חוסרים, שינויים חודשיים ומגמות. תמונה ברורה של מה השתנה ולמה.',
    meta: 'דיאגרמות חיות. לא טבלאות מתות.',
  },
  {
    label: 'שקט',
    theme: 'amber',
    headline: 'עבודה<br/>שמתבצעת<br/>בלעדיכם.',
    body: 'הזמן להפסיק לרדוף אחרי קבצים. הסוכן עובד גם כשאתם לא.',
    cta: { label: 'הצטרפו עכשיו', to: '/signup' },
  },
]

const howSteps = [
  {
    title: 'המערכת טוענת לבד',
    desc: 'סוכני AI מושכים קבצי פרודוקציה ונפרעים באופן אוטומטי — ללא העלאות, ללא גרירה.',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>'
  },
  {
    title: 'AI קורא הסכמים ומשווה',
    desc: 'המערכת קוראת הסכמים, מעדכנת טבלאות עמלות לכל חברה ומוצר, ומאתרת פערים.',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>'
  },
  {
    title: 'תובנות זורמות אליכם',
    desc: 'חוסרים, שינויים חודשיים ומגמות — מוצגים בדיאגרמות AI חיות, בלי בדיקות ידניות.',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 118 2.83"/><path d="M22 12A10 10 0 0012 2v10z"/></svg>'
  },
]

const featureCards = [
  {
    num: 'יכולת 01',
    title: 'טעינה אוטומטית של קבצים',
    desc: 'סוכני AI מושכים קבצי פרודוקציה ונפרעים בעצמם. בלי העלאות, בלי גרירה — הכל מתחיל לבד.',
    video: '/landing/feature-01-autoload.webm',
    poster: '/landing/feature-01-autoload.jpg',
  },
  {
    num: 'יכולת 02',
    title: 'הסכמים חיים',
    desc: 'טוענים הסכם — טבלאות העמלות לנפרעים והיקפים מתעדכנות אוטומטית לכל חברה ולכל מוצר.',
    video: '/landing/feature-02-agreements.webm',
    poster: '/landing/feature-02-agreements.jpg',
  },
  {
    num: 'יכולת 03',
    title: 'בדיקת עמלות אוטומטית',
    desc: 'סריקה רציפה של עמלות נפרעים. המערכת מאתרת אי-התאמות ופערים לפני שאתם שמים לב.',
    video: '/landing/feature-03-audit.webm',
    poster: '/landing/feature-03-audit.jpg',
  },
  {
    num: 'יכולת 04',
    title: 'תובנות חודשיות',
    desc: 'חוסרים, שינויים מחודש לחודש ומגמות לאורך זמן — תמונה ברורה של מה השתנה ולמה.',
    video: '/landing/feature-04-insights.webm',
    poster: '/landing/feature-04-insights.jpg',
  },
  {
    num: 'יכולת 05',
    title: 'עוזר AI דיאגרמי',
    desc: 'שואלים שאלה — מקבלים דיאגרמה חיה. עוזר אישי שמסביר את התיק שלכם בויזואל, לא בטקסט.',
    video: '/landing/feature-05-ai.webm',
    poster: '/landing/feature-05-ai.jpg',
  },
]

// Scroll progress: rAF-throttled writer for a single CSS variable on the progress bar element
let scrollRafQueued = false
let progressBarEl = null

// IntersectionObserver for pausing feature card videos when offscreen
let featureVideoObserver = null
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

onMounted(() => {
  const prefersReduced = prefersReducedMotion.value

  // Native smooth scroll — scoped to the landing page via a class on <html>
  document.documentElement.classList.add('landing-smooth')

  // Cross-route anchor support — if we arrived here via /#features (e.g. from
  // the SlideTabs nav on /pricing), wait a frame for layout, then scroll.
  // Uses the same 24px offset as SlideTabs.onAnchorClick.
  if (route.hash) {
    const id = route.hash.slice(1)
    if (id === 'top' || id === '') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } else {
      requestAnimationFrame(() => {
        const target = document.getElementById(id)
        if (target) {
          const y = target.getBoundingClientRect().top + window.scrollY - 24
          window.scrollTo({ top: y, behavior: 'smooth' })
        }
      })
    }
  }

  // Progress bar: single rAF-throttled listener, writes a CSS custom property
  progressBarEl = progressBar.value
  updateProgressBar()
  window.addEventListener('scroll', onScrollThrottled, { passive: true })

  // SlideTabs uses mix-blend-difference internally — it adapts to whatever's
  // beneath it without any per-section light/dark toggling. No GSAP nav triggers
  // needed anymore.

  if (!prefersReduced) {
    // ---- CHAPTER 2: Story Stack (FlowArt) ----
    // Verbatim mechanic from the FlowArt reference: stacking cards, each pinned at
    // its own bottom while the next slides in with a 30°→0° rotation pivoting on
    // bottom-left. Calls ScrollTrigger.refresh() at the end so pin positions are
    // recalculated after the document height changes from setup.
    const stackEls = storyCardEls.value
    if (stackEls && stackEls.length > 0) {
      stackEls.forEach((card, i) => {
        if (!card) return
        gsap.set(card, { zIndex: i + 1 })
        const inner = card.querySelector('.story-inner')
        if (!inner) return

        if (i > 0) {
          gsap.set(inner, { rotation: 30, transformOrigin: 'bottom left' })
          gsap.to(inner, {
            rotation: 0,
            ease: 'none',
            scrollTrigger: {
              trigger: card,
              start: 'top bottom',
              end: 'top 25%',
              scrub: true,
            },
          })
        }

        if (i < stackEls.length - 1) {
          ScrollTrigger.create({
            trigger: card,
            start: 'bottom bottom',
            end: 'bottom top',
            pin: true,
            pinSpacing: false,
          })
        }
      })

      // Force pin/scrub positions to recompute after layout settles.
      ScrollTrigger.refresh()
    }

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

    // (CTA background image animation removed — replaced by FooterAnimatedBoxes)

  } else {
    // ---- Reduced Motion Fallback ----
    // Story stack: cards display inline, no rotation
    storyCardEls.value?.forEach((card) => {
      if (!card) return
      card.style.position = 'relative'
      const inner = card.querySelector('.story-inner')
      if (inner) inner.style.transform = 'none'
    })

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

  // ---- Pause feature-card videos when offscreen ----
  // 5 videos all autoplaying simultaneously was a major perf hit. IntersectionObserver
  // pauses each video when its card scrolls out of view and resumes on re-entry.
  if (typeof IntersectionObserver !== 'undefined') {
    featureVideoObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const video = entry.target
          if (!(video instanceof HTMLVideoElement)) return
          if (entry.isIntersecting) {
            video.play().catch(() => { /* autoplay may be blocked — fine */ })
          } else {
            video.pause()
          }
        })
      },
      { rootMargin: '15% 0px 15% 0px', threshold: 0 },
    )
    // Defer until videos exist in DOM (after Vue paint)
    requestAnimationFrame(() => {
      document.querySelectorAll('.feature-card-bg video').forEach((v) => {
        featureVideoObserver?.observe(v)
      })
    })
  }
})

onBeforeUnmount(() => {
  ScrollTrigger.getAll().forEach(t => t.kill())
  window.removeEventListener('scroll', onScrollThrottled)
  document.documentElement.classList.remove('landing-smooth')
  progressBarEl = null
  if (featureVideoObserver) {
    featureVideoObserver.disconnect()
    featureVideoObserver = null
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

/* ── Navigation lives in SlideTabs.vue (mix-blend-difference pill) ── */

/* ══════════════════════════════════════ */
/* CHAPTER 1: HERO — SHADER (dark)       */
/* Live @paper-design/shaders-react WebGL — section is just a positioning frame. */
/* ══════════════════════════════════════ */
.chapter-hero {
  position: relative;
  min-height: 100dvh;
  width: 100%;
  overflow: hidden;
  background: #000;
}

.chapter-hero--shader {
  isolation: isolate;
}

/* The chapter "01" outline number sits on top of the shader in white at low opacity */
.chapter-num--on-shader {
  -webkit-text-stroke-color: rgba(255, 255, 255, 0.06) !important;
  z-index: 4;
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
/* CHAPTER 2: STORY STACK (cream)        */
/* Sticky cards that pin and stack, the next slides in rotated 30°→0° */
/* ══════════════════════════════════════ */
.chapter-stack {
  position: relative;
  width: 100%;
  overflow-x: hidden;
  background: var(--cream-bg);
}

.story-card {
  position: relative;
  min-height: 100vh;
  width: 100%;
  overflow: hidden;
  /* z-index set dynamically in GSAP onMounted so later cards sit above earlier ones */
}

.story-inner {
  position: relative;
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1.5vw;
  padding: clamp(2.5rem, 8vw, 6rem) clamp(2rem, 4vw, 5rem) 4vw;
  /* transform-origin set by GSAP for cards 1..N — first card never rotates. */
  will-change: transform;
}

.story-top {
  display: flex;
  align-items: baseline;
  gap: 24px;
}

.story-num {
  font-size: clamp(56px, 9vw, 140px);
  font-weight: 900;
  line-height: 0.85;
  letter-spacing: -3px;
  color: transparent;
  -webkit-text-stroke: 1.5px currentColor;
  opacity: 0.35;
}

.story-label {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  opacity: 0.7;
}

.story-divider {
  border: none;
  border-top: 1px solid currentColor;
  opacity: 0.18;
  margin: 0;
}

.story-headline {
  font-size: clamp(3.2rem, 11vw, 12rem);
  font-weight: 900;
  line-height: 0.88;
  letter-spacing: -2px;
  margin: 0;
}

.story-body {
  max-width: 52ch;
  font-size: clamp(1rem, 1.8vw, 1.6rem);
  font-weight: 400;
  line-height: 1.55;
  opacity: 0.78;
}

.story-meta {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  margin-top: auto;
  align-self: flex-start;
  padding-top: 0.5vw;
}

.story-accent-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
}

.story-cta-row {
  margin-top: auto;
  padding-top: 0.5vw;
}

.story-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: var(--story-accent, var(--land-orange));
  color: #fff !important;
  padding: 18px 36px;
  border-radius: 999px;
  font-size: 1.1rem;
  font-weight: 700;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  box-shadow: 0 8px 28px rgba(45, 37, 34, 0.12);
}

.story-cta:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 36px rgba(45, 37, 34, 0.18);
}

.story-cta svg {
  width: 18px;
  height: 18px;
}

/* ── Card themes (high-contrast alternating values) ──
   The background goes on the INNER (which is what GSAP rotates) so the entire
   surface tilts in together — exactly the FlowArt mechanic. The outer .story-card
   is just a clipping frame.

   Sequence: orange → noir → cream → forest → obsidian. Adjacent cards always
   invert in value, so each 30°→0° rotation reveals a dramatically different
   surface descending from the right side of the viewport.
*/
.story-card--peach .story-inner {
  background: linear-gradient(135deg, #E8660A 0%, #C85A00 100%);
  color: #FFFFFF;
  --story-accent: #1A1614;
}
.story-card--sage .story-inner {
  background: linear-gradient(135deg, #1F1A16 0%, #0F0C09 100%);
  color: #F5F0E8;
  --story-accent: #E8660A;
}
.story-card--slate .story-inner {
  background: linear-gradient(135deg, #F5F0E8 0%, #ECE5D8 100%);
  color: #1A1614;
  --story-accent: #E8660A;
}
.story-card--mauve .story-inner {
  background: linear-gradient(135deg, #2D332E 0%, #1B201D 100%);
  color: #F5F0E8;
  --story-accent: #D4B26A;
}
.story-card--amber .story-inner {
  background: linear-gradient(135deg, #0F0C09 0%, #1F1A16 100%);
  color: #F5F0E8;
  --story-accent: #E8660A;
}

/* Per-theme: tint label / chapter num / meta with each card's accent.
   On the orange card, accent text shifts to soft white instead of orange
   (orange-on-orange is illegible). */
.story-card--peach .story-label,
.story-card--peach .story-meta,
.story-card--peach .story-num { color: rgba(255, 255, 255, 0.85); }
.story-card--sage .story-label,
.story-card--sage .story-meta,
.story-card--sage .story-num { color: #E8660A; }
.story-card--slate .story-label,
.story-card--slate .story-meta,
.story-card--slate .story-num { color: #E8660A; }
.story-card--mauve .story-label,
.story-card--mauve .story-meta,
.story-card--mauve .story-num { color: #D4B26A; }
.story-card--amber .story-label,
.story-card--amber .story-meta,
.story-card--amber .story-num { color: #E8660A; }

/* Divider opacity tweaks — light dividers need higher opacity on dark cards,
   darker dividers need lower opacity on cream/orange cards. */
.story-card--peach .story-divider { border-top-color: rgba(0, 0, 0, 0.22); opacity: 1; }
.story-card--slate .story-divider { border-top-color: rgba(26, 22, 20, 0.18); opacity: 1; }
.story-card--sage .story-divider,
.story-card--mauve .story-divider,
.story-card--amber .story-divider { border-top-color: rgba(245, 240, 232, 0.16); opacity: 1; }

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

.feature-card-bg img,
.feature-card-bg video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Warm-tint legacy stock photos only — Remotion clips ship pre-toned */
.feature-card-bg img {
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
  /* Reference uses slate-900 — a cool dark that lets the slate-700 cell
     borders read clearly. */
  background: rgb(15 23 42);
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
  /* Legacy warm-dark overlay — superseded by .cta-boxes-mask above the
     boxes grid. Hidden so the new mask is the single source of truth. */
  display: none;
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

/* CTA chapter — boxes grid covers the whole section (z=0). The headline
   + button sit above at z=3; pointer events on .cta-content are disabled
   so hovers reach the boxes underneath, except the actual button. */
.chapter-cta .cta-boxes {
  z-index: 0;
}
.chapter-cta .cta-content {
  pointer-events: none;
}
.chapter-cta .cta-content .cta-btn {
  pointer-events: auto;
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
}

@media (max-width: 480px) {
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