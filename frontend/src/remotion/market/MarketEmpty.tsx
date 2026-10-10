import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame, Easing } from 'remotion'

/**
 * Nifra Market's empty state — a ladder of tracks drawn in thin line art while a soft scan line passes over
 * it, looking for the agent's customers. Calm, not a spinner: the bars draw on once, breathe, and the scan
 * repeats every LOOP frames (whole cycles → no seam). `tone` "ok" swaps the scan for a gentle check.
 */
export const MARKET_EMPTY_W = 520
export const MARKET_EMPTY_H = 220
const LOOP = 240
export const MARKET_EMPTY_FRAMES = LOOP * 360

const BARS = [70, 110, 92, 140, 120, 96, 128]

export const MarketEmpty: React.FC<{ color?: string; tone?: 'empty' | 'ok' }> = ({ color = '#5B8DD6', tone = 'empty' }) => {
  const f = useCurrentFrame()
  const t = (f % LOOP) / LOOP
  const draw = interpolate(f, [0, 50], [0, 1], { extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) })
  const scanX = interpolate(t, [0, 1], [70, 450])
  const base = 186
  return (
    <AbsoluteFill style={{ background: 'transparent' }}>
      <svg width={MARKET_EMPTY_W} height={MARKET_EMPTY_H} viewBox={`0 0 ${MARKET_EMPTY_W} ${MARKET_EMPTY_H}`}>
        <defs>
          <linearGradient id="me-scan" x1="0" x2="1">
            <stop offset="0" stopColor={color} stopOpacity="0" />
            <stop offset="0.5" stopColor={color} stopOpacity="0.22" />
            <stop offset="1" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <circle cx={120} cy={70} r={60 + 6 * Math.sin(t * Math.PI * 2)} fill={color} fillOpacity={0.06} />
        <circle cx={410} cy={120} r={74 + 8 * Math.sin(t * Math.PI * 4)} fill={color} fillOpacity={0.05} />
        <line x1={50} x2={50 + 420 * draw} y1={base} y2={base} stroke={color} strokeOpacity={0.35} strokeWidth={1.5} />
        {BARS.map((h, i) => {
          const x = 90 + i * 56
          const hh = h * draw * (1 + 0.05 * Math.sin(t * Math.PI * 2 * (1 + (i % 2)) + i))
          return <rect key={i} x={x - 14} y={base - hh} width={28} height={hh} rx={14} fill="none"
                       stroke={color} strokeOpacity={0.5} strokeWidth={2} />
        })}
        {tone === 'empty' ? (
          <rect x={scanX - 40} y={30} width={80} height={base - 30} fill="url(#me-scan)" />
        ) : (
          <g transform={`translate(${260} ${66})`} opacity={draw}>
            <circle r={26 + 3 * Math.sin(t * Math.PI * 2)} fill={color} fillOpacity={0.14} />
            <path d="M-10 0 L-3 8 L12 -8" fill="none" stroke={color} strokeWidth={4} strokeLinecap="round"
                  strokeLinejoin="round" strokeDasharray={40} strokeDashoffset={40 * (1 - draw)} />
          </g>
        )}
      </svg>
    </AbsoluteFill>
  )
}
