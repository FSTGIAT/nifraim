// MissingFiles — Remotion composition. One ring per month; each company that
// appears in that month's production is a node placed around the ring —
// green = נפרעים file uploaded, red = missing. The ring center shows the
// missing count. Answers "which נפרעים files am I still waiting for?".
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion'

const FONT = 'Heebo, sans-serif'

export interface MissingFilesCompany {
  company: string
  uploaded: boolean
}
export interface MissingFilesMonth {
  period_month: string
  label: string
  company_status: MissingFilesCompany[]
  missing_count: number
}
export interface MissingFilesProps {
  months: MissingFilesMonth[]   // newest → oldest (rendered top → bottom)
  title?: string
}

const C = {
  ok: '#2E844A',
  okSoft: 'rgba(46, 132, 74, 0.14)',
  miss: '#EA001E',
  missSoft: 'rgba(234, 0, 30, 0.10)',
  text: '#181818',
  textMuted: '#706E6B',
  border: '#E5E5E5',
  bg: '#FFFFFF',
  bgWarm: '#FFFBF4',
  ring: 'rgba(112, 110, 107, 0.22)',
}

function shortName(name: string): string {
  const n = (name || '').trim()
  return n.length > 9 ? n.slice(0, 9) + '…' : n
}

export function MissingFilesComposition(props: MissingFilesProps) {
  const frame = useCurrentFrame()
  const { width, height, fps } = useVideoConfig()
  const months = (props.months || []).filter((m) => (m.company_status || []).length > 0)

  const padX = 28
  const titleY = 30
  const headerH = 64
  const count = Math.max(1, months.length)
  const bandH = (height - headerH) / count
  const isEmpty = months.length === 0

  const titleOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' })
  const emptyR = Math.min(width, height - headerH) / 2 - 56
  const emptyPop = spring({ frame: frame - 8, fps, config: { damping: 200, stiffness: 90, mass: 0.6 } })

  return (
    <div
      style={{
        width,
        height,
        direction: 'rtl',
        fontFamily: FONT,
        background: `linear-gradient(135deg, ${C.bg} 0%, ${C.bgWarm} 100%)`,
        color: C.text,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          insetInlineStart: padX,
          insetInlineEnd: padX,
          top: titleY,
          fontSize: 18,
          fontWeight: 800,
          opacity: titleOpacity,
        }}
      >
        {props.title || 'קבצי נפרעים חסרים לפי חודש'}
      </div>
      <div
        style={{
          position: 'absolute',
          insetInlineStart: padX,
          top: titleY + 24,
          fontSize: 12,
          color: C.textMuted,
          opacity: titleOpacity,
        }}
      >
        חברות ששולחות נפרעים · ירוק=הגיע החודש · אדום=חסר
      </div>

      {/* Empty state — no נפרעים files uploaded at all. A gray ring with a
          clear message instead of a confusing blank panel. */}
      {isEmpty && (
        <div
          style={{
            position: 'absolute',
            insetInlineStart: 0,
            insetInlineEnd: 0,
            top: headerH,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            opacity: emptyPop,
          }}
        >
          <div
            style={{
              width: Math.max(120, emptyR * 2),
              height: Math.max(120, emptyR * 2),
              borderRadius: '50%',
              border: `2px dashed ${C.ring}`,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(112, 110, 107, 0.05)',
              transform: `scale(${emptyPop})`,
            }}
          >
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={C.textMuted} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
              <line x1="4" y1="3" x2="20" y2="21" />
            </svg>
            <span style={{ fontSize: 13, fontWeight: 700, color: C.textMuted, marginTop: 10 }}>אין קבצים</span>
          </div>
          <div style={{ textAlign: 'center', maxWidth: width - 64 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: C.text }}>טרם הועלו קבצי נפרעים</div>
            <div style={{ fontSize: 12, color: C.textMuted, marginTop: 4 }}>
              לאחר העלאת קובץ נפרעים ראשון, יוצגו כאן החברות שטרם שלחו דיווח
            </div>
          </div>
        </div>
      )}

      {months.map((m, mi) => {
        const cs = m.company_status || []
        const bandTop = headerH + bandH * mi
        const cx = width / 2
        const cy = bandTop + bandH / 2 + 6
        const ringR = Math.min(width / 2 - 70, bandH / 2 - 34)
        const monthStart = 8 + mi * 8
        const monthIntro = spring({ frame: frame - monthStart, fps, config: { damping: 200, stiffness: 90, mass: 0.6 } })

        return (
          <div key={m.period_month} style={{ opacity: monthIntro }}>
            {/* Month label (top-right of band in RTL) */}
            <div
              style={{
                position: 'absolute',
                top: bandTop + 6,
                insetInlineEnd: padX,
                fontSize: 13,
                fontWeight: 700,
                color: C.text,
              }}
            >
              {m.label}
            </div>

            {/* Ring guide circle */}
            <div
              style={{
                position: 'absolute',
                left: cx - ringR,
                top: cy - ringR,
                width: ringR * 2,
                height: ringR * 2,
                borderRadius: '50%',
                border: `1.5px dashed ${C.ring}`,
              }}
            />

            {/* Center: missing count */}
            <div
              style={{
                position: 'absolute',
                left: cx - 44,
                top: cy - 30,
                width: 88,
                height: 60,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '50%',
                background: m.missing_count > 0 ? C.missSoft : C.okSoft,
              }}
            >
              <span
                style={{
                  fontSize: 26,
                  fontWeight: 800,
                  lineHeight: 1,
                  color: m.missing_count > 0 ? C.miss : C.ok,
                  direction: 'ltr',
                }}
              >
                {m.missing_count}
              </span>
              <span style={{ fontSize: 10, fontWeight: 600, color: C.textMuted, marginTop: 2 }}>
                {m.missing_count === 0 ? 'הכל הגיע' : m.missing_count === 1 ? 'חסר' : 'חסרים'}
              </span>
            </div>

            {/* Company nodes around the ring */}
            {cs.map((co, j) => {
              const ang = (-90 + j * (360 / cs.length)) * (Math.PI / 180)
              const nx = cx + ringR * Math.cos(ang)
              const ny = cy + ringR * Math.sin(ang)
              const pop = spring({
                frame: frame - (monthStart + 6 + j * 1.4),
                fps,
                config: { damping: 200, stiffness: 140, mass: 0.5 },
              })
              const color = co.uploaded ? C.ok : C.miss
              // Label sits radially outward from the node.
              const lx = cx + (ringR + 14) * Math.cos(ang)
              const ly = cy + (ringR + 14) * Math.sin(ang)
              const onLeft = Math.cos(ang) < -0.05
              const onRight = Math.cos(ang) > 0.05
              return (
                <div key={co.company + j}>
                  <div
                    style={{
                      position: 'absolute',
                      left: nx - 6,
                      top: ny - 6,
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      background: color,
                      boxShadow: co.uploaded ? 'none' : `0 0 0 3px ${C.missSoft}`,
                      transform: `scale(${pop})`,
                    }}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      top: ly - 7,
                      left: onRight ? lx : undefined,
                      right: onLeft ? width - lx : undefined,
                      ...(!onLeft && !onRight ? { left: lx - 28, width: 56, textAlign: 'center' as const } : {}),
                      maxWidth: 78,
                      fontSize: 9,
                      fontWeight: co.uploaded ? 500 : 700,
                      color: co.uploaded ? C.textMuted : C.miss,
                      whiteSpace: 'nowrap',
                      opacity: pop,
                    }}
                  >
                    {shortName(co.company)}
                  </div>
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

export const MISSING_FILES_DURATION_FRAMES = 120
export const MISSING_FILES_FPS = 30
