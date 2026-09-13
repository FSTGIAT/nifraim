// Shared chart chrome for the production-insights tab.
//
// Centralised so every chart in the tab carries the same recessive grid, the
// same Heebo typography, and the same hover layer — an HTML chart is
// interactive by default, and a reader who can't hover a mark to see its value
// is left guessing at a bar's length.
//
// Text here wears TEXT tokens, never a series colour: the coloured mark beside
// a label is what carries identity.

const INK = '#3E3E3C'
const INK_MUTED = '#706E6B'
const GRID = '#E5E5E5'

export const BASE_CHART = {
  chart: {
    fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, easing: 'easeout', speed: 500 },
  },
  grid: { borderColor: GRID, strokeDashArray: 3 },
  states: { hover: { filter: { type: 'darken', value: 0.9 } } },
  tooltip: {
    theme: 'light',
    style: { fontFamily: 'Heebo, sans-serif', fontSize: '12px' },
  },
  noData: { text: 'אין נתונים', style: { fontFamily: 'Heebo, sans-serif', color: INK_MUTED } },
}

export const CHART_INK = INK
export const CHART_INK_MUTED = INK_MUTED

/** ₪ with thousands separators; '—' for nothing, so an empty cell reads as
 *  absent rather than as a real zero. */
export function money(v) {
  const n = Math.round(Number(v || 0))
  if (!n) return '—'
  return '₪' + n.toLocaleString('en-US')
}

/** Signed ₪ — for deltas, where the direction is the point. */
export function signedMoney(v) {
  const n = Math.round(Number(v || 0))
  if (!n) return '₪0'
  return (n > 0 ? '+' : '−') + '₪' + Math.abs(n).toLocaleString('en-US')
}

/** Compact axis ticks — ₪54.5M beats ₪54,536,228 repeated down an axis. */
export function axisMoney(v) {
  const n = Number(v || 0)
  const a = Math.abs(n)
  if (a >= 1e6) return '₪' + (n / 1e6).toFixed(1) + 'M'
  // One decimal below 10K, or a ₪2,051 tick and a ₪1,730 tick both render
  // "₪2K" and the axis repeats itself.
  if (a >= 1e4) return '₪' + Math.round(n / 1e3) + 'K'
  if (a >= 1e3) return '₪' + (n / 1e3).toFixed(1) + 'K'
  return '₪' + Math.round(n)
}

export function pct(v, digits = 2) {
  if (v === null || v === undefined) return '—'
  const n = Number(v) * 100
  return (n < 1 ? n.toFixed(3) : n.toFixed(digits)) + '%'
}
