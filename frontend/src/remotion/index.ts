import { BarComposition } from './BarComposition'
import { KpiComposition } from './KpiComposition'
import { DonutComposition } from './DonutComposition'
import type { Viz } from './types'

export { BarComposition, KpiComposition, DonutComposition }
export { WelcomeComposition } from './WelcomeComposition'
export type { WelcomeCompositionProps } from './WelcomeComposition'
export type { Viz } from './types'
export * from './types'

/** Map a Viz payload type to its Remotion composition component. */
export function componentForViz(viz: Viz) {
  switch (viz.type) {
    case 'bar':
      return BarComposition
    case 'kpi':
      return KpiComposition
    case 'donut':
      return DonutComposition
  }
}

/** Per-type composition dimensions (width × height). Chosen for chat panel layout. */
export function sizeForViz(viz: Viz): { width: number; height: number } {
  if (viz.type === 'kpi') return { width: 800, height: 400 }
  if (viz.type === 'donut') return { width: 720, height: 560 }
  // bar — taller to accommodate many rows
  return { width: 800, height: 560 }
}

/** Total frames to run the intro. 30 fps × 3 s feels right for all types. */
export const VIZ_DURATION_FRAMES = 90
export const VIZ_FPS = 30
