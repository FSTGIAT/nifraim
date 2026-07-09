import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'
// One source of truth for seed → palette + character, shared with Avatar.vue so
// the picker's swatches match the avatar you actually get.
import { avatarPalette } from '../utils/avatarSeed'
import { faceSvg, isBlinkFrame } from '../utils/avatarFace'

/**
 * Generative animated avatar for a single person.
 *
 * "Random" but NOT random: every visual property is derived from a hash of the
 * user's `seed` (their @username), so the same person always gets the same face
 * on every device and every reload. Math.random() here would give someone a new
 * identity on each render, which is the opposite of an avatar.
 *
 * Loop-perfect: orbs travel a full turn of sin/cos over the loop, and the sheen
 * fades to 0 at both ends, so the wrap is seamless.
 *
 * Mounted at most ONCE at a time (the chat header's own avatar) — never one per
 * contact row. Contact rows use the cheap CSS gradient in Avatar.vue.
 */
export const AVATAR_LOOP_FRAMES = 240 // 8s @ 30fps

const TAU = Math.PI * 2

type Props = { seed?: string; initial?: string }

export const AvatarLoop: React.FC<Props> = ({ seed = 'nifraim', initial = '?' }) => {
  const frame = useCurrentFrame()
  const t = frame / AVATAR_LOOP_FRAMES // 0..1 over the loop

  // `next` is the SAME rng stream the palette consumed, handed back mid-flight —
  // the orbs below continue it, so this face matches the picker's swatch.
  const { bgA, bgB, angle, next } = avatarPalette(seed)

  // faceSvg re-derives from the seed independently (its own fresh stream), so it
  // stays identical to what Avatar.vue draws for the same seed.
  const face = faceSvg(seed, { blink: isBlinkFrame(frame, AVATAR_LOOP_FRAMES) })
  const bob = Math.sin(t * TAU) * 1.2

  // 3 orbs, each with its own orbit radius, phase and size — this is what makes
  // two users with similar hues still read as different faces.
  const orbs = Array.from({ length: 3 }, () => ({
    size: 26 + next() * 34,
    cx: 22 + next() * 56,
    cy: 22 + next() * 56,
    r: 6 + next() * 12,
    phase: next() * TAU,
    dir: next() > 0.5 ? 1 : -1,
    hue: Math.floor(next() * 360),
    op: 0.24 + next() * 0.22,
  }))

  const sheen = Math.sin(t * Math.PI) // 0 -> 1 -> 0, seamless at the wrap

  return (
    <AbsoluteFill
      style={{
        borderRadius: '50%',
        overflow: 'hidden',
        background: `linear-gradient(${angle}deg, ${bgA}, ${bgB})`,
      }}
    >
      {orbs.map((o, i) => {
        const a = o.phase + o.dir * t * TAU
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              width: o.size,
              height: o.size,
              left: `${o.cx + Math.cos(a) * o.r}%`,
              top: `${o.cy + Math.sin(a) * o.r}%`,
              transform: 'translate(-50%, -50%)',
              borderRadius: '50%',
              background: `hsl(${o.hue} 80% 70%)`,
              opacity: o.op,
              filter: 'blur(14px)',
            }}
          />
        )
      })}

      {/* Soft moving sheen, fading at both ends so the loop point is invisible. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(circle at ${28 + t * 44}% ${22 + t * 30}%, rgba(255,255,255,0.42) 0%, rgba(255,255,255,0) 62%)`,
          opacity: sheen * 0.75,
        }}
      />

      {/* The character. Same seed, same face as the static Avatar.vue — it just
          blinks and breathes here. `bob` is a sub-pixel rise, deliberately tiny:
          a big bounce reads as a toy, not a person. */}
      <AbsoluteFill style={{ transform: `translateY(${bob}px)` }}>
        <svg
          viewBox="0 0 100 100"
          width="100%"
          height="100%"
          style={{ display: 'block' }}
          dangerouslySetInnerHTML={{ __html: face }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  )
}
