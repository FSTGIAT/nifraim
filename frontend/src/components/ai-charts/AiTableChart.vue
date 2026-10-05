<template>
  <!-- A table the agent asked for ("צור טבלה"), in the AI-chart family: one accent
       (--viz-accent), hairline rows, the first column carries the row's identity,
       amounts are LTR numbers, and an empty cell stays EMPTY (never "—"). Rows rise in
       one after another with the silk motion. -->
  <div class="atb" :class="{ 'atb--in': entered }">
    <div class="atb-wrap">
      <table class="atb-table">
        <thead>
          <tr><th v-for="(c, j) in columns" :key="j" :class="{ 'is-num': numCol[j] }">{{ c }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="i" :style="{ '--i': i }">
            <td v-for="(cell, j) in r" :key="j" :class="{ 'is-num': numCol[j], 'is-first': j === 0 }">
              <span v-if="isNum(cell)" class="ltr-number">{{ money(cell, j) }}</span>
              <span v-else-if="cell !== null && cell !== undefined && cell !== ''">{{ cell }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="viz.insight" class="ai-chart-insight">{{ viz.insight }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { fmtFull, prefersReducedMotion } from './format.js'

const props = defineProps({ viz: { type: Object, required: true } })
const columns = computed(() => props.viz.columns || [])
const rows = computed(() => (props.viz.rows || []).slice(0, 40))
const isNum = (v) => typeof v === 'number' && Number.isFinite(v)
// a column of amounts aligns as numbers; ID/policy-like strings stay text
const numCol = computed(() => columns.value.map((_, j) => rows.value.some((r) => isNum(r[j]))))
const MONEY_HINT = /צבירה|פרמיה|עמלה|סכום|₪|פער|צפי/
function money(v, j) {
  const col = String(columns.value[j] || '')
  return MONEY_HINT.test(col) || props.viz.unit === '₪' ? fmtFull(v, '₪') : fmtFull(v, '')
}
const entered = ref(false)
onMounted(() => {
  if (prefersReducedMotion()) { entered.value = true; return }
  requestAnimationFrame(() => requestAnimationFrame(() => { entered.value = true }))
})
</script>

<style scoped>
.atb { width: 100%; --acc: var(--viz-accent, var(--primary, #181818)); }
.atb-wrap { max-height: 380px; overflow: auto; }
.atb-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.atb-table th {
  position: sticky; top: 0; z-index: 1; background: #fff;
  text-align: start; font-size: 11.5px; font-weight: 700; color: var(--text-muted);
  padding: 6px 10px 8px; border-bottom: 2px solid color-mix(in srgb, var(--acc) 55%, transparent); white-space: nowrap;
}
.atb-table td { padding: 8px 10px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); vertical-align: top; }
.atb-table td.is-first { color: var(--text); font-weight: 700; white-space: nowrap; }
.atb-table th.is-num, .atb-table td.is-num { text-align: center; white-space: nowrap; }
.atb-table td.is-num span { color: var(--text); font-variant-numeric: tabular-nums; }
.atb-table tbody tr { opacity: 0; transform: translateY(6px);
  transition: opacity 0.45s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + var(--i) * 45ms),
              transform 0.55s var(--ease-silk, ease) calc(var(--silk-content-delay, 280ms) + var(--i) * 45ms), background 0.15s; }
.atb--in tbody tr { opacity: 1; transform: none; }
.atb-table tbody tr:hover { background: color-mix(in srgb, var(--acc) 5%, transparent); }
.atb-table tbody tr:last-child td { border-bottom: none; }
@media (prefers-reduced-motion: reduce) { .atb-table tbody tr { transition: none; opacity: 1; transform: none; } }
</style>
