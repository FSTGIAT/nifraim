import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion'
import { VizKpi, colorsFor, formatMoney } from './types'

const FONT = 'Heebo, sans-serif'

export function KpiComposition(props: VizKpi) {
  const frame = useCurrentFrame()
  const { fps, width, height } = useVideoConfig()
  const colors = colorsFor(props.direction)

  // CountUp: frame 0..60
  const progress = spring({
    frame: frame - 4,
    fps,
    config: { damping: 18, mass: 0.9, stiffness: 110 },
  })
  const shownValue = props.value * progress

  const titleOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: 'clamp',
  })
  const subtitleOpacity = interpolate(frame, [38, 58], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })
  const subtitleY = interpolate(frame, [38, 58], [14, 0], {
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
        background:
          'radial-gradient(circle at top left, rgba(245,124,0,0.08), transparent 60%), #ffffff',
        color: '#181818',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 42,
        position: 'relative',
      }}
    >
      {/* Title */}
      <div
        style={{
          fontSize: 20,
          fontWeight: 700,
          color: '#706E6B',
          opacity: titleOpacity,
          marginBottom: 18,
          textAlign: 'center',
        }}
      >
        {props.title}
      </div>

      {/* Hero value */}
      <div
        style={{
          fontSize: 96,
          fontWeight: 900,
          lineHeight: 1,
          color: colors.main,
          direction: 'ltr',
          letterSpacing: '-0.02em',
          fontVariantNumeric: 'tabular-nums',
          textShadow: `0 4px 24px ${colors.main}22`,
        }}
      >
        {formatMoney(shownValue, props.unit ?? '₪')}
      </div>

      {/* Subtitle */}
      {props.subtitle ? (
        <div
          style={{
            marginTop: 22,
            padding: '10px 18px',
            borderRadius: 999,
            background: colors.soft,
            color: colors.main,
            fontSize: 16,
            fontWeight: 700,
            opacity: subtitleOpacity,
            transform: `translateY(${subtitleY}px)`,
          }}
        >
          {props.subtitle}
        </div>
      ) : null}
    </div>
  )
}
