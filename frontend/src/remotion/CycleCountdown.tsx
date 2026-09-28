import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'

/**
 * Locked Production tab (monthly cycle): a live countdown to the agent's first
 * cycle + a hand-drawn "this is how the app works" strip underneath.
 *
 *   [ ה-21 בחודש ] ──► [ המחשב מוריד ] ──► [ נפרעים + פרודוקציה ] ──► [ ההשוואה מוכנה ]
 *      (read right → left, like the page)
 *
 * - The digits are REAL time: `targetMs - Date.now()` on every frame (a Player,
 *   never rendered to video, so wall-clock reads are fine). The loop only drives
 *   the drawing, so the countdown never "rewinds" at the seam.
 * - Hand-drawn look: every stroke draws on (pathLength=1 dash trick) through an
 *   feTurbulence displacement whose seed "boils" every 4 frames, like a sketch.
 * - Loop-perfect: the strip starts empty at frame 0 and fades back to empty
 *   before the last frame; 240 is a multiple of the 12-frame boil cycle.
 * - Colours come in as props (Remotion can't read CSS variables).
 */
export const CYCLE_COUNTDOWN_FRAMES = 240 // 8s @ 30fps

export type CycleCountdownProps = {
  targetMs: number
  skewMs?: number
  color?: string // tab accent (production cobalt)
  ink?: string
  periodName?: string // "ספטמבר 2026"
  heading?: string // line above the digits
  compact?: boolean // digits only (home card, narrow screens) — composition 800×210
  alignRight?: boolean // RTL page flow: heading + digits hug the right edge
}

const W = 960
const H = 440

function Draw({ d, p, stroke, width = 3.2, fill = 'none' }: { d: string; p: number; stroke: string; width?: number; fill?: string }) {
  const k = Math.max(0, Math.min(1, p))
  return (
    <path
      d={d}
      pathLength={1}
      fill={fill}
      stroke={stroke}
      strokeWidth={width}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeDasharray="1"
      strokeDashoffset={1 - k}
    />
  )
}

const ease = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })

// Station centres, right → left (RTL reading order).
const SX = [820, 600, 370, 140]
const SY = 318

export const CycleCountdown: React.FC<CycleCountdownProps> = ({
  targetMs,
  skewMs = 0,
  color = '#2F73C4',
  ink = '#181818',
  periodName = '',
  heading = 'לשונית הפרודוקציה נפתחת בעוד',
  compact = false,
  alignRight = false,
}) => {
  const frame = useCurrentFrame()

  // ── live countdown ──
  const remaining = Math.max(0, targetMs - (Date.now() + skewMs))
  const totalS = Math.floor(remaining / 1000)
  const units = [
    { v: Math.floor(totalS / 86400), l: 'ימים' },
    { v: Math.floor((totalS % 86400) / 3600), l: 'שעות' },
    { v: Math.floor((totalS % 3600) / 60), l: 'דקות' },
    { v: totalS % 60, l: 'שניות' },
  ]
  const msInSec = remaining % 1000
  const tick = msInSec > 820 ? ((msInSec - 820) / 180) * 0.07 : 0 // bump as the second flips

  // ── strip timeline ──
  const st = (i: number) => ease(frame, 10 + i * 40, 40 + i * 40) // station i draws
  const cn = (i: number) => ease(frame, 36 + i * 40, 56 + i * 40) // connector i→i+1
  const checkP = ease(frame, 168, 184)
  const fade = interpolate(frame, [212, 234], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  const seed = Math.floor(frame / 4) % 3

  const captions = ['ה-21 בחודש · 06:00', 'המחשב מוריד לבד', 'נפרעים + פרודוקציה', 'ההשוואה מוכנה']

  return (
    <AbsoluteFill style={{ fontFamily: 'Heebo, sans-serif' }}>
      {/* countdown */}
      <div style={{ position: 'absolute', top: compact ? 8 : 18, left: 0, right: alignRight ? 24 : 0, textAlign: alignRight ? 'right' : 'center', direction: 'rtl', fontSize: compact ? 30 : 22, fontWeight: 700, color: ink, opacity: 0.6 }}>
        {remaining > 0 ? heading : 'המחזור מתחיל עכשיו…'}
      </div>
      <div style={{ position: 'absolute', top: compact ? 56 : 58, left: 0, right: alignRight ? 6 : 0, display: 'flex', flexDirection: 'row', direction: 'ltr', justifyContent: alignRight ? 'flex-end' : 'center', alignItems: 'flex-start', gap: compact ? 10 : 18 }}>
        {units.map((u, i) => (
          <React.Fragment key={u.l}>
            {i > 0 && <div style={{ fontSize: compact ? 84 : 76, fontWeight: 800, color, opacity: 0.3, lineHeight: compact ? '104px' : '96px' }}>:</div>}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: compact ? 150 : 132 }}>
              <div
                style={{
                  fontSize: compact ? 100 : 88, fontWeight: 900, lineHeight: compact ? '104px' : '96px', color,
                  fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.02em',
                  transform: i === 3 ? `scale(${1 + tick})` : undefined,
                }}
              >
                {String(u.v).padStart(2, '0')}
              </div>
              <div style={{ fontSize: compact ? 28 : 19, fontWeight: 700, color: ink, opacity: 0.55, direction: 'rtl' }}>{u.l}</div>
            </div>
          </React.Fragment>
        ))}
      </div>

      {/* hand-drawn "how it works" strip */}
      {!compact && <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: 'absolute', inset: 0, opacity: fade }}>
        <defs>
          <filter id="cc-sketch" x="-5%" y="-5%" width="110%" height="110%">
            <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed={seed} result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale="3.2" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
        <g filter="url(#cc-sketch)">
          {/* 1 · calendar "21" */}
          <g>
            <Draw p={st(0)} stroke={ink} d={`M${SX[0] - 42} ${SY - 36} h84 a8 8 0 0 1 8 8 v70 a8 8 0 0 1 -8 8 h-84 a8 8 0 0 1 -8 -8 v-70 a8 8 0 0 1 8 -8 z`} />
            <Draw p={st(0)} stroke={ink} d={`M${SX[0] - 50} ${SY - 12} h100`} />
            <Draw p={st(0)} stroke={ink} d={`M${SX[0] - 24} ${SY - 46} v18 M${SX[0] + 24} ${SY - 46} v18`} />
            <text x={SX[0]} y={SY + 34} textAnchor="middle" fontSize="38" fontWeight="900" fill={color} opacity={st(0)}>21</text>
          </g>
          {/* 2 · computer with download arrow */}
          <g>
            <Draw p={st(1)} stroke={ink} d={`M${SX[1] - 54} ${SY - 40} h108 a6 6 0 0 1 6 6 v62 a6 6 0 0 1 -6 6 h-108 a6 6 0 0 1 -6 -6 v-62 a6 6 0 0 1 6 -6 z`} />
            <Draw p={st(1)} stroke={ink} d={`M${SX[1] - 22} ${SY + 52} h44 M${SX[1]} ${SY + 34} v18`} />
            <Draw p={st(1)} stroke={color} width={4} d={`M${SX[1]} ${SY - 26} v34 M${SX[1] - 14} ${SY - 4} l14 14 l14 -14`} />
          </g>
          {/* 3 · two files */}
          <g>
            <Draw p={st(2)} stroke={ink} d={`M${SX[2] - 62} ${SY - 44} h40 l16 16 v70 h-56 z`} />
            <Draw p={st(2)} stroke={ink} d={`M${SX[2] + 6} ${SY - 36} h40 l16 16 v70 h-56 z`} />
            <Draw p={st(2)} stroke={color} width={2.6} d={`M${SX[2] - 52} ${SY - 8} h32 M${SX[2] - 52} ${SY + 6} h26 M${SX[2] - 52} ${SY + 20} h30`} />
            <Draw p={st(2)} stroke={color} width={2.6} d={`M${SX[2] + 16} ${SY} h32 M${SX[2] + 16} ${SY + 14} h26 M${SX[2] + 16} ${SY + 28} h30`} />
          </g>
          {/* 4 · comparison + check */}
          <g>
            <Draw p={st(3)} stroke={ink} d={`M${SX[3] - 50} ${SY + 40} v-40 M${SX[3] - 24} ${SY + 40} v-66 M${SX[3] + 2} ${SY + 40} v-30 M${SX[3] + 28} ${SY + 40} v-54 M${SX[3] - 62} ${SY + 42} h104`} width={5} />
            <circle cx={SX[3] + 48} cy={SY - 40} r={22 * checkP} fill="#2E844A" />
            <Draw p={checkP} stroke="#fff" width={4.5} d={`M${SX[3] + 38} ${SY - 40} l7 7 l13 -14`} />
          </g>
          {/* connectors (right → left) + a traveling dot */}
          {[0, 1, 2].map((i) => {
            const x1 = SX[i] - 78
            const x2 = SX[i + 1] + 84
            const p = cn(i)
            const dotT = ease(frame, 56 + i * 40, 78 + i * 40)
            return (
              <g key={i}>
                <Draw p={p} stroke={color} width={2.6} d={`M${x1} ${SY} C${x1 - 30} ${SY - 22}, ${x2 + 30} ${SY + 22}, ${x2} ${SY}`} />
                <Draw p={p} stroke={color} width={2.6} d={`M${x2 + 12} ${SY - 9} L${x2} ${SY} L${x2 + 12} ${SY + 9}`} />
                {dotT > 0 && dotT < 1 && (
                  <circle cx={x1 + (x2 - x1) * dotT} cy={SY + Math.sin(dotT * Math.PI * 2) * -8} r={6} fill={color} />
                )}
              </g>
            )
          })}
        </g>
        {captions.map((c, i) => (
          <text key={c} x={SX[i]} y={SY + 94} textAnchor="middle" direction="rtl" fontSize="19" fontWeight="700" fill={ink} opacity={0.7 * st(i)}>
            {c}
            {i === 2 && periodName && <tspan x={SX[i]} dy="24" fontWeight="500">{periodName}</tspan>}
          </text>
        ))}
      </svg>}
    </AbsoluteFill>
  )
}

export const CYCLE_COUNTDOWN_SIZE = { width: W, height: H }
export const CYCLE_COUNTDOWN_COMPACT_SIZE = { width: 800, height: 210 }
