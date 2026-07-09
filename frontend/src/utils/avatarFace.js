/**
 * Seed → a generated CHARACTER, not just a colour.
 *
 * Draws a flat-illustration person as inline SVG: skin tone, hair style and
 * colour, eyes, brows, mouth, and sometimes glasses or a beard. Every feature is
 * chosen from the seed's deterministic rng stream, so one person always gets the
 * same face — on every device, every reload, and in everyone else's contact list.
 *
 * Inline SVG rather than an avatar service (DiceBear, Gravatar): the app's CSP
 * blocks external hosts, and this keeps a person's identity 64 bytes of seed
 * instead of a hosted image.
 *
 * Each feature draws from its OWN hashed sub-stream (`seed:skin`, `seed:hair`…)
 * rather than sharing one sequence. Sharing correlated the features with the
 * palette — the first draft put glasses on six faces out of eight — and it made
 * the draw ORDER load-bearing, so inserting a feature silently rerolled
 * everyone's face. Independent streams are stable under change.
 */
import { hashSeed, makeRng } from './avatarSeed.js'

const SKIN = ['#F5D0B0', '#EFC09A', '#E0A878', '#C98A5E', '#A26A45', '#7A4B2E']
const HAIR = ['#2B2118', '#4A3423', '#7B4B2A', '#B5793B', '#C9A227', '#8E8E93', '#3E4A78', '#8E44AD']
const CLOTH = ['#2F73C4', '#0E8C8A', '#8E44AD', '#E84A7F', '#3DB6B0', '#4A8B2C', '#F9A937']

/** One deterministic 0..1 value per (seed, feature) — independent of the others. */
const roll = (seed, feature) => makeRng(hashSeed(`${seed}:${feature}`))()
const pickFrom = (seed, feature, arr) => arr[Math.floor(roll(seed, feature) * arr.length)]

/** Shade a hex colour toward black — used for the neck shadow under the chin. */
function darken (hex, amount = 0.18) {
  const n = parseInt(hex.slice(1), 16)
  const r = Math.round(((n >> 16) & 255) * (1 - amount))
  const g = Math.round(((n >> 8) & 255) * (1 - amount))
  const b = Math.round((n & 255) * (1 - amount))
  return `rgb(${r},${g},${b})`
}

function hairMarkup (style, color) {
  switch (style) {
    case 0: // short fringe
      return `<path d="M28 46C28 27 40 21 50 21s22 6 22 25c0-9-7-13-22-13S28 37 28 46Z" fill="${color}"/>`
    case 1: // side part
      return `<path d="M28 46C28 27 40 21 50 21s22 6 22 25c0-10-9-12-19-9-6 2-9 6-13 8-4 2-7 1-9-1-1 3-1 2-1 2Z" fill="${color}"/>`
    case 2: // long
      return `<path d="M28 46C28 27 40 21 50 21s22 6 22 25c0-9-7-13-22-13S28 37 28 46Z" fill="${color}"/>
              <path d="M27 44h5v26h-5zM68 44h5v26h-5z" fill="${color}"/>`
    case 3: // curly
      return `<path d="M28 46C28 27 40 21 50 21s22 6 22 25c0-9-7-13-22-13S28 37 28 46Z" fill="${color}"/>
              <circle cx="33" cy="30" r="7" fill="${color}"/><circle cx="50" cy="24" r="8" fill="${color}"/>
              <circle cx="67" cy="30" r="7" fill="${color}"/>`
    case 4: // bun
      return `<path d="M28 46C28 27 40 21 50 21s22 6 22 25c0-9-7-13-22-13S28 37 28 46Z" fill="${color}"/>
              <circle cx="50" cy="17" r="7" fill="${color}"/>`
    case 5: // buzz cut
      return `<path d="M30 44c0-14 9-19 20-19s20 5 20 19c0-6-8-9-20-9s-20 3-20 9Z" fill="${color}"/>`
    default: // bald
      return ''
  }
}

function eyesMarkup (style, blink) {
  if (blink) {
    return `<path d="M39 45q3.5 3 7 0M54 45q3.5 3 7 0" stroke="#2B2118" stroke-width="2" fill="none" stroke-linecap="round"/>`
  }
  switch (style) {
    case 0: // dots
      return `<circle cx="42.5" cy="45" r="2.6" fill="#2B2118"/><circle cx="57.5" cy="45" r="2.6" fill="#2B2118"/>`
    case 1: // wide with pupils
      return `<circle cx="42.5" cy="45" r="4" fill="#fff"/><circle cx="57.5" cy="45" r="4" fill="#fff"/>
              <circle cx="43.2" cy="45.4" r="2" fill="#2B2118"/><circle cx="58.2" cy="45.4" r="2" fill="#2B2118"/>`
    case 2: // happy arcs
      return `<path d="M38.5 46q4-5 8 0M53.5 46q4-5 8 0" stroke="#2B2118" stroke-width="2.2" fill="none" stroke-linecap="round"/>`
    default: // sleepy
      return `<path d="M39 44.5h7M54 44.5h7" stroke="#2B2118" stroke-width="2.2" stroke-linecap="round"/>
              <circle cx="42.5" cy="46.6" r="1.8" fill="#2B2118"/><circle cx="57.5" cy="46.6" r="1.8" fill="#2B2118"/>`
  }
}

function mouthMarkup (style) {
  switch (style) {
    case 0: return `<path d="M42 55q8 7 16 0" stroke="#8A4A3E" stroke-width="2.2" fill="none" stroke-linecap="round"/>`
    case 1: return `<path d="M42 54h16a8 8 0 0 1-16 0Z" fill="#8A4A3E"/><path d="M43.5 54.6h13a6.5 6.5 0 0 1-13 0Z" fill="#fff"/>`
    case 2: return `<path d="M44 56h12" stroke="#8A4A3E" stroke-width="2.2" stroke-linecap="round"/>`
    case 3: return `<ellipse cx="50" cy="56" rx="3.4" ry="4" fill="#8A4A3E"/>`
    default: return `<path d="M43 55q7 5 14 -1" stroke="#8A4A3E" stroke-width="2.2" fill="none" stroke-linecap="round"/>`
  }
}

/**
 * Inner markup for a 100×100 viewBox. `blink` swaps the eyes shut — the animated
 * avatar drives it on a timer; the static one never blinks.
 */
export function faceSvg (seed, { blink = false } = {}) {
  const skin = pickFrom(seed, 'skin', SKIN)
  const hairColor = pickFrom(seed, 'hairColor', HAIR)
  const hairStyle = Math.floor(roll(seed, 'hairStyle') * 7)   // 0..6, 6 = bald
  const eyeStyle = Math.floor(roll(seed, 'eyes') * 4)
  const mouthStyle = Math.floor(roll(seed, 'mouth') * 5)
  const cloth = pickFrom(seed, 'cloth', CLOTH)
  const glasses = roll(seed, 'glasses') < 0.28
  const beard = roll(seed, 'beard') < 0.22 && hairStyle !== 4

  const behindHair = hairStyle === 2   // long hair sits behind the head

  return `
    <path d="M16 100c0-19 15-28 34-28s34 9 34 28Z" fill="${cloth}"/>
    <path d="M44 60h12v12H44z" fill="${darken(skin, 0.14)}"/>
    ${behindHair ? hairMarkup(hairStyle, hairColor) : ''}
    <circle cx="29.5" cy="47" r="4.2" fill="${skin}"/>
    <circle cx="70.5" cy="47" r="4.2" fill="${skin}"/>
    <ellipse cx="50" cy="45" rx="20" ry="21" fill="${skin}"/>
    ${behindHair ? '' : hairMarkup(hairStyle, hairColor)}
    <path d="M38.5 39.5q4-2.2 8 0M53.5 39.5q4-2.2 8 0" stroke="${hairColor}" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.85"/>
    ${eyesMarkup(eyeStyle, blink)}
    ${beard ? `<path d="M32 48c0 13 8 20 18 20s18-7 18-20c0 8-6 11-18 11s-18-3-18-11Z" fill="${hairColor}" opacity="0.92"/>` : ''}
    ${mouthMarkup(mouthStyle)}
    ${glasses ? `<g stroke="#2B2118" stroke-width="1.8" fill="none" opacity="0.9" stroke-linecap="round">
        <circle cx="42.5" cy="45" r="6.4"/><circle cx="57.5" cy="45" r="6.4"/>
        <path d="M48.9 44.6h2.2M36.1 44.2l-4.6-1M63.9 44.2l4.6-1"/></g>` : ''}
  `
}

/** Frames on which the animated avatar blinks — sparse, so it reads as alive. */
export function isBlinkFrame (frame, total) {
  const t = frame % total
  return (t > total * 0.42 && t < total * 0.42 + 5) || (t > total * 0.86 && t < total * 0.86 + 5)
}
