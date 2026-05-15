// Hebrew-friendly month-over-month delta formatter.
// Examples: monthDeltaPercent(120, 100) => "+20%", monthDeltaPercent(80, 100) => "−20%"
//           monthDeltaPercent(50, 0)    => "—" (no baseline)
export function monthDeltaPercent(current, previous) {
  if (previous === undefined || previous === null || Number(previous) === 0) return '—'
  const delta = ((Number(current) - Number(previous)) / Number(previous)) * 100
  if (!Number.isFinite(delta)) return '—'
  const rounded = Math.round(delta)
  if (rounded === 0) return '0%'
  const sign = rounded > 0 ? '+' : '−'
  return `${sign}${Math.abs(rounded)}%`
}

// Direction for color cues: 'up' / 'down' / 'flat' / 'none'
export function deltaDirection(current, previous) {
  if (previous === undefined || previous === null || Number(previous) === 0) return 'none'
  const c = Number(current); const p = Number(previous)
  if (!Number.isFinite(c) || !Number.isFinite(p)) return 'none'
  if (c > p) return 'up'
  if (c < p) return 'down'
  return 'flat'
}

// Compact ILS / number formatter — short suffixes for the dashboard sparklines.
// 1234567 => "1.2M ₪", 12500 => "12.5K ₪"
export function shortShekel(n) {
  if (n === null || n === undefined || isNaN(n)) return '—'
  const v = Number(n)
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(1).replace(/\.0$/, '')}M ₪`
  if (abs >= 1_000)     return `${(v / 1_000).toFixed(1).replace(/\.0$/, '')}K ₪`
  return `${Math.round(v).toLocaleString('he-IL')} ₪`
}
