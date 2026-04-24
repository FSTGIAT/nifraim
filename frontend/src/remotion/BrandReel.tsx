import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion'

// 3-beat brand reel, 12s @ 30fps = 360 frames.
//   Beat 1 (0–120):   Luma A — four people buried in numbered paperwork
//   Beat 2 (120–240): Luma B — numbers lift off papers into orange particles
//   Beat 3 (240–360): DashboardReveal — Nifraim dashboard materializes + classical text
//
// Luma's Ray-2 only allows 5s or 9s clips, so we generate 5s mp4s and the <Sequence>
// durationInFrames prop trims playback to 4s (120 frames) — no re-encoding required.

const CROSSFADE_FRAMES = 10 // Beat 2 → Beat 3 opacity fade-in

// Keep identifiers identical to HeroProduct.tsx:28-33 so both compositions show the same
// bar data at render time. Duplicated deliberately per plan — don't refactor into a shared
// module (would risk the existing hero-product render pipeline).
const DASHBOARD_ROWS = [
  { label: 'אקסלנס', value: 0.92, color: '#E65100' },
  { label: 'הפניקס', value: 0.78, color: '#F57C00' },
  { label: 'מגדל', value: 0.65, color: '#FF9800' },
  { label: 'כלל', value: 0.54, color: '#FFB74D' },
]

const HEBREW_HERO_FONT = "'David Libre', 'Heebo', serif"
const LATIN_SERIF_FONT = "'Cormorant Garamond', 'Times New Roman', serif"

export function BrandReel() {
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Sequence from={0} durationInFrames={120}>
        <OffthreadVideo src={staticFile('landing/brand-reel/clip-a.mp4')} />
      </Sequence>

      <Sequence from={120} durationInFrames={120}>
        <OffthreadVideo src={staticFile('landing/brand-reel/clip-b.mp4')} />
      </Sequence>

      {/* Beat 3 starts 10 frames early so its cream vignette cross-fades over Luma B's tail */}
      <Sequence from={240 - CROSSFADE_FRAMES} durationInFrames={120 + CROSSFADE_FRAMES}>
        <DashboardReveal crossfadeFrames={CROSSFADE_FRAMES} />
      </Sequence>
    </AbsoluteFill>
  )
}

function DashboardReveal({ crossfadeFrames }: { crossfadeFrames: number }) {
  const frame = useCurrentFrame() // 0..(119 + crossfadeFrames)
  const { fps, width, height } = useVideoConfig()
  // Shift local frame so Beat-3 animation timings (bar rows, counter, text) start at 0
  // while the crossfade vignette uses the raw Sequence frame.
  const localFrame = Math.max(0, frame - crossfadeFrames)

  const vignetteOpacity = interpolate(frame, [0, crossfadeFrames + 10], [0, 1], {
    extrapolateRight: 'clamp',
  })

  const cardEntry = spring({
    frame: localFrame,
    fps,
    config: { damping: 22, mass: 0.9, stiffness: 140 },
  })
  const cardY = (1 - cardEntry) * 40
  const cardOpacity = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateRight: 'clamp',
  })

  const totalProgress = interpolate(localFrame, [30, 60], [0, 54300], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })
  const totalDisplay = Math.round(totalProgress).toLocaleString('he-IL')

  const textOpacity = interpolate(localFrame, [60, 100], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  // Dashboard card sits in upper ~60%, text block in lower ~35% with 5% breathing room
  const cardW = Math.min(width * 0.58, 960)
  const cardH = Math.min(height * 0.52, 560)

  return (
    <AbsoluteFill
      style={{
        background:
          'radial-gradient(circle at 50% 35%, #FFF8F0 0%, #FFE8D0 60%, #FFB88A 100%)',
        opacity: vignetteOpacity,
        direction: 'rtl',
        fontFamily: "'Heebo', -apple-system, sans-serif",
      }}
    >
      {/* Soft brand orbs */}
      <div
        style={{
          position: 'absolute',
          width: width * 0.35,
          height: width * 0.35,
          borderRadius: '50%',
          background: 'rgba(245, 124, 0, 0.16)',
          top: -width * 0.08,
          left: -width * 0.05,
          filter: 'blur(80px)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: width * 0.28,
          height: width * 0.28,
          borderRadius: '50%',
          background: 'rgba(255, 183, 77, 0.2)',
          bottom: -width * 0.06,
          right: -width * 0.04,
          filter: 'blur(80px)',
        }}
      />

      {/* Dashboard card — upper 60% */}
      <div
        style={{
          position: 'absolute',
          top: height * 0.08,
          left: (width - cardW) / 2,
          width: cardW,
          height: cardH,
          background: '#fff',
          borderRadius: 24,
          boxShadow: '0 40px 80px rgba(45, 37, 34, 0.14)',
          padding: 40,
          opacity: cardOpacity,
          transform: `translateY(${cardY}px)`,
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
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
              fontSize: 26,
              fontWeight: 800,
              color: '#2D2522',
              letterSpacing: '-0.02em',
            }}
          >
            עמלות לפי חברה
          </div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: '0.15em',
              color: '#F57C00',
              textTransform: 'uppercase',
              background: 'rgba(245,124,0,0.1)',
              padding: '5px 12px',
              borderRadius: 99,
            }}
          >
            Live
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, flex: 1 }}>
          {DASHBOARD_ROWS.map((r, i) => {
            const start = 12 + i * 6
            const progress = interpolate(localFrame, [start, start + 18], [0, 1], {
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
                  gap: 16,
                  opacity: interpolate(localFrame, [start, start + 8], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  }),
                }}
              >
                <div
                  style={{
                    width: 130,
                    fontSize: 18,
                    fontWeight: 700,
                    color: '#2D2522',
                  }}
                >
                  {r.label}
                </div>
                <div
                  style={{
                    flex: 1,
                    height: 22,
                    background: 'rgba(45,37,34,0.05)',
                    borderRadius: 8,
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
                      borderRadius: 8,
                      direction: 'ltr',
                    }}
                  />
                </div>
                <div
                  style={{
                    width: 84,
                    textAlign: 'start',
                    fontSize: 18,
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

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginTop: 'auto',
            paddingTop: 20,
            borderTop: '1px solid rgba(45,37,34,0.06)',
          }}
        >
          <div style={{ fontSize: 16, color: '#6B6260', fontWeight: 500 }}>סה"כ נמצא</div>
          <div
            style={{
              fontSize: 34,
              fontWeight: 900,
              color: '#E65100',
              letterSpacing: '-0.02em',
              direction: 'ltr',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            ₪{totalDisplay}
          </div>
        </div>
      </div>

      {/* Classical text overlay — lower 35% */}
      <div
        style={{
          position: 'absolute',
          top: height * 0.68,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 18,
          opacity: textOpacity,
        }}
      >
        <div
          style={{
            fontFamily: LATIN_SERIF_FONT,
            fontStyle: 'italic',
            fontWeight: 500,
            fontSize: 20,
            letterSpacing: '0.28em',
            textTransform: 'uppercase',
            color: '#6B6260',
            direction: 'ltr',
          }}
        >
          AI On-Prem
        </div>
        <div
          style={{
            fontFamily: HEBREW_HERO_FONT,
            fontWeight: 700,
            fontSize: 72,
            lineHeight: 1,
            color: '#2D2522',
            letterSpacing: '-0.01em',
          }}
        >
          ניתוח עמלות מבוסס AI
        </div>
        <div style={{ width: 96, height: 1, background: '#E65100', margin: '4px 0' }} />
        <div
          style={{
            fontFamily: LATIN_SERIF_FONT,
            fontWeight: 500,
            fontSize: 18,
            letterSpacing: '0.32em',
            color: '#2D2522',
            direction: 'ltr',
          }}
        >
          NIFRAIM.COM
        </div>
      </div>
    </AbsoluteFill>
  )
}
