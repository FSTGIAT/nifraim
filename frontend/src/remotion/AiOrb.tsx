import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'

/**
 * The AI assistant's orb — the workspace's one always-present AI affordance.
 *
 * Replaces a full-width summary card that sat above every comparison. The card
 * spent a whole band of the page restating what the charts below already said;
 * the orb spends a 44px circle and opens the same conversation.
 *
 * Two motion states:
 *   idle    — the orb breathes and its sparks drift a slow full turn per
 *             cycle. Enough to read as alive from across the page; the first
 *             pass parked the sparks at idle and at widget size that looked
 *             like a static dot.
 *   active  — mounted while the conversation sheet is open: the sparks run at
 *             double speed and the glow lifts, so it reads as "listening".
 *
 * Loop-perfect: every term is a function of sin/cos over a full turn of the
 * cycle, so frame 0 and frame N are identical and the wrap is invisible.
 */
export const AI_ORB_FRAMES = 120 // 4s @ 30fps

const TAU = Math.PI * 2

type Props = { color?: string; active?: boolean }

export const AiOrb: React.FC<Props> = ({ color = '#7C4DBE', active = false }) => {
  const frame = useCurrentFrame()
  const t = (frame / AI_ORB_FRAMES) % 1
  const phase = t * TAU

  // The breath. Visible at idle, awake when active, never frantic.
  const amp = active ? 0.12 : 0.085
  const breath = 1 + Math.sin(phase) * amp
  const glow = active ? 0.42 + 0.18 * Math.sin(phase) : 0.3 + 0.12 * Math.sin(phase)
  // A slow counter-rotating halo gives the orb depth without a second element
  // fighting the sparks for attention.
  const spin = (active ? t * 2 : t) * 360

  // Three sparks orbiting the core. They only travel while active — at rest
  // they sit still at their phase offsets so nothing moves for its own sake.
  const sparks = [0, 1 / 3, 2 / 3].map((offset, i) => {
    // Always travelling — at idle one full turn per cycle, double when active.
    const a = ((active ? t * 2 : t) + offset) * TAU
    const r = 31 + (i % 2 === 0 ? 0 : 4)
    return {
      x: 50 + Math.cos(a) * r,
      y: 50 + Math.sin(a) * r,
      s: i === 0 ? 5.6 : 4.2,
      o: active ? 0.7 + 0.28 * Math.sin(a * 2) : 0.5 + 0.22 * Math.sin(a * 2),
    }
  })

  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
      {/* soft halo */}
      <div
        style={{
          position: 'absolute', width: '88%', height: '88%', borderRadius: '50%',
          background: `radial-gradient(circle, ${color} 0%, transparent 68%)`,
          opacity: glow, transform: `scale(${breath})`,
        }}
      />
      {/* a thin arc that sweeps the rim — the cue that reads as "thinking" */}
      <div
        style={{
          position: 'absolute', width: '74%', height: '74%', borderRadius: '50%',
          border: `2px solid ${color}`,
          borderRightColor: 'transparent', borderBottomColor: 'transparent',
          opacity: active ? 0.75 : 0.45,
          transform: `rotate(${spin}deg)`,
        }}
      />
      {/* the core */}
      <div
        style={{
          position: 'absolute', width: '52%', height: '52%', borderRadius: '50%',
          background: color, opacity: 0.95, transform: `scale(${breath})`,
        }}
      />
      {/* sparks */}
      {sparks.map((s, i) => (
        <div
          key={i}
          style={{
            position: 'absolute', left: `${s.x}%`, top: `${s.y}%`,
            width: s.s, height: s.s, marginLeft: -s.s / 2, marginTop: -s.s / 2,
            // The sparks orbit OUTSIDE the core, over the widget's own light
            // surface, so they take the accent colour — white dots on a white
            // card rendered as nothing at all.
            borderRadius: '50%', background: color, opacity: s.o,
          }}
        />
      ))}
    </AbsoluteFill>
  )
}
