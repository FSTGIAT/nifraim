// Soft, cream-friendly palette for landing feature clips.
// Explicitly NOT the saturated #F57C00 / #2D2522 of HeroProduct.tsx —
// these clips sit inside Chapter 04 cards next to the cream chapter sections,
// so accents are muted to read as editorial rather than promotional.

export const SOFT = {
  // Backgrounds (warm cream gradient stops)
  bgTop: '#FAF6F0',
  bgBottom: '#F0E8DC',
  card: '#FFFFFF',
  cardSoft: '#FAF6F0',

  // Text — warm dark, not pure black
  text: '#3A322F',
  textMuted: '#7A6E68',
  textDim: '#A89E97',

  // 5 muted accents — one per feature, harmonious in cream
  feature01: '#D4936F', // soft peach/copper — auto-load
  feature02: '#9CAE9F', // soft sage — agreements
  feature03: '#8B95A8', // soft slate — audit
  feature04: '#B89AAC', // soft mauve — insights
  feature05: '#D4B26A', // soft amber — AI diagram

  // Subtle dividers / borders
  divider: 'rgba(45, 37, 34, 0.08)',
  dividerSoft: 'rgba(45, 37, 34, 0.04)',

  // Soft shadows (HeroProduct uses rgba(45,37,34,0.14) — too sharp here)
  shadowSoft: '0 12px 32px rgba(45, 37, 34, 0.06)',
  shadowMed: '0 20px 48px rgba(45, 37, 34, 0.08)',
} as const

export const FONT = "'Heebo', -apple-system, sans-serif"

/** Append 2-char hex alpha to a 6-char hex color, e.g. tint('#D4936F', 0.2) → '#D4936F33' */
export function tint(hex: string, alpha: number): string {
  const a = Math.round(Math.max(0, Math.min(1, alpha)) * 255)
    .toString(16)
    .padStart(2, '0')
  return `${hex}${a}`
}
