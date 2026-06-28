<template>
  <span class="typewriter" dir="auto">
    <span class="typewriter__text">{{ displayText }}</span>
    <span v-if="!reduced" class="typewriter__cursor" aria-hidden="true">{{ cursor }}</span>
  </span>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  text: { type: [String, Array], required: true },
  speed: { type: Number, default: 90 },
  deleteSpeed: { type: Number, default: 45 },
  delay: { type: Number, default: 1600 },
  loop: { type: Boolean, default: true },
  cursor: { type: String, default: '|' },
})

const textArray = computed(() => (Array.isArray(props.text) ? props.text : [props.text]))

const reduced = ref(false)
const displayText = ref('')

let timer = null
let charIndex = 0
let arrIndex = 0
let deleting = false

function clear() {
  if (timer) { clearTimeout(timer); timer = null }
}

function tick() {
  const current = textArray.value[arrIndex] || ''
  if (!deleting) {
    if (charIndex < current.length) {
      charIndex += 1
      displayText.value = current.slice(0, charIndex)
      timer = setTimeout(tick, props.speed)
    } else if (props.loop && textArray.value.length > 0) {
      // pause at full word, then start deleting
      timer = setTimeout(() => { deleting = true; tick() }, props.delay)
    }
  } else {
    if (charIndex > 0) {
      charIndex -= 1
      displayText.value = current.slice(0, charIndex)
      timer = setTimeout(tick, props.deleteSpeed)
    } else {
      deleting = false
      arrIndex = (arrIndex + 1) % textArray.value.length
      timer = setTimeout(tick, props.speed)
    }
  }
}

function start() {
  clear()
  charIndex = 0
  arrIndex = 0
  deleting = false
  if (reduced.value) {
    // Respect reduced-motion: show the first string statically, no animation.
    displayText.value = textArray.value[0] || ''
    return
  }
  displayText.value = ''
  timer = setTimeout(tick, props.speed)
}

let mql = null
function onReducedChange(e) {
  reduced.value = e.matches
  start()
}

onMounted(() => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    mql = window.matchMedia('(prefers-reduced-motion: reduce)')
    reduced.value = mql.matches
    if (mql.addEventListener) mql.addEventListener('change', onReducedChange)
    else if (mql.addListener) mql.addListener(onReducedChange)
  }
  start()
})

watch(() => props.text, start)

onBeforeUnmount(() => {
  clear()
  if (mql) {
    if (mql.removeEventListener) mql.removeEventListener('change', onReducedChange)
    else if (mql.removeListener) mql.removeListener(onReducedChange)
  }
})
</script>

<style scoped>
.typewriter { display: inline-flex; align-items: baseline; }
.typewriter__cursor {
  display: inline-block;
  margin-inline-start: 1px;
  font-weight: 400;
  animation: tw-blink 1s step-end infinite;
}
@keyframes tw-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .typewriter__cursor { animation: none; }
}
</style>
