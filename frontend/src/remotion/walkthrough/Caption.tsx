import { Easing, interpolate, spring, useVideoConfig } from 'remotion'

const FONT = "'Heebo', sans-serif"
const BRAND = '#F57C00'
const BRAND_DEEP = '#E65100'
const HAIRLINE = '#F2D9BC'

/**
 * Prominent caption banner at the TOP of a screenshot slide — Hebrew RTL.
 * The per-slide explanation is the headline: large, bold, ORANGE, on a faintly
 * tinted banner with a thick orange accent bar. Animates with a zoom-in pop on
 * entry and a zoom-out push on exit so the viewer's eye is drawn to it.
 */
export function Caption({
  text,
  index,
  total,
  local,
  durationInFrames,
}: {
  text: string
  index: number
  total: number
  local: number
  durationInFrames: number
}) {
  const { fps } = useVideoConfig()

  // Zoom-in pop: spring overshoots slightly past 1 then settles.
  const enter = spring({ frame: local - 2, fps, from: 0, to: 1, config: { damping: 11, mass: 0.6, stiffness: 120 } })
  const enterScale = 0.78 + 0.22 * enter
  const enterOpacity = interpolate(enter, [0, 0.3], [0, 1], { extrapolateRight: 'clamp' })

  // Zoom-out push on exit: grows + fades as it leaves.
  const exitT = interpolate(local, [durationInFrames - 18, durationInFrames - 2], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  })
  const scale = enterScale * (1 + exitT * 0.12)
  const opacity = Math.min(enterOpacity, 1 - exitT)

  return (
    <div
      style={{
        position: 'absolute',
        top: 28,
        insetInline: 0,
        display: 'flex',
        justifyContent: 'center',
        padding: '0 56px',
        opacity,
        transform: `scale(${scale})`,
        transformOrigin: 'center top',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 22,
          direction: 'rtl',
          fontFamily: FONT,
          maxWidth: 1700,
          background: 'linear-gradient(180deg, #FFFFFF 0%, #FFF4E6 100%)',
          border: `1.5px solid ${HAIRLINE}`,
          borderRadius: 20,
          padding: '20px 22px 20px 34px',
          boxShadow: `0 22px 52px rgba(230,81,0,0.20), 0 4px 14px rgba(26,20,16,0.10)`,
          overflow: 'hidden',
        }}
      >
        {/* thick orange leading-edge accent bar */}
        <div
          style={{
            flex: 'none',
            width: 12,
            alignSelf: 'stretch',
            margin: '-20px 0',
            background: `linear-gradient(${BRAND}, ${BRAND_DEEP})`,
          }}
        />

        <span
          style={{
            display: 'grid',
            placeItems: 'center',
            minWidth: 70,
            height: 44,
            padding: '0 12px',
            borderRadius: 999,
            background: `linear-gradient(135deg, ${BRAND}, ${BRAND_DEEP})`,
            color: '#fff',
            fontWeight: 800,
            fontSize: 22,
            direction: 'ltr',
            letterSpacing: 0.5,
            boxShadow: `0 6px 16px ${BRAND_DEEP}55`,
          }}
        >
          {index + 1}/{total}
        </span>

        <span
          style={{
            fontSize: 47,
            fontWeight: 800,
            color: BRAND_DEEP,
            lineHeight: 1.2,
            letterSpacing: -0.5,
            textAlign: 'center',
            textShadow: '0 1px 0 rgba(255,255,255,0.6)',
          }}
        >
          {text}
        </span>
      </div>
    </div>
  )
}
