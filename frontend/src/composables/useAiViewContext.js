import { computed } from 'vue'
import {
  buildProductionComparisonSummary,
  buildCommissionComparisonSummary,
} from '../utils/comparisonSummary.js'

/**
 * Routes view-specific data into a structured AI context bundle:
 *   { viewKey, viewTitle, summary, suggestions, viewContextString }
 *
 * Supported viewKey values:
 *   - "production-comparison" → needs `comparisonResult` (the result returned by /api/production/compare)
 *   - "commission-comparison" → needs `customers` + `categoryLabel` + `companySources`
 *
 * Returns null when the view has no data yet — AiInsightCard treats null as
 * "don't render anything". Adding new views = adding new branches here.
 *
 * @param {{
 *   viewKey: string | import('vue').Ref<string>,
 *   comparisonResult?: any,
 *   customers?: any,
 *   categoryLabel?: any,
 *   companySources?: any,
 * }} opts
 */
export function useAiViewContext(opts) {
  const { viewKey, comparisonResult, customers, categoryLabel, companySources } = opts || {}
  return computed(() => {
    const key = typeof viewKey === 'string' ? viewKey : viewKey?.value

    if (key === 'production-comparison') {
      const result = comparisonResult?.value ?? comparisonResult
      if (!result) return null
      const built = buildProductionComparisonSummary(result)
      if (!built || !built.summary) return null
      return { viewKey: 'production-comparison', viewTitle: 'השוואת קבצים', ...built }
    }

    if (key === 'commission-comparison') {
      const list = customers?.value ?? customers ?? []
      const label = categoryLabel?.value ?? categoryLabel ?? ''
      const sources = companySources?.value ?? companySources ?? []
      const built = buildCommissionComparisonSummary(list, label, sources)
      if (!built || !built.summary) return null
      return { viewKey: 'commission-comparison', viewTitle: 'השוואת נפרעים', ...built }
    }

    return null
  })
}
