// Number formatting shared by every AI chart. One place, so a ₪ amount reads
// the same in a bar tip, a tooltip, a donut centre and the table view.

/** Full amount: ₪38,300 · 12.5% · 1,284 */
export function fmtFull(value, unit = '') {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  if (unit === '%') return `${n.toLocaleString('en-US', { maximumFractionDigits: 2 })}%`
  const abs = Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: Math.abs(n) < 100 ? 2 : 0 })
  return `${n < 0 ? '-' : ''}${unit === '₪' ? '₪' : ''}${abs}${unit && unit !== '₪' ? ` ${unit}` : ''}`
}

/** Compact for axes and stat rows: ₪794K · ₪1.2M · 12.9K */
export function fmtCompact(value, unit = '') {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  if (unit === '%') return `${Math.round(n * 10) / 10}%`
  const abs = Math.abs(n)
  let body
  if (abs >= 1e6) body = `${(abs / 1e6).toFixed(abs >= 1e7 ? 0 : 1)}M`
  else if (abs >= 1e4) body = `${Math.round(abs / 1e3)}K`
  else if (abs >= 1e3) body = `${(abs / 1e3).toFixed(1)}K`
  else body = `${Math.round(abs * 10) / 10}`
  return `${n < 0 ? '-' : ''}${unit === '₪' ? '₪' : ''}${body.replace('.0', '')}${unit && unit !== '₪' ? ` ${unit}` : ''}`
}

export function fmtPct(part, total) {
  if (!total) return '0%'
  const p = (part / total) * 100
  return `${p < 10 ? p.toFixed(1) : Math.round(p)}%`
}

/** 3-5 clean axis ticks between 0 and max: 0 / 200K / 400K / 600K / 800K */
export function niceTicks(min, max, count = 4) {
  const lo = Math.min(0, min)
  const hi = Math.max(0, max)
  const span = hi - lo || 1
  const raw = span / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || raw
  const start = Math.floor(lo / step) * step
  const end = Math.ceil(hi / step) * step
  const ticks = []
  for (let t = start; t <= end + step / 2; t += step) ticks.push(Math.round(t * 1e6) / 1e6)
  return { ticks, lo: start, hi: end }
}

export function prefersReducedMotion() {
  return typeof window !== 'undefined'
    && !!window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Tone by payload direction. Gain/loss use the chart pair from App.vue,
 * never the alert red (see the --chart-gain/--chart-loss comment there). */
export function toneFor(direction) {
  if (direction === 'up') return { main: 'var(--chart-gain)', soft: 'rgba(46, 132, 74, 0.5)' }
  if (direction === 'down') return { main: 'var(--chart-loss)', soft: 'rgba(220, 38, 38, 0.45)' }
  return { main: 'var(--primary)', soft: 'rgba(245, 124, 0, 0.52)' }
}
