import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion'
import type { VizFundTrack } from './types'

const FONT = 'Heebo, sans-serif'

const PERIOD_LABELS: { key: 'month' | 'y1' | 'y3' | 'y5'; he: string }[] = [
  { key: 'month', he: 'חודש' },
  { key: 'y1', he: 'שנה' },
  { key: 'y3', he: '3 שנים' },
  { key: 'y5', he: '5 שנים' },
]

const POS = '#2E844A'
const NEG = '#C23934'
const FLAT = '#94A3B8'

function colorFor(v: number | null | undefined) {
  if (v === null || v === undefined || !Number.isFinite(v)) return FLAT
  if (v > 0) return POS
  if (v < 0) return NEG
  return FLAT
}

function fmtPct(v: number | null | undefined, progress = 1) {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—'
  const shown = v * progress
  const sign = shown > 0 ? '+' : ''
  return `${sign}${shown.toFixed(2)}%`
}

export function FundTrackComposition(props: VizFundTrack) {
  const frame = useCurrentFrame()
  const { fps, width, height } = useVideoConfig()

  const funds = (props.funds ?? []).slice(0, 10)

  // Build a single max-abs across all periods so bar widths are comparable.
  const allValues = [
    props.averages.month, props.averages.y1, props.averages.y3, props.averages.y5,
    ...funds.flatMap((f) => [f.month, f.y1, f.y3, f.y5]),
  ].filter((v): v is number => v !== null && v !== undefined && Number.isFinite(v))
  const maxAbs = Math.max(1, ...allValues.map((v) => Math.abs(v)))

  // Layout
  const pad = 36
  const titleY = 36
  const kpiY = 80
  const kpiH = 56
  const tableTop = kpiY + kpiH + 20
  const rowGap = 6
  const tableHeight = height - tableTop - 36
  const rowHeight = funds.length > 0
    ? Math.max(28, tableHeight / funds.length - rowGap)
    : 32
  const nameW = 220
  const cellGap = 8
  const cellsArea = width - pad * 2 - nameW - 16
  const cellW = (cellsArea - cellGap * 3) / 4

  // Entrance animations
  const titleOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' })
  const titleSlide = interpolate(frame, [0, 14], [-8, 0], { extrapolateRight: 'clamp' })

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
      {/* decorative orb */}
      <div
        style={{
          position: 'absolute',
          width: 360,
          height: 360,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(245,124,0,0.16), transparent 70%)',
          top: -120,
          insetInlineStart: -80,
          pointerEvents: 'none',
        }}
      />

      {/* Title + period chip */}
      <div
        style={{
          position: 'absolute',
          insetInlineStart: pad,
          insetInlineEnd: pad,
          top: titleY + titleSlide,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          opacity: titleOpacity,
        }}
      >
        <div style={{ fontSize: 22, fontWeight: 800, color: '#181818', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {props.title}
        </div>
        {props.period_label ? (
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: '#F57C00',
              background: 'rgba(245,124,0,0.10)',
              padding: '4px 10px',
              borderRadius: 999,
            }}
          >
            תקופה · {props.period_label}
          </div>
        ) : null}
      </div>

      {/* Averages — 4 KPI pills (track-wide averages across all funds in this maslul) */}
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
          const v = props.averages[p.key]
          const start = 6 + i * 4
          const prog = spring({
            frame: frame - start,
            fps,
            config: { damping: 18, mass: 0.6, stiffness: 160 },
          })
          const valueProgress = interpolate(
            frame,
            [start + 4, start + 24],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          )
          const color = colorFor(v)
          return (
            <div
              key={p.key}
              style={{
                flex: 1,
                height: kpiH,
                borderRadius: 12,
                background: 'rgba(255,255,255,0.85)',
                border: '1px solid rgba(0,0,0,0.06)',
                boxShadow: '0 2px 6px rgba(17,12,6,0.04)',
                padding: '8px 12px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                gap: 2,
                opacity: prog,
                transform: `translateY(${(1 - prog) * 10}px)`,
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 600, color: '#6B6B6B' }}>
                ממוצע · {p.he}
              </div>
              <div
                style={{
                  fontSize: 18,
                  fontWeight: 800,
                  color,
                  direction: 'ltr',
                  textAlign: 'start',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {fmtPct(v, valueProgress)}
              </div>
            </div>
          )
        })}
      </div>

      {/* Funds table */}
      {funds.length === 0 ? (
        <div
          style={{
            position: 'absolute',
            insetInlineStart: pad,
            insetInlineEnd: pad,
            top: tableTop + 40,
            fontSize: 14,
            color: '#6B6B6B',
            textAlign: 'center',
          }}
        >
          אין נתוני קרנות
        </div>
      ) : (
        funds.map((f, i) => {
          const rowStart = 18 + i * 5
          const introProgress = spring({
            frame: frame - rowStart,
            fps,
            config: { damping: 18, mass: 0.7, stiffness: 140 },
          })
          const valueProgress = interpolate(
            frame,
            [rowStart + 4, rowStart + 28],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          )
          const y = tableTop + i * (rowHeight + rowGap)

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
                opacity: introProgress,
                transform: `translateX(${(1 - introProgress) * -24}px)`,
              }}
            >
              <div
                style={{
                  width: nameW,
                  fontSize: 13,
                  fontWeight: 700,
                  color: '#3E3E3C',
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
                  const v = f[p.key]
                  const c = colorFor(v)
                  const hasVal = v !== null && v !== undefined && Number.isFinite(v as number)
                  const widthPct = hasVal
                    ? (Math.abs(v as number) / maxAbs)
                    : 0
                  return (
                    <div
                      key={p.key}
                      style={{
                        width: cellW,
                        height: rowHeight - 6,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        gap: 2,
                      }}
                    >
                      <div
                        style={{
                          height: 6,
                          background: 'rgba(0,0,0,0.06)',
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
                            background: c,
                            borderRadius: 4,
                          }}
                        />
                      </div>
                      <div
                        style={{
                          fontSize: 12,
                          fontWeight: 700,
                          color: c,
                          direction: 'ltr',
                          textAlign: 'start',
                          fontVariantNumeric: 'tabular-nums',
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
    </div>
  )
}
