import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion'
import { FONT, SOFT, tint } from './landingPalette'

// Feature 05 — Personal diagrammatic AI assistant.
// Visual: 6 nodes in a soft graph layout connected by curved edges.
// Edges draw in one-by-one (line dash trick), nodes "wake" with a small scale pop,
// a "?" pill sits in the corner, the central node pulses with a "✓".
// 90 frames @ 30fps = 3s seamless loop.

const ACCENT = SOFT.feature05

// Layout in normalized 0..1 coords (will multiply by canvas size).
const NODES = [
  { id: 'center', nx: 0.5, ny: 0.5, label: 'תיק', size: 64 },
  { id: 'n1', nx: 0.18, ny: 0.32, label: 'גמל', size: 44 },
  { id: 'n2', nx: 0.82, ny: 0.3, label: 'פנסיה', size: 44 },
  { id: 'n3', nx: 0.22, ny: 0.74, label: 'ביטוח', size: 44 },
  { id: 'n4', nx: 0.78, ny: 0.72, label: 'נפרעים', size: 44 },
  { id: 'n5', nx: 0.5, ny: 0.16, label: 'הסכמים', size: 44 },
]
const EDGES: Array<[string, string]> = [
  ['center', 'n1'],
  ['center', 'n2'],
  ['center', 'n3'],
  ['center', 'n4'],
  ['center', 'n5'],
  ['n1', 'n3'],
  ['n2', 'n4'],
]

export function Feature05AiDiagram() {
  const frame = useCurrentFrame()
  const { width, height, durationInFrames } = useVideoConfig()

  // Map nodes into canvas pixel coords (with margin so labels don't clip)
  const inset = 80
  const w = width - inset * 2
  const h = height - inset * 2
  const nodes = NODES.map((n) => ({
    ...n,
    x: inset + n.nx * w,
    y: inset + n.ny * h,
  }))
  const nodeById = Object.fromEntries(nodes.map((n) => [n.id, n]))

  // Central pulse — full-period sine for seamless loop
  const pulse = 0.5 + 0.5 * Math.sin((frame / durationInFrames) * Math.PI * 2)

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 50% 50%, ${SOFT.bgTop} 0%, ${SOFT.bgBottom} 100%)`,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {/* Amber accent orb */}
      <div
        style={{
          position: 'absolute',
          width: width * 0.55,
          height: width * 0.55,
          borderRadius: '50%',
          background: tint(ACCENT, 0.1),
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          filter: 'blur(90px)',
        }}
      />

      {/* SVG graph */}
      <svg
        style={{ position: 'absolute', inset: 0 }}
        viewBox={`0 0 ${width} ${height}`}
      >
        {/* Edges — draw in one by one */}
        {EDGES.map(([from, to], i) => {
          const start = 10 + i * 5
          const draw = interpolate(frame, [start, start + 22], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          })
          const a = nodeById[from]
          const b = nodeById[to]
          // Slight curve via control point perpendicular to midpoint
          const mx = (a.x + b.x) / 2
          const my = (a.y + b.y) / 2
          const dx = b.x - a.x
          const dy = b.y - a.y
          const len = Math.hypot(dx, dy)
          // Perpendicular offset, small bow
          const nx = -dy / len
          const ny = dx / len
          const bow = 30
          const cx = mx + nx * bow
          const cy = my + ny * bow
          const path = `M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`
          const pathLen = len * 1.3
          return (
            <path
              key={i}
              d={path}
              fill="none"
              stroke={ACCENT}
              strokeWidth={2.2}
              strokeLinecap="round"
              opacity={0.55}
              strokeDasharray={pathLen}
              strokeDashoffset={pathLen * (1 - draw)}
            />
          )
        })}
      </svg>

      {/* Nodes — placed via absolute divs for crisp text */}
      {nodes.map((n, i) => {
        const isCenter = n.id === 'center'
        // Each node has an entrance window
        const start = isCenter ? 0 : 16 + i * 4
        const scale = interpolate(frame, [start, start + 14], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
        const op = interpolate(frame, [start, start + 10], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
        const sz = n.size
        const finalScale = isCenter ? 1 + pulse * 0.04 : 1
        return (
          <div
            key={n.id}
            style={{
              position: 'absolute',
              left: n.x - sz / 2,
              top: n.y - sz / 2,
              width: sz,
              height: sz,
              borderRadius: '50%',
              background: isCenter ? ACCENT : SOFT.card,
              border: isCenter ? `2px solid ${ACCENT}` : `2px solid ${tint(ACCENT, 0.5)}`,
              boxShadow: isCenter
                ? `0 0 0 ${8 + pulse * 8}px ${tint(ACCENT, 0.15 - pulse * 0.06)}`
                : SOFT.shadowSoft,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transform: `scale(${scale * finalScale})`,
              opacity: op,
            }}
          >
            {isCenter ? (
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: SOFT.text,
                  letterSpacing: '-0.01em',
                }}
              >
                {n.label}
              </span>
            )}
          </div>
        )
      })}

      {/* Center label below central node */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: nodeById.center.y + 50,
          textAlign: 'center',
          fontSize: 14,
          fontWeight: 700,
          color: SOFT.textMuted,
          letterSpacing: '0.05em',
        }}
      >
        תיק הביטוח שלכם
      </div>

      {/* "?" pill in bottom-right corner */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          right: 60,
          background: SOFT.card,
          border: `1px solid ${SOFT.divider}`,
          borderRadius: 22,
          padding: '14px 22px',
          boxShadow: SOFT.shadowSoft,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          opacity: interpolate(frame, [50, 66], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          }),
        }}
      >
        <span
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: tint(ACCENT, 0.18),
            color: ACCENT,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 900,
            fontSize: 18,
          }}
        >
          ?
        </span>
        <span style={{ fontSize: 15, fontWeight: 700, color: SOFT.text }}>
          שאלו את העוזר
        </span>
      </div>
    </AbsoluteFill>
  )
}
