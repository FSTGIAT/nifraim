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
 * The choices offered in the picker. The first is the person's default (their
 * bare username) so "no choice" and "chose the first one" render identically.
 */
export function candidateSeeds (username, count = 8) {
  const base = username || 'nifraim'
  return Array.from({ length: count }, (_, i) => (i === 0 ? base : `${base}#${i}`))
}

/** What actually seeds a face: an explicit pick, else the username. */
export function seedFor (user) {
  return user?.avatar_seed || user?.username || 'nifraim'
}
