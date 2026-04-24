import { computed } from 'vue'
import { buildProductionComparisonSummary } from '../utils/comparisonSummary.js'

/**
 * Phase 1: the only supported view is the Production file-comparison view.
 * Other tabs get a null viewContext, which tells AiInsightCard to render nothing.
 * Adding new views = adding new branches here.
 *
 * @param {{ viewKey: import('vue').Ref<string>, comparisonResult: import('vue').Ref<any> }} opts
 * @returns {import('vue').ComputedRef<{
 *   viewKey: string,
 *   viewTitle: string,
 *   summary: string,
 *   suggestions: string[],
 *   viewContextString: string,
 * } | null>}
 */
export function useAiViewContext({ viewKey, comparisonResult }) {
  return computed(() => {
    const key = typeof viewKey === 'string' ? viewKey : viewKey?.value
    const result = comparisonResult?.value ?? comparisonResult

    if (key === 'production-comparison' && result) {
      const built = buildProductionComparisonSummary(result)
      if (!built || !built.summary) return null
      return {
        viewKey: 'production-comparison',
        viewTitle: 'השוואת קבצים',
        ...built,
      }
    }

    return null
  })
}
