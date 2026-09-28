<template>
  <!-- Vue port of the AiStreamingText design (React/Tailwind original):
       text streams in by character or word on requestAnimationFrame, with a
       blinking cursor until done; emits `complete`. -->
  <span class="ast" role="status" aria-live="polite" :aria-label="text">
    <span class="ast-text">{{ shown }}</span>
    <span v-if="showCursor && !done" class="ast-cursor" aria-hidden="true"></span>
  </span>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  speed: { type: Number, default: 30 },          // ms per token
  mode: { type: String, default: 'character' },  // 'character' | 'word'
  showCursor: { type: Boolean, default: true },
  start: { type: Boolean, default: true },       // hold until true (sequential lines)
})
const emit = defineEmits(['complete'])

const shown = ref('')
const done = ref(false)
let raf = 0

function stop() { if (raf) cancelAnimationFrame(raf); raf = 0 }

function run() {
  stop()
  shown.value = ''
  done.value = false
  if (!props.text) { done.value = true; emit('complete'); return }
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    shown.value = props.text; done.value = true; emit('complete'); return
  }
  const tokens = props.mode === 'word' ? props.text.split(/(\s+)/) : Array.from(props.text)
  let i = 0
  let last = 0
  const tick = (t) => {
    if (t - last >= props.speed) {
      last = t
      if (i < tokens.length) {
        shown.value += tokens[i++]
      } else {
        done.value = true
        raf = 0
        emit('complete')
        return
      }
    }
    raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}

watch(() => [props.text, props.start], () => { if (props.start) run() }, { immediate: true })
onBeforeUnmount(stop)
</script>

<style scoped>
.ast { position: relative; }
.ast-text { white-space: pre-wrap; }
.ast-cursor {
  display: inline-block; width: 2px; height: 1.15em; margin-inline-start: 2px;
  vertical-align: middle; background: currentColor; animation: astBlink 1s steps(2, start) infinite;
}
@keyframes astBlink { to { opacity: 0; } }
</style>
