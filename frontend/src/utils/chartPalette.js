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
  // Slots 1-11 are VALIDATED for categorical use (lightness band, chroma floor,
  // CVD separation, normal-vision floor) against the app's light chart surface.
  // Re-run before changing any value:
  //   node validate_palette.js "<comma-separated hexes>" --mode light
  // The previous values failed three checks: #F9A937/#9CCC3C/#F4D35E sat above
  // the lightness band, and magenta beside turquoise measured ΔE 5.7 (deutan) —
  // under the 6.0 floor, i.e. indistinguishable to a red-green colourblind
  // reader. EVERY slot keeps its original hue family — slot 8's yellow is the
  // primary 'run all portals' button (--chart-8-ink/-deep are built on it) and
  // slot 7's turquoise is the recruits tab, so neither could move families.
  // The separation was won by deepening slot 6's magenta instead.
  // Contrast vs surface is a WARN for four slots, which obligates the visible
  // labels + table view these charts ship (never colour alone).
  '#E04B48', // coral red
  '#4E9DD0', // sky blue
  '#D9820F', // golden amber
  '#8E44AD', // purple
  '#6FA82C', // lime green
  '#D6336C', // magenta pink
  '#0FA39B', // turquoise
  '#C9A227', // gold
  '#2F73C4', // cobalt blue
  '#4A8B2C', // forest green
  '#D96AB5', // orchid
  // Slots 12-15 are OUTSIDE the validated range — they cannot clear the chroma
  // floor without abandoning their hue families. A chart needing more than 11
  // categories must fold the remainder into "אחרות" rather than reach here.
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


// ── Stable per-company colour ────────────────────────────────────────────
// A company must keep the SAME colour in every chart and across every filter
// change. Assigning by array index makes colour follow RANK instead of the
// entity: filtering one company out, or a month where only one company
// reported, repaints all the survivors and the reader silently re-learns the
// legend. Keying off the company's own name fixes it.
//
// `COMPANY_BRAND`'s key order is the fixed registry; anything outside it (a
// new insurer) gets a deterministic hash slot, which can collide but never
// shifts between renders.
import { COMPANY_BRAND, brandForLabel } from './companyBrand.js'

const _BRAND_ORDER = Object.values(COMPANY_BRAND).map(b => b.label)

// Only the VALIDATED range — see the note on CHART_PALETTE. Beyond it a chart
// folds the remainder into "אחרות" rather than inventing a hue.
export const VALIDATED_SLOTS = 11

export function companyColor(name) {
  return CHART_PALETTE[preferredSlot(name)]
}

function preferredSlot(name) {
  if (!name) return 0
  const brand = brandForLabel(name)
  const idx = brand && brand.label ? _BRAND_ORDER.indexOf(brand.label) : -1
  if (idx >= 0) return idx % VALIDATED_SLOTS
  let h = 0
  const str = String(name)
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0
  return h % VALIDATED_SLOTS
}

/**
 * `Map(name → hex)` for a set of companies drawn together, with NO two sharing
 * a colour.
 *
 * `companyColor` alone cannot guarantee that: there are more known brands than
 * validated slots, so `index % 11` collides — live, הראל (brand 12) landed on
 * הפניקס's slot 1 and the two biggest companies in the chart were the same
 * blue. Two companies sharing a colour in one chart is strictly worse than a
 * company's colour shifting between two different charts, so preference gives
 * way to distinctness: each name takes its preferred slot when free, otherwise
 * the next free one, walking a fixed order so the result is deterministic for
 * a given set.
 */
export function assignCompanyColors(names) {
  const out = new Map()
  const taken = new Set()
  const list = Array.from(names || [])
  // Two passes: everyone who can have their preferred slot gets it first, so
  // one early collision can't cascade through the rest.
  for (const n of list) {
    const slot = preferredSlot(n)
    if (!taken.has(slot)) {
      taken.add(slot)
      out.set(n, CHART_PALETTE[slot])
    }
  }
  let next = 0
  for (const n of list) {
    if (out.has(n)) continue
    while (taken.has(next) && next < CHART_PALETTE.length) next++
    const slot = next < CHART_PALETTE.length ? next : out.size % VALIDATED_SLOTS
    taken.add(slot)
    out.set(n, CHART_PALETTE[slot])
  }
  return out
}
