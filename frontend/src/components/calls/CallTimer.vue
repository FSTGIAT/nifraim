<template>
  <!-- The recording timer on its own, so the 4×/s tick re-renders only this
       text node — never the studio around it (and never the ruler). -->
  <span class="ltr-number">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { useCallsStore } from '../../stores/calls'

const store = useCallsStore()
const label = computed(() => {
  const s = store.elapsed
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})
</script>
