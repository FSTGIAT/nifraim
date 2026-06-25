// Bright-bold categorical palette for data-viz (chart bars, donuts, treemaps,
// company legends). Modeled on the "Bright Bold Colors" reference: many clearly
// separable hues so every category/company/bar reads as distinct.
//
// This is intentionally SEPARATE from the brand UI tokens in App.vue (orange/
// green). Buttons, headers and semantic states (success/error) stay on-brand;
// categorical chart series use these bright hues so they don't collapse into a
// few oranges. Keep the order stable so colors are consistent across charts.
// Interleaved warm/cool so even a 5-bar chart shows a full bright spread
// (instead of running red→pink→yellow before reaching the greens/blues).
export const CHART_PALETTE = [
  '#EF5350', // coral red
  '#4E9DD0', // sky blue
  '#F9A937', // golden amber
  '#8E44AD', // purple
  '#9CCC3C', // lime green
  '#E84A7F', // magenta pink
  '#3DB6B0', // turquoise
  '#F4D35E', // soft yellow
  '#2F73C4', // cobalt blue
  '#4A8B2C', // forest green
  '#FF5C8A', // bright pink
  '#0E8C8A', // teal
  '#B79CEB', // lavender
  '#2C5F6B', // deep teal
  '#8FD9C6', // mint
]

// Pick a color by index (wraps around for long category lists).
export function chartColor(i) {
  return CHART_PALETTE[((i % CHART_PALETTE.length) + CHART_PALETTE.length) % CHART_PALETTE.length]
}

function hexToRgb(hex) {
  const clean = (hex || '#706E6B').replace('#', '')
  const full = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean
  const n = parseInt(full, 16)
  return { r: (n >> 16) & 0xff, g: (n >> 8) & 0xff, b: n & 0xff }
}

function dist2(a, b) {
  return (a.r - b.r) ** 2 + (a.g - b.g) ** 2 + (a.b - b.b) ** 2
}

// Return the palette color CLOSEST to a given hex (RGB distance). Used to map a
// company's brand color onto the on-palette hue nearest to it — keeps brand
// recognition while staying on-palette.
export function nearestChartColor(hex) {
  const t = hexToRgb(hex)
  let best = CHART_PALETTE[0]
  let bestD = Infinity
  for (const c of CHART_PALETTE) {
    const d = dist2(hexToRgb(c), t)
    if (d < bestD) { bestD = d; best = c }
  }
  return best
}

// Assign each item a DISTINCT palette color, preferring the one nearest its brand
// color and falling back to the next-nearest unused color on collision. This keeps
// look-alike brands (e.g. several red insurers) visually separable instead of all
// mapping to the same red. `items`: [{ key, brand }] in stable order.
// Returns Map<key, paletteHex>. Reuses colors only when items exceed the palette.
export function assignNearestDistinct(items) {
  const used = new Set()
  const out = new Map()
  for (const { key, brand } of items) {
    if (out.has(key)) continue
    const t = hexToRgb(brand)
    const ranked = CHART_PALETTE
      .map((c) => ({ c, d: dist2(hexToRgb(c), t) }))
      .sort((a, b) => a.d - b.d)
    const pick = ranked.find((r) => !used.has(r.c)) || ranked[0]
    used.add(pick.c)
    out.set(key, pick.c)
  }
  return out
}
