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
  // NEW: trend chart + donut row sits between KPIs and the fund table.
  const trendTop = kpiY + kpiH + 18
  const trendH = 196
  const trendDonutW = 240
  const trendChartW = width - pad * 2 - trendDonutW - 18
  const tableTop = trendTop + trendH + 18
  const insightH = props.insight ? 56 : 0
  const tableHeight = Math.max(120, height - tableTop - 24 - insightH)
  const rowGap = 6
  // Cap table rows to 7 so each row stays legible at the new compact height.
  const tableRows = Math.min(funds.length, 7)
  const rowHeight = tableRows > 0
    ? Math.max(30, tableHeight / tableRows - rowGap)
    : 30
  const nameW = 230
  const cellGap = 8
  const cellsArea = width - pad * 2 - nameW - 16
  const cellW = (cellsArea - cellGap * 3) / 4

  // --- Trend chart inputs (top 5 funds by 1Y desc; series = month/1Y/3Y/5Y) ---
  const trendFunds = funds.slice(0, 5)
  const trendPeriods: { key: Period; label: string }[] = [
    { key: 'month', label: 'חודש' },
    { key: 'y1', label: 'שנה' },
    { key: 'y3', label: '3ש' },
    { key: 'y5', label: '5ש' },
  ]
  const trendValues: number[] = trendFunds.flatMap((f) =>
    trendPeriods.map((p) => f[p.key]).filter((v): v is number => v !== null && v !== undefined && Number.isFinite(v as number)),
  )
  const trendMax = Math.max(1, ...trendValues, ...(allValues.filter((v) => v > 0)))
  const trendMin = Math.min(0, ...trendValues, ...(allValues.filter((v) => v < 0)))
  const trendRange = trendMax - trendMin || 1
  // Color palette for the non-hero trend lines.
  const LINE_PALETTE = ['#4f46e5', '#0891b2', '#7c3aed', '#ec4899', '#84cc16']

  // --- Donut inputs: count of 1Y returns by sign across the top 10 funds ---
  let posCount = 0, negCount = 0, flatCount = 0
  for (const f of funds) {
    const v = f.y1 ?? f.month
    if (v === null || v === undefined || !Number.isFinite(v as number)) { flatCount++; continue }
    if ((v as number) > 0) posCount++
    else if ((v as number) < 0) negCount++
    else flatCount++
  }
  const donutTotal = Math.max(1, posCount + negCount + flatCount)

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

      {/* ─── NEW: Trend chart (left) + Winners-vs-Losers donut (right) ─── */}
      {funds.length > 0 ? (
        <>
          {/* Trend chart card */}
          {(() => {
            const cardX = pad
            const cardY = trendTop
            const cardW = trendChartW
            const cardH = trendH
            const innerPad = 14
            const chartX0 = innerPad + 28 // leave room for Y-axis labels
            const chartY0 = innerPad + 28 // leave room for title
            const chartW = cardW - chartX0 - innerPad
            const chartH = cardH - chartY0 - innerPad - 16 // 16 for x labels

            // Map a value/period to (x, y) inside the chart area
            const xAt = (i: number) => chartX0 + (i / (trendPeriods.length - 1)) * chartW
            const yAt = (v: number) => chartY0 + chartH - ((v - trendMin) / trendRange) * chartH
            const zeroY = yAt(0)

            // Trend section reveals as soon as the KPIs land
            const sectionProg = spring({
              frame: frame - 18,
              fps,
              config: { damping: 18, mass: 0.7, stiffness: 130 },
            })
            const lineProg = interpolate(frame, [24, 70], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              easing: Easing.out(Easing.cubic),
            })

            return (
              <div
                style={{
                  position: 'absolute',
                  insetInlineStart: cardX,
                  top: cardY,
                  width: cardW,
                  height: cardH,
                  background: 'rgba(255,255,255,0.95)',
                  border: '1px solid rgba(0,0,0,0.05)',
                  borderRadius: 14,
                  boxShadow: '0 8px 24px rgba(17,12,6,0.06), inset 0 1px 0 rgba(255,255,255,0.8)',
                  opacity: sectionProg,
                  transform: `translateY(${(1 - sectionProg) * 14}px)`,
                  overflow: 'hidden',
                }}
              >
                <div style={{
                  position: 'absolute',
                  insetInlineStart: innerPad,
                  insetInlineEnd: innerPad,
                  top: 10,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#1A1A1A', letterSpacing: '0.01em' }}>
                    מגמת תשואה — טופ 5 קרנות
                  </div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#7A7672' }}>תקופה מצטברת</div>
                </div>

                <svg width={cardW} height={cardH} style={{ position: 'absolute', insetInlineStart: 0, top: 0, direction: 'ltr' }}>
                  {/* Zero gridline */}
                  {trendMin < 0 && trendMax > 0 ? (
                    <line x1={chartX0} y1={zeroY} x2={chartX0 + chartW} y2={zeroY}
                      stroke="rgba(0,0,0,0.18)" strokeDasharray="4 4" strokeWidth={1} />
                  ) : null}
                  {/* X axis labels */}
                  {trendPeriods.map((p, i) => (
                    <text key={p.key}
                      x={xAt(i)} y={chartY0 + chartH + 14}
                      fontSize={10} fontFamily={FONT} fontWeight={700}
                      fill="#7A7672" textAnchor="middle">
                      {p.label}
                    </text>
                  ))}
                  {/* Lines — non-hero first so hero sits on top */}
                  {trendFunds.map((f, idx) => {
                    const isHero = idx === 0
                    const pts = trendPeriods
                      .map((p, i) => {
                        const v = f[p.key]
                        if (v === null || v === undefined || !Number.isFinite(v as number)) return null
                        return { x: xAt(i), y: yAt(v as number) }
                      })
                      .filter((p): p is { x: number; y: number } => p !== null)
                    if (pts.length < 2) return null
                    // Animate path stroke by limiting how much of pts is drawn.
                    const visibleCount = Math.max(2, Math.ceil(pts.length * lineProg))
                    const shownPts = pts.slice(0, visibleCount)
                    // Interpolate the last visible segment for a smooth tip
                    if (lineProg < 1 && visibleCount < pts.length) {
                      const segProg = (pts.length * lineProg) - (visibleCount - 1)
                      const a = pts[visibleCount - 1]
                      const b = pts[visibleCount]
                      shownPts[shownPts.length - 1] = {
                        x: a.x + (b.x - a.x) * segProg,
                        y: a.y + (b.y - a.y) * segProg,
                      }
                    }
                    const d = shownPts.map((p, k) => `${k === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
                    const lastPt = shownPts[shownPts.length - 1]
                    const stroke = isHero ? GOLD_DEEP : LINE_PALETTE[(idx - 1) % LINE_PALETTE.length]
                    return (
                      <g key={`line-${idx}`}>
                        <path d={d} fill="none" stroke={stroke}
                          strokeWidth={isHero ? 3 : 1.75}
                          strokeLinecap="round" strokeLinejoin="round"
                          opacity={isHero ? 1 : 0.7}
                          style={isHero ? { filter: `drop-shadow(0 0 6px ${GOLD}88)` } : undefined}
                        />
                        {lineProg > 0.95 ? (
                          <circle cx={lastPt.x} cy={lastPt.y} r={isHero ? 5 : 3}
                            fill={stroke} stroke="#fff" strokeWidth={1.5} />
                        ) : null}
                      </g>
                    )
                  })}
                </svg>

                {/* Legend chips (top performer + count of others) */}
                <div style={{
                  position: 'absolute',
                  insetInlineEnd: innerPad,
                  bottom: 12,
                  display: 'flex',
                  gap: 6,
                  alignItems: 'center',
                  opacity: lineProg,
                }}>
                  <span style={{
                    fontSize: 10, fontWeight: 800, color: GOLD_DEEP,
                    background: `linear-gradient(135deg, ${GOLD}22, ${GOLD}11)`,
                    padding: '3px 8px', borderRadius: 999,
                    border: `1px solid ${GOLD}55`,
                    maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    direction: 'rtl',
                  }}>
                    {trendFunds[0]?.name || ''}
                  </span>
                  {trendFunds.length > 1 ? (
                    <span style={{ fontSize: 10, fontWeight: 700, color: '#7A7672' }}>
                      + {trendFunds.length - 1} נוספות
                    </span>
                  ) : null}
                </div>
              </div>
            )
          })()}

          {/* Donut: winners / losers / flat across top 10 funds (1Y) */}
          {(() => {
            const cardX = pad + trendChartW + 18
            const cardY = trendTop
            const cardW = trendDonutW
            const cardH = trendH
            const cx = cardW / 2
            const cy = cardH / 2 + 4
            const outerR = Math.min(cardW, cardH) * 0.32
            const innerR = outerR * 0.62
            const sectionProg = spring({
              frame: frame - 22,
              fps,
              config: { damping: 18, mass: 0.7, stiffness: 130 },
            })
            const arcProg = interpolate(frame, [28, 70], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              easing: Easing.out(Easing.cubic),
            })

            type Seg = { value: number; color: string; label: string }
            const segs: Seg[] = [
              { value: posCount, color: POS, label: 'חיוביות' },
              { value: negCount, color: NEG, label: 'שליליות' },
              { value: flatCount, color: FLAT, label: 'ללא' },
            ].filter((s) => s.value > 0)

            // Build arc paths using describeArc-style math
            let acc = 0
            const arcs = segs.map((s) => {
              const angle = (s.value / donutTotal) * 360
              const start = acc
              const end = acc + angle * arcProg
              acc += angle
              const polar = (a: number) => {
                const rad = ((a - 90) * Math.PI) / 180
                return { x: cx + outerR * Math.cos(rad), y: cy + outerR * Math.sin(rad) }
              }
              const polarInner = (a: number) => {
                const rad = ((a - 90) * Math.PI) / 180
                return { x: cx + innerR * Math.cos(rad), y: cy + innerR * Math.sin(rad) }
              }
              if (end - start < 0.01) return null
              const p1 = polar(start)
              const p2 = polar(end)
              const p3 = polarInner(end)
              const p4 = polarInner(start)
              const largeArc = end - start > 180 ? 1 : 0
              const d = [
                `M ${p1.x} ${p1.y}`,
                `A ${outerR} ${outerR} 0 ${largeArc} 1 ${p2.x} ${p2.y}`,
                `L ${p3.x} ${p3.y}`,
                `A ${innerR} ${innerR} 0 ${largeArc} 0 ${p4.x} ${p4.y}`,
                'Z',
              ].join(' ')
              return { d, color: s.color, label: s.label, value: s.value }
            }).filter((a): a is { d: string; color: string; label: string; value: number } => a !== null)

            // Hero pct (positive share of total)
            const posPct = Math.round((posCount / donutTotal) * 100)
            const heroPct = Math.round(interpolate(frame, [30, 70], [0, posPct], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            }))

            return (
              <div
                style={{
                  position: 'absolute',
                  insetInlineStart: cardX,
                  top: cardY,
                  width: cardW,
                  height: cardH,
                  background: 'rgba(255,255,255,0.95)',
                  border: '1px solid rgba(0,0,0,0.05)',
                  borderRadius: 14,
                  boxShadow: '0 8px 24px rgba(17,12,6,0.06), inset 0 1px 0 rgba(255,255,255,0.8)',
                  opacity: sectionProg,
                  transform: `translateY(${(1 - sectionProg) * 14}px)`,
                  overflow: 'hidden',
                }}
              >
                <div style={{
                  position: 'absolute', insetInlineStart: 12, insetInlineEnd: 12, top: 10,
                  fontSize: 12, fontWeight: 800, color: '#1A1A1A',
                }}>
                  מנצחות / מפסידות (שנה)
                </div>
                <svg width={cardW} height={cardH} style={{ position: 'absolute', insetInlineStart: 0, top: 0, direction: 'ltr' }}>
                  {arcs.map((a, i) => (
                    <path key={i} d={a.d} fill={a.color}
                      stroke="#fff" strokeWidth={1.5}
                      style={{ filter: `drop-shadow(0 4px 6px ${a.color}55)` }} />
                  ))}
                  <text x={cx} y={cy - 4} textAnchor="middle"
                    fontSize={28} fontWeight={800} fontFamily={FONT}
                    fill={POS_DEEP}>
                    {heroPct}%
                  </text>
                  <text x={cx} y={cy + 18} textAnchor="middle"
                    fontSize={10} fontWeight={700} fontFamily={FONT}
                    fill="#7A7672">
                    חיוביות
                  </text>
                </svg>
                {/* Legend */}
                <div style={{
                  position: 'absolute', insetInlineStart: 12, insetInlineEnd: 12,
                  bottom: 10,
                  display: 'flex', justifyContent: 'space-around', alignItems: 'center',
                  opacity: arcProg, gap: 6,
                }}>
                  {[
                    { color: POS, label: 'חיובי', val: posCount },
                    { color: NEG, label: 'שלילי', val: negCount },
                    flatCount > 0 ? { color: FLAT, label: 'ללא', val: flatCount } : null,
                  ].filter(Boolean).map((l, i) => l && (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: 2, background: l.color }} />
                      <span style={{ fontSize: 10, fontWeight: 700, color: '#3E3E3C' }}>
                        {l.label} · {l.val}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}
        </>
      ) : null}

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
        funds.slice(0, tableRows).map((f, i) => {
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
