// Shared types for Remotion viz payloads emitted by the AI stream.
// Keep in lockstep with backend system-prompt examples in ai_service.py.

export interface VizBarPoint {
  label: string
  value: number
  /** Optional stable id (e.g. client id_number) for future drill-down. */
  id?: string
}

export interface VizBar {
  type: 'bar'
  title: string
  unit?: string
  /** Direction for coloring: 'up' = emerald, 'down' = red-deep, else neutral primary orange */
  direction?: 'up' | 'down' | 'neutral'
  data: VizBarPoint[]
  /** label that should pulse / stand out */
  highlight_label?: string
  /** short narrative shown at bottom, e.g. "75% ממקור אחד: יחזקאל קר" */
  insight?: string
}

export interface VizKpi {
  type: 'kpi'
  title: string
  value: number
  unit?: string
  subtitle?: string
  direction?: 'up' | 'down' | 'neutral'
}

export interface VizDonutSlice {
  label: string
  value: number
}

export interface VizDonut {
  type: 'donut'
  title: string
  unit?: string
  data: VizDonutSlice[]
  highlight_label?: string
  insight?: string
}

export type Viz = VizBar | VizKpi | VizDonut

/** Directional brand colors shared across compositions. */
export const VIZ_COLORS = {
  up: { main: '#2E844A', soft: 'rgba(46, 132, 74, 0.12)' },
  down: { main: '#C23934', soft: 'rgba(194, 57, 52, 0.12)' },
  neutral: { main: '#F57C00', soft: 'rgba(245, 124, 0, 0.12)' },
} as const

export function colorsFor(direction?: 'up' | 'down' | 'neutral') {
  return VIZ_COLORS[direction ?? 'neutral']
}

export function formatMoney(value: number, unit = '₪'): string {
  const abs = Math.abs(Math.round(value))
  const sign = value < 0 ? '-' : ''
  return `${sign}${unit}${abs.toLocaleString('en-US')}`
}
