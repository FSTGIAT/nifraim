<template>
  <span class="avatar" :class="{ 'avatar--online': online }" :style="style" :title="title || name || username">
    <!-- Generated character. Markup is built by faceSvg() from a seed we control —
         never user input — so v-html has no injection surface here. -->
    <svg class="avatar-face" viewBox="0 0 100 100" role="img" :aria-label="name || username" v-html="face"></svg>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { avatarGradient } from '../utils/avatarSeed.js'
import { faceSvg } from '../utils/avatarFace.js'

const props = defineProps({
  name: { type: String, default: '' },       // full name, preferred source of the initial
  username: { type: String, default: '' },   // fallback when there is no name
  avatarSeed: { type: String, default: '' }, // explicit pick; falls back to username
  initial: { type: String, default: '' },    // explicit override (server already computes one)
  size: { type: Number, default: 36 },
  online: { type: Boolean, default: false },
  title: { type: String, default: '' },
})

const seed = computed(() => props.avatarSeed || props.username || props.name || '?')

// Same seed → same character as the animated Remotion avatar. Shared math, so a
// picker swatch and the real avatar can never disagree.
const face = computed(() => faceSvg(seed.value))

const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  background: avatarGradient(seed.value),
}))
</script>

<style scoped>
.avatar {
  position: relative;
  flex-shrink: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  user-select: none;
  /* NOT overflow:hidden — that would clip the online dot below. The face clips
     itself instead: the character's shoulders reach the square's corners, which
     fall outside the circle. */
}
.avatar-face {
  width: 100%; height: 100%; display: block;
  border-radius: 50%;
  overflow: hidden;
}

/* Presence ring. Drawn on the avatar itself so a contact row, the presence rail
   and the pill all read the same way without each re-implementing the dot. */
.avatar--online::after {
  content: '';
  position: absolute;
  inset-block-end: -1px;
  inset-inline-end: -1px;
  width: 30%;
  height: 30%;
  min-width: 8px;
  min-height: 8px;
  border-radius: 50%;
  background: #2E844A;
  box-shadow: 0 0 0 2px var(--bg-surface);
  animation: msgrPulse 2.4s ease-out infinite;
}

/* Local to the messenger — deliberately NOT the worker chip's keyframes, so the
   two surfaces can never drift into each other. */
@keyframes msgrPulse {
  0%   { box-shadow: 0 0 0 2px var(--bg-surface), 0 0 0 2px rgba(46, 132, 74, 0.5); }
  70%  { box-shadow: 0 0 0 2px var(--bg-surface), 0 0 0 7px rgba(46, 132, 74, 0); }
  100% { box-shadow: 0 0 0 2px var(--bg-surface), 0 0 0 0 rgba(46, 132, 74, 0); }
}

@media (prefers-reduced-motion: reduce) {
  .avatar--online::after { animation: none; }
}
</style>
