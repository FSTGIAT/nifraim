<template>
  <!-- One number is not a chart: a hero figure, the one thing this view leads
       with. Counts up once; the direction is an icon + sign, never colour alone. -->
  <div class="aikpi">
    <strong class="aikpi-value ltr-number">{{ fmtFull(shown, viz.unit || '') }}</strong>
    <span v-if="viz.subtitle || dir" class="aikpi-sub">
      <span v-if="dir" class="aikpi-dir" :class="`aikpi-dir--${dir}`">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-if="dir === 'up'" d="M7 17L17 7M9 7h8v8" />
          <path v-else d="M7 7l10 10M17 9v8H9" />
        </svg>
        {{ dir === 'up' ? 'עלייה' : 'ירידה' }}
      </span>
      <span v-if="viz.subtitle">{{ viz.subtitle }}</span>
    </span>
    <p v-if="viz.insight" class="ai-chart-insight">{{ viz.insight }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { fmtFull, prefersReducedMotion } from './format.js'

const props = defineProps({ viz: { type: Object, required: true } })
const target = computed(() => Number(props.viz.value) || 0)
const dir = computed(() => (props.viz.direction === 'up' || props.viz.direction === 'down' ? props.viz.direction : null))

const shown = ref(0)
let raf = 0
onMounted(() => {
  if (prefersReducedMotion()) { shown.value = target.value; return }
  const t0 = performance.now()
  const step = (t) => {
    const k = Math.min(1, (t - t0) / 900)
    shown.value = target.value * (1 - (1 - k) ** 3)
    if (k < 1) raf = requestAnimationFrame(step)
    else shown.value = target.value
  }
  raf = requestAnimationFrame(step)
})
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<style scoped>
.aikpi { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 36px 0 16px; text-align: center; width: 100%; }
.aikpi-value { font-size: 56px; font-weight: 700; color: var(--text); line-height: 1.05; }
.aikpi-sub { display: flex; gap: 12px; align-items: center; font-size: 13.5px; color: var(--text-secondary); }
.aikpi-dir { display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: 999px; font-weight: 600; font-size: 12.5px; }
.aikpi-dir--up { background: var(--green-light, #EBF7EE); color: var(--green, #2E844A); }
.aikpi-dir--down { background: var(--red-light, #FEF1EE); color: var(--red-deep, #C23934); }
.aikpi .ai-chart-insight { align-self: stretch; text-align: start; }
</style>
