import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion'
import { FONT, SOFT, tint } from './landingPalette'

// Feature 02 — Agreements → auto rate-table updates.
// Visual: Agreement doc on the left, curved flow lines reach a rate table on the right;
// table cells light up one-by-one as the agreement "feeds" them.
// 90 frames @ 30fps = 3s seamless loop.

const ACCENT = SOFT.feature02
const ROWS = 5
const COLS = 3
const COMPANIES = ['הראל', 'מגדל', 'אקסלנס', 'הפניקס', 'כלל']
const PRODUCTS = ['גמל', 'פנסיה', 'ביטוח']

export function Feature02Agreements() {
  const frame = useCurrentFrame()
  const { width, height, durationInFrames } = useVideoConfig()

  const breathe = Math.sin((frame / durationInFrames) * Math.PI * 2) * 3

  const docW = 260
  const docH = 360
  const docLeft = width * 0.08
  const docTop = (height - docH) / 2

  const tableW = 580
  const tableH = 360
  const tableRight = width * 0.08
  const tableLeft = width - tableW - tableRight
  const tableTop = (height - tableH) / 2

  const cellH = (tableH - 80) / ROWS

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${SOFT.bgTop} 0%, ${SOFT.bgBottom} 100%)`,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {/* Sage accent orb */}
      <div
        style={{
          position: 'absolute',
          width: width * 0.4,
          height: width * 0.4,
          borderRadius: '50%',
          background: tint(ACCENT, 0.14),
          bottom: -width * 0.15,
          right: width * 0.25,
          filter: 'blur(80px)',
        }}
      />

      {/* Flow curves — SVG full-bleed behind doc + table */}
      <svg
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
        viewBox={`0 0 ${width} ${height}`}
      >
        {Array.from({ length: ROWS }).map((_, i) => {
          const start = 14 + i * 5
          const draw = interpolate(frame, [start, start + 18], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          })
          const y1 = docTop + docH / 2
          const y2 = tableTop + 60 + i * cellH + cellH / 2
          const x1 = docLeft + docW
          const x2 = tableLeft + 40
          const midX = (x1 + x2) / 2
          const path = `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`
          const pathLen = Math.hypot(x2 - x1, y2 - y1) * 1.4
          return (
            <path
              key={i}
              d={path}
              fill="none"
              stroke={ACCENT}
              strokeWidth={2}
              strokeLinecap="round"
              opacity={0.6}
              strokeDasharray={pathLen}
              strokeDashoffset={pathLen * (1 - draw)}
            />
          )
        })}
      </svg>

      {/* Agreement doc */}
      <div
        style={{
          position: 'absolute',
          top: docTop,
          left: docLeft,
          width: docW,
          height: docH,
          background: SOFT.card,
          borderRadius: 18,
          boxShadow: SOFT.shadowMed,
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
          transform: `translateY(${breathe}px)`,
          border: `1px solid ${SOFT.divider}`,
        }}
      >
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.18em',
            color: ACCENT,
          }}
        >
          הסכם
        </div>
        <div
          style={{
            fontSize: 18,
            fontWeight: 800,
            color: SOFT.text,
            letterSpacing: '-0.01em',
            lineHeight: 1.2,
          }}
        >
          טבלת עמלות
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {[0.9, 0.7, 0.85, 0.6, 0.78].map((w, i) => (
            <div
              key={i}
              style={{ height: 6, width: `${w * 100}%`, background: SOFT.divider, borderRadius: 3 }}
            />
          ))}
        </div>
        {/* Seal */}
        <div
          style={{
            position: 'absolute',
            bottom: 16,
            left: 16,
            width: 44,
            height: 44,
            borderRadius: '50%',
            background: tint(ACCENT, 0.16),
            border: `2px solid ${ACCENT}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 18,
            color: ACCENT,
            fontWeight: 800,
          }}
        >
          ₪
        </div>
      </div>

      {/* Rate table */}
      <div
        style={{
          position: 'absolute',
          top: tableTop,
          left: tableLeft,
          width: tableW,
          height: tableH,
          background: SOFT.card,
          borderRadius: 22,
          boxShadow: SOFT.shadowMed,
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
          border: `1px solid ${SOFT.divider}`,
        }}
      >
        {/* Header row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `1.2fr repeat(${COLS}, 1fr)`,
            gap: 12,
            paddingBottom: 14,
            borderBottom: `1px solid ${SOFT.divider}`,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: SOFT.textMuted }}>חברה</div>
          {PRODUCTS.map((p) => (
            <div
              key={p}
              style={{ fontSize: 12, fontWeight: 700, color: SOFT.textMuted, textAlign: 'center' }}
            >
              {p}
            </div>
          ))}
        </div>
        {/* Data rows */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, paddingTop: 8 }}>
          {COMPANIES.map((company, r) => {
            const rowStart = 18 + r * 5
            return (
              <div
                key={company}
                style={{
                  display: 'grid',
                  gridTemplateColumns: `1.2fr repeat(${COLS}, 1fr)`,
                  gap: 12,
                  alignItems: 'center',
                  flex: 1,
                  borderBottom: r < ROWS - 1 ? `1px solid ${SOFT.dividerSoft}` : 'none',
                }}
              >
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: SOFT.text,
                  }}
                >
                  {company}
                </div>
                {PRODUCTS.map((_, c) => {
                  const cellStart = rowStart + c * 3 + 14
                  const fill = interpolate(frame, [cellStart, cellStart + 10], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  })
                  const pct = [12, 9, 15, 7, 11][r] + c * 2
                  return (
                    <div
                      key={c}
                      style={{
                        height: 28,
                        background: `linear-gradient(135deg, ${tint(ACCENT, 0.08 + fill * 0.18)}, ${tint(ACCENT, fill * 0.12)})`,
                        border: `1px solid ${tint(ACCENT, 0.2 + fill * 0.3)}`,
                        borderRadius: 8,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 13,
                        fontWeight: 700,
                        color: SOFT.text,
                        opacity: 0.35 + fill * 0.65,
                        direction: 'ltr',
                      }}
                    >
                      {Math.round(pct * fill * 10) / 10}%
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    </AbsoluteFill>
  )
}
