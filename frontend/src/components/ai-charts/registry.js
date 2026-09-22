// The AI chart registry — the ONE place a chart type is declared.
//
// Adding a chart type:
//   1. Build `AiXxxChart.vue` taking a single `viz` prop (see AiBarChart.vue).
//   2. Register it below: component + table(viz) for the accessible table view.
//   3. Teach the model: add the type to `VIZ_TYPES` in
//      backend/app/services/ai_service.py (the prompt is generated from it).
//   4. Add a fixture to `docs/AI_VIZ.md` and render it.
//
// Types absent here (fund-track) still render through the Remotion player in
// AiVizPanel.vue, so a new native type never breaks an old one.
import AiBarChart from './AiBarChart.vue'
import AiTrendChart from './AiTrendChart.vue'
import AiDonutChart from './AiDonutChart.vue'
import AiKpiChart from './AiKpiChart.vue'
import { fmtFull, fmtPct } from './format.js'

function labelValueTable(viz) {
  const unit = viz.unit || ''
  return {
    columns: ['פריט', 'ערך'],
    rows: (viz.data || []).map((d) => [String(d.label), fmtFull(d.value, unit)]),
  }
}

function shareTable(viz) {
  const unit = viz.unit || ''
  const data = (viz.data || []).filter((d) => Number(d.value) > 0)
  const total = data.reduce((s, d) => s + Number(d.value), 0)
  return {
    columns: ['פלח', 'ערך', 'חלק'],
    rows: data
      .slice()
      .sort((a, b) => b.value - a.value)
      .map((d) => [String(d.label), fmtFull(d.value, unit), fmtPct(Number(d.value), total)]),
  }
}

export const CHART_TYPES = {
  bar: { component: AiBarChart, table: labelValueTable },
  trend: { component: AiTrendChart, table: labelValueTable },
  donut: { component: AiDonutChart, table: shareTable },
  kpi: { component: AiKpiChart, table: null },
}

// Names a model reaches for when it improvises — mapped, not rejected.
const ALIASES = { line: 'trend', column: 'trend', timeline: 'trend', pie: 'donut', ranking: 'bar', stat: 'kpi' }

export function resolveType(viz) {
  const t = String(viz?.type || '').toLowerCase()
  return CHART_TYPES[t] ? t : ALIASES[t] || null
}

/** The native chart entry for a viz payload, or null → Remotion fallback. */
export function nativeChartFor(viz) {
  const t = resolveType(viz)
  return t ? CHART_TYPES[t] : null
}
