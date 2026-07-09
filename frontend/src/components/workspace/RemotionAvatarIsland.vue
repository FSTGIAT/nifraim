<template>
  <!-- Animated generative avatar. Falls back to the static CSS Avatar under
       prefers-reduced-motion or if the Remotion chunk fails to load, so the
       header never renders an empty hole. -->
  <div class="ra" :style="{ width: size + 'px', height: size + 'px' }">
    <Avatar
      v-if="fallback"
      :name="name"
      :username="username"
      :avatar-seed="avatarSeed"
      :initial="initial"
      :size="size"
      :online="online"
    />
    <template v-else>
      <div ref="mountEl" class="ra-mount"></div>
      <span v-if="online" class="ra-dot" aria-hidden="true"></span>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import Avatar from '../Avatar.vue'

const props = defineProps({
  username: { type: String, required: true },   // fallback seed
  avatarSeed: { type: String, default: '' },    // the chosen seed, when set
  name: { type: String, default: '' },
  initial: { type: String, default: '' },
  size: { type: Number, default: 40 },
  online: { type: Boolean, default: false },
})

const mountEl = ref(null)
const fallback = ref(false)
let reactRoot = null

function prefersReducedMotion () {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

function seedOf () {
  return props.avatarSeed || props.username
}

function initialOf () {
  if (props.initial) return props.initial
  const src = (props.name || '').trim() || props.username || ''
  return src ? src.charAt(0).toUpperCase() : '?'
}

async function render () {
  if (!mountEl.value) return
  try {
    const [rdClient, react, player, remotion] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/AvatarLoop'),
    ])
    if (!mountEl.value) return
    reactRoot = rdClient.createRoot(mountEl.value)
    reactRoot.render(
      react.createElement(player.Player, {
        component: remotion.AvatarLoop,
        inputProps: { seed: seedOf(), initial: initialOf() },
        durationInFrames: remotion.AVATAR_LOOP_FRAMES,
        fps: 30,
        compositionWidth: 120,
        compositionHeight: 120,
        autoPlay: true,
        loop: true,
        controls: false,
        clickToPlay: false,
        doubleClickToFullscreen: false,
        showPosterWhenUnplayed: false,
        showPosterWhenPaused: false,
        showPosterWhenEnded: false,
        showPosterWhenBuffering: false,
        acknowledgeRemotionLicense: true,
        style: { width: '100%', height: '100%', backgroundColor: 'transparent' },
      }),
    )
  } catch (e) {
    console.error('[RemotionAvatarIsland] render failed', e)
    fallback.value = true
  }
}

function teardown () {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
}

onMounted(() => {
  if (prefersReducedMotion()) {
    fallback.value = true
    return
  }
  nextTick(render)
})

// Renaming your handle, or picking a new avatar, re-seeds the face — remount
// so it actually changes.
watch(() => [props.username, props.avatarSeed], async () => {
  if (fallback.value) return
  teardown()
  await nextTick()
  render()
})

onBeforeUnmount(teardown)
</script>

<style scoped>
.ra {
  position: relative;
  flex-shrink: 0;
  border-radius: 50%;
  overflow: visible;
}

/* The Player centres with LTR-assuming math and drifts half a scene off-box
   under the app's RTL root. Scope `direction: ltr` to the INNER mount only,
   never the positioned root. See memory remotion_rtl_player. */
.ra-mount {
  width: 100%;
  height: 100%;
  direction: ltr;
  border-radius: 50%;
  overflow: hidden;
}

.ra-dot {
  position: absolute;
  inset-block-end: -1px;
  inset-inline-end: -1px;
  width: 30%;
  height: 30%;
  min-width: 9px;
  min-height: 9px;
  border-radius: 50%;
  background: #2E844A;
  box-shadow: 0 0 0 2px var(--bg-surface);
}
</style>
