import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame, Easing } from 'remotion'

/**
 * Nifra Market's header loop — a risk-level ladder that keeps re-ranking itself.
 *
 *   - nine thin bars (tracks in one risk group) breathe at their own pace, so the order shifts
 *   - one bar is "your customer's track": a filled dot rides its tip and a soft ribbon rises from it
 *     to the leader's height — the yearly gap the studio is about
 *   - a faint baseline grid draws on once
 *
 * Every motion completes whole cycles per LOOP frames, so the loop has no seam. Colour comes from the
 * Vue side (Remotion can't read CSS variables). Decoration stays faint — the numbers below are the point.
 */
export const MARKET_PULSE_W = 560
export const MARKET_PULSE_H = 180
const LOOP = 300
export const MARKET_PULSE_FRAMES = LOOP * 360 // ~1h; the studio never stays open that long

const BARS = 9
const BASE = 150
const GAP = 46
const X0 = 72

export const MarketPulse: React.FC<{ color?: string }> = ({ color = '#5B8DD6' }) => {
  const f = useCurrentFrame()
  const t = (f % LOOP) / LOOP
  const draw = interpolate(f, [0, 40], [0, 1], { extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) })
  const heights = Array.from({ length: BARS }, (_, i) => {
    const base = 46 + ((i * 37) % 70)
    const turns = 1 + (i % 3) // 1–3 whole turns per loop → seamless
    return base + Math.sin(t * Math.PI * 2 * turns + i * 1.7) * 16
  })
  const mine = 6
  const lead = Math.max(...heights)
  const xMine = X0 + mine * GAP
  const yMine = BASE - heights[mine] * draw
  const yLead = BASE - lead * draw
  return (
    <AbsoluteFill style={{ background: 'transparent' }}>
      <svg width={MARKET_PULSE_W} height={MARKET_PULSE_H} viewBox={`0 0 ${MARKET_PULSE_W} ${MARKET_PULSE_H}`}>
        {[0, 1, 2, 3].map((k) => (
          <line key={k} x1={40} x2={40 + 480 * draw} y1={BASE - k * 32} y2={BASE - k * 32}
                stroke={color} strokeOpacity={0.12} strokeWidth={1} />
        ))}
        {heights.map((h, i) => (
          <rect key={i} x={X0 + i * GAP - 9} width={18} y={BASE - h * draw} height={h * draw} rx={9}
                fill={color} fillOpacity={i === mine ? 0.55 : 0.16} />
        ))}
        <rect x={xMine - 2} width={4} y={yLead} height={Math.max(0, yMine - yLead)} rx={2}
              fill={color} fillOpacity={0.35} />
        <line x1={xMine - 30} x2={xMine + 30} y1={yLead} y2={yLead} stroke={color} strokeOpacity={0.45}
              strokeWidth={1.5} strokeDasharray="4 4" />
        <circle cx={xMine} cy={yMine} r={7} fill={color} />
        <circle cx={xMine} cy={yMine} r={7 + 8 * ((t * 3) % 1)} fill="none" stroke={color}
                strokeOpacity={0.4 * (1 - ((t * 3) % 1))} strokeWidth={2} />
      </svg>
    </AbsoluteFill>
  )
}
