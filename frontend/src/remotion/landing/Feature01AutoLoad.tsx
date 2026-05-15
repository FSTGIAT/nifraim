import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion'
import { FONT, SOFT, tint } from './landingPalette'

// Feature 01 — Auto file loading.
// Visual: 3 doc-icons drift in from the right edge into a soft "tray",
// each gets a soft check mark, then the loop wraps. No cursor, no hand.
// 90 frames @ 30fps = 3s seamless loop.

const DOC_COUNT = 3
const ACCENT = SOFT.feature01

export function Feature01AutoLoad() {
  const frame = useCurrentFrame()
  const { width, height, durationInFrames } = useVideoConfig()

  // Sine-based ambient drift so the tray + docs gently breathe with a full period
  // matching the composition length (frame 0 ≈ frame N for seamless wrap).
  const breathe = Math.sin((frame / durationInFrames) * Math.PI * 2) * 4

  // Tray sits center; docs enter from the right edge and settle in tray.
  const trayW = Math.min(width * 0.7, 920)
  const trayH = Math.min(height * 0.5, 380)
  const trayLeft = (width - trayW) / 2
  const trayTop = (height - trayH) / 2

  const docW = (trayW - 80) / DOC_COUNT - 16

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 30% 30%, ${SOFT.bgTop} 0%, ${SOFT.bgBottom} 100%)`,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {/* Soft accent orb */}
      <div
        style={{
          position: 'absolute',
          width: width * 0.5,
          height: width * 0.5,
          borderRadius: '50%',
          background: tint(ACCENT, 0.12),
          top: -width * 0.18,
          left: width * 0.35,
          filter: 'blur(80px)',
        }}
      />

      {/* Tray label */}
      <div
        style={{
          position: 'absolute',
          top: trayTop - 56,
          right: trayLeft,
          width: trayW,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
        }}
      >
        <div
          style={{
            fontSize: 28,
            fontWeight: 800,
            color: SOFT.text,
            letterSpacing: '-0.02em',
          }}
        >
          טעינה אוטומטית
        </div>
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: '0.15em',
            color: ACCENT,
            background: tint(ACCENT, 0.12),
            padding: '4px 14px',
            borderRadius: 99,
          }}
        >
          AGENT • LIVE
        </div>
      </div>

      {/* Tray */}
      <div
        style={{
          position: 'absolute',
          top: trayTop,
          left: trayLeft,
          width: trayW,
          height: trayH,
          background: SOFT.card,
          borderRadius: 28,
          boxShadow: SOFT.shadowMed,
          padding: 40,
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          transform: `translateY(${breathe}px)`,
        }}
      >
        {Array.from({ length: DOC_COUNT }).map((_, i) => {
          // Each doc has its own entrance window so they cascade in.
          const start = 8 + i * 12
          const settled = start + 22
          const checkAt = settled + 6
          const xOff = interpolate(frame, [start, settled], [width * 0.55, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          })
          const opacity = interpolate(frame, [start, start + 10], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          })
          const checkScale = interpolate(frame, [checkAt, checkAt + 10], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          })

          return (
            <div
              key={i}
              style={{
                flex: 1,
                height: '100%',
                background: SOFT.cardSoft,
                border: `1px solid ${SOFT.divider}`,
                borderRadius: 16,
                padding: 18,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                opacity,
                transform: `translateX(${xOff}px)`,
                position: 'relative',
                maxWidth: docW,
              }}
            >
              {/* Doc header stripe */}
              <div
                style={{
                  height: 8,
                  width: '60%',
                  background: tint(ACCENT, 0.4),
                  borderRadius: 4,
                }}
              />
              {/* Doc body lines */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ height: 5, width: '90%', background: SOFT.divider, borderRadius: 3 }} />
                <div style={{ height: 5, width: '75%', background: SOFT.divider, borderRadius: 3 }} />
                <div style={{ height: 5, width: '82%', background: SOFT.divider, borderRadius: 3 }} />
                <div style={{ height: 5, width: '60%', background: SOFT.divider, borderRadius: 3 }} />
              </div>
              {/* Check badge */}
              <div
                style={{
                  position: 'absolute',
                  bottom: -14,
                  right: 14,
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: ACCENT,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transform: `scale(${checkScale})`,
                  boxShadow: SOFT.shadowSoft,
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
            </div>
          )
        })}
      </div>

      {/* Footer caption */}
      <div
        style={{
          position: 'absolute',
          bottom: 56,
          left: 0,
          right: 0,
          textAlign: 'center',
          fontSize: 16,
          fontWeight: 600,
          color: SOFT.textMuted,
          letterSpacing: '0.02em',
        }}
      >
        ללא העלאות. ללא גרירה.
      </div>
    </AbsoluteFill>
  )
}
