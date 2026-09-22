import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'

/**
 * The "add" affordance, as motion rather than a dashed rectangle.
 *
 * The plus ITSELF never moves. It is the target you are aiming at, and a
 * rotating or scaling target is a worse target — so the motion lives entirely
 * in the ring and halo around it. A plus spun even slightly reads as an X,
 * which is the opposite action.
 *
 * Loop-perfect: the ring's rotation is a full 360° over the cycle and the
 * halo is a sine, so frame 0 and frame N are identical.
 */
export const PLUS_PULSE_FRAMES = 150 // 5s @ 30fps

const TAU = Math.PI * 2

type Props = { color?: string; active?: boolean }

export const PlusPulse: React.FC<Props> = ({ color = '#D6336C', active = false }) => {
  const frame = useCurrentFrame()
  const t = (frame / PLUS_PULSE_FRAMES) % 1
  const phase = t * TAU

  // Hover speeds the ring and lifts the glow — the control answering you.
  const spin = (active ? t * 2 : t) * 360
  const halo = (active ? 0.3 : 0.16) + 0.08 * Math.sin(phase)
  const breath = 1 + Math.sin(phase) * (active ? 0.07 : 0.04)

  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
      {/* halo */}
      <div
        style={{
          position: 'absolute', width: '92%', height: '92%', borderRadius: '50%',
          background: `radial-gradient(circle, ${color} 0%, transparent 66%)`,
          opacity: halo, transform: `scale(${breath})`,
        }}
      />
      {/* the travelling ring — a dashed circle turning once per cycle */}
      <div
        style={{
          position: 'absolute', width: '76%', height: '76%', borderRadius: '50%',
          border: `2px dashed ${color}`,
          opacity: active ? 0.85 : 0.5,
          transform: `rotate(${spin}deg)`,
        }}
      />
      {/* a solid arc riding the same turn, so the ring has a leading edge */}
      <div
        style={{
          position: 'absolute', width: '76%', height: '76%', borderRadius: '50%',
          border: `2px solid ${color}`,
          borderRightColor: 'transparent',
          borderBottomColor: 'transparent',
          borderLeftColor: 'transparent',
          opacity: active ? 0.95 : 0.7,
          transform: `rotate(${-spin * 1.5}deg)`,
        }}
      />
    </AbsoluteFill>
  )
}
