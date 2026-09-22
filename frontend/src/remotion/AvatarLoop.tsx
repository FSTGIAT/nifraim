import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'
// One source of truth for seed → palette + character, shared with Avatar.vue so
// the picker's swatches match the avatar you actually get.
import { avatarTone, avatarImage } from '../utils/avatarSeed'
import { monogramMark, MONOGRAM_DEFS } from '../utils/avatarFace'

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

  // Same tone and same mark Avatar.vue draws for this seed, so the animated
  // avatar and every static one are literally the same identity. What moves is
  // the light across it, not the identity itself.
  const tone = avatarTone(seed)
  const mark = MONOGRAM_DEFS + monogramMark(seed)
  // Same portrait Avatar.vue resolves for this seed, so the animated avatar
  // and every static one are literally the same person.
  const portrait = avatarImage(seed)
  const bob = Math.sin(t * TAU) * 1.2


  const sheen = Math.sin(t * Math.PI) // 0 -> 1 -> 0, seamless at the wrap

  return (
    <AbsoluteFill
      style={{
        borderRadius: '50%',
        overflow: 'hidden',
        background: tone,
      }}
    >
      {/* Soft moving sheen, fading at both ends so the loop point is invisible. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(circle at ${30 + t * 40}% ${24 + t * 28}%, rgba(255,255,255,0.22) 0%, rgba(255,255,255,0) 58%)`,
          opacity: sheen * 0.8,
        }}
      />

      {/* The mark and the initials. `bob` is a sub-pixel rise, deliberately
          tiny: a big bounce reads as a toy, not a person — and this one is on
          an account in a financial product. */}
      <AbsoluteFill style={{ transform: `translateY(${bob}px)` }}>
        <svg
          viewBox="0 0 100 100"
          width="100%"
          height="100%"
          style={{ display: 'block' }}
          dangerouslySetInnerHTML={{ __html: mark }}
        />
        {portrait ? (
          <img
            src={portrait}
            alt=""
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              borderRadius: '50%',
            }}
          />
        ) : null}
        {portrait ? null : (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'grid',
              placeItems: 'center',
              color: '#fff',
              fontWeight: 700,
              fontSize: 38,
              letterSpacing: '0.02em',
              direction: 'ltr',
            }}
          >
            {initial}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  )
}
