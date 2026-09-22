<template>
  <!-- Host for one AI chart: picks the registered component, or its table
       view (every chart has one — values are never gated behind hover/colour). -->
  <div class="ai-chart">
    <component :is="entry.component" v-if="entry && !showTable" :viz="viz" />
    <div v-else-if="table" class="ai-chart-table-wrap">
      <table class="ai-chart-table">
        <thead>
          <tr><th v-for="c in table.columns" :key="c">{{ c }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in table.rows" :key="i">
            <td v-for="(cell, j) in r" :key="j"><span :class="{ 'ltr-number': j > 0 }">{{ cell }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { nativeChartFor } from './registry.js'

const props = defineProps({
  viz: { type: Object, required: true },
  showTable: { type: Boolean, default: false },
})
const entry = computed(() => nativeChartFor(props.viz))
const table = computed(() => (entry.value?.table ? entry.value.table(props.viz) : null))
</script>

<style>
/* Shared by every chart component — the one-line story under the plot. Ink
   text on a quiet wash with an accent rule; never text in the data colour. */
.ai-chart-insight {
  margin: 20px 0 0;
  padding: 10px 14px;
  border-inline-start: 3px solid var(--primary);
  background: var(--primary-light, #FFF3E0);
  border-radius: 8px;
  border-start-start-radius: 0; border-end-start-radius: 0;
  font-size: 14px; font-weight: 550; color: var(--text);
}
</style>

<style scoped>
.ai-chart { width: 100%; }
.ai-chart-table-wrap { max-height: 460px; overflow: auto; border: 1px solid var(--border-subtle); border-radius: 10px; }
.ai-chart-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13.5px; }
.ai-chart-table th {
  position: sticky; top: 0; background: #FAFAF9;
  text-align: start; font-weight: 600; color: var(--text-muted); font-size: 12px;
  padding: 9px 14px; border-bottom: 1px solid var(--border-subtle);
}
.ai-chart-table th:not(:first-child), .ai-chart-table td:not(:first-child) { text-align: center; width: 130px; }
.ai-chart-table td { padding: 8px 14px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); }
.ai-chart-table tr:last-child td { border-bottom: 0; }
.ai-chart-table td span.ltr-number { font-variant-numeric: tabular-nums; color: var(--text); }
</style>
