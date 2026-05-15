import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion'
import { FONT, SOFT, tint } from './landingPalette'

// HeroMesh — drop-in replacement for the static hero photo.
// A "soft shader" feel achieved with 6 large blurred radial orbs that drift on
// independent sine cycles, layered grain, and a corner "pulsing badge" with
// rotating Hebrew text. Same brand-aligned cream/peach/amber palette as the
// Chapter 04 feature clips, so the hero flows visually into Chapter 02 below.
// 180 frames × 30 fps = 6s seamless loop.

type Orb = {
  color: string
  size: number       // relative to width (0..1)
  baseX: number      // base position (0..1)
  baseY: number      // base position (0..1)
  driftX: number     // px amplitude
  driftY: number     // px amplitude
  phase: number      // radians offset for variety
  alpha: number      // 0..1 opacity
}

const ORBS: Orb[] = [
  // Peach — big anchor, top-right
  { color: SOFT.feature01, size: 0.95, baseX: 0.78, baseY: 0.25, driftX: 60, driftY: 80, phase: 0,     alpha: 0.55 },
  // Amber — second anchor, middle-left
  { color: SOFT.feature05, size: 0.85, baseX: 0.18, baseY: 0.55, driftX: 80, driftY: 60, phase: 1.2,   alpha: 0.50 },
  // Sage — soft fill, bottom-center
  { color: SOFT.feature02, size: 0.7,  baseX: 0.55, baseY: 0.85, driftX: 70, driftY: 50, phase: 2.4,   alpha: 0.42 },
  // Mauve — accent, top-left
  { color: SOFT.feature04, size: 0.55, baseX: 0.22, baseY: 0.22, driftX: 50, driftY: 70, phase: 3.6,   alpha: 0.40 },
  // Slate — cool accent, middle-right
  { color: SOFT.feature03, size: 0.5,  baseX: 0.82, baseY: 0.65, driftX: 60, driftY: 50, phase: 4.5,   alpha: 0.34 },
  // Deep peach — small focal, lower-right
  { color: SOFT.feature01, size: 0.35, baseX: 0.68, baseY: 0.6,  driftX: 40, driftY: 40, phase: 5.6,   alpha: 0.45 },
]

export function HeroMesh() {
  const frame = useCurrentFrame()
  const { width, height, durationInFrames } = useVideoConfig()

  // Full-period sine so frame N === frame 0 for seamless loop
  const t = (frame / durationInFrames) * Math.PI * 2

  // Pulsing badge rotation — slow continuous
  const badgeRot = (frame / durationInFrames) * 360

  // Pulsing inner ring scale, sine-loop
  const pulse = 0.5 + 0.5 * Math.sin(t * 2) // 2x speed = 2 pulses per loop

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #FAF5EC 0%, #F2E7D6 100%)`,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {/* Mesh — 6 drifting blurred orbs */}
      {ORBS.map((orb, i) => {
        const orbSize = orb.size * width * 0.9
        const x = orb.baseX * width + Math.sin(t + orb.phase) * orb.driftX
        const y = orb.baseY * height + Math.cos(t + orb.phase * 1.3) * orb.driftY
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x - orbSize / 2,
              top: y - orbSize / 2,
              width: orbSize,
              height: orbSize,
              borderRadius: '50%',
              background: orb.color,
              opacity: orb.alpha,
              filter: 'blur(100px)',
              mixBlendMode: 'multiply',
            }}
          />
        )
      })}

      {/* Top wash — subtle vertical light bias for depth */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg, rgba(255,250,240,0.35) 0%, transparent 35%, transparent 70%, rgba(45,37,34,0.06) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Grain (very subtle, decorative) */}
      <svg style={{ position: 'absolute', inset: 0, opacity: 0.04, pointerEvents: 'none' }}>
        <filter id="hero-grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" />
        </filter>
        <rect width="100%" height="100%" filter="url(#hero-grain)" />
      </svg>

      {/* ─── Hero foreground overlay ─── */}
      {/* Eyebrow text */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          right: 80,
          color: SOFT.feature01,
          fontWeight: 700,
          fontSize: 16,
          letterSpacing: '0.22em',
          textTransform: 'uppercase',
          opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' }),
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: SOFT.feature01,
            boxShadow: `0 0 12px ${tint(SOFT.feature01, 0.6)}`,
          }}
        />
        Nifraim Agent
      </div>

      {/* Big mark — large outlined word/symbol in center, anchors the image */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            fontSize: Math.min(width * 0.5, 480),
            fontWeight: 900,
            color: 'transparent',
            WebkitTextStroke: `1.5px ${tint(SOFT.text, 0.18)}`,
            letterSpacing: '-0.04em',
            lineHeight: 1,
          }}
        >
          AI
        </div>
      </div>

      {/* ─── Pulsing badge in bottom-right corner ─── */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          left: 80,
          width: 200,
          height: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Outer rotating text ring (SVG textPath) */}
        <svg
          width="200"
          height="200"
          viewBox="0 0 200 200"
          style={{
            position: 'absolute',
            inset: 0,
            transform: `rotate(${badgeRot}deg)`,
          }}
        >
          <defs>
            <path id="badge-circle" d="M 100, 100 m -78, 0 a 78,78 0 1,1 156,0 a 78,78 0 1,1 -156,0" />
          </defs>
          <text
            fontSize="14"
            fontWeight="700"
            letterSpacing="6"
            fill={SOFT.text}
            style={{ opacity: 0.7 }}
          >
            <textPath href="#badge-circle" startOffset="0%">
              סוכן AI פעיל • סוכן AI פעיל • סוכן AI פעיל •
            </textPath>
          </text>
        </svg>

        {/* Pulsing concentric rings */}
        {[0, 1, 2].map((i) => {
          const ringPulse = 0.5 + 0.5 * Math.sin(t * 2 + i * 0.6)
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                width: 90 + i * 14,
                height: 90 + i * 14,
                borderRadius: '50%',
                border: `2px solid ${tint(SOFT.feature01, 0.5 - i * 0.12)}`,
                opacity: 0.6 - ringPulse * 0.3,
                transform: `scale(${1 + ringPulse * 0.06})`,
              }}
            />
          )
        })}

        {/* Inner solid badge */}
        <div
          style={{
            position: 'relative',
            width: 70,
            height: 70,
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${SOFT.feature01}, ${SOFT.feature05})`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 8px 24px ${tint(SOFT.feature01, 0.5)}`,
            transform: `scale(${1 + pulse * 0.04})`,
          }}
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
      </div>
    </AbsoluteFill>
  )
}
