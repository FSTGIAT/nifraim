import React from 'react'
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion'

/**
 * Big, very faint backdrop behind the Production sub-screens (like the
 * automation tab's gears). One slow scene per sub-screen, in the tab colour:
 *
 *   compare — two giant sheets; rows drift from last month's into this month's
 *   volume  — giant bars climbing to a dashed target line, a coin at the top
 *   history — a giant month rail; calendar pages settle onto it in turn
 *
 * Kept at stroke ≈0.12 / fill ≈0.035 so the cards on top stay primary.
 * Loop-perfect over PRODUCTION_BACKDROP_FRAMES (every motion whole cycles).
 */
export const PRODUCTION_BACKDROP_FRAMES = 1200 // 40s @ 30fps — slow on purpose
export const PRODUCTION_BACKDROP_W = 1600
export const PRODUCTION_BACKDROP_H = 1000

type Props = { variant?: 'compare' | 'volume' | 'history'; color?: string }

const TAU = Math.PI * 2
const S_OP = 0.16 // stroke opacity
const F_OP = 0.045 // fill opacity

export const ProductionBackdrop: React.FC<Props> = ({ variant = 'compare', color = '#2F73C4' }) => {
  const frame = useCurrentFrame()
  const t = (frame % PRODUCTION_BACKDROP_FRAMES) / PRODUCTION_BACKDROP_FRAMES // 0..1
  const stroke = { stroke: color, strokeOpacity: S_OP, strokeWidth: 4, fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }

  if (variant === 'volume') {
    const H = [260, 380, 470, 560, 660]
    return (
      <AbsoluteFill>
        <svg width={PRODUCTION_BACKDROP_W} height={PRODUCTION_BACKDROP_H} viewBox={`0 0 ${PRODUCTION_BACKDROP_W} ${PRODUCTION_BACKDROP_H}`}>
          <line x1={120} y1={900} x2={1480} y2={900} {...stroke} strokeWidth={6} />
          <line x1={120} y1={900 - 600} x2={1480} y2={900 - 600} {...stroke} strokeDasharray="22 26" strokeDashoffset={-t * 480 * 2} />
          {H.map((h, i) => {
            // each bar breathes up and down twice per loop, staggered
            const k = 0.72 + 0.28 * Math.sin(t * TAU * 2 + i * 0.9)
            const bh = h * k
            return (
              <rect key={i} x={220 + i * 240} y={900 - bh} width={150} height={bh} rx={26}
                fill={color} fillOpacity={F_OP + i * 0.006} stroke={color} strokeOpacity={S_OP} strokeWidth={4} />
            )
          })}
          <g transform={`translate(1380 ${220 + Math.sin(t * TAU) * 24})`}>
            <circle r={90} fill={color} fillOpacity={F_OP} {...{ stroke: color, strokeOpacity: S_OP, strokeWidth: 4 }} />
            <circle r={62} {...stroke} />
            <path d="M-18 -30 h26 a18 18 0 0 1 0 36 h-18 a18 18 0 0 0 0 36 h26 M0 -48 v18 M0 42 v18" {...stroke} strokeWidth={8} />
          </g>
        </svg>
      </AbsoluteFill>
    )
  }

  if (variant === 'history') {
    const X = [160, 480, 800, 1120, 1440]
    const lift = (i: number) => {
      const ph = (t * 2 + i / X.length) % 1 // two passes along the rail per loop
      return interpolate(ph, [0, 0.25, 0.75, 1], [0, 1, 1, 0], { easing: Easing.inOut(Easing.cubic) })
    }
    return (
      <AbsoluteFill>
        <svg width={PRODUCTION_BACKDROP_W} height={PRODUCTION_BACKDROP_H} viewBox={`0 0 ${PRODUCTION_BACKDROP_W} ${PRODUCTION_BACKDROP_H}`}>
          <line x1={60} y1={930} x2={1540} y2={930} {...stroke} strokeWidth={8} />
          {X.map((x, i) => {
            const k = lift(i)
            return (
              <g key={i}>
                <circle cx={x} cy={930} r={22} fill={color} fillOpacity={F_OP * 2} stroke={color} strokeOpacity={S_OP} strokeWidth={4} />
                {/* calendar page hovering over its month */}
                <g transform={`translate(${x - 110} ${630 - k * 50})`} opacity={0.55 + 0.45 * k}>
                  <rect width={220} height={240} rx={28} fill={color} fillOpacity={F_OP} stroke={color} strokeOpacity={S_OP} strokeWidth={4} />
                  <line x1={0} y1={70} x2={220} y2={70} {...stroke} />
                  <line x1={60} y1={-18} x2={60} y2={30} {...stroke} strokeWidth={8} />
                  <line x1={160} y1={-18} x2={160} y2={30} {...stroke} strokeWidth={8} />
                  {[0, 1, 2].map((r) => [0, 1, 2, 3].map((c) => (
                    <rect key={`${r}${c}`} x={28 + c * 44} y={100 + r * 42} width={28} height={22} rx={6} fill={color} fillOpacity={F_OP * 1.6} />
                  )))}
                </g>
              </g>
            )
          })}
          {/* the clock, far corner */}
          <g transform="translate(1500 330)">
            <circle r={120} {...stroke} />
            <line x1={0} y1={0} x2={0} y2={-80} {...stroke} strokeWidth={8} transform={`rotate(${t * 360 * 4})`} />
            <line x1={0} y1={0} x2={56} y2={0} {...stroke} strokeWidth={8} transform={`rotate(${t * 360})`} />
          </g>
        </svg>
      </AbsoluteFill>
    )
  }

  // compare: two giant sheets and rows drifting between them
  const ROWS = 7
  return (
    <AbsoluteFill>
      <svg width={PRODUCTION_BACKDROP_W} height={PRODUCTION_BACKDROP_H} viewBox={`0 0 ${PRODUCTION_BACKDROP_W} ${PRODUCTION_BACKDROP_H}`}>
        {[{ x: 150, fill: F_OP * 1.4 }, { x: 930, fill: F_OP * 0.7 }].map((sh, i) => (
          <g key={i} transform={`translate(${sh.x} 150)`}>
            <rect width={520} height={720} rx={44} fill={color} fillOpacity={sh.fill} stroke={color} strokeOpacity={S_OP} strokeWidth={4} />
            <rect width={520} height={90} rx={44} fill={color} fillOpacity={sh.fill * 2} />
            {Array.from({ length: ROWS }, (_, r) => (
              <rect key={r} x={50} y={140 + r * 80} width={i ? 300 : 380} height={30} rx={15} fill={color} fillOpacity={F_OP * 1.8} />
            ))}
          </g>
        ))}
        {/* rows travelling from last month (right) to this month (left), 3 per loop, staggered */}
        {[0, 1, 2].map((n) => {
          const ph = (t * 3 + n / 3) % 1
          const k = interpolate(ph, [0.1, 0.6], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) })
          const op = interpolate(ph, [0.05, 0.15, 0.6, 0.75], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
          const y = 290 + n * 160
          return (
            <rect key={n} x={interpolate(k, [0, 1], [980, 200])} y={y + Math.sin(k * Math.PI) * -60} width={320} height={34} rx={17}
              fill={color} fillOpacity={F_OP * 3} stroke={color} strokeOpacity={S_OP} strokeWidth={3} opacity={op} />
          )
        })}
        <path d="M880 500 H720 M760 460 L720 500 L760 540" {...stroke} strokeWidth={8} />
      </svg>
    </AbsoluteFill>
  )
}
