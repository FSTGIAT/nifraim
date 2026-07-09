<template>
  <!-- Duotone tab glyph. Color flows through `currentColor` (both layers), so the
       icon inherits its tab's --tab-* color from the surrounding wrapper — no
       per-icon color plumbing. Markup is a trusted static constant (no user
       input), so v-html is safe here. -->
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 256 256"
    fill="currentColor"
    role="img"
    aria-hidden="true"
    v-html="inner"
  />
</template>

<script setup>
import { computed } from 'vue'
import { TAB_ICONS } from './tabIcons.js'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 22 },
})

const inner = computed(() => TAB_ICONS[props.name] || '')
</script>
