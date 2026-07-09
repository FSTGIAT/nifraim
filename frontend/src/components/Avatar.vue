<template>
  <span class="avatar" :class="{ 'avatar--online': online }" :style="style" :title="title">
    <span class="avatar-initial">{{ initial }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { avatarGradient } from '../utils/avatarSeed.js'

const props = defineProps({
  name: { type: String, default: '' },       // full name, preferred source of the initial
  username: { type: String, default: '' },   // fallback when there is no name
  avatarSeed: { type: String, default: '' }, // explicit pick; falls back to username
  initial: { type: String, default: '' },    // explicit override (server already computes one)
  size: { type: Number, default: 36 },
  online: { type: Boolean, default: false },
  title: { type: String, default: '' },
})

const initial = computed(() => {
  if (props.initial) return props.initial
  const src = (props.name || '').trim() || props.username || ''
  return src ? src.charAt(0).toUpperCase() : '?'
})

// Same seed → same face as the animated Remotion avatar. Shared math, so a
// picker swatch and the real avatar can never disagree.
const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  fontSize: `${Math.round(props.size * 0.4)}px`,
  background: avatarGradient(props.avatarSeed || props.username || props.name || '?'),
}))
</script>

<style scoped>
.avatar {
  position: relative;
  flex-shrink: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 800;
  line-height: 1;
  user-select: none;
}
.avatar-initial { transform: translateY(1px); }

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
