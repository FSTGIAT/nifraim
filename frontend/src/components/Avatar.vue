<template>
  <span
    class="avatar"
    :class="{ 'avatar--online': online }"
    :style="style"
    :title="title || name || username"
    role="img"
    :aria-label="name || username"
  >
    <!-- The monogram stays underneath as the fallback: it is what shows while
         the portrait decodes, and what remains if the file ever 404s. -->
    <svg class="avatar-mark" viewBox="0 0 100 100" aria-hidden="true" v-html="mark"></svg>
    <span class="avatar-mono" :style="{ fontSize: `${Math.round(size * 0.38)}px` }">{{ letters }}</span>
    <img
      v-if="portrait && !broken"
      class="avatar-img"
      :src="portrait"
      alt=""
      draggable="false"
      @error="broken = true"
    />
  </span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { avatarTone, initialsFor, avatarImage } from '../utils/avatarSeed.js'
import { monogramMark, MONOGRAM_DEFS } from '../utils/avatarFace.js'

const props = defineProps({
  name: { type: String, default: '' },       // full name, preferred source of the initials
  username: { type: String, default: '' },   // fallback when there is no name
  avatarSeed: { type: String, default: '' }, // explicit pick; falls back to username
  initial: { type: String, default: '' },    // explicit override (server already computes one)
  size: { type: Number, default: 36 },
  online: { type: Boolean, default: false },
  title: { type: String, default: '' },
})

const seed = computed(() => props.avatarSeed || props.username || props.name || '?')

/*
 * A monogram, not a character.
 *
 * The generated faces this used to draw read as a toy next to a commission
 * table — the app is a financial product and the account avatar should say so.
 * Everything else about the system is unchanged: the same seed still decides
 * the look, so a swatch in the picker is still literally the thing you get,
 * and the messenger, the rail and the animated avatar cannot disagree.
 */
const letters = computed(
  () => props.initial || initialsFor({ full_name: props.name, username: props.username }),
)

const mark = computed(() => MONOGRAM_DEFS + monogramMark(seed.value))

const portrait = computed(() => avatarImage(seed.value))
const broken = ref(false)
watch(portrait, () => { broken.value = false })

const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  background: avatarTone(seed.value),
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
  color: #fff;
  /* NOT overflow:hidden — that would clip the online dot below. */
}
.avatar-mark {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  border-radius: 50%;
  overflow: hidden;
  pointer-events: none;
}
.avatar-img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
  pointer-events: none;
  user-select: none;
}
.avatar-mono {
  position: relative;   /* above the mark */
  font-family: inherit;
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1;
  /* Latin initials in an RTL document read backwards without this. */
  direction: ltr;
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
</style>
