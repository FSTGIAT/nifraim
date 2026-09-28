import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'

/**
 * Workspace-home widget for the monthly cycle.
 *
 *   ┌──────────┐   21.10 ◄─ ▪ ▪ ▪ ─── ● היום ──────── 21.9
 *   │  ring    │   נפרעים          (15 מסלקה)
 *   │  22 ימים │
 *   └──────────┘
 *
 * - Ring = share of the month already elapsed (start → target), REAL time.
 *   Inside: days, and HH:MM:SS ticking live (Date.now() per frame — Player only).
 * - Rail reads right → left like the page: today's pulse on the right part,
 *   the target flag at the left end; little reports flow toward the flag.
 * - Loop-perfect over 180 frames: every motion is a whole number of cycles.
 */
export const CYCLE_WIDGET_FRAMES = 180 // 6s @ 30fps
export const CYCLE_WIDGET_SIZE = { width: 880, height: 230 }

export type CycleWidgetProps = {
  targetMs: number
  startMs: number
  color?: string
  ink?: string
  targetLabel?: string // "21.10"
  targetCaption?: string // "נפרעים ספטמבר"
  startLabel?: string // "21.9"
  maslakaMs?: number | null
  maslakaLabel?: string // "15.11"
  waiting?: boolean
  narrow?: boolean // phones: the ring alone, composition 300×230
}

const RAIL_R = 830 // right end (start of the month)
const RAIL_L = 330 // left end (the cycle)
const RAIL_Y = 120

export const CycleWidget: React.FC<CycleWidgetProps> = ({
  targetMs,
  startMs,
  color = '#2F73C4',
  ink = '#181818',
  targetLabel = '',
  targetCaption = '',
  startLabel = '',
  maslakaMs = null,
  maslakaLabel = '',
  waiting = false,
  narrow = false,
}) => {
  const frame = useCurrentFrame()
  const t = frame / CYCLE_WIDGET_FRAMES // 0..1 over the loop

  const now = Date.now()
  const remaining = Math.max(0, targetMs - now)
  const span = Math.max(1, targetMs - startMs)
  const frac = Math.max(0.02, Math.min(1, 1 - remaining / span))
  const totalS = Math.floor(remaining / 1000)
  const days = Math.floor(totalS / 86400)
  const hms = [Math.floor((totalS % 86400) / 3600), Math.floor((totalS % 3600) / 60), totalS % 60]
    .map((n) => String(n).padStart(2, '0'))
    .join(':')

  // ── ring ──
  const cx = narrow ? 150 : 128
  const cy = 115
  const r = 86
  const C = 2 * Math.PI * r
  const tipA = -Math.PI / 2 + frac * 2 * Math.PI
  const tipX = cx + r * Math.cos(tipA)
  const tipY = cy + r * Math.sin(tipA)
  const pulse = (Math.sin(t * Math.PI * 2 * 2) + 1) / 2 // 2 beats per loop
  const glow = 0.25 + 0.2 * pulse

  // ── rail ──
  const todayX = RAIL_R - frac * (RAIL_R - RAIL_L)
  const railX = (ms: number) => RAIL_R - ((ms - startMs) / span) * (RAIL_R - RAIL_L)
  const showMaslaka = !!maslakaMs && maslakaMs > startMs && maslakaMs < targetMs
  const flagSway = Math.sin(t * Math.PI * 2 * 3) * 6 // 3 sways per loop

  // Reports flowing from today → flag (3 staggered, each one full pass per loop).
  const docs = [0, 1 / 3, 2 / 3].map((ph) => {
    const life = (t + ph) % 1
    const x = interpolate(life, [0, 1], [todayX - 16, RAIL_L + 26])
    const op = interpolate(life, [0, 0.12, 0.85, 1], [0, 1, 1, 0])
    const bob = Math.sin(life * Math.PI * 4) * 3
    return { x, op, bob }
  })

  const accent = waiting ? '#8A6300' : color

  return (
    <AbsoluteFill style={{ fontFamily: 'Heebo, sans-serif' }}>
      <svg width={narrow ? 300 : 880} height={230} viewBox={narrow ? '0 0 300 230' : '0 0 880 230'}>
        <defs>
          <linearGradient id="cw-arc" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity="0.55" />
            <stop offset="100%" stopColor={accent} />
          </linearGradient>
          <filter id="cw-soft" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" />
          </filter>
        </defs>

        {/* ring: faint tick marks = days of the month */}
        {Array.from({ length: 30 }).map((_, i) => {
          const a = -Math.PI / 2 + (i / 30) * 2 * Math.PI
          const r1 = r + 14
          const r2 = r + (i % 5 === 0 ? 22 : 18)
          return (
            <line key={i} x1={cx + r1 * Math.cos(a)} y1={cy + r1 * Math.sin(a)} x2={cx + r2 * Math.cos(a)} y2={cy + r2 * Math.sin(a)}
              stroke={ink} strokeOpacity={i / 30 <= frac ? 0.28 : 0.1} strokeWidth={2} strokeLinecap="round" />
          )
        })}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={accent} strokeOpacity={0.12} strokeWidth={14} />
        <circle
          cx={cx} cy={cy} r={r} fill="none" stroke="url(#cw-arc)" strokeWidth={14} strokeLinecap="round"
          strokeDasharray={`${C * frac} ${C}`} transform={`rotate(-90 ${cx} ${cy})`}
        />
        <circle cx={tipX} cy={tipY} r={16 + 6 * pulse} fill={accent} opacity={glow} filter="url(#cw-soft)" />
        <circle cx={tipX} cy={tipY} r={9} fill="#fff" stroke={accent} strokeWidth={4} />
        <text x={cx} y={cy + 8} textAnchor="middle" fontSize="60" fontWeight="900" fill={accent} style={{ fontVariantNumeric: 'tabular-nums' }}>{days}</text>
        <text x={cx} y={cy + 34} textAnchor="middle" fontSize="17" fontWeight="700" fill={ink} opacity={0.55}>ימים</text>
        <text x={cx} y={cy + 58} textAnchor="middle" fontSize="17" fontWeight="800" fill={ink} opacity={0.75} style={{ fontVariantNumeric: 'tabular-nums' }}>{hms}</text>

        {!narrow && <g>
        {/* rail: elapsed solid, ahead dashed */}
        <line x1={RAIL_R} y1={RAIL_Y} x2={todayX} y2={RAIL_Y} stroke={accent} strokeWidth={5} strokeLinecap="round" />
        <line x1={todayX} y1={RAIL_Y} x2={RAIL_L} y2={RAIL_Y} stroke={accent} strokeOpacity={0.35} strokeWidth={4}
          strokeDasharray="2 12" strokeLinecap="round" strokeDashoffset={-t * 14 * 6} />
        <circle cx={RAIL_R} cy={RAIL_Y} r={6} fill={accent} opacity={0.5} />
        {startLabel && RAIL_R - todayX > 70 && <text x={RAIL_R} y={RAIL_Y + 34} textAnchor="middle" fontSize="16" fontWeight="700" fill={ink} opacity={0.45}>{startLabel}</text>}

        {/* מסלקה marker */}
        {showMaslaka && Math.abs(railX(maslakaMs!) - todayX) > 60 && (
          <g>
            <circle cx={railX(maslakaMs!)} cy={RAIL_Y} r={8} fill="#fff" stroke="#2C5F6B" strokeWidth={3.5} />
            <text x={railX(maslakaMs!)} y={RAIL_Y + 34} textAnchor="middle" fontSize="15" fontWeight="700" fill="#2C5F6B" direction="rtl">{`${maslakaLabel} · מסלקה`}</text>
          </g>
        )}

        {/* flowing reports */}
        {docs.map((d, i) => (
          <g key={i} opacity={d.op} transform={`translate(${d.x} ${RAIL_Y - 34 + d.bob})`}>
            <path d="M-9 -12 h12 l6 6 v18 h-18 z" fill="#fff" stroke={accent} strokeWidth={2.2} strokeLinejoin="round" />
            <path d="M-5 -1 h10 M-5 4 h8" stroke={accent} strokeWidth={1.8} strokeLinecap="round" />
          </g>
        ))}

        {/* today */}
        <circle cx={todayX} cy={RAIL_Y} r={12 + 10 * pulse} fill={accent} opacity={0.18 * (1 - pulse) + 0.06} />
        <circle cx={todayX} cy={RAIL_Y} r={10} fill={accent} />
        <circle cx={todayX} cy={RAIL_Y} r={4} fill="#fff" />
        <text x={todayX} y={RAIL_Y + 36} textAnchor="middle" fontSize="16" fontWeight="800" fill={accent}>היום</text>

        {/* target flag */}
        <g transform={`translate(${RAIL_L} ${RAIL_Y})`}>
          <line x1={0} y1={0} x2={0} y2={-58} stroke={ink} strokeWidth={3.5} strokeLinecap="round" />
          <path d={`M0 -58 q 22 ${-6 + flagSway * 0.3} 44 ${flagSway * 0.4} q -22 ${6 + flagSway * 0.3} -44 ${24}`} fill={accent} />
          <circle cx={0} cy={0} r={9} fill="#fff" stroke={ink} strokeWidth={3.5} />
        </g>
        {targetLabel && <text x={RAIL_L} y={RAIL_Y + 36} textAnchor="middle" fontSize="18" fontWeight="900" fill={ink}>{targetLabel}</text>}
        {targetCaption && <text x={RAIL_L} y={RAIL_Y + 58} textAnchor="middle" fontSize="15" fontWeight="600" fill={ink} opacity={0.6} direction="rtl">{targetCaption}</text>}
        </g>}
      </svg>
    </AbsoluteFill>
  )
}
