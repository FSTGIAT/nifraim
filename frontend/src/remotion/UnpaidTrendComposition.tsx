import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion'

const FONT = 'Heebo, sans-serif'

// Nifraim orange palette — top company gets the darkest, deepest orange.
const PALETTE = ['#E65100', '#F57C00', '#FB8C00', '#FFA726', '#FFB74D']

export interface UnpaidTrendSeries {
  company: string
  data: number[]
}

export interface UnpaidTrendProps {
  title?: string
  periods: string[]
  series: UnpaidTrendSeries[]
  insight?: string
}

function formatPct(v: number): string {
  const sign = v > 0 ? '+' : ''
  return `${sign}${Math.round(v)}%`
}

export function UnpaidTrendComposition(props: UnpaidTrendProps) {
  const frame = useCurrentFrame()
  const { fps, width, height } = useVideoConfig()

  const periods = props.periods ?? []
  const latestPeriod = periods[periods.length - 1] ?? ''
  const earliestPeriod = periods[0] ?? ''

  // Build bar rows from series — latest count is the bar value, history feeds
  // the inline sparkline. Sort by latest count desc so the top company sits
  // first / largest.
  const rawSeries = (props.series ?? []).filter(
    (s) => Array.isArray(s.data) && s.data.length > 0,
  )
  const rows = rawSeries
    .map((s) => {
      const data = s.data
      const last = Number(data[data.length - 1] || 0)
      const prev = data.length > 1 ? Number(data[data.length - 2] || 0) : null
      const delta = prev != null && prev > 0 ? ((last - prev) / prev) * 100 : null
      return {
        company: s.company,
        last,
        prev,
        delta,
        history: data.slice(-6), // last 6 periods for sparkline
      }
    })
    .filter((r) => r.last >= 0)
    .sort((a, b) => b.last - a.last)
    .slice(0, 5)

  const hasData = rows.length > 0

  // Layout — sized to fit comfortably inside the monitor's chart card with
  // safe inner padding so corner decorations never overlap content.
  const padInline = 32
  const headerH = 80
  const footerH = 52
  const rowsArea = height - headerH - footerH
  const rowGap = 10
  const rowH = rows.length
    ? Math.min(48, (rowsArea - rowGap * (rows.length - 1)) / rows.length)
    : 0
  const labelW = 120
  const numW = 92
  const sparkW = periods.length > 1 ? 90 : 0
  const sparkGap = sparkW > 0 ? 10 : 0
  // Inner gap budget: padInline×2 outer + 14×N gaps between elements
  const innerGaps = 14 * (sparkW > 0 ? 3 : 2)
  const trackW = Math.max(
    60,
    width - padInline * 2 - labelW - numW - sparkW - sparkGap - innerGaps,
  )

  const maxLast = Math.max(1, ...rows.map((r) => r.last))

  // Header entrance
  const titleOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' })
  const titleY = interpolate(frame, [0, 16], [-8, 0], { extrapolateRight: 'clamp' })

  // Period range chip pulse
  const dotR = 4 + 3 * Math.sin(frame * 0.18)

  return (
    <div
      style={{
        width,
        height,
        direction: 'rtl',
        fontFamily: FONT,
        background:
          'linear-gradient(135deg, #FFFFFF 0%, #FFF7EC 55%, #FFEFD7 100%)',
        color: '#181818',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative orbs — pushed well off-canvas. zIndex:0 made these float
          above bar rows with auto z-index, hiding the company labels.
          Solution: keep orbs subtle in the background AND give content rows
          explicit z-index above them. */}
      <div
        style={{
          position: 'absolute',
          width: 200,
          height: 200,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(245,124,0,0.08), transparent 70%)',
          top: -160,
          insetInlineStart: -160,
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 160,
          height: 160,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(230,81,0,0.05), transparent 70%)',
          bottom: -140,
          insetInlineEnd: -140,
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      {/* Eyebrow + Title */}
      <div
        style={{
          position: 'absolute',
          insetInlineStart: padInline,
          top: 18 + titleY,
          opacity: titleOpacity,
          maxWidth: width - padInline * 2 - 180,
          zIndex: 1,
        }}
      >
        <div
          style={{
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: 1.2,
            color: '#E65100',
            textTransform: 'uppercase',
            marginBottom: 4,
          }}
        >
          לא-שולם · לפי חברה
        </div>
        <div
          style={{
            fontSize: 18,
            fontWeight: 800,
            color: '#181818',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {props.title || 'דירוג חברות לפי לקוחות שלא שולמו'}
        </div>
      </div>

      {/* Period chip — pulsing dot + range */}
      <div
        style={{
          position: 'absolute',
          top: 26,
          insetInlineEnd: padInline,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '5px 10px',
          background: 'rgba(245,124,0,0.10)',
          border: '1px solid rgba(245,124,0,0.22)',
          borderRadius: 999,
          fontSize: 10,
          fontWeight: 700,
          color: '#E65100',
          opacity: titleOpacity,
          zIndex: 1,
          whiteSpace: 'nowrap',
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#F57C00',
            boxShadow: `0 0 0 ${dotR.toFixed(1)}px rgba(245,124,0,0.18)`,
          }}
        />
        {earliestPeriod === latestPeriod
          ? latestPeriod
          : `${earliestPeriod} → ${latestPeriod}`}
      </div>

      {/* Empty state */}
      {!hasData && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#A8A29A',
            fontSize: 14,
          }}
        >
          טרם הצטברו נתוני לא-שולם
        </div>
      )}

      {/* Bars */}
      {hasData &&
        rows.map((r, i) => {
          const color = PALETTE[i % PALETTE.length]
          const isTop = i === 0
          const startFrame = 14 + i * 6

          // Bar grow + entrance — spring for a satisfying "land"
          const intro = spring({
            frame: frame - startFrame,
            fps,
            config: { damping: 18, mass: 0.75, stiffness: 140 },
          })
          const valueProgress = interpolate(
            frame,
            [startFrame + 4, startFrame + 30],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          )
          const widthPct = (r.last / maxLast) * 100
          const fillW = Math.max(6, (trackW * widthPct) / 100) * intro
          const shownNum = Math.round(r.last * valueProgress)

          // Top bar pulses — subtle, only after settle
          const pulse = isTop ? 0.92 + 0.08 * Math.sin((frame - startFrame) * 0.16) : 1

          const y = headerH + i * (rowH + rowGap)

          // Sparkline
          const sparkPath = (() => {
            if (!sparkW || r.history.length < 2) return null
            const sw = sparkW
            const sh = rowH - 18
            const sx = (idx: number) =>
              (idx / (r.history.length - 1)) * sw
            const max = Math.max(1, ...r.history)
            const min = Math.min(0, ...r.history)
            const sy = (v: number) =>
              sh - ((v - min) / Math.max(1, max - min)) * sh
            return r.history.map((v, idx) => `${idx === 0 ? 'M' : 'L'} ${sx(idx).toFixed(2)} ${sy(v).toFixed(2)}`).join(' ')
          })()

          return (
            <div
              key={r.company}
              style={{
                position: 'absolute',
                top: y,
                insetInlineStart: padInline,
                width: width - padInline * 2,
                height: rowH,
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                opacity: intro,
                transform: `translateX(${(1 - intro) * -28}px)`,
                zIndex: 2,
              }}
            >
              {/* Company label + delta */}
              <div
                style={{
                  width: labelW,
                  flexShrink: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 2,
                  textAlign: 'start',
                }}
              >
                <div
                  style={{
                    fontSize: isTop ? 16 : 14,
                    fontWeight: 800,
                    color: isTop ? color : '#181818',
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    lineHeight: 1.2,
                  }}
                  title={r.company || '—'}
                >
                  {r.company || '—'}
                </div>
                {r.delta != null ? (
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: r.delta > 0 ? '#C23934' : r.delta < 0 ? '#2E844A' : '#706E6B',
                      direction: 'ltr',
                      textAlign: 'start',
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    {formatPct(r.delta)} מהחודש הקודם
                  </div>
                ) : (
                  <div style={{ fontSize: 10, color: '#A8A29A', fontWeight: 600 }}>
                    תקופה ראשונה
                  </div>
                )}
              </div>

              {/* Bar track */}
              <div
                style={{
                  flex: 1,
                  height: rowH - 18,
                  background: 'rgba(245,124,0,0.06)',
                  borderRadius: 10,
                  position: 'relative',
                  overflow: 'hidden',
                  direction: 'ltr',
                }}
              >
                {/* Subtle inset stripe pattern for texture */}
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    backgroundImage:
                      'linear-gradient(90deg, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0) 100%)',
                    pointerEvents: 'none',
                  }}
                />
                {/* Filled bar */}
                <div
                  style={{
                    position: 'absolute',
                    insetInlineStart: 0,
                    top: 0,
                    bottom: 0,
                    width: fillW,
                    background: `linear-gradient(90deg, ${color}, ${color}cc)`,
                    borderRadius: 10,
                    boxShadow: isTop
                      ? `0 0 22px ${color}55, inset 0 0 0 1px ${color}33`
                      : `inset 0 0 0 1px ${color}22`,
                    opacity: pulse,
                  }}
                />
                {/* Glow tip on the leading edge */}
                <div
                  style={{
                    position: 'absolute',
                    insetInlineStart: Math.max(0, fillW - 10),
                    top: 0,
                    bottom: 0,
                    width: 14,
                    background: `linear-gradient(90deg, transparent, ${color})`,
                    opacity: intro * 0.9,
                    filter: 'blur(2px)',
                  }}
                />
              </div>

              {/* Value chip */}
              <div
                style={{
                  width: numW,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-end',
                  gap: 2,
                  direction: 'ltr',
                }}
              >
                <div
                  style={{
                    fontSize: isTop ? 22 : 18,
                    fontWeight: 800,
                    color: isTop ? color : '#181818',
                    fontVariantNumeric: 'tabular-nums',
                    lineHeight: 1,
                  }}
                >
                  {shownNum.toLocaleString('en-US')}
                </div>
                <div
                  style={{
                    fontSize: 10,
                    color: '#706E6B',
                    fontWeight: 600,
                  }}
                >
                  לקוחות
                </div>
              </div>

              {/* Inline sparkline (only when we have multi-period history) */}
              {sparkPath && (
                <svg
                  width={sparkW}
                  height={rowH - 18}
                  style={{ direction: 'ltr', overflow: 'visible' }}
                >
                  <path
                    d={sparkPath}
                    fill="none"
                    stroke={color}
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{
                      filter: `drop-shadow(0 1px 2px ${color}44)`,
                      strokeDasharray: 400,
                      strokeDashoffset: 400 * (1 - valueProgress),
                    }}
                  />
                  {/* End-point dot */}
                  {(() => {
                    const sw = sparkW
                    const sh = rowH - 18
                    const lastIdx = r.history.length - 1
                    const sx = (lastIdx / Math.max(1, r.history.length - 1)) * sw
                    const max = Math.max(1, ...r.history)
                    const min = Math.min(0, ...r.history)
                    const sy =
                      sh -
                      ((r.history[lastIdx] - min) / Math.max(1, max - min)) * sh
                    return (
                      <circle
                        cx={sx}
                        cy={sy}
                        r={3 * valueProgress}
                        fill="#fff"
                        stroke={color}
                        strokeWidth={2}
                      />
                    )
                  })()}
                </svg>
              )}
            </div>
          )
        })}

      {/* Insight chip */}
      {hasData && props.insight ? (
        <div
          style={{
            position: 'absolute',
            insetInlineStart: padInline,
            bottom: 18,
            padding: '8px 14px',
            borderRadius: 999,
            background: 'rgba(245,124,0,0.10)',
            border: '1px solid rgba(245,124,0,0.22)',
            color: '#E65100',
            fontSize: 12,
            fontWeight: 700,
            opacity: interpolate(frame, [54, 76], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
            transform: `translateY(${interpolate(frame, [54, 76], [10, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })}px)`,
          }}
        >
          {props.insight}
        </div>
      ) : null}

      {/* Total chip on the end side */}
      {hasData && (
        <div
          style={{
            position: 'absolute',
            insetInlineEnd: padInline,
            bottom: 18,
            display: 'flex',
            alignItems: 'baseline',
            gap: 6,
            color: '#3E3E3C',
            fontSize: 12,
            fontWeight: 600,
            opacity: interpolate(frame, [60, 78], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
          }}
        >
          סה״כ
          <span
            style={{
              fontSize: 16,
              fontWeight: 800,
              color: '#E65100',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {rows.reduce((s, r) => s + r.last, 0).toLocaleString('en-US')}
          </span>
          <span style={{ color: '#A8A29A' }}>לקוחות</span>
        </div>
      )}
    </div>
  )
}
