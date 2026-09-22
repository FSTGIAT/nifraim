/**
 * Seed → avatar identity. ONE source of truth.
 *
 * Both the CSS avatar (Avatar.vue) and the animated Remotion avatar
 * (remotion/AvatarLoop.tsx) derive their palette from here. If they each had
 * their own hash, the swatch a user taps in the picker would not match the
 * avatar they actually get — the preview would be a lie.
 *
 * Deterministic on purpose: the same seed always produces the same face, on
 * every device and every reload. Math.random() would hand a person a new
 * identity on each render, which is the opposite of an avatar.
 */

/** FNV-1a — small, stable, well-spread across short strings like handles. */
export function hashSeed (s) {
  let h = 0x811c9dc5
  for (let i = 0; i < String(s).length; i++) {
    h ^= String(s).charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

/** xorshift32 — deterministic 0..1 stream; each call advances the state. */
export function makeRng (state) {
  let s = state || 1
  return () => {
    s ^= s << 13; s >>>= 0
    s ^= s >>> 17
    s ^= s << 5; s >>>= 0
    return s / 0xffffffff
  }
}

/**
 * The base look of an avatar: two hues a pleasing distance apart, clamped to a
 * saturation/lightness band that keeps white text readable on top.
 *
 * The property read order here is load-bearing — AvatarLoop draws its orbs from
 * the SAME rng stream immediately after these six values, so any reordering
 * silently changes everyone's avatar.
 */
export function avatarPalette (seed) {
  const next = makeRng(hashSeed(seed || 'nifraim'))

  const hueA = Math.floor(next() * 360)
  const hueB = (hueA + 55 + Math.floor(next() * 90)) % 360
  const satA = 58 + Math.floor(next() * 16)
  const litA = 52 + Math.floor(next() * 8)
  const satB = 54 + Math.floor(next() * 16)
  const litB = 38 + Math.floor(next() * 8)

  return {
    bgA: `hsl(${hueA} ${satA}% ${litA}%)`,
    bgB: `hsl(${hueB} ${satB}% ${litB}%)`,
    angle: Math.floor(next() * 360),
    next,   // hand the live stream to AvatarLoop so its orbs stay in sync
  }
}

/** The CSS gradient for a seed — used by swatches and the static avatar. */
export function avatarGradient (seed) {
  const { bgA, bgB, angle } = avatarPalette(seed)
  return `linear-gradient(${angle}deg, ${bgA}, ${bgB})`
}

/**
 * The monogram palette — flat, deep tones that carry white text at 4.5:1.
 *
 * A financial product's account avatar is a monogram, not a character: the
 * generated faces read as a toy next to a commission table. These are the
 * app's own CHART_PALETTE entries, restricted to the ones dark enough for
 * white type, so an avatar can never introduce a colour the app does not
 * already use.
 */
export const AVATAR_TONES = [
  '#2F73C4', // cobalt
  '#2C5F6B', // deep teal
  '#0E8C8A', // teal
  '#4A8B2C', // forest
  '#8E44AD', // purple
  '#C42B60', // deep magenta
  '#D9820F', // amber
  '#A8412F', // clay
  '#3F5C8C', // slate blue
  '#5B6B4E', // moss
  '#6E4B8E', // plum
  '#1F6F5C', // pine
]

/**
 * A seed's flat tone. Derived straight from `hashSeed`, NOT from
 * `avatarPalette` — that function's rng read order is load-bearing for
 * AvatarLoop's orbs, and drawing one more value from it would silently change
 * everyone's animated avatar.
 */
export function avatarTone (seed) {
  return AVATAR_TONES[hashSeed(seed || 'nifraim') % AVATAR_TONES.length]
}

/** One or two letters: the person, not their file name. */
export function initialsFor (user) {
  const name = String(user?.full_name || '').trim()
  if (name) {
    const parts = name.split(/\s+/).filter(Boolean)
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
    return parts[0].slice(0, 2).toUpperCase()
  }
  const handle = String(user?.username || user?.email || '').trim()
  return handle ? handle.slice(0, 2).toUpperCase() : '—'
}

/**
 * The portrait set. Generated once and vendored, NOT fetched — an avatar that
 * needs the network is an avatar that is missing while the page loads, and a
 * third party would learn who is logged in every time a contact row renders.
 *
 * Two families, told apart by filename rather than by index: `flat-*` are the
 * flat-vector portraits, `soft-*` the soft-3D ones. An index range would have
 * silently re-labelled every avatar the first time the set was reordered.
 */
const PORTRAITS = Object.entries(
  import.meta.glob('../assets/avatars/*.webp', { eager: true, import: 'default' }),
)
  .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
  .map(([path, url]) => ({ url, family: path.includes('/soft-') ? 'soft' : 'flat' }))

export const AVATAR_FAMILIES = ['flat', 'soft']

/** The portrait a seed resolves to. Deterministic, like everything else here. */
export function avatarImage (seed) {
  if (!PORTRAITS.length) return ''
  return PORTRAITS[hashSeed(seed || 'nifraim') % PORTRAITS.length].url
}

/**
 * Which family a seed's portrait belongs to.
 *
 * Hashing stays over the WHOLE set, never over one family: a saved seed has to
 * resolve to the same face no matter which tab the picker happens to be on,
 * and filtering before hashing would have moved everyone's avatar the moment
 * the families were introduced.
 */
export function avatarFamily (seed) {
  if (!PORTRAITS.length) return 'flat'
  return PORTRAITS[hashSeed(seed || 'nifraim') % PORTRAITS.length].family
}

/**
 * The choices offered in the picker, optionally limited to one family.
 *
 * Walks suffixed seeds and keeps one per DISTINCT portrait, so the deck shows
 * every face exactly once — hashing straight onto `#1..#n` collided and the
 * same person turned up two or three times in a row. The bare username comes
 * first so "no choice" and "chose the first one" render identically.
 */
export function candidateSeeds (username, family = '') {
  const base = username || 'nifraim'
  if (!PORTRAITS.length) return [base]
  const want = family
    ? PORTRAITS.filter((p) => p.family === family).length
    : PORTRAITS.length
  const seen = new Set()
  const out = []
  for (let i = 0; out.length < want && i < PORTRAITS.length * 40; i++) {
    const seed = i === 0 ? base : `${base}#${i}`
    const idx = hashSeed(seed) % PORTRAITS.length
    if (family && PORTRAITS[idx].family !== family) continue
    if (seen.has(idx)) continue
    seen.add(idx)
    out.push(seed)
  }
  return out
}


/** What actually seeds a face: an explicit pick, else the username. */
export function seedFor (user) {
  return user?.avatar_seed || user?.username || 'nifraim'
}
