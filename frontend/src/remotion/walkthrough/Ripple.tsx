import { interpolate } from 'remotion'

const BRAND = '#F57C00'

/**
 * Click ripple + glow, centered on a canvas point. `frame` is the local frame
 * within the step; `clickAt` is the frame the press lands on.
 */
export function Ripple({
  x,
  y,
  frame,
  clickAt,
  color = BRAND,
}: {
  x: number
  y: number
  frame: number
  clickAt: number
  color?: string
}) {
  // Two staggered expanding rings.
  const rings = [0, 8].map((delay) => {
    const t = interpolate(frame, [clickAt + delay, clickAt + delay + 26], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    })
    const visible = frame >= clickAt + delay && frame <= clickAt + delay + 26
    return { t, visible }
  })

  // Soft target glow that pulses up at the press and lingers.
  const glow = interpolate(frame, [clickAt - 12, clickAt, clickAt + 40], [0, 1, 0.25], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  return (
    <div style={{ position: 'absolute', left: x, top: y, width: 0, height: 0, pointerEvents: 'none' }}>
      {/* glow halo */}
      <div
        style={{
          position: 'absolute',
          left: -70,
          top: -70,
          width: 140,
          height: 140,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${color}55 0%, ${color}00 70%)`,
          opacity: glow,
        }}
      />
      {rings.map((r, i) =>
        r.visible ? (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: -20,
              top: -20,
              width: 40,
              height: 40,
              borderRadius: '50%',
              border: `3px solid ${color}`,
              transform: `scale(${1 + r.t * 4.5})`,
              opacity: (1 - r.t) * 0.7,
            }}
          />
        ) : null,
      )}
    </div>
  )
}
