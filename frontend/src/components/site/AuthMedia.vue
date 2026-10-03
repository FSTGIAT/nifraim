<template>
  <aside class="am" :class="{ 'am--in': shown }" aria-hidden="true">
    <!-- The media side of the public pages (login, signup, pricing…): one of the home
         page's Kling videos, opening out of a soft circle, easing in from a slight
         zoom, played once and held on its last frame. The framing drifts with the
         camera so the subject stays in a half-width panel. -->
    
    <div class="am-frame">
      <video
        v-if="!reduced && !failed" ref="videoEl" class="am-media" :poster="clip.poster"
        :style="{ '--from': clip.from, '--to': clip.to }" muted playsinline autoplay preload="auto"
        @playing="shown = true"
      >
        <source :src="clip.webm" type="video/webm" />
        <source :src="clip.mp4" type="video/mp4" @error="failed = true" />
      </video>
      <img v-else class="am-media am-media--still" :src="clip.still" alt="" :style="{ objectPosition: clip.to }" />
    </div>
    <div class="am-shade"></div>
    <p class="am-mark" dir="ltr">Nifraim<span>.com</span></p>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import heroStill from '../../assets/home/hero.webp'
import heroPoster from '../../assets/home/hero-first.webp'
import ctaStill from '../../assets/home/cta.webp'
import ctaPoster from '../../assets/home/cta-first.webp'
import portalStill from '../../assets/home/portal.webp'
import portalPoster from '../../assets/home/portal-first.webp'

const props = defineProps({
  // hero = lighthouse by day · dusk = lighthouse at dusk · portal = the white arch
  video: { type: String, default: 'hero' },
})

// from → to = the object-position at the first and last frame (the camera drifts right)
const CLIPS = {
  hero: {
    webm: new URL('../../assets/home/hero.webm', import.meta.url).href,
    mp4: new URL('../../assets/home/hero.mp4', import.meta.url).href,
    poster: heroPoster, still: heroStill, from: '50% 50%', to: '96% 60%',
  },
  dusk: {
    webm: new URL('../../assets/home/cta.webm', import.meta.url).href,
    mp4: new URL('../../assets/home/cta.mp4', import.meta.url).href,
    poster: ctaPoster, still: ctaStill, from: '50% 50%', to: '98% 58%',
  },
  portal: {
    webm: new URL('../../assets/home/portal.webm', import.meta.url).href,
    mp4: new URL('../../assets/home/portal.mp4', import.meta.url).href,
    poster: portalPoster, still: portalStill, from: '86% 50%', to: '96% 50%',
  },
}
const clip = computed(() => CLIPS[props.video] || CLIPS.hero)

const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const videoEl = ref(null)
const failed = ref(false)
const shown = ref(false)
onMounted(() => {
  if (reduced) { shown.value = true; return }
  // never leave the panel blank if autoplay is slow or blocked
  setTimeout(() => { shown.value = true }, 900)
})
</script>

<style scoped>
@property --am-r {
  syntax: '<percentage>';
  inherits: false;
  initial-value: 0%;
}
.am {
  position: relative; overflow: hidden; isolation: isolate; background: #E9EEF3;
}
/* the soft circle opening — the home page's chapter reveal */
.am-frame {
  position: absolute; inset: 0;
  --am-r: 0%;
  -webkit-mask-image: radial-gradient(circle at 50% 46%, #000 calc(var(--am-r) - 14%), transparent var(--am-r));
          mask-image: radial-gradient(circle at 50% 46%, #000 calc(var(--am-r) - 14%), transparent var(--am-r));
  transition: --am-r 1.8s cubic-bezier(0.22, 1, 0.36, 1);
}
.am--in .am-frame { --am-r: 165%; }
.am-media {
  position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
  object-position: var(--from);
  transform: scale(1.14); opacity: 0;
  transition: transform 7s cubic-bezier(0.22, 1, 0.36, 1), opacity 1s ease, object-position 5s ease-in-out;
}
.am--in .am-media { transform: scale(1); opacity: 1; object-position: var(--to); }
.am-media--still { transition: transform 7s cubic-bezier(0.22, 1, 0.36, 1), opacity 1s ease; }
.am-shade {
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(to top, rgba(10, 20, 35, 0.28), rgba(10, 20, 35, 0) 38%);
}
.am-mark {
  position: absolute; bottom: 28px; inset-inline-end: 32px; margin: 0;
  font: 900 22px 'Heebo', sans-serif; letter-spacing: -0.03em; color: #FFFFFF;
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.25); opacity: 0; transform: translateY(10px);
  transition: opacity 1s ease 1.2s, transform 1s cubic-bezier(0.22, 1, 0.36, 1) 1.2s;
}
.am-mark span { color: #CFE2F7; }
.am--in .am-mark { opacity: 1; transform: none; }

@media (prefers-reduced-motion: reduce) {
  .am-frame, .am-media, .am-mark { transition: none !important; }
}
</style>
