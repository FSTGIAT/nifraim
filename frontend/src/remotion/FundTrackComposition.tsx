import { useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from 'remotion'
import type { VizFundTrack, VizFundTrackRow } from './types'

const FONT = 'Heebo, sans-serif'

const PERIOD_LABELS: { key: 'month' | 'y1' | 'y3' | 'y5'; he: string }[] = [
  { key: 'month', he: 'חודש' },
  { key: 'y1', he: 'שנה' },
  { key: 'y3', he: '3 שנים' },
  { key: 'y5', he: '5 שנים' },
]

const POS = '#1E9E5A'
const POS_DEEP = '#16713F'
const NEG = '#D63E36'
const NEG_DEEP = '#A12921'
const FLAT = '#94A3B8'
const GOLD = '#FBBF24'
const GOLD_DEEP = '#D97706'

type Period = 'month' | 'y1' | 'y3' | 'y5'

function colorFor(v: number | null | undefined): { main: string; deep: string } {
  if (v === null || v === undefined || !Number.isFinite(v)) return { main: FLAT, deep: FLAT }
  if (v > 0) return { main: POS, deep: POS_DEEP }
  if (v < 0) return { main: NEG, deep: NEG_DEEP }
  return { main: FLAT, deep: FLAT }
}

function fmtPct(v: number | null | undefined, progress = 1) {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—'
  const shown = v * progress
  const sign = shown > 0 ? '+' : ''
  return `${sign}${shown.toFixed(2)}%`
}

// Decorative floating particles — deterministic positions (frame-stable)
const PARTICLES = Array.from({ length: 18 }, (_, i) => ({
  x: (i * 53) % 100,
  y: (i * 71) % 100,
  size: 2 + (i % 4),
  delay: (i * 7) % 60,
  speed: 0.4 + ((i * 13) % 7) / 10,
}))

export function FundTrackComposition(props: VizFundTrack) {
  const frame = useCurrentFrame()
  const { fps, width, height } = useVideoConfig()

  const rawFunds = (props.funds ?? []) as VizFundTrackRow[]
  // Sort by 1Y descending (fallback month) so the hero highlight is meaningful.
  const funds = [...rawFunds]
    .map((f, i) => ({ ...f, _origIdx: i }))
    .sort((a, b) => {
      const av = a.y1 ?? a.month ?? -Infinity
      const bv = b.y1 ?? b.month ?? -Infinity
      return (bv as number) - (av as number)
    })
    .slice(0, 10)

  const averages = props.averages ?? { month: null, y1: null, y3: null, y5: null }

  // Build a single max-abs across all periods so bar widths are comparable.
  const allValues = [
    averages.month, averages.y1, averages.y3, averages.y5,
    ...funds.flatMap((f) => [f.month, f.y1, f.y3, f.y5]),
  ].filter((v): v is number => v !== null && v !== undefined && Number.isFinite(v))
  const maxAbs = Math.max(1, ...allValues.map((v) => Math.abs(v)))

  // Layout
  const pad = 36
  const titleY = 32
  const kpiY = 88
  const kpiH = 64
  const tableTop = kpiY + kpiH + 22
  const insightH = props.insight ? 56 : 0
  const tableHeight = height - tableTop - 24 - insightH
  const rowGap = 6
  const rowHeight = funds.length > 0
    ? Math.max(34, tableHeight / funds.length - rowGap)
    : 32
  const nameW = 230
  const cellGap = 8
  const cellsArea = width - pad * 2 - nameW - 16
  const cellW = (cellsArea - cellGap * 3) / 4

  // Title entrance — spring scale + slide
  const titleSpring = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.6, stiffness: 130 },
  })
  const periodChipProg = spring({
    frame: frame - 8,
    fps,
    config: { damping: 16, mass: 0.55, stiffness: 150 },
  })

  // Soft mesh-style background — two radial gradients
  return (
    <div
      style={{
        width,
        height,
        direction: 'rtl',
        fontFamily: FONT,
        background:
          'radial-gradient(1200px 600px at 100% 0%, rgba(245,124,0,0.22), transparent 60%),' +
          'radial-gradient(900px 500px at 0% 100%, rgba(99,102,241,0.16), transparent 55%),' +
          'linear-gradient(180deg, #FFFBF5 0%, #FFFFFF 80%)',
        color: '#181818',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Floating particles */}
      {PARTICLES.map((p, i) => {
        const phase = ((frame + p.delay) * p.speed) % 200
        const yOffset = (phase - 100) * 0.6
        const opacity = 0.35 - Math.abs(phase - 100) / 280
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
              borderRadius: '50%',
              background: i % 3 === 0 ? GOLD : '#F57C00',
              opacity: Math.max(0, opacity),
              transform: `translateY(${yOffset}px)`,
              filter: 'blur(0.5px)',
              pointerEvents: 'none',
            }}
          />
        )
      })}

      {/* Title + period chip */}
      <div
        style={{
          position: 'absolute',
          insetInlineStart: pad,
          insetInlineEnd: pad,
          top: titleY,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          opacity: titleSpring,
          transform: `translateY(${(1 - titleSpring) * -12}px)`,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #F57C00, #FF9800)',
              boxShadow: '0 10px 24px rgba(245,124,0,0.4)',
              display: 'grid',
              placeItems: 'center',
              color: '#fff',
              fontSize: 18,
              fontWeight: 800,
              flexShrink: 0,
            }}
          >
            ₪
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <div
              style={{
                fontSize: 26,
                fontWeight: 800,
                color: '#1A1A1A',
                lineHeight: 1.1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                letterSpacing: '-0.01em',
              }}
            >
              {props.title}
            </div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#7A7672', marginTop: 4 }}>
              ביצועי קופה — נתוני שוק
            </div>
          </div>
        </div>
        {props.period_label ? (
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: '#fff',
              background: 'linear-gradient(135deg, #F57C00, #FF9800)',
              padding: '6px 14px',
              borderRadius: 999,
              boxShadow: '0 4px 14px rgba(245,124,0,0.3)',
              opacity: periodChipProg,
              transform: `scale(${0.85 + periodChipProg * 0.15})`,
              flexShrink: 0,
            }}
          >
            תקופה · {props.period_label}
          </div>
        ) : null}
      </div>

      {/* Averages — 4 hero KPI pills */}
      <div
        style={{
          position: 'absolute',
          insetInlineStart: pad,
          insetInlineEnd: pad,
          top: kpiY,
          display: 'flex',
          gap: 10,
        }}
      >
        {PERIOD_LABELS.map((p, i) => {
          const v = averages[p.key]
          const start = 10 + i * 4
          const prog = spring({
            frame: frame - start,
            fps,
            config: { damping: 18, mass: 0.65, stiffness: 160 },
          })
          const valueProgress = interpolate(
            frame,
            [start + 4, start + 32],
            [0, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
              easing: Easing.out(Easing.cubic),
            },
          )
          const c = colorFor(v)
          return (
            <div
              key={p.key}
              style={{
                flex: 1,
                height: kpiH,
                borderRadius: 14,
                background: 'rgba(255,255,255,0.95)',
                border: '1px solid rgba(0,0,0,0.05)',
                boxShadow: `0 8px 24px rgba(17,12,6,0.06), inset 0 1px 0 rgba(255,255,255,0.8)`,
                padding: '10px 14px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                gap: 3,
                opacity: prog,
                transform: `translateY(${(1 - prog) * 14}px) scale(${0.92 + prog * 0.08})`,
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {/* color accent strip */}
              <div
                style={{
                  position: 'absolute',
                  insetInlineStart: 0,
                  top: 0,
                  bottom: 0,
                  width: 4,
                  background: `linear-gradient(180deg, ${c.main}, ${c.deep})`,
                }}
              />
              <div style={{ fontSize: 11, fontWeight: 700, color: '#7A7672', letterSpacing: '0.02em' }}>
                ממוצע · {p.he}
              </div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  color: c.main,
                  direction: 'ltr',
                  textAlign: 'start',
                  fontVariantNumeric: 'tabular-nums',
                  letterSpacing: '-0.01em',
                }}
              >
                {fmtPct(v, valueProgress)}
              </div>
            </div>
          )
        })}
      </div>

      {/* Funds — staggered animated rows with hero highlight on #1 */}
      {funds.length === 0 ? (
        <div
          style={{
            position: 'absolute',
            insetInlineStart: pad,
            insetInlineEnd: pad,
            top: tableTop + 40,
            fontSize: 14,
            color: '#7A7672',
            textAlign: 'center',
          }}
        >
          אין נתוני קרנות
        </div>
      ) : (
        funds.map((f, i) => {
          const isHero = i === 0
          const rowStart = 22 + i * 5
          const introProgress = spring({
            frame: frame - rowStart,
            fps,
            config: { damping: 18, mass: 0.7, stiffness: 140 },
          })
          const valueProgress = interpolate(
            frame,
            [rowStart + 4, rowStart + 30],
            [0, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
              easing: Easing.out(Easing.cubic),
            },
          )
          const y = tableTop + i * (rowHeight + rowGap)
          const heroPulse = isHero ? 0.94 + 0.06 * Math.sin((frame - rowStart) * 0.18) : 1

          return (
            <div
              key={`${f.name}-${i}`}
              style={{
                position: 'absolute',
                top: y,
                insetInlineStart: pad,
                width: width - pad * 2,
                height: rowHeight,
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                padding: isHero ? '6px 10px 6px 10px' : 0,
                background: isHero
                  ? `linear-gradient(90deg, rgba(251,191,36,0.15) 0%, rgba(245,124,0,0.06) 60%, transparent 100%)`
                  : 'transparent',
                borderRadius: isHero ? 12 : 0,
                border: isHero ? `1px solid rgba(251,191,36,0.35)` : '1px solid transparent',
                boxShadow: isHero
                  ? `0 6px 18px rgba(245,124,0,${0.18 * heroPulse})`
                  : 'none',
                opacity: introProgress,
                transform: `translateX(${(1 - introProgress) * -24}px)`,
              }}
            >
              {/* rank pill */}
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 8,
                  background: isHero
                    ? `linear-gradient(135deg, ${GOLD}, ${GOLD_DEEP})`
                    : 'rgba(0,0,0,0.05)',
                  color: isHero ? '#fff' : '#7A7672',
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: 12,
                  fontWeight: 800,
                  flexShrink: 0,
                  boxShadow: isHero ? `0 4px 10px rgba(217,119,6,0.4)` : 'none',
                }}
              >
                {isHero ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2l2.39 7.36H22l-6.18 4.49L18.21 21 12 16.51 5.79 21l2.39-7.15L2 9.36h7.61z" />
                  </svg>
                ) : i + 1}
              </div>
              <div
                style={{
                  width: nameW - 36,
                  fontSize: isHero ? 14 : 13,
                  fontWeight: isHero ? 800 : 700,
                  color: isHero ? '#7A4E0C' : '#3E3E3C',
                  overflow: 'hidden',
                  whiteSpace: 'nowrap',
                  textOverflow: 'ellipsis',
                }}
                title={f.name}
              >
                {f.name}
              </div>
              <div style={{ flex: 1, display: 'flex', gap: cellGap }}>
                {PERIOD_LABELS.map((p) => {
                  const v = f[p.key as Period]
                  const c = colorFor(v)
                  const hasVal = v !== null && v !== undefined && Number.isFinite(v as number)
                  const widthPct = hasVal ? (Math.abs(v as number) / maxAbs) : 0
                  return (
                    <div
                      key={p.key}
                      style={{
                        width: cellW,
                        height: rowHeight - 8,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        gap: 3,
                      }}
                    >
                      <div
                        style={{
                          height: 8,
                          background: 'rgba(0,0,0,0.05)',
                          borderRadius: 4,
                          overflow: 'hidden',
                          position: 'relative',
                          direction: 'ltr',
                        }}
                      >
                        <div
                          style={{
                            position: 'absolute',
                            insetInlineStart: 0,
                            top: 0,
                            bottom: 0,
                            width: `${widthPct * 100 * introProgress}%`,
                            background: `linear-gradient(90deg, ${c.main}, ${c.deep})`,
                            borderRadius: 4,
                            boxShadow: isHero && hasVal ? `0 0 10px ${c.main}66` : 'none',
                          }}
                        />
                      </div>
                      <div
                        style={{
                          fontSize: isHero ? 13 : 12,
                          fontWeight: 800,
                          color: c.main,
                          direction: 'ltr',
                          textAlign: 'start',
                          fontVariantNumeric: 'tabular-nums',
                          letterSpacing: '-0.01em',
                        }}
                      >
                        {fmtPct(v, valueProgress)}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })
      )}

      {/* Insight chip — final wow moment */}
      {props.insight ? (
        <div
          style={{
            position: 'absolute',
            insetInline: pad,
            bottom: 18,
            padding: '14px 18px',
            borderRadius: 14,
            background: 'linear-gradient(135deg, rgba(245,124,0,0.10), rgba(251,191,36,0.10))',
            border: '1px solid rgba(245,124,0,0.18)',
            color: '#7A4E0C',
            fontSize: 14,
            fontWeight: 700,
            opacity: interpolate(frame, [70, 88], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
            transform: `translateY(${interpolate(frame, [70, 88], [12, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })}px)`,
            boxShadow: '0 8px 22px rgba(245,124,0,0.12)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <span
            style={{
              width: 24,
              height: 24,
              borderRadius: 6,
              background: 'linear-gradient(135deg, #F57C00, #FF9800)',
              color: '#fff',
              display: 'grid',
              placeItems: 'center',
              flexShrink: 0,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </span>
          {props.insight}
        </div>
      ) : null}
    </div>
  )
}
