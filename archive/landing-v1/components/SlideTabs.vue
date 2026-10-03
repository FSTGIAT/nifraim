<template>
  <nav class="slide-tabs-nav" :aria-label="ariaLabel">
    <ul ref="listEl" class="slide-tabs">
      <li
        v-for="(tab, i) in tabs"
        :key="tab.label"
        class="slide-tab"
        :class="[tab.styleClass, { 'slide-tab--active': selected === i }]"
      >
        <router-link
          v-if="tab.to"
          :to="tab.to"
          class="slide-tab-link"
          @click="onTabClick(tab, i)"
        >
          {{ tab.label }}
        </router-link>
        <a
          v-else
          :href="tab.href || '#'"
          class="slide-tab-link"
          @click.prevent="onAnchorClick(tab, i)"
        >
          {{ tab.label }}
        </a>
      </li>

      <!-- Sliding cursor — orange tint, slides between hovered/selected tabs. -->
      <li class="slide-tabs-cursor" :style="cursorStyle" aria-hidden="true"></li>
    </ul>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const props = defineProps({
  tabs: {
    type: Array,
    required: true,
  },
  initialIndex: { type: Number, default: 0 },
  ariaLabel: { type: String, default: 'ניווט ראשי' },
})

const listEl = ref(null)
const selected = ref(props.initialIndex)
// Opacity defaults to 1 — the cursor is hidden purely via width:0 until first
// measurement. Avoids the cursor accidentally getting stuck at opacity:0 if
// reactive state somehow gets reset.
const position = ref({ left: 0, width: 0, opacity: 1 })

// Read tab elements directly from the UL via querySelectorAll. More reliable
// than per-item function refs, which can be inconsistent under v-for re-renders.
function measureTab(i) {
  if (!listEl.value) return null
  const tabs = listEl.value.querySelectorAll('.slide-tab')
  const tab = tabs[i]
  if (!tab) return null
  return {
    left: tab.offsetLeft,
    width: tab.offsetWidth,
    opacity: 1,
  }
}

function setPositionFromIndex(i) {
  const m = measureTab(i)
  if (m) position.value = m
}

function resetToSelected() {
  setPositionFromIndex(selected.value)
}

function onTabClick(tab, i) {
  selected.value = i
}

function onAnchorClick(tab, i) {
  selected.value = i
  if (!tab.href) return
  // Anchor tabs (#top, #features, #portal) only have targets on the landing
  // page. From any other route, push to `/#hash` and let LandingView.onMounted
  // do the scroll once it's painted.
  if (route.path !== '/') {
    router.push({ path: '/', hash: tab.href })
    return
  }
  const id = tab.href.startsWith('#') ? tab.href.slice(1) : null
  if (id === '' || id === 'top') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }
  if (id) {
    const target = document.getElementById(id)
    if (target) {
      const y = target.getBoundingClientRect().top + window.scrollY - 24
      window.scrollTo({ top: y, behavior: 'smooth' })
    }
  }
}

// Animate via `transform: translateX(...)` instead of `left` so the cursor is
// composited on the GPU — no layout/paint per frame. Width still animates as a
// CSS property, which is unavoidable for a variable-width pill, but it's a
// single cheap layout-only animation now instead of two stacked ones.
const cursorStyle = computed(() => ({
  transform: `translate3d(${position.value.left}px, 0, 0)`,
  width: position.value.width + 'px',
  opacity: position.value.opacity,
}))

let resizeObserver = null
// Track listeners so we can remove them cleanly on unmount.
const enterListeners = []
let ulLeaveListener = null

onMounted(() => {
  if (!listEl.value) return

  // Wait one frame so the v-for'd tabs are in the DOM and laid out, then attach
  // native DOM mouseenter listeners. Avoids any of Vue's event-system quirks.
  requestAnimationFrame(() => {
    setPositionFromIndex(selected.value)

    const tabs = listEl.value.querySelectorAll('.slide-tab')
    tabs.forEach((tab, i) => {
      const handler = () => setPositionFromIndex(i)
      tab.addEventListener('mouseenter', handler)
      enterListeners.push({ tab, handler })
    })

    ulLeaveListener = () => resetToSelected()
    listEl.value.addEventListener('mouseleave', ulLeaveListener)
  })

  if (typeof ResizeObserver !== 'undefined' && listEl.value) {
    resizeObserver = new ResizeObserver(() => setPositionFromIndex(selected.value))
    resizeObserver.observe(listEl.value)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect()
  enterListeners.forEach(({ tab, handler }) => tab.removeEventListener('mouseenter', handler))
  enterListeners.length = 0
  if (ulLeaveListener && listEl.value) {
    listEl.value.removeEventListener('mouseleave', ulLeaveListener)
    ulLeaveListener = null
  }
})

watch(selected, (i) => setPositionFromIndex(i))
</script>

<style scoped>
.slide-tabs-nav {
  position: fixed;
  top: 22px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  pointer-events: none;
  width: max-content;
  max-width: calc(100vw - 32px);
}

/* Glass pill — semi-transparent over whatever content is behind it.
   Backdrop blur dialed back to 14px (was 22px + saturate) — heavy blur over
   the live WebGL shader was causing the cursor's slide to feel sluggish.
   Static box-shadow only — the previous breathing-glow keyframes constantly
   repainted the backdrop, fighting with the cursor's transform animation. */
.slide-tabs {
  position: relative;
  display: flex;
  align-items: center;
  width: max-content;
  margin: 0;
  padding: 6px;
  list-style: none;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  pointer-events: auto;
  /* Inherits RTL from the document, so tabs[0] (בית) is visually rightmost and
     tabs[4] (התחל עכשיו) is leftmost — Hebrew eye-flow correct. The cursor's
     transform uses physical offsetLeft regardless of direction, so the math
     still works without any LTR override here. */
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.14),
    0 8px 32px rgba(0, 0, 0, 0.22);
}

/* All tab labels sit above the cursor and use white text. The glass pill is
   dark-ish (low-opacity white over dark bg => slightly lighter than backdrop),
   so white text reads consistently across the dark hero, orange Chapter 02,
   cream Chapter 03, etc. The sliding cursor draws an orange-tinted glow that
   shifts the active tab visually without needing color changes. */
.slide-tab {
  position: relative;
  z-index: 10;
  cursor: pointer;
  user-select: none;
  list-style: none;
  margin: 0 2px;
}

.slide-tab-link {
  display: block;
  padding: 12px 26px;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  white-space: nowrap;
  /* Only color transitions on hover. Letter-spacing/transform would change the
     tab's layout width mid-transition, which makes the cursor (measured at
     mouseenter via offsetLeft/offsetWidth) appear to "jump" as neighbors shift. */
  transition: color 220ms ease;
  /* Generous breathing room between Hebrew characters — editorial pace */
  letter-spacing: 0.05em;
}

@media (min-width: 768px) {
  .slide-tab-link {
    padding: 14px 32px;
  }
}

/* Smart-tech Hebrew type system — all modern sans-serif Hebrew faces sharing
   the same geometric DNA. Heebo (workhorse) + Assistant (alt neutral) + Rubik
   (geometric tech) + Secular One (bold display). No serif, no italic, no
   vintage — fonts that look like they belong to an AI agent product. The mix
   is via WEIGHT and FACE within the modernist family, not across genres, so
   the row reads as one voice with five intonations. */
.tab-style--light {
  font-family: 'Heebo', sans-serif;
  font-weight: 300;
  font-size: 15px;
}
.tab-style--serif-italic {
  /* Class name kept for back-compat; visual is now geometric Rubik medium. */
  font-family: 'Rubik', 'Heebo', sans-serif;
  font-weight: 500;
  font-size: 15px;
  letter-spacing: 0.04em !important;
}
.tab-style--small-caps {
  font-family: 'Assistant', 'Heebo', sans-serif;
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.2em !important;
}
.tab-style--display {
  /* "Smart" CTA font — Secular One: geometric, modern, confident Hebrew display.
     Reads like a tech product's primary action, not a vintage logotype. */
  font-family: 'Secular One', 'Heebo', sans-serif;
  font-weight: 400;
  font-size: 17px;
  letter-spacing: 0.02em !important;
}
.tab-style--regular {
  font-family: 'Heebo', sans-serif;
  font-weight: 500;
  font-size: 15px;
}

.slide-tab:hover .slide-tab-link {
  color: #fff;
}

.slide-tab--active .slide-tab-link {
  color: #fff;
}

/* Sliding cursor — flat orange tint, no shadow, no gradient.
   The heavy gradient + 22px box-shadow used previously made every move feel
   like a "jolt" even with smooth interpolation, because the visual mass was
   so large that any pixel shift was amplified. Clean flat fill = the slide
   reads as smooth motion, not a flickering glow.

   Easing: cubic-bezier(0.16, 1, 0.3, 1) — Apple's iOS "easeOutQuint" — heavy
   deceleration, soft settle, no overshoot. Reads as "sliding" not "snapping". */
.slide-tabs-cursor {
  position: absolute;
  top: 6px;
  bottom: 6px;
  left: 0;
  z-index: 0;
  border-radius: 999px;
  /* Stronger orange so the cursor is clearly visible when it lands on a tab.
     Previous 0.42 alpha was getting lost against the dark shader through the
     glass backdrop. */
  background: rgba(232, 102, 10, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-sizing: border-box;
  transform: translate3d(0, 0, 0);
  transition:
    transform 380ms cubic-bezier(0.16, 1, 0.3, 1),
    width 380ms cubic-bezier(0.16, 1, 0.3, 1),
    opacity 200ms ease;
  pointer-events: none;
  will-change: transform, width;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .slide-tabs-cursor {
    transition: opacity 200ms ease;
  }
  .slide-tab-link {
    transition: none;
  }
}

/* Mobile — tighter padding so all 5 tabs still fit on narrow screens */
@media (max-width: 640px) {
  .slide-tabs-nav {
    top: 14px;
  }
  .slide-tabs {
    padding: 4px;
  }
  .slide-tab-link {
    padding: 10px 14px;
  }
  .tab-style--serif-italic { font-size: 12px; }
  .tab-style--display { font-size: 13px; }
  .tab-style--light,
  .tab-style--regular { font-size: 12px; }
  .tab-style--small-caps { font-size: 10px; letter-spacing: 0.16em !important; }
}
</style>
