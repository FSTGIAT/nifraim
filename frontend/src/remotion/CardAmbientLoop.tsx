import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'

/**
 * Abstract, color-matched ambient loop for a workspace card background.
 * Tinted entirely by the `color` prop (the card's --accent) so one scene
 * serves all 8 cards. Mounted only while a card is hovered. Motion is subtle
 * and low-opacity so the card's icon/label stay readable on top.
 *
 * Loop-perfect: blobs drift on sin/cos of a full-turn phase; the light sweep
 * moves linearly but fades to 0 opacity at both ends so the wrap is seamless.
 */
export const CARD_AMBIENT_LOOP_FRAMES = 180 // 6s @ 30fps

const TAU = Math.PI * 2

type Props = { color?: string }

export const CardAmbientLoop: React.FC<Props> = ({ color = '#2F73C4' }) => {
  const frame = useCurrentFrame()
  const t = frame / CARD_AMBIENT_LOOP_FRAMES // 0..1 over the loop

  // Drifting soft blobs (positions in %, sizes in px on a ~220×170 comp).
  const blobs = [
    { size: 150, ox: 28, oy: 34, ax: 13, ay: 9, ph: 0.0, op: 0.30 },
    { size: 120, ox: 74, oy: 64, ax: 11, ay: 13, ph: 2.1, op: 0.22 },
    { size: 90, ox: 56, oy: 18, ax: 15, ay: 12, ph: 4.0, op: 0.16 },
  ]

  const sweepX = -40 + t * 180 // % — travels fully across
  const sweepOpacity = Math.sin(Math.PI * t) * 0.20 // 0 at both ends → seamless

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent', overflow: 'hidden' }}>
      {blobs.map((b, i) => {
        const cx = b.ox + Math.cos(t * TAU + b.ph) * b.ax
        const cy = b.oy + Math.sin(t * TAU + b.ph) * b.ay
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${cx}%`,
              top: `${cy}%`,
              width: b.size,
              height: b.size,
              marginLeft: -b.size / 2,
              marginTop: -b.size / 2,
              borderRadius: '50%',
              background: `radial-gradient(circle, ${color} 0%, ${color}00 70%)`,
              opacity: b.op,
              filter: 'blur(6px)',
            }}
          />
        )
      })}
      <div
        style={{
          position: 'absolute',
          top: '-30%',
          left: `${sweepX}%`,
          width: '42%',
          height: '160%',
          transform: 'rotate(18deg)',
          background: `linear-gradient(90deg, ${color}00 0%, ${color} 50%, ${color}00 100%)`,
          opacity: sweepOpacity,
          filter: 'blur(10px)',
        }}
      />
    </AbsoluteFill>
  )
}
