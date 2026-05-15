import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion'
import { FONT, SOFT, tint } from './landingPalette'

// Feature 04 — Insights: gaps, monthly changes, trends.
// Visual: Soft area chart fills left-to-right (months on X), three pill badges
// fade in above the chart with insight numbers.
// 90 frames @ 30fps = 3s seamless loop.

const ACCENT = SOFT.feature04
const MONTHS = ['ינו', 'פבר', 'מרץ', 'אפר', 'מאי', 'יונ', 'יול', 'אוג']
// Normalized values 0..1 — gentle uptrend with a dip mid-way
const VALUES = [0.32, 0.41, 0.36, 0.55, 0.48, 0.62, 0.71, 0.86]

const PILLS = [
  { label: 'פער', value: '₪2,400', color: SOFT.feature01 },
  { label: 'צבירה', value: '+12%', color: SOFT.feature02 },
  { label: 'מגמה', value: '↗', color: SOFT.feature05 },
]

export function Feature04Insights() {
  const frame = useCurrentFrame()
  const { width, height, durationInFrames } = useVideoConfig()

  const cardW = Math.min(width * 0.82, 1000)
  const cardH = Math.min(height * 0.82, 620)
  const cardLeft = (width - cardW) / 2
  const cardTop = (height - cardH) / 2

  // Chart region
  const chartPadX = 40
  const chartTop = 220
  const chartBottom = cardH - 60
  const chartH = chartBottom - chartTop
  const chartLeft = chartPadX
  const chartRight = cardW - chartPadX
  const chartW = chartRight - chartLeft

  // Reveal progress 0..1 — sweeps in, then holds. Loop seamless via sine-shaped progress.
  // We use eased-rise from 0 → 1 over first 70% of timeline, then hold at 1 until loop wraps.
  const reveal = interpolate(frame, [6, durationInFrames * 0.65], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  // Build the area path. Coordinates are local to the SVG inside the card.
  const points = VALUES.map((v, i) => {
    const x = chartLeft + (i / (VALUES.length - 1)) * chartW
    const y = chartBottom - v * chartH
    return { x, y }
  })

  // Visible up to `reveal * (n-1)` index
  const visibleEnd = reveal * (VALUES.length - 1)

  // Build smooth path with cubic-ish midpoint curves
  const pathSegments: string[] = []
  for (let i = 0; i <= Math.floor(visibleEnd); i++) {
    if (i === 0) pathSegments.push(`M ${points[0].x} ${points[0].y}`)
    else {
      const prev = points[i - 1]
      const cur = points[i]
      const midX = (prev.x + cur.x) / 2
      pathSegments.push(`C ${midX} ${prev.y}, ${midX} ${cur.y}, ${cur.x} ${cur.y}`)
    }
  }
  // Partial segment if reveal between two points
  const fracIdx = Math.floor(visibleEnd)
  const frac = visibleEnd - fracIdx
  if (frac > 0 && fracIdx < VALUES.length - 1) {
    const prev = points[fracIdx]
    const next = points[fracIdx + 1]
    const x = prev.x + (next.x - prev.x) * frac
    const y = prev.y + (next.y - prev.y) * frac
    const midX = (prev.x + x) / 2
    pathSegments.push(`C ${midX} ${prev.y}, ${midX} ${y}, ${x} ${y}`)
  }
  const linePath = pathSegments.join(' ')

  // Close the area path back along the baseline for fill
  const lastX = visibleEnd >= VALUES.length - 1
    ? points[VALUES.length - 1].x
    : points[fracIdx].x + (points[fracIdx + 1].x - points[fracIdx].x) * frac
  const areaPath = `${linePath} L ${lastX} ${chartBottom} L ${chartLeft} ${chartBottom} Z`

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${SOFT.bgTop} 0%, ${SOFT.bgBottom} 100%)`,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {/* Mauve accent orb */}
      <div
        style={{
          position: 'absolute',
          width: width * 0.4,
          height: width * 0.4,
          borderRadius: '50%',
          background: tint(ACCENT, 0.14),
          top: width * 0.05,
          right: -width * 0.1,
          filter: 'blur(80px)',
        }}
      />

      {/* Card */}
      <div
        style={{
          position: 'absolute',
          top: cardTop,
          left: cardLeft,
          width: cardW,
          height: cardH,
          background: SOFT.card,
          borderRadius: 28,
          boxShadow: SOFT.shadowMed,
          padding: 36,
          border: `1px solid ${SOFT.divider}`,
        }}
      >
        {/* Title */}
        <div
          style={{
            fontSize: 24,
            fontWeight: 800,
            color: SOFT.text,
            letterSpacing: '-0.02em',
          }}
        >
          תובנות חודשיות
        </div>
        <div
          style={{
            fontSize: 14,
            color: SOFT.textMuted,
            marginTop: 4,
          }}
        >
          פערים, שינויים ומגמות לאורך זמן
        </div>

        {/* Pill row */}
        <div style={{ display: 'flex', gap: 12, marginTop: 22 }}>
          {PILLS.map((p, i) => {
            const start = 12 + i * 8
            const op = interpolate(frame, [start, start + 12], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
            const y = interpolate(frame, [start, start + 12], [10, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
            return (
              <div
                key={p.label}
                style={{
                  padding: '10px 18px',
                  background: tint(p.color, 0.14),
                  border: `1px solid ${tint(p.color, 0.32)}`,
                  borderRadius: 14,
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 8,
                  opacity: op,
                  transform: `translateY(${y}px)`,
                }}
              >
                <span style={{ fontSize: 12, color: SOFT.textMuted, fontWeight: 600 }}>
                  {p.label}
                </span>
                <span
                  style={{
                    fontSize: 18,
                    fontWeight: 800,
                    color: p.color,
                    letterSpacing: '-0.01em',
                    fontVariantNumeric: 'tabular-nums',
                    direction: 'ltr',
                  }}
                >
                  {p.value}
                </span>
              </div>
            )
          })}
        </div>

        {/* Chart SVG */}
        <svg
          style={{ position: 'absolute', left: 0, top: 0, width: cardW, height: cardH }}
          viewBox={`0 0 ${cardW} ${cardH}`}
        >
          {/* Y baselines (decorative) */}
          {[0.25, 0.5, 0.75].map((p, i) => {
            const y = chartBottom - p * chartH
            return (
              <line
                key={i}
                x1={chartLeft}
                x2={chartRight}
                y1={y}
                y2={y}
                stroke={SOFT.dividerSoft}
                strokeWidth={1}
                strokeDasharray="4 6"
              />
            )
          })}

          {/* Area fill */}
          <defs>
            <linearGradient id="f4-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={ACCENT} stopOpacity="0.3" />
              <stop offset="100%" stopColor={ACCENT} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill="url(#f4-area)" />

          {/* Line on top */}
          <path
            d={linePath}
            fill="none"
            stroke={ACCENT}
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Dots for visible months — already filtered by visibleEnd */}
          {points.map((pt, i) => {
            if (i > visibleEnd) return null
            return (
              <circle
                key={i}
                cx={pt.x}
                cy={pt.y}
                r={4}
                fill={SOFT.card}
                stroke={ACCENT}
                strokeWidth={2.5}
              />
            )
          })}

          {/* X-axis month labels */}
          {MONTHS.map((m, i) => {
            const x = chartLeft + (i / (MONTHS.length - 1)) * chartW
            return (
              <text
                key={m}
                x={x}
                y={chartBottom + 24}
                textAnchor="middle"
                fontSize="12"
                fontFamily={FONT}
                fill={SOFT.textMuted}
                fontWeight={600}
              >
                {m}
              </text>
            )
          })}
        </svg>
      </div>
    </AbsoluteFill>
  )
}
