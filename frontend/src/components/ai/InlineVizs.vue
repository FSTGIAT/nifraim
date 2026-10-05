<template>
  <!-- AI charts live IN the conversation, under the answer that made them — never a
       modal in the middle of the screen. They rise in with the app's silk motion
       (--ease-silk) and wear the surface's ONE accent (--viz-accent: ink in the chat,
       Nifra Agent teal in its panel). Types the native registry doesn't know
       (fund-track → Remotion) still open the viz panel via `open-legacy`. -->
  <div v-if="native.length" class="ivz" :class="{ 'ivz--compact': compact }">
    <section v-for="(v, i) in native" :key="i" class="ivz-card" :style="{ '--n': i }">
      <h4 v-if="v.title" class="ivz-title">{{ v.title }}</h4>
      <AiChart :viz="v" :show-table="false" />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import AiChart from '../ai-charts/AiChart.vue'
import { nativeChartFor } from '../ai-charts/registry.js'

const props = defineProps({
  vizs: { type: Array, default: () => [] },
  compact: { type: Boolean, default: true },
})
const emit = defineEmits(['open-legacy'])
const native = computed(() => (props.vizs || []).filter((v) => nativeChartFor(v)).slice(0, 3))
onMounted(() => {
  const legacy = (props.vizs || []).filter((v) => !nativeChartFor(v))
  if (legacy.length) emit('open-legacy', legacy)
})
</script>

<style scoped>
.ivz { display: flex; flex-direction: column; gap: 12px; margin-top: 10px; width: 100%; }
.ivz-card {
  padding: 14px 16px 12px; border: 1px solid var(--border-subtle); border-radius: 14px; background: #fff;
  box-shadow: 0 1px 2px rgba(24, 24, 24, 0.04);
  animation: ivzIn var(--dur-silk, 650ms) var(--ease-silk, cubic-bezier(0.32, 0.72, 0, 1)) both;
  animation-delay: calc(120ms + var(--n) * 140ms);
}
@keyframes ivzIn {
  from { opacity: 0; transform: translateY(16px) scale(0.97); filter: blur(6px); }
  to { opacity: 1; transform: none; filter: none; }
}
.ivz-title { margin: 0 0 10px; font-size: 13px; font-weight: 700; color: var(--text-secondary); }

/* compact = inside a chat column: shorter plots, smaller readouts */
.ivz--compact :deep(.htb-plot) { height: 170px; }
.ivz--compact :deep(.htb-v), .ivz--compact :deep(.hdo-v) { font-size: 26px; }
.ivz--compact :deep(.aitr-plot) { grid-template-rows: 170px auto; }
.ivz--compact :deep(.aitr-trace-v) { font-size: 24px; }
.ivz--compact :deep(.aikpi-value) { font-size: 40px; }
.ivz--compact :deep(.hdo-body) { grid-template-columns: minmax(110px, 150px) 1fr; }
.ivz--compact :deep(.ai-chart-insight) { margin-top: 12px; font-size: 13px; }

@media (prefers-reduced-motion: reduce) { .ivz-card { animation: none; } }
</style>
