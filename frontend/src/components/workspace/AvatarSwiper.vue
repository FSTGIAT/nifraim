<template>
  <!--
    A deck of faces you flick through, ported from the shadcn `ImageSwiper`
    card stack. The geometry is the original's — perspective, a Z and Y offset
    per card, translateX + rotateY while dragging — driven the same way, by CSS
    custom properties set on each card.

    Four things are deliberately NOT the original's, each because it misbehaves:
      · the original commits the swipe from inside `handleMove` the instant you
        pass 50px, so the card leaves under your finger and you can never drag
        further than the threshold. Here the gesture commits on release.
      · it advances the deck the same way whichever way you swiped. Here right
        goes back.
      · it never captures the pointer, so letting go outside the deck leaves it
        mid-swipe forever. Here the deck captures it.
      · it is pointer-only. Arrow keys work here, same as the company picker.
  -->
  <div
    ref="deckEl"
    class="deck"
    :style="{ '--card-max-z-index': seeds.length }"
    tabindex="0"
    role="listbox"
    :aria-label="'בחירת אווטאר — ' + (index + 1) + ' מתוך ' + seeds.length"
    @pointerdown="onDown"
    @pointermove="onMove"
    @pointerup="onUp"
    @pointercancel="onUp"
    @keydown.left.prevent="step(1)"
    @keydown.right.prevent="step(-1)"
    @keydown.up.prevent="step(-1)"
    @keydown.down.prevent="step(1)"
    @keydown.enter.prevent="$emit('choose', front)"
  >
    <article
      v-for="(seed, i) in order"
      :key="seed"
      ref="cardEls"
      class="deck-card"
      :class="{
        'deck-card--front': i === 0,
        'deck-card--on': seed === modelValue,
        'deck-card--tail': i >= VISIBLE,
      }"
      :style="cardStyle(seed, i)"
      :aria-selected="seed === modelValue"
      role="option"
      @click="i === 0 ? $emit('choose', seed) : null"
    >
      <Avatar :avatar-seed="seed" :username="username" :name="name" :size="size" class="deck-face" />
    </article>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import Avatar from '../Avatar.vue'

const props = defineProps({
  seeds: { type: Array, default: () => [] },
  username: { type: String, default: '' },
  name: { type: String, default: '' },
  modelValue: { type: String, default: '' },  // the seed currently saved
  size: { type: Number, default: 96 },
})
const emit = defineEmits(['front', 'choose'])

const SWAP_MS = 300
const THRESHOLD = 50

const deckEl = ref(null)
const cardEls = ref([])
const order = ref([...props.seeds])
const index = ref(0)           // how far we have walked, for the counter
const front = computed(() => order.value[0] || '')

// Open on the face you already wear, rather than on whatever happens to be
// first — you should be able to see what you are changing away from.
watch(
  () => [props.seeds, props.modelValue],
  () => {
    const list = [...props.seeds]
    const at = list.indexOf(props.modelValue)
    order.value = at > 0 ? [...list.slice(at), ...list.slice(0, at)] : list
    index.value = at > 0 ? at : 0
    nextTick(reset)
  },
  { immediate: true, deep: true },
)
watch(front, (s) => emit('front', s))

function cards() {
  return (cardEls.value || []).filter(Boolean)
}

/* One face at a time.
   The original fans the whole deck out behind the front card. With circular
   avatars that tail read as slices of stray colour under the portrait rather
   than as depth, so only the front card is drawn — the ones behind are still
   in the DOM and still rotate, they are simply not shown. */
const VISIBLE = 1

function cardStyle(seed, i) {
  return {
    '--i': Math.min(i + 1, VISIBLE),
    zIndex: props.seeds.length - i,
  }
}

/** Put every card back on its shelf: no offset, no rotation, full opacity. */
function reset() {
  cards().forEach((c) => {
    c.style.transition = ''
    c.style.setProperty('--swipe-x', '0px')
    c.style.setProperty('--swipe-rotate', '0deg')
    c.style.opacity = ''
  })
}

function paint(dx) {
  const c = cards()[0]
  if (!c) return
  c.style.setProperty('--swipe-x', `${dx}px`)
  c.style.setProperty('--swipe-rotate', `${dx * 0.2}deg`)
  c.style.opacity = String(1 - Math.min(Math.abs(dx) / 140, 1) * 0.7)
}

/** dir = +1 walks forward through the deck, -1 walks back. */
function step(dir) {
  const n = order.value.length
  if (n < 2) return
  order.value = dir > 0
    ? [...order.value.slice(1), order.value[0]]
    : [order.value[n - 1], ...order.value.slice(0, n - 1)]
  index.value = (index.value + (dir > 0 ? 1 : n - 1)) % n
  nextTick(reset)
}

/* ── the drag ─────────────────────────────────────────────────────────── */
const dragging = ref(false)
let startX = 0
let dx = 0
let raf = null

function onDown(e) {
  if (dragging.value) return
  dragging.value = true
  startX = e.clientX
  dx = 0
  deckEl.value?.setPointerCapture?.(e.pointerId)
  const c = cards()[0]
  if (c) c.style.transition = 'none'
}

function onMove(e) {
  if (!dragging.value) return
  if (raf) cancelAnimationFrame(raf)
  raf = requestAnimationFrame(() => {
    dx = e.clientX - startX
    paint(dx)
  })
}

function onUp(e) {
  if (!dragging.value) return
  dragging.value = false
  if (raf) { cancelAnimationFrame(raf); raf = null }
  deckEl.value?.releasePointerCapture?.(e.pointerId)

  const c = cards()[0]
  if (!c) return
  c.style.transition = `transform ${SWAP_MS}ms ease, opacity ${SWAP_MS}ms ease`

  if (Math.abs(dx) <= THRESHOLD) { paint(0); dx = 0; return }

  // Throw it clear of the deck, then rotate the order once it is out of sight.
  const dir = Math.sign(dx)
  c.style.setProperty('--swipe-x', `${dir * 320}px`)
  c.style.setProperty('--swipe-rotate', `${dir * 20}deg`)
  const forward = dir < 0   // flicked away from you = next
  setTimeout(() => step(forward ? 1 : -1), SWAP_MS)
  dx = 0
}

defineExpose({ front, step })
</script>

<style scoped>
.deck {
  position: relative;
  display: grid;
  place-content: center;
  /* Sized from the avatar itself — there is no card around it to measure. */
  width: 100%;
  /* No tail to leave room for any more. */
  height: calc(var(--deck-size, 96px) + 10px);
  touch-action: none;
  transform-style: preserve-3d;
  outline: none;
  --card-perspective: 700px;
  --card-z-offset: 11px;
  --card-y-offset: 7px;
}
.deck:focus-visible { outline: 2px solid var(--tab-production, #2F73C4); outline-offset: 8px; border-radius: 20px; }

.deck-card {
  position: absolute;
  place-self: center;
  /* No card. The avatar is the whole object — a white tile around a circle was
     chrome wrapping chrome, and it is what made this read as a modal. */
  border-radius: 50%;
  line-height: 0;
  will-change: transform, opacity;
  cursor: grab;
  /* A ramp down the stack, so the discs behind read as depth rather than as a
     stripe of stray colour under the front one. --i is 1 for the front card,
     and reset() clears the inline opacity so this rule wins again after a
     drag. */
  /* Everything but the front card is invisible; the swap still works, you
     just never see the pile. */
  opacity: 0;
  /* The original's stack geometry, unchanged. */
  transform:
    perspective(var(--card-perspective))
    translateZ(calc(-1 * var(--card-z-offset) * var(--i)))
    translateY(calc(var(--card-y-offset) * var(--i)))
    translateX(var(--swipe-x, 0px))
    rotateY(var(--swipe-rotate, 0deg));
}
.deck-card:active { cursor: grabbing; }
/* Only the front card is pressable; the ones behind are scenery. */
.deck-card--front { opacity: 1; }
.deck-card:not(.deck-card--front) { pointer-events: none; }
.deck-card--tail { opacity: 0; }
/* The one you already wear gets a ring, not a label. */
.deck-card--on { box-shadow: 0 0 0 3px var(--card-bg), 0 0 0 5px var(--tab-production, #2F73C4); }

.deck-face { pointer-events: none; }


@media (prefers-reduced-motion: reduce) {
  .deck-card { transition: none !important; }
}
</style>
