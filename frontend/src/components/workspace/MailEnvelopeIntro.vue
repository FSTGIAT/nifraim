<template>
  <!-- One-shot Remotion opening for an AI-answered mail. Emits `done` when the
       letter has settled (or immediately under reduced motion / if the React
       stack fails), and on click so the agent can skip it. -->
  <div class="mei" :class="{ 'mei--behind': reverse }" role="presentation" @click="finish">
    <div ref="mountEl" class="mei-mount"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  initial: { type: String, default: '' },
  reverse: { type: Boolean, default: false }, // play the closing instead
})
const emit = defineEmits(['done'])

const mountEl = ref(null)
let reactRoot = null
let fallback = null
let finished = false

function finish() {
  if (finished) return
  finished = true
  clearTimeout(fallback)
  emit('done')
}

onMounted(async () => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return finish()
  // Never let the intro hold the letter hostage (slow chunk, player hiccup).
  fallback = setTimeout(finish, 3500)
  try {
    const [rdClient, react, player, comp] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/MailEnvelopeIntro'),
    ])
    if (finished || !mountEl.value) return
    const onRef = (p) => { if (p) p.addEventListener('ended', finish) }
    reactRoot = rdClient.createRoot(mountEl.value)
    reactRoot.render(
      react.createElement(player.Player, {
        ref: onRef,
        component: comp.MailEnvelopeIntro,
        inputProps: { name: props.name, initial: props.initial, reverse: props.reverse },
        durationInFrames: props.reverse ? comp.ENVELOPE_CLOSE_FRAMES : comp.ENVELOPE_INTRO_FRAMES,
        fps: 30,
        compositionWidth: comp.ENVELOPE_W,
        compositionHeight: comp.ENVELOPE_H,
        autoPlay: true,
        loop: false,
        controls: false,
        clickToPlay: false,
        doubleClickToFullscreen: false,
        showPosterWhenUnplayed: false,
        showPosterWhenPaused: false,
        showPosterWhenEnded: false,
        showPosterWhenBuffering: false,
        acknowledgeRemotionLicense: true,
        style: { width: '100%', height: '100%' },
      }),
    )
  } catch (e) {
    console.error('[MailEnvelopeIntro] render failed', e)
    finish()
  }
})

onBeforeUnmount(() => {
  clearTimeout(fallback)
  reactRoot?.unmount()
  reactRoot = null
})
</script>

<style scoped>
.mei { width: min(640px, 100%); aspect-ratio: 640 / 440; cursor: pointer; animation: mei-in 0.12s ease-out both; }
@keyframes mei-in { from { opacity: 0; } }
/* Closing: sits behind the real letter (absolute children of the centring
   flex overlay stay centred), so the letter can shrink onto it. */
.mei--behind { position: absolute; z-index: 0; }
/* Remotion Player's centring maths assumes LTR — see TabHeroLoop.vue. */
.mei-mount { width: 100%; height: 100%; direction: ltr; }
</style>
