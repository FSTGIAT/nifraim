import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion'
import { VizDonut, colorsFor } from './types'

const FONT = 'Heebo, sans-serif'
const PALETTE = [
  '#F57C00', '#E8720A', '#2E844A', '#4f46e5', '#ec4899',
  '#0891b2', '#f59e0b', '#7c3aed', '#0ea5e9', '#84cc16',
]

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const polar = (a: number) => {
    const rad = ((a - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }
  const start = polar(endAngle)
  const end = polar(startAngle)
  const largeArc = endAngle - startAngle > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`
}

export function DonutComposition(props: VizDonut) {
  const frame = useCurrentFrame()
  const { fps, width, height } = useVideoConfig()
  const colors = colorsFor()

  const slices = (props.data ?? [])
    .filter((s) => s.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)

  const total = slices.reduce((s, x) => s + x.value, 0) || 1

  const cx = width / 2
  const cy = height / 2 - 8
  const outerR = Math.min(width, height) * 0.28
  const innerR = outerR * 0.62
  const strokeW = outerR - innerR

  // Reveal slices 0→360 over 0..60 frames, staggered
  const revealProgress = interpolate(frame, [4, 60], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  let accAngle = 0
  const arcs = slices.map((s, i) => {
    const sliceAngle = (s.value / total) * 360
    const startAngle = accAngle
    const shownEnd = startAngle + sliceAngle * revealProgress
    accAngle += sliceAngle
    const highlight = s.label === props.highlight_label
    const explode = highlight
      ? spring({ frame: frame - 50, fps, config: { damping: 14, stiffness: 120 } }) * 12
      : 0
    const mid = (startAngle + (startAngle + sliceAngle)) / 2
    const rad = ((mid - 90) * Math.PI) / 180
    const dx = Math.cos(rad) * explode
    const dy = Math.sin(rad) * explode
    return {
      slice: s,
      startAngle,
      shownEnd,
      color: PALETTE[i % PALETTE.length],
      highlight,
      dx,
      dy,
    }
  })

  // Hero label — biggest slice's percentage
  const hero = slices[0]
  const heroPct = hero ? Math.round((hero.value / total) * 100) : 0
  const heroProgress = interpolate(frame, [10, 60], [0, heroPct], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  return (
    <div
      style={{
        width,
        height,
        direction: 'rtl',
        fontFamily: FONT,
        background: 'linear-gradient(135deg, #ffffff 0%, #fff8f0 100%)',
        color: '#181818',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Title */}
      <div
        style={{
          position: 'absolute',
          insetInline: 40,
          top: 36,
          fontSize: 22,
          fontWeight: 800,
          textAlign: 'center',
          opacity: interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
        }}
      >
        {props.title}
      </div>

      <svg width={width} height={height} style={{ position: 'absolute', inset: 0 }}>
        {arcs.map((a) => {
          const midR = (outerR + innerR) / 2
          const path = describeArc(cx + a.dx, cy + a.dy, midR, a.startAngle, a.shownEnd)
          return (
            <path
              key={a.slice.label}
              d={path}
              fill="none"
              stroke={a.color}
              strokeWidth={strokeW}
              strokeLinecap="butt"
              style={{
                filter: a.highlight ? `drop-shadow(0 0 14px ${a.color}99)` : 'none',
              }}
            />
          )
        })}
      </svg>

      {/* Hero % in center */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: cy - 32,
          textAlign: 'center',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            fontSize: 56,
            fontWeight: 900,
            color: colors.main,
            direction: 'ltr',
            fontVariantNumeric: 'tabular-nums',
            letterSpacing: '-0.02em',
          }}
        >
          {Math.round(heroProgress)}%
        </div>
        <div
          style={{
            fontSize: 14,
            color: '#706E6B',
            fontWeight: 600,
            marginTop: 4,
            maxWidth: 200,
            margin: '4px auto 0',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            padding: '0 12px',
          }}
        >
          {hero?.label ?? ''}
        </div>
      </div>

      {/* Legend */}
      <div
        style={{
          position: 'absolute',
          bottom: 32,
          insetInline: 40,
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px 14px',
          justifyContent: 'center',
          opacity: interpolate(frame, [40, 70], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          }),
        }}
      >
        {arcs.map((a) => (
          <div
            key={a.slice.label}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 13,
              fontWeight: a.highlight ? 700 : 500,
              color: '#3E3E3C',
            }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: 3,
                background: a.color,
                display: 'inline-block',
              }}
            />
            {a.slice.label}
          </div>
        ))}
      </div>
    </div>
  )
}
