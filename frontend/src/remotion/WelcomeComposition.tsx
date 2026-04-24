import { GridPixelateWipe } from './GridPixelateWipe'
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion'

const FONT = "'Heebo', sans-serif"
const CREAM = '#FFF8F0'

export interface WelcomeCompositionProps {
  userName?: string
}

function clamp(min: number, val: number, max: number) {
  return Math.max(min, Math.min(max, val))
}

function SceneA() {
  const frame = useCurrentFrame()
  const { width, height } = useVideoConfig()

  const nifraimSize = clamp(40, width * 0.072, 120)
  const tileSize = clamp(56, width * 0.065, 96)
  const iconSize = tileSize * 0.48
  const gap = clamp(12, width * 0.015, 24)

  const tileOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' })
  const tileY = interpolate(frame, [0, 14], [10, 0], { extrapolateRight: 'clamp' })
  const wordOpacity = interpolate(frame, [4, 16], [0, 1], { extrapolateRight: 'clamp' })
  const wordY = interpolate(frame, [4, 18], [12, 0], { extrapolateRight: 'clamp' })

  const circleBig = clamp(160, Math.max(width, height) * 0.22, 340)
  const circleMid = clamp(100, Math.max(width, height) * 0.14, 220)
  const circleSmall = clamp(56, Math.max(width, height) * 0.07, 120)

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: CREAM,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
        padding: '0 24px',
      }}
    >
      <div
        style={{
          position: 'absolute',
          width: circleBig,
          height: circleBig,
          borderRadius: '50%',
          background: 'rgba(245,124,0,0.08)',
          top: -circleBig * 0.25,
          insetInlineStart: -circleBig * 0.2,
          filter: 'blur(2px)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: circleMid,
          height: circleMid,
          borderRadius: '50%',
          background: 'rgba(255,152,0,0.06)',
          bottom: height * 0.1,
          insetInlineEnd: width * 0.05,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: circleSmall,
          height: circleSmall,
          borderRadius: '50%',
          background: 'rgba(255,183,77,0.10)',
          top: '28%',
          insetInlineEnd: '22%',
        }}
      />

      <div
        style={{
          width: tileSize,
          height: tileSize,
          borderRadius: tileSize * 0.24,
          background: 'rgba(245,124,0,0.10)',
          border: '1px solid rgba(245,124,0,0.18)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: tileOpacity,
          transform: `translateY(${tileY}px)`,
        }}
      >
        <svg
          width={iconSize}
          height={iconSize}
          viewBox="0 0 24 24"
          fill="none"
          stroke="#E65100"
          strokeWidth={2.2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      </div>

      <div
        style={{
          fontSize: nifraimSize,
          fontWeight: 900,
          letterSpacing: '-0.04em',
          color: '#E65100',
          lineHeight: 1,
          opacity: wordOpacity,
          transform: `translateY(${wordY}px)`,
        }}
      >
        Nifraim
      </div>

    </div>
  )
}

function SceneB({ userName }: { userName: string }) {
  const frame = useCurrentFrame()
  const { width, height } = useVideoConfig()

  const isNarrow = width < 640
  const heroSize = clamp(40, width * 0.078, 140)
  const nameSize = clamp(22, width * 0.032, 56)
  const subSize = clamp(11, width * 0.014, 22)
  const subTracking = isNarrow ? '0.15em' : '0.25em'
  const gap = clamp(10, width * 0.014, 20)
  const edgePad = clamp(20, width * 0.04, 80)

  const heroOpacity = interpolate(frame, [54, 68], [0, 1], { extrapolateRight: 'clamp' })
  const heroScale = interpolate(frame, [54, 68], [1.06, 1], { extrapolateRight: 'clamp' })
  const nameOpacity = interpolate(frame, [60, 74], [0, 1], { extrapolateRight: 'clamp' })
  const nameY = interpolate(frame, [60, 74], [14, 0], { extrapolateRight: 'clamp' })
  const subOpacity = interpolate(frame, [66, 80], [0, 1], { extrapolateRight: 'clamp' })

  const hasName = userName && userName.trim().length > 0

  const blobBig = clamp(260, Math.max(width, height) * 0.4, 620)
  const blobMid = clamp(180, Math.max(width, height) * 0.28, 420)

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background:
          'radial-gradient(circle at 50% 50%, #E65100 0%, #F57C00 55%, #FFB74D 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap,
        color: '#fff',
        fontFamily: FONT,
        direction: 'rtl',
        padding: `0 ${edgePad}px`,
        textAlign: 'center',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          width: blobBig,
          height: blobBig,
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.09)',
          top: -blobBig * 0.3,
          insetInlineStart: -blobBig * 0.25,
          filter: 'blur(1px)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: blobMid,
          height: blobMid,
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.06)',
          bottom: -blobMid * 0.3,
          insetInlineEnd: -blobMid * 0.2,
        }}
      />

      <div
        style={{
          position: 'relative',
          fontSize: heroSize,
          fontWeight: 900,
          letterSpacing: '-0.04em',
          lineHeight: 1,
          textShadow: '0 6px 30px rgba(120,40,0,0.25)',
          opacity: heroOpacity,
          transform: `scale(${heroScale})`,
          maxWidth: '100%',
        }}
      >
        ברוכים הבאים
      </div>

      {hasName ? (
        <div
          style={{
            position: 'relative',
            fontSize: nameSize,
            fontWeight: 700,
            letterSpacing: '-0.02em',
            opacity: nameOpacity * 0.95,
            transform: `translateY(${nameY}px)`,
            maxWidth: '100%',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {userName}
        </div>
      ) : null}

      <div
        style={{
          position: 'relative',
          marginTop: gap * 0.4,
          fontSize: subSize,
          fontWeight: 700,
          letterSpacing: subTracking,
          opacity: subOpacity * 0.95,
          textTransform: 'uppercase',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          maxWidth: '100%',
        }}
      >
        מערכת ניהול עמלות
      </div>
    </div>
  )
}

export function WelcomeComposition({ userName = '' }: WelcomeCompositionProps) {
  return (
    <GridPixelateWipe
      cols={12}
      rows={7}
      pattern="wave"
      transitionStart={22}
      transitionDuration={34}
      cellFadeFrames={5}
      cellColor={CREAM}
      from={<SceneA />}
      to={<SceneB userName={userName} />}
    />
  )
}
