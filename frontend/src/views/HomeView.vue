<template>
  <div class="hd" ref="rootEl" :style="{ '--accent': activeColor }">
    <!-- The Nifraim.com homepage. The wordmark sits in a big clear-glass circle over a
         Kling video of the lighthouse pulling back from its lantern window. Every scroll
         opens the next chapter (Nifra Agent · Nifra Calls · Nifra Report · portal) in its
         own product colour; a dusk lighthouse closes the page. Scroll engine = one rAF
         that writes --p / --e (0→1) per chapter. Keep this comment INSIDE the root: a
         root-level comment makes a fragment that the app's page <transition> can't animate. -->
    <div class="hd-progress" :style="{ transform: `scaleX(${pageP})` }" aria-hidden="true"></div>

    <!-- ── Top tabs (shared with the other public pages) ── -->
    <SiteNav home :active="active" :solid="scrolled" @go="go" @brand-hover="beamOn = $event" />

    <!-- ── 00 HERO — Nifraim.com over the control tower ── -->
    <section id="top" class="hero" data-ch="top" :ref="setCh">
      <div class="hero-stick">
        <div class="hero-photo">
          <!-- plays once: from the lantern window back to the full view, then holds on the still -->
          <video
            v-if="!reduced && !videoFailed" ref="heroPhotoEl" class="hero-video" :class="{ 'hero-video--done': heroLanded }"
            :poster="heroFirst" muted playsinline autoplay preload="auto"
            @loadedmetadata="measure" @ended="heroLanded = true"
          >
            <source :src="heroVideoWebm" type="video/webm" />
            <source :src="heroVideo" type="video/mp4" @error="videoFailed = true; heroLanded = true" />
          </video>
          <img v-else ref="heroPhotoEl" :src="img.hero" alt="" fetchpriority="high" @load="measure" />
        </div>
        <div class="beam" :class="{ 'beam--on': beamOn && heroLanded }" aria-hidden="true">
          <span class="beam-cone"></span>
          <span class="beam-cone beam-cone--back"></span>
          <span class="beam-lamp"></span>
        </div>
        <div class="hero-veil" aria-hidden="true"></div>
        <span class="ring ring--a" aria-hidden="true"></span>
        <span class="ring ring--b" aria-hidden="true"></span>
        <span class="ring ring--c" aria-hidden="true"></span>

        <div class="hero-circle" aria-hidden="true"></div>
        <div class="hero-copy">
          <h1 class="hero-word" :class="{ 'word-lit': beamOn && heroLanded }" dir="ltr" aria-label="Nifraim.com — המגדלור של סוכני הביטוח" @mouseenter="beamOn = true" @mouseleave="beamOn = false">
            <span v-for="(ch, i) in 'Nifraim'" :key="'n' + i" class="hw-ch" :style="{ '--i': i }">{{ ch }}</span><span class="hw-com"><span ref="kickerEl" class="hw-kicker" dir="rtl" aria-hidden="true">המגדלור של סוכני הביטוח</span><span
              v-for="(ch, i) in '.com'" :key="'c' + i" class="hw-ch hw-ch--com" :style="{ '--i': i + 7 }">{{ ch }}</span></span>
          </h1>
          <p class="hero-line rv" style="--d: 0.9s">עמלות<i class="hl-dot"></i>לקוחות<i class="hl-dot"></i>שיחות<i class="hl-dot"></i>דוחות</p>
          <div class="hero-cta rv" style="--d: 1.05s">
            <router-link to="/signup" class="hd-btn hd-btn--lg">התחילו עכשיו</router-link>
            <a href="#agent" class="hd-btn hd-btn--lg hd-btn--ghost" @click.prevent="go('agent')">גלו את Nifra</a>
          </div>
        </div>

        <button class="hero-cue" type="button" aria-label="גללו למטה" @click="go('agent')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
        </button>
      </div>
    </section>

    <!-- ── 01–03 Products ── -->
    <section
      v-for="(c, n) in chapters" :key="c.id" :id="c.id"
      class="ch" :class="['ch--' + c.id, { 'ch--dark': c.dark }]"
      :data-ch="c.id" :ref="setCh"
      :style="{ '--c': c.color, '--ci': c.ink, '--cw': c.wash, '--cbg': c.bg }"
    >
      <div class="ch-stick">
        <div v-if="c.img" class="ch-photo" aria-hidden="true"><img :src="c.img" alt="" loading="lazy" /></div>
        <span class="ring ring--a" aria-hidden="true"></span>
        <span class="ring ring--b" aria-hidden="true"></span>

        <div class="ch-body">
          <span class="ch-num ltr-number" aria-hidden="true">{{ String(n + 1).padStart(2, '0') }}</span>
          <p class="ch-kicker rv">{{ c.kicker }}</p>
          <h2 class="ch-title" dir="ltr">
            <span class="ct-w"><span class="ct-in">Nifra</span></span>
            <span class="ct-w"><span class="ct-in ct-in--c" style="--d: 0.12s">{{ c.word }}</span></span>
          </h2>
          <p class="ch-line rv" style="--d: 0.3s">{{ c.line }}</p>
          <ul class="ch-points">
            <li v-for="(pt, k) in c.points" :key="k" class="rv" :style="{ '--d': 0.42 + k * 0.1 + 's' }">
              <span class="ch-dot" aria-hidden="true"></span>{{ pt }}
            </li>
          </ul>
        </div>

        <div class="ch-orb" aria-hidden="true">
          <span class="ch-orb-glow"></span>
          <CallsOrb v-if="c.id === 'call'" class="ch-callorb" :size="callOrbSize" state="recording" :level="voiceLevel" />
          <span v-else class="ch-orb-disc">
            <ThinkingOrbIsland class="ch-orb-canvas" :state="c.orb" :size="64" :color="c.color"
              :theme="c.dark ? 'dark' : 'light'" :dot-size="1.35" :dots="1.15" />
          </span>
          <span v-if="c.id !== 'call'" class="ch-orb-cap" dir="ltr">Nifra <b>{{ c.word }}</b></span>


        </div>
      </div>
    </section>

    <!-- ── 04 Portal — one big clean circle ── -->
    <section id="portal" class="pt" data-ch="portal" :ref="setCh">
      <div class="pt-stick">
        <div class="pt-head">
          <span class="ch-num ltr-number" aria-hidden="true">04</span>
          <p class="ch-kicker rv">פורטל לקוחות</p>
          <h2 class="pt-title rv" style="--d: 0.1s">הלקוח רואה את התיק שלו.<br /><em>רק מה שצריך.</em></h2>
        </div>
        <div class="pt-circle" aria-hidden="true">
          <!-- a slow push toward the arch, played when the circle comes into view -->
          <video
            v-if="!reduced && !portalFailed" ref="portalVideoEl" :poster="portalFirst" muted playsinline preload="auto"
          >
            <source :src="portalVideoWebm" type="video/webm" />
            <source :src="portalVideo" type="video/mp4" @error="portalFailed = true" />
          </video>
          <img v-else :src="img.portal" alt="" loading="lazy" />
        </div>
        <ul class="pt-feats">
          <li v-for="(f, k) in portalFeats" :key="f.t" class="pt-feat rv" :style="{ '--d': 0.2 + k * 0.12 + 's' }">
            <span class="pt-ico" v-html="f.icon"></span>
            <b>{{ f.t }}</b>
            <span>{{ f.d }}</span>
          </li>
        </ul>
      </div>
    </section>

    <!-- ── CTA ── -->
    <section id="start" class="cta" data-ch="start" :ref="setCh">
      <div class="cta-photo" aria-hidden="true">
        <video
          v-if="!reduced && !ctaFailed" ref="ctaMediaEl" :poster="ctaFirst" muted playsinline preload="auto"
          @loadedmetadata="measure" @ended="ctaLanded = true"
        >
          <source :src="ctaVideoWebm" type="video/webm" />
          <source :src="ctaVideo" type="video/mp4" @error="ctaFailed = true; ctaLanded = true" />
        </video>
        <img v-else ref="ctaMediaEl" :src="img.cta" alt="" loading="lazy" @load="measure" />
      </div>
      <!-- after the pull-back lands the lamp keeps turning: one slow beam, always on -->
      <div class="beam beam--cta" :class="{ 'beam--on': ctaLanded }" aria-hidden="true">
        <span class="beam-cone"></span>
        <span class="beam-cone beam-cone--back"></span>
        <span class="beam-lamp"></span>
      </div>
      <div class="cta-veil" aria-hidden="true"></div>
      <div class="cta-in">
        <!-- the glow lives on an inner span: a :class on the .rv element itself would wipe the
             IntersectionObserver's rv--in class on re-render and hide the wordmark -->
        <p class="cta-word rv" dir="ltr" style="--d: 0.1s"><span :class="{ 'word-lit': ctaLanded }">Nifraim<span>.com</span></span></p>
        <router-link to="/signup" class="hd-btn hd-btn--lg rv" style="--d: 0.25s">התחילו עכשיו</router-link>
      </div>
    </section>

    <footer class="hd-foot">
      <span class="hd-brand hd-brand--sm" dir="ltr">Nifraim<span>.com</span></span>
      <nav>
        <router-link to="/pricing">תמחור</router-link>
        <router-link to="/login">התחברות</router-link>
        <a href="/privacy">מדיניות פרטיות</a>
      </nav>
      <span class="ltr-number">© 2026 Nifraim</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import SiteNav from '../components/site/SiteNav.vue'
import ThinkingOrbIsland from '../components/workspace/ThinkingOrbIsland.vue'
import CallsOrb from '../components/calls/CallsOrb.vue'
import heroImg from '../assets/home/hero.webp'
import heroFirst from '../assets/home/hero-first.webp'
import ctaFirst from '../assets/home/cta-first.webp'
import portalFirst from '../assets/home/portal-first.webp'
import agentImg from '../assets/home/agent.webp'
import callsImg from '../assets/home/calls.webp'
import reportImg from '../assets/home/report.webp'
import portalImg from '../assets/home/portal.webp'
import ctaImg from '../assets/home/cta.webp'

const img = { hero: heroImg, portal: portalImg, cta: ctaImg }
// new URL (not import) so the page still renders while the video file is being produced
const heroVideo = new URL('../assets/home/hero.mp4', import.meta.url).href
const heroVideoWebm = new URL('../assets/home/hero.webm', import.meta.url).href
const heroLanded = ref(false)
const videoFailed = ref(false)
const ctaVideo = new URL('../assets/home/cta.mp4', import.meta.url).href
const ctaVideoWebm = new URL('../assets/home/cta.webm', import.meta.url).href
const ctaMediaEl = ref(null)
const ctaLanded = ref(false)
const ctaFailed = ref(false)
const portalVideo = new URL('../assets/home/portal.mp4', import.meta.url).href
const portalVideoWebm = new URL('../assets/home/portal.webm', import.meta.url).href
const portalVideoEl = ref(null)
const portalFailed = ref(false)

// Product colours (the brand table): accent for marks/decoration, ink for text.
const chapters = [
  {
    id: 'agent', word: 'Agent', orb: 'connecting', img: agentImg,
    color: '#0E8C8A', ink: '#0A6664', wash: 'rgba(14,140,138,0.08)', bg: '#FFFFFF',
    kicker: 'סוכן המשרד',
    line: 'המגדלור של התיק שלך. מזהה הזדמנות, מניע צמיחה.',
    points: ['קורא את המייל של המשרד', 'רודף אחרי עמלות שלא שולמו'],
  },
  {
    id: 'call', word: 'Calls', orb: 'listening', img: callsImg,
    color: '#D96AB5', ink: '#A63A86', wash: 'rgba(217,106,181,0.08)', bg: '#FFFFFF',
    kicker: 'שיחות',
    line: 'מקליטים, מתמללים, מסכמים — בעברית מושלמת.',
    points: ['תמלול עברית מדויק', 'סיכום ומשימות להמשך', 'מכתב סיכום ללקוח'],
  },
  {
    id: 'report', word: 'Report', orb: 'shaping', img: reportImg, dark: true,
    color: '#8F8BEA', ink: '#C9C6FF', wash: 'rgba(143,139,234,0.12)', bg: '#2E2A8C',
    kicker: 'דוחות',
    line: 'דוח חתום ומסודר. מוכן ללקוח, מוכן לבעלים.',
    points: ['פרודוקציה ונפרעים בדוח אחד', 'חודש מול חודש, חברה מול חברה', 'מוכן להדפסה ולשיתוף'],
  },
]

const COLORS = { top: '#2F73C4', agent: '#0E8C8A', call: '#D96AB5', report: '#2E2A8C', portal: '#4E9DD0', start: '#2F73C4' }

const portalFeats = [
  { t: 'קישור מאובטח', d: 'סיסמה, תוקף, והגנה מפני ניחוש',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>' },
  { t: 'התיק במבט אחד', d: 'פרמיה, צבירה ומוצרים לפי חברה',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 3v9l6 5"/></svg>' },
  { t: 'שינויים לאורך זמן', d: 'מה השתנה מאז הפעם הקודמת',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>' },
]

/* ── scroll engine ── */
const rootEl = ref(null)
const chEls = []
function setCh(el) { if (el && !chEls.includes(el)) chEls.push(el) }

const active = ref('top')
const scrolled = ref(false)
const pageP = ref(0)
const activeColor = computed(() => COLORS[active.value] || '#2F73C4')

const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
let raf = 0
let io = null
let ctaIo = null
let portalIo = null

// a speaking voice for the Call orb: two slow sines + a little grain, 0..1
const voiceLevel = () => {
  const t = performance.now() / 1000
  return Math.max(0, 0.45 + 0.3 * Math.sin(t * 5.3) * Math.sin(t * 1.7) + 0.12 * Math.sin(t * 13.1))
}
const callOrbSize = ref(260)

// Lighthouse beam — hovering "Nifraim" lights the lamp. The lamp's spot in the
// source photo (fractions of the cropped hero.webp), mapped through object-fit
// cover + the hero's scroll scale so the beam starts exactly at the lantern.
const LAMP = { x: 0.818, y: 0.450, iw: 1920, ih: 1080 }
const beamOn = ref(false)
const heroPhotoEl = ref(null)
function placeLamp(heroEl, p) {
  lampOn(heroEl, heroPhotoEl.value, LAMP, 1.08 - p * 0.06, p * 0.04)
}
// Same mapping for the dusk CTA: its media scales 1.15 → 1 as the chapter enters (--e)
const LAMP_CTA = { x: 0.853, y: 0.513, iw: 1920, ih: 1080 }
function lampOn(target, img, L, k, dyFrac) {
  if (!img) return
  const W = img.clientWidth, H = img.clientHeight
  const sc = Math.max(W / L.iw, H / L.ih)
  const dw = L.iw * sc, dh = L.ih * sc
  const pos = getComputedStyle(img).objectPosition.split(' ').map(v => parseFloat(v) / 100)
  let x = (W - dw) * pos[0] + L.x * dw
  let y = (H - dh) * pos[1] + L.y * dh
  x = W / 2 + (x - W / 2) * k
  y = H / 2 + (y - H / 2) * k - dyFrac * H
  target.style.setProperty('--lx', x.toFixed(1) + 'px')
  target.style.setProperty('--ly', y.toFixed(1) + 'px')
}

function measure() {
  const vh = window.innerHeight
  const y = window.scrollY
  const doc = document.documentElement.scrollHeight - vh
  pageP.value = doc > 0 ? Math.min(1, y / doc) : 0
  scrolled.value = y > 24
  let cur = 'top'
  for (const el of chEls) {
    const r = el.getBoundingClientRect()
    const span = Math.max(1, el.offsetHeight - vh)
    const p = reduced ? 1 : Math.min(1, Math.max(0, -r.top / span))
    // --e: how far the chapter has entered from below (0 → 1 as its top reaches the viewport top)
    const e = reduced ? 1 : Math.min(1, Math.max(0, 1 - r.top / vh))
    el.style.setProperty('--p', p.toFixed(4))
    if (el.dataset.ch === 'top') placeLamp(el, p)
    if (el.dataset.ch === 'start') lampOn(el, ctaMediaEl.value, LAMP_CTA, 1.15 - e * 0.15, 0)
    el.style.setProperty('--e', e.toFixed(4))
    if (r.top <= vh * 0.45) cur = el.dataset.ch
  }
  if (cur !== active.value) active.value = cur
}
function onScroll() {
  if (raf) return
  raf = requestAnimationFrame(() => { raf = 0; measure() })
}
function go(id) {
  const el = id === 'top' ? document.body : document.getElementById(id)
  if (!el) return
  // land where the chapter is fully "open" (a little past its top)
  const extra = id === 'top' ? 0 : Math.min(window.innerHeight * 0.55, el.offsetHeight - window.innerHeight)
  const top = id === 'top' ? 0 : el.getBoundingClientRect().top + window.scrollY + Math.max(0, extra)
  window.scrollTo({ top, behavior: reduced ? 'auto' : 'smooth' })
}

// The kicker must exactly span ".com" and sit a hair above its letters, whatever font
// the machine renders: measure the ".com" box and the "com" glyph top, then fit.
const kickerEl = ref(null)
function fitKicker() {
  const k = kickerEl.value, com = k?.parentElement
  if (!k || !com) return
  const cs = getComputedStyle(com)
  const H = parseFloat(cs.fontSize)
  const comW = com.getBoundingClientRect().width
  // measure the kicker as the browser actually draws it, at a known size
  k.style.fontSize = '100px'
  const kw100 = k.getBoundingClientRect().width
  const size = Math.max(9, Math.min(H * 0.15, (comW * 0.72 / kw100) * 100))
  // top of the "com" letters, using the wordmark's own computed font
  const ctx = document.createElement('canvas').getContext('2d')
  ctx.font = `${cs.fontWeight} ${H}px ${cs.fontFamily}`
  const m = ctx.measureText('com')
  const lh = com.getBoundingClientRect().height
  const baseline = (lh - (m.fontBoundingBoxAscent + m.fontBoundingBoxDescent)) / 2 + m.fontBoundingBoxAscent
  const glyphTop = baseline - m.actualBoundingBoxAscent
  k.style.fontSize = size.toFixed(2) + 'px'
  const kh = k.getBoundingClientRect().height
  const gap = Math.max(5, H * 0.07)
  k.style.bottom = 'auto'
  k.style.top = (glyphTop - gap - kh).toFixed(1) + 'px'
  // right-aligned (RTL start): its right edge meets the right edge of the "m"
  k.style.left = 'auto'
  k.style.right = (H * 0.08).toFixed(1) + 'px'
  k.style.translate = '0 0'
}

// A refresh must open on the hero, not wherever the browser last scrolled to
let prevRestoration = 'auto'
onMounted(() => {
  prevRestoration = history.scrollRestoration
  history.scrollRestoration = 'manual'
  if (!location.hash) window.scrollTo(0, 0)
  document.documentElement.classList.add('hd-html')
  if (reduced) heroLanded.value = true
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll)
  window.addEventListener('resize', fitKicker)
  io = new IntersectionObserver((entries) => {
    for (const en of entries) if (en.isIntersecting) { en.target.classList.add('rv--in'); io.unobserve(en.target) }
  }, { threshold: 0.2 })
  rootEl.value.querySelectorAll('.rv, .ch-title, .pt-circle').forEach((el) => io.observe(el))
  ctaIo = new IntersectionObserver((entries) => {
    if (entries.some(en => en.isIntersecting)) { ctaMediaEl.value?.play?.().catch(() => { ctaLanded.value = true }); ctaIo.disconnect() }
  }, { threshold: 0.5 })
  portalIo = new IntersectionObserver((entries) => {
    if (entries.some(en => en.isIntersecting)) { portalVideoEl.value?.play?.().catch(() => {}); portalIo.disconnect() }
  }, { threshold: 0.35 })
  const ptCircle = rootEl.value.querySelector('.pt-circle')
  if (ptCircle) portalIo.observe(ptCircle)
  const ctaSec = document.getElementById('start')
  if (ctaSec) ctaIo.observe(ctaSec)
  if (reduced) ctaLanded.value = true
  measure()
  fitKicker()
  document.fonts?.ready?.then(fitKicker)
  setTimeout(fitKicker, 1200) // again once the letters have finished animating in
  callOrbSize.value = window.innerWidth <= 960 ? 190 : 300
  requestAnimationFrame(() => rootEl.value?.classList.add('hd--ready'))
})
onBeforeUnmount(() => {
  history.scrollRestoration = prevRestoration
  document.documentElement.classList.remove('hd-html')
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onScroll)
  window.removeEventListener('resize', fitKicker)
  cancelAnimationFrame(raf)
  io?.disconnect()
  ctaIo?.disconnect()
  portalIo?.disconnect()
})
</script>

<style>
/* page-level: the demo owns the whole canvas while mounted */
html.hd-html, html.hd-html body { background: #FFFFFF; overflow-x: clip; }
</style>

<style scoped>
.hd {
  --ink: #181818;
  --graphite: #2A2E35; /* the "Nifraim" of the wordmark — a softer black */
  --blue: #2F73C4;
  --muted: #5B6470;
  --ease: cubic-bezier(0.22, 1, 0.36, 1);
  font-family: 'Heebo', sans-serif; color: var(--ink); background: #FFFFFF;
  direction: rtl; overflow-x: clip;
}

/* progress */
.hd-progress {
  position: fixed; inset: 0 0 auto 0; height: 3px; z-index: 120; transform-origin: right;
  background: var(--accent); transition: background 0.6s ease;
}

/* the brand in the footer */
.hd-brand { font-weight: 900; font-size: 20px; letter-spacing: -0.03em; color: var(--graphite); text-decoration: none; }
.hd-brand span { color: var(--blue); }
.hd-brand--sm { font-size: 18px; }

.hd-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 9px 18px; border-radius: 10px; border: 1px solid transparent;
  background: var(--ink); color: #FFFFFF; font: 700 14px 'Heebo', sans-serif; text-decoration: none; cursor: pointer;
  box-shadow: 0 6px 18px rgba(24, 24, 24, 0.18); transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
}
.hd-btn:hover { transform: translateY(-1px); background: #000; box-shadow: 0 10px 24px rgba(24, 24, 24, 0.24); }
.hd-btn--ghost { background: transparent; color: var(--ink); border-color: rgba(24, 24, 24, 0.16); box-shadow: none; }
.hd-btn--ghost:hover { background: rgba(24, 24, 24, 0.05); box-shadow: none; }
.hd-btn--lg { padding: 14px 28px; font-size: 16px; border-radius: 12px; }

/* ── reveal ── */
.rv { opacity: 0; transform: translateY(40px); transition: opacity 1s var(--ease) var(--d, 0s), transform 1.2s var(--ease) var(--d, 0s); }
.rv--in { opacity: 1; transform: none; }

/* ── big decorative rings ── */
.ring { position: absolute; border-radius: 50%; pointer-events: none; border: 1px solid var(--rc, rgba(47, 115, 196, 0.22)); }
.ring--a { width: 72vmax; height: 72vmax; top: 50%; left: 50%; margin: -36vmax 0 0 -36vmax; animation: ringSpin 60s linear infinite; border-style: dashed; }
.ring--b { width: 52vmax; height: 52vmax; top: 50%; left: 50%; margin: -26vmax 0 0 -26vmax; }
.ring--c { width: 92vmax; height: 92vmax; top: 50%; left: 50%; margin: -46vmax 0 0 -46vmax; opacity: 0.6; }
@keyframes ringSpin { to { transform: rotate(360deg); } }

/* ═════ HERO ═════ */
.hero { position: relative; height: 210vh; --p: 0; }
.hero-stick { position: sticky; top: 0; height: 100vh; overflow: hidden; display: grid; place-items: center; }
.hero-photo { position: absolute; inset: 0; overflow: hidden; }
.hero-photo img, .hero-photo video {
  width: 100%; height: 100%; object-fit: cover; object-position: 50% 60%;
  transform: scale(calc(1.08 - var(--p) * 0.06)) translateY(calc(var(--p) * -4%));
}
.hero-veil {
  position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse 60% 55% at 50% 52%, rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0) 70%),
              linear-gradient(to bottom, rgba(255, 255, 255, 0) 70%, rgba(255, 255, 255, 0.6));
}
.hero .ring { --rc: rgba(255, 255, 255, 0.45); }
/* lighthouse beam — off until "Nifraim" is hovered; then the lamp wakes and
   one soft cone sweeps slowly across the sky (a lighthouse turning) */
.beam { position: absolute; inset: 0; pointer-events: none; z-index: 1; opacity: 0; transition: opacity 0.9s ease; }
.beam--on { opacity: 1; }
/* a touch of dusk so the light reads against the bright sky */
.beam::before { content: ''; position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(18, 38, 70, 0.22), rgba(18, 38, 70, 0.08) 70%, rgba(18, 38, 70, 0)); }
.beam-lamp {
  position: absolute; left: var(--lx, 70%); top: var(--ly, 40%); width: 90px; height: 90px; margin: -45px 0 0 -45px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 252, 235, 1) 0%, rgba(255, 244, 200, 0.75) 22%, rgba(255, 240, 190, 0) 70%);
  filter: blur(3px); animation: lampPulse 6s ease-in-out infinite;
}
@keyframes lampPulse { 50% { transform: scale(1.1); opacity: 0.85; } }
.beam-cone {
  position: absolute; left: var(--lx, 70%); top: var(--ly, 40%); width: 130vw; height: 34vh; translate: -100% -50%;
  transform-origin: 100% 50%;
  background: linear-gradient(to left, rgba(255, 246, 215, 0.6), rgba(255, 246, 215, 0.26) 30%, rgba(255, 246, 215, 0) 78%);
  clip-path: polygon(100% 49%, 0 0, 0 100%, 100% 51%);
  filter: blur(12px);
  animation: beamSweep 12s ease-in-out infinite;
}
/* the far side of the turning lens: fainter, out over the hill */
.beam-cone--back { translate: 0 -50%; transform-origin: 0 50%; width: 60vw; opacity: 0.3;
  background: linear-gradient(to right, rgba(255, 250, 225, 0.8), rgba(255, 250, 225, 0) 70%);
  clip-path: polygon(0 49%, 100% 0, 100% 100%, 0 51%); animation-delay: -6s; }
@keyframes beamSweep {
  0%, 100% { transform: scaleX(1) rotate(-2deg); opacity: 0.9; }
  50% { transform: scaleX(0.45) rotate(2deg); opacity: 0.3; }
}
.hero-word { cursor: default; }
.beam--cta { z-index: 0; }
/* the lighthouse lights the wordmark: a warm glow that swells each time the beam
   sweeps toward it (same 7s cycle as beamSweep) */
.word-lit .hw-ch, .cta-word .word-lit { animation: wordLit 12s ease-in-out infinite; }
.hd--ready .word-lit .hw-ch { animation: chIn 1.1s var(--ease) calc(0.25s + var(--i) * 0.055s) forwards, wordLit 12s ease-in-out infinite; }
@keyframes wordLit {
  0%, 100% { text-shadow: 0 0 16px rgba(255, 242, 210, 0.7), 0 0 44px rgba(255, 234, 180, 0.45), 0 0 90px rgba(255, 228, 160, 0.25); }
  50% { text-shadow: 0 0 8px rgba(255, 240, 200, 0.35), 0 0 22px rgba(255, 232, 170, 0.2); }
}
.hero-word .hw-ch, .cta-word { transition: text-shadow 0.8s ease; }
.beam--cta::before { display: none; }
.beam--cta .beam-cone { opacity: 0.7; }
.hd-brand { transition: text-shadow 0.6s ease; }
.hd-brand:hover { text-shadow: 0 0 18px rgba(255, 236, 170, 0.9); }

.ch-callorb { position: relative; }

/* the big circle — grows with scroll until it IS the next page */
.hero-circle {
  position: absolute; top: 50%; left: 50%;
  width: min(94vw, 1040px); aspect-ratio: 1; border-radius: 50%;
  translate: -50% -50%;
  /* clear glass: the photo stays real — only a soft wash behind the type */
  background: radial-gradient(circle, rgba(255, 255, 255, calc(0.5 + var(--p) * 0.5)) 0%, rgba(255, 255, 255, calc(0.16 + var(--p) * 0.84)) 62%, rgba(255, 255, 255, calc(0.06 + var(--p) * 0.94)) 100%);
  box-shadow: 0 0 0 1.5px rgba(255, 255, 255, 0.85) inset, 0 0 0 10px rgba(255, 255, 255, 0.12), 0 40px 120px rgba(20, 50, 90, 0.12);
  transform: scale(calc(0.86 + var(--p) * var(--p) * 2.4));
  animation: circleIn 1.4s var(--ease) both;
}
@keyframes circleIn { from { opacity: 0; scale: 0.6; } to { opacity: 1; scale: 1; } }
.hero-copy {
  position: relative; z-index: 2; text-align: center; padding: 0 16px;
  display: flex; flex-direction: column; align-items: center; gap: 18px;
  transform: translateY(calc(var(--p) * -60px)) scale(calc(1 - var(--p) * 0.12));
  opacity: calc(1 - var(--p) * 1.6);
}
.hero-kicker { margin: 0; font-size: 15px; font-weight: 700; letter-spacing: 0.02em; color: #2B3138; }
.hero-word {
  margin: 0; font-weight: 900; line-height: 0.95; letter-spacing: -0.05em;
  font-size: clamp(54px, 11.5vw, 168px); color: var(--graphite); white-space: nowrap;
}
.hw-ch { display: inline-block; opacity: 0; transform: translateY(0.5em) rotate(4deg); filter: blur(10px); }
.hd--ready .hw-ch { animation: chIn 1.1s var(--ease) calc(0.25s + var(--i) * 0.055s) forwards; }
.hw-ch--com { color: var(--blue); }
.hw-com { position: relative; display: inline-block; }
/* sits right above ".com", sized to its width (≈0.155em of the wordmark) */
.hw-kicker {
  /* size + top are MEASURED in fitKicker() (fonts differ per machine); these are the first-paint guesses */
  position: absolute; bottom: 100%; left: 50%; translate: -50% 1.55em; white-space: nowrap;
  font-size: max(11.5px, 0.14em); font-weight: 700; letter-spacing: 0; line-height: 1; color: #2B3138;
  opacity: 0; animation: chIn 1s var(--ease) 1s forwards;
}
@keyframes chIn { to { opacity: 1; transform: none; filter: blur(0); } }
.hero-line { margin: 0; font-size: clamp(17px, 1.6vw, 22px); font-weight: 500; color: #2B3138; }
.hero-line { display: inline-flex; align-items: center; gap: 14px; }
.hl-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--blue); opacity: 0.7; }
.hero-cta { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin-top: 6px; }
.hero-cue {
  position: absolute; bottom: 28px; left: 50%; translate: -50% 0; z-index: 3;
  width: 46px; height: 46px; border-radius: 50%; border: 1px solid rgba(24, 24, 24, 0.18);
  background: rgba(255, 255, 255, 0.7); color: var(--ink); cursor: pointer; display: grid; place-items: center;
  opacity: calc(1 - var(--p) * 4); animation: cue 2.2s ease-in-out infinite;
}
.hero-cue svg { width: 20px; height: 20px; }
@keyframes cue { 50% { transform: translateY(6px); } }

/* ═════ PRODUCT CHAPTERS ═════ */
.ch { position: relative; height: 240vh; background: var(--cbg); --p: 0; --e: 0; }
.ch-stick {
  position: sticky; top: 0; height: 100vh; overflow: hidden;
  display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); align-items: center;
  padding: 90px clamp(16px, 6vw, 96px) 40px; gap: clamp(16px, 4vw, 64px);
}
.ch .ring { --rc: color-mix(in srgb, var(--c) 26%, transparent); }
.ch .ring--a { left: 26%; }
.ch .ring--b { left: 26%; }
/* photo opens out of a circle centred on the orb, then settles masked into the page */
.ch-photo {
  position: absolute; inset: 0; pointer-events: none;
  /* the photo opens from the orb as a SOFT, feathered circle (a hard clip read as
     a cut-out disc behind the orb), fades toward the text and out at the bottom */
  --open: radial-gradient(circle at 27% 52%, #000 calc(var(--p) * 140vmax - 14vmax), transparent calc(var(--p) * 140vmax + 6vmax));
  -webkit-mask-image: var(--open), linear-gradient(to left, transparent 30%, #000 62%), linear-gradient(to top, transparent 0, #000 22%);
          mask-image: var(--open), linear-gradient(to left, transparent 30%, #000 62%), linear-gradient(to top, transparent 0, #000 22%);
  -webkit-mask-composite: source-in, source-in; mask-composite: intersect;
}
.ch-photo img {
  width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1) scale(calc(1.22 - var(--p) * 0.22));
}
.ch-body { position: relative; z-index: 2; grid-column: 1; display: flex; flex-direction: column; gap: 18px; }
.ch-num {
  font-weight: 900; font-size: clamp(64px, 9vw, 132px); line-height: 0.8; letter-spacing: -0.04em;
  align-self: flex-start; direction: ltr;
  color: transparent; -webkit-text-stroke: 1.5px color-mix(in srgb, var(--c) 55%, transparent);
  transform: translateY(calc((1 - var(--e)) * 80px)); opacity: var(--e);
}
.ch-kicker { margin: 0; font-size: 15px; font-weight: 700; color: var(--ci); letter-spacing: 0.02em; }
.ch-title {
  margin: 0; display: flex; gap: 0.22em; justify-content: flex-end;
  font-weight: 900; font-size: clamp(50px, 7.6vw, 128px); line-height: 0.92; letter-spacing: -0.05em; color: var(--ink);
}
.ct-w { display: inline-block; overflow: hidden; padding: 0 0.08em 0.1em; margin: 0 -0.08em; }
.ct-in { display: inline-block; transform: translateY(105%); transition: transform 1.2s var(--ease) var(--d, 0s); }
.ct-in--c { color: var(--ci); }
.ch-title.rv--in .ct-in { transform: none; }
.ch-line { margin: 0; max-width: 30ch; font-size: clamp(19px, 1.9vw, 26px); font-weight: 500; line-height: 1.45; color: #2B3138; }
.ch-points { list-style: none; margin: 6px 0 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.ch-points li { display: flex; align-items: center; gap: 12px; font-size: 16px; font-weight: 500; color: var(--muted); }
.ch-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); box-shadow: 0 0 0 5px var(--cw); flex: none; }

.ch-orb {
  position: relative; z-index: 2; grid-column: 2; justify-self: center;
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  transform: translateY(calc((1 - var(--e)) * 120px)) scale(calc(0.8 + var(--e) * 0.2));
}
.ch-orb-glow {
  position: absolute; top: 50%; left: 50%; width: 420px; height: 420px; margin: -250px 0 0 -210px; border-radius: 50%;
  background: conic-gradient(from 0deg, transparent, color-mix(in srgb, var(--c) 40%, transparent), transparent 60%);
  filter: blur(40px); opacity: 0.8; animation: ringSpin 12s linear infinite; pointer-events: none;
}
.ch-orb-disc {
  position: relative; width: clamp(180px, 22vw, 300px); aspect-ratio: 1; border-radius: 50%; display: grid; place-items: center;
  background: radial-gradient(circle at 35% 30%, #FFFFFF 0%, color-mix(in srgb, var(--c) 8%, #FFFFFF) 60%, color-mix(in srgb, var(--c) 18%, #FFFFFF) 100%);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 25%, transparent), 0 30px 80px color-mix(in srgb, var(--c) 30%, transparent);
  animation: breathe 5s ease-in-out infinite;
}
.ch-orb-canvas { width: 64px; height: 64px; transform: scale(2.6); } /* sized so the reduced-motion static dot shows */
@media (min-width: 1100px) { .ch-orb-canvas { transform: scale(3.2); } }
@keyframes breathe { 50% { transform: scale(1.03); } }
.ch-orb-cap {
  padding: 6px 16px; border-radius: 999px; font-size: 15px; font-weight: 600; color: var(--ink);
  background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(8px); box-shadow: 0 4px 16px rgba(24, 24, 24, 0.08);
}
.ch-orb-cap b { color: var(--ci); font-weight: 900; }

/* Report = the dark chapter */
.ch--dark { color: #FFFFFF; }
.ch--dark .ch-title { color: #FFFFFF; }
.ch--dark .ch-line { color: rgba(255, 255, 255, 0.86); }
.ch--dark .ch-points li { color: rgba(255, 255, 255, 0.72); }
.ch--dark .ch-photo { -webkit-mask-image: var(--open), linear-gradient(to left, transparent 32%, #000 70%), linear-gradient(to top, transparent 0, #000 22%); mask-image: var(--open), linear-gradient(to left, transparent 32%, #000 70%), linear-gradient(to top, transparent 0, #000 22%); }
.ch--dark .ch-orb-disc {
  background: radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.04) 70%);
  backdrop-filter: blur(10px); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18), 0 30px 80px rgba(0, 0, 0, 0.35);
}
.ch--dark .ch-orb-cap { background: rgba(255, 255, 255, 0.1); color: #FFFFFF; }

/* ═════ PORTAL ═════ */
.pt { position: relative; height: 200vh; background: #FFFFFF; --p: 0; --e: 0; }
.pt-stick {
  position: sticky; top: 0; height: 100vh; overflow: hidden;
  display: grid; grid-template-rows: auto 1fr auto; justify-items: center; align-items: center;
  padding: 90px 16px 28px; gap: 14px; text-align: center;
}
.pt-head { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.pt-head .ch-num { --c: #4E9DD0; align-self: center; font-size: clamp(48px, 6vw, 88px); }
.pt-head .ch-kicker { color: #35719A; }
.pt-title { margin: 0; font-weight: 900; font-size: clamp(32px, 4.4vw, 66px); line-height: 1.02; letter-spacing: -0.04em; }
.pt-title em { font-style: normal; color: #35719A; }
.pt-circle {
  width: min(46vh, 78vw); aspect-ratio: 1; border-radius: 50%; overflow: hidden;
  box-shadow: 0 0 0 14px rgba(78, 157, 208, 0.08), 0 0 0 30px rgba(78, 157, 208, 0.05), 0 40px 100px rgba(53, 113, 154, 0.25);
  clip-path: circle(calc(14% + var(--p) * 120%) at 50% 50%);
}
.pt-circle video { width: 100%; height: 100%; object-fit: cover; object-position: 100% 50%; transform: scale(calc(1.3 - var(--p) * 0.3)); }
.pt-circle img { width: 100%; height: 100%; object-fit: cover; object-position: 80% 50%; transform: scale(calc(1.3 - var(--p) * 0.3)); }
.pt-feats { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 220px)); gap: 14px; }
.pt-feat { display: flex; flex-direction: column; align-items: center; gap: 4px; font-size: 14px; color: var(--muted); }
.pt-feat b { font-size: 17px; font-weight: 800; color: var(--ink); }
.pt-ico { width: 42px; height: 42px; border-radius: 50%; display: grid; place-items: center; color: #35719A; background: rgba(78, 157, 208, 0.12); margin-bottom: 4px; }
.pt-ico :deep(svg) { width: 20px; height: 20px; }

/* ═════ CTA ═════ */
.cta { position: relative; min-height: 100vh; display: grid; place-items: center; overflow: hidden; }
.cta-photo { position: absolute; inset: 0; }
.cta-photo img, .cta-photo video { width: 100%; height: 100%; object-fit: cover; object-position: 50% 55%; transform: scale(calc(1.15 - var(--e, 0) * 0.15)); }
/* dusk: keep the sky and the lit lamp — only a soft light circle behind the type */
.cta-veil { position: absolute; inset: 0; background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.82) 0, rgba(255, 255, 255, 0.6) 18%, rgba(255, 255, 255, 0) 40%); }
.cta-in { position: relative; display: flex; flex-direction: column; align-items: center; gap: 22px; text-align: center; padding: 0 16px; }
.cta-word { margin: 0; color: var(--graphite); font-weight: 900; font-size: clamp(48px, 9vw, 132px); letter-spacing: -0.05em; line-height: 1; }
.cta-word span span { color: var(--blue); }

.hd-foot {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 14px;
  padding: 28px clamp(16px, 6vw, 96px); border-top: 1px solid rgba(24, 24, 24, 0.08); font-size: 14px; color: var(--muted);
}
.hd-foot nav { display: flex; gap: 20px; }
.hd-foot a { color: var(--muted); text-decoration: none; }
.hd-foot a:hover { color: var(--ink); }

/* Report — the orb rises from the signed report */
.ch--report .ch-orb { flex-direction: column; }
.ch--report .ch-orb-disc { animation: grow 5s ease-in-out infinite; transform-origin: 50% 100%; }
@keyframes grow { 0%, 100% { transform: translateY(6px) scale(0.97); } 50% { transform: translateY(-6px) scale(1.02); } }

/* ── responsive ── */
@media (max-width: 960px) {
  .ch-stick { grid-template-columns: 1fr; grid-template-rows: auto auto; align-content: center; padding-top: 84px; }
  .ch-orb { grid-column: 1; grid-row: 1; }
  .ch-body { grid-row: 2; align-items: flex-start; }
  .ch-num { display: none; }
  .ch-photo, .ch--dark .ch-photo {
    --open: radial-gradient(circle at 50% 26%, #000 calc(var(--p) * 140vmax - 14vmax), transparent calc(var(--p) * 140vmax + 6vmax));
    -webkit-mask-image: var(--open), linear-gradient(to bottom, #000 25%, transparent 60%);
            mask-image: var(--open), linear-gradient(to bottom, #000 25%, transparent 60%);
  }
  .ch .ring--a, .ch .ring--b { left: 50%; top: 26%; }
  .ch-orb-disc { width: clamp(140px, 34vw, 200px); }
  .ch-orb-canvas { transform: scale(2.2) !important; }
  .ch-orb-glow { width: 280px; height: 280px; margin: -170px 0 0 -140px; }
  .pt-feats { grid-template-columns: 1fr; gap: 10px; }
  .pt-feat { flex-direction: row; gap: 10px; }
  .pt-feat > span:last-child { display: none; }
  .pt-ico { margin: 0; width: 34px; height: 34px; }
  .pt-circle { width: min(42vh, 78vw); }
}
@media (max-width: 700px) {
  .cta-photo img, .cta-photo video { object-position: 84% 55%; }
  /* portrait: keep the lighthouse in frame, under the circle */
  .hero-photo img, .hero-photo video { object-position: 84% 60%; }
}
@media (max-width: 520px) {
  .hero-circle { width: 118vw; }
  .ch-line { font-size: 18px; }
  .ch-points li { font-size: 15px; }
}

@media (prefers-reduced-motion: reduce) {
  .word-lit .hw-ch, .cta-word .word-lit { text-shadow: 0 0 18px rgba(255, 240, 200, 0.9), 0 0 46px rgba(255, 232, 170, 0.6); }
  .rv, .ct-in, .hw-ch, .hw-kicker { opacity: 1 !important; transform: none !important; filter: none !important; transition: none !important; animation: none !important; }
  .beam-cone, .beam-lamp, .ring, .hero-photo img, .hero-circle, .ch-orb-glow, .ch-orb-disc, .hero-cue { animation: none !important; }
  .hero, .ch, .pt { height: auto; }
  .hero-stick, .ch-stick, .pt-stick { position: relative; min-height: 100vh; height: auto; }
  .hero-circle { transform: scale(0.86); }
  .hero-copy { opacity: 1; transform: none; }
}
</style>
