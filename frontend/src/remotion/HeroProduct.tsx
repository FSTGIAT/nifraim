import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion'

const FONT = "'Heebo', -apple-system, sans-serif"

// Seamless 4s loop at 30fps. The final frame must equal frame 0 for a clean wrap-around —
// pills are animated with full-period sine curves (duration = durationInFrames / fps × 2π).
export function HeroProduct() {
  const frame = useCurrentFrame()
  const { fps, width, height, durationInFrames } = useVideoConfig()

  // Full-period sine so pill Y at frame=durationInFrames-1 ≈ Y at frame=0.
  const period = durationInFrames
  const pillA = Math.sin((frame / period) * Math.PI * 2) * 8
  const pillB = Math.sin((frame / period) * Math.PI * 2 + Math.PI) * 8

  // Dashboard card entrance (0–18 frames)
  const cardEntry = spring({
    frame,
    fps,
    config: { damping: 20, mass: 0.8, stiffness: 160 },
  })
  const cardY = (1 - cardEntry) * 40
  const cardOpacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateRight: 'clamp',
  })

  // Bar chart rows (staggered, each row draws in for 18 frames starting at frame 12 + i*6)
  const rows = [
    { label: 'אקסלנס', value: 0.92, color: '#E65100' },
    { label: 'הפניקס', value: 0.78, color: '#F57C00' },
    { label: 'מגדל', value: 0.65, color: '#FF9800' },
    { label: 'כלל', value: 0.54, color: '#FFB74D' },
  ]

  const cardW = Math.min(width * 0.76, 720)
  const cardH = Math.min(height * 0.52, 540)

  return (
    <div
      style={{
        width,
        height,
        background:
          'radial-gradient(circle at 30% 20%, #FFF8F0 0%, #FFE8D0 70%, #FFB88A 100%)',
        fontFamily: FONT,
        direction: 'rtl',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Soft brand orbs (static — no keyframes on video) */}
      <div
        style={{
          position: 'absolute',
          width: width * 0.5,
          height: width * 0.5,
          borderRadius: '50%',
          background: 'rgba(245, 124, 0, 0.18)',
          top: -width * 0.15,
          left: -width * 0.1,
          filter: 'blur(60px)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: width * 0.35,
          height: width * 0.35,
          borderRadius: '50%',
          background: 'rgba(255, 183, 77, 0.22)',
          bottom: -width * 0.1,
          right: -width * 0.08,
          filter: 'blur(60px)',
        }}
      />

      {/* Dashboard card */}
      <div
        style={{
          position: 'absolute',
          top: (height - cardH) / 2,
          left: (width - cardW) / 2,
          width: cardW,
          height: cardH,
          background: '#fff',
          borderRadius: 24,
          boxShadow: '0 40px 80px rgba(45, 37, 34, 0.14)',
          padding: 36,
          opacity: cardOpacity,
          transform: `translateY(${cardY}px)`,
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: '#2D2522',
              letterSpacing: '-0.02em',
            }}
          >
            עמלות לפי חברה
          </div>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: '0.15em',
              color: '#F57C00',
              textTransform: 'uppercase',
              background: 'rgba(245,124,0,0.1)',
              padding: '4px 10px',
              borderRadius: 99,
            }}
          >
            Live
          </div>
        </div>

        {/* Bar rows */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, flex: 1 }}>
          {rows.map((r, i) => {
            const start = 12 + i * 6
            const progress = interpolate(frame, [start, start + 18], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
            const displayed = r.value * progress
            return (
              <div
                key={r.label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  opacity: interpolate(frame, [start, start + 8], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  }),
                }}
              >
                <div
                  style={{
                    width: 110,
                    fontSize: 15,
                    fontWeight: 700,
                    color: '#2D2522',
                  }}
                >
                  {r.label}
                </div>
                <div
                  style={{
                    flex: 1,
                    height: 18,
                    background: 'rgba(45,37,34,0.05)',
                    borderRadius: 6,
                    overflow: 'hidden',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      insetInlineStart: 0,
                      top: 0,
                      bottom: 0,
                      width: `${displayed * 100}%`,
                      background: `linear-gradient(90deg, ${r.color}, ${r.color}dd)`,
                      borderRadius: 6,
                      direction: 'ltr',
                    }}
                  />
                </div>
                <div
                  style={{
                    width: 72,
                    textAlign: 'start',
                    fontSize: 15,
                    fontWeight: 800,
                    color: r.color,
                    fontVariantNumeric: 'tabular-nums',
                    direction: 'ltr',
                  }}
                >
                  {Math.round(displayed * 100)}%
                </div>
              </div>
            )
          })}
        </div>

        {/* Footer stat */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginTop: 'auto',
            paddingTop: 18,
            borderTop: '1px solid rgba(45,37,34,0.06)',
          }}
        >
          <div style={{ fontSize: 14, color: '#6B6260', fontWeight: 500 }}>סה"כ נמצא</div>
          <div
            style={{
              fontSize: 28,
              fontWeight: 900,
              color: '#E65100',
              letterSpacing: '-0.02em',
              direction: 'ltr',
            }}
          >
            ₪54,300
          </div>
        </div>
      </div>

      {/* Floating KPI pill A — upper right */}
      <div
        style={{
          position: 'absolute',
          top: height * 0.14,
          right: width * 0.08,
          background: '#fff',
          borderRadius: 18,
          padding: '14px 20px',
          boxShadow: '0 20px 40px rgba(45,37,34,0.12)',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          transform: `translateY(${pillA}px)`,
          opacity: interpolate(frame, [8, 22], [0, 1], { extrapolateLeft: 'clamp' }),
        }}
      >
        <div style={{ fontSize: 11, color: '#6B6260', fontWeight: 600, letterSpacing: '0.05em' }}>
          חיסכון בזמן
        </div>
        <div
          style={{
            fontSize: 30,
            fontWeight: 900,
            color: '#E65100',
            letterSpacing: '-0.02em',
            direction: 'ltr',
          }}
        >
          95%
        </div>
      </div>

      {/* Floating KPI pill B — lower left */}
      <div
        style={{
          position: 'absolute',
          bottom: height * 0.14,
          left: width * 0.08,
          background: '#fff',
          borderRadius: 18,
          padding: '14px 20px',
          boxShadow: '0 20px 40px rgba(45,37,34,0.12)',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          transform: `translateY(${pillB}px)`,
          opacity: interpolate(frame, [14, 28], [0, 1], { extrapolateLeft: 'clamp' }),
        }}
      >
        <div style={{ fontSize: 11, color: '#6B6260', fontWeight: 600, letterSpacing: '0.05em' }}>
          זמן עיבוד
        </div>
        <div
          style={{
            fontSize: 30,
            fontWeight: 900,
            color: '#2D2522',
            letterSpacing: '-0.02em',
            direction: 'ltr',
          }}
        >
          3.2s
        </div>
      </div>
    </div>
  )
}
