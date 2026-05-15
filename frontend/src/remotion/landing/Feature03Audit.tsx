import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion'
import { FONT, SOFT, tint } from './landingPalette'

// Feature 03 — Commission audit automation.
// Visual: Vertical list of rows. A horizontal "scanner" bar sweeps top→bottom;
// each row, as the scanner passes, gets a soft check (matched) or warning dot (gap).
// 90 frames @ 30fps = 3s seamless loop.

const ACCENT = SOFT.feature03
const ROWS = [
  { label: 'אקסלנס • גמל', amount: '₪4,820', status: 'ok' as const },
  { label: 'הפניקס • ביטוח', amount: '₪3,210', status: 'gap' as const },
  { label: 'מגדל • פנסיה', amount: '₪5,940', status: 'ok' as const },
  { label: 'הראל • גמל', amount: '₪2,675', status: 'gap' as const },
  { label: 'כלל • ביטוח', amount: '₪6,420', status: 'ok' as const },
  { label: 'אלטשולר • פנסיה', amount: '₪3,950', status: 'ok' as const },
]

export function Feature03Audit() {
  const frame = useCurrentFrame()
  const { width, height, durationInFrames } = useVideoConfig()

  const cardW = Math.min(width * 0.78, 920)
  const cardH = Math.min(height * 0.78, 600)
  const cardLeft = (width - cardW) / 2
  const cardTop = (height - cardH) / 2

  const rowH = (cardH - 130) / ROWS.length
  const rowsTop = cardTop + 90

  // Scanner sweeps from top of rows to bottom, looping smoothly via full-period sine
  // shifted so that scannerY at frame 0 = scannerY at frame N (seamless).
  const scanCycle = (frame / durationInFrames) % 1
  const scannerY = rowsTop + scanCycle * (rowH * ROWS.length)

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${SOFT.bgTop} 0%, ${SOFT.bgBottom} 100%)`,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {/* Slate accent orb */}
      <div
        style={{
          position: 'absolute',
          width: width * 0.45,
          height: width * 0.45,
          borderRadius: '50%',
          background: tint(ACCENT, 0.1),
          top: -width * 0.12,
          left: -width * 0.1,
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
          borderRadius: 26,
          boxShadow: SOFT.shadowMed,
          padding: 36,
          overflow: 'hidden',
          border: `1px solid ${SOFT.divider}`,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 22,
          }}
        >
          <div
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: SOFT.text,
              letterSpacing: '-0.02em',
            }}
          >
            בדיקת עמלות
          </div>
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.18em',
              color: ACCENT,
              background: tint(ACCENT, 0.12),
              padding: '4px 12px',
              borderRadius: 99,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: ACCENT,
                opacity: 0.5 + 0.5 * Math.abs(Math.sin((frame / 30) * Math.PI)),
              }}
            />
            SCANNING
          </div>
        </div>

        {/* Scanner sweep line (positioned relative to card; we translate it across rows region) */}
        <div
          style={{
            position: 'absolute',
            left: 36,
            right: 36,
            top: scannerY - cardTop,
            height: 32,
            background: `linear-gradient(180deg, transparent, ${tint(ACCENT, 0.18)}, transparent)`,
            borderRadius: 8,
            pointerEvents: 'none',
          }}
        />

        {/* Rows */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {ROWS.map((r, i) => {
            // Each row reveals its status icon when the scanner passes it.
            const rowCenter = rowsTop + i * rowH + rowH / 2
            const dist = Math.abs(scannerY - rowCenter)
            const reveal = interpolate(dist, [0, rowH * 0.6], [1, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
            // Lock in once revealed: track a per-row "seen" via frame at which scanner reached it.
            // Approximation: rowCenter / total = pct → seenFrame = pct * durationInFrames.
            const totalRowRegion = rowH * ROWS.length
            const seenAt = ((rowCenter - rowsTop) / totalRowRegion) * durationInFrames
            const locked = interpolate(frame, [seenAt, seenAt + 4], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
            const opacity = Math.max(reveal, locked)
            const okColor = SOFT.feature02 // soft sage for OK (rather than green)
            const gapColor = SOFT.feature01 // soft peach for gap (rather than red)

            return (
              <div
                key={r.label}
                style={{
                  height: rowH,
                  display: 'flex',
                  alignItems: 'center',
                  borderBottom: i < ROWS.length - 1 ? `1px solid ${SOFT.dividerSoft}` : 'none',
                  gap: 16,
                  paddingInline: 4,
                }}
              >
                {/* Status badge */}
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: '50%',
                    background: r.status === 'ok' ? tint(okColor, 0.16) : tint(gapColor, 0.16),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity,
                    transform: `scale(${0.6 + opacity * 0.4})`,
                  }}
                >
                  {r.status === 'ok' ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={okColor} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: gapColor }} />
                  )}
                </div>
                {/* Label */}
                <div
                  style={{
                    flex: 1,
                    fontSize: 17,
                    fontWeight: 700,
                    color: SOFT.text,
                  }}
                >
                  {r.label}
                </div>
                {/* Amount */}
                <div
                  style={{
                    fontSize: 16,
                    fontWeight: 800,
                    color: r.status === 'gap' ? gapColor : SOFT.text,
                    fontVariantNumeric: 'tabular-nums',
                    direction: 'ltr',
                    opacity: 0.5 + opacity * 0.5,
                  }}
                >
                  {r.amount}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </AbsoluteFill>
  )
}
