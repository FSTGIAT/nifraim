import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'

/**
 * Background of the מסלקה tab, in the family of the automation gears and the
 * portal connections: the insurers (small buildings, left) send their files
 * along faint dashed lines into the clearinghouse (a breathing vault, centre),
 * which hands each one on to the agent's file (right), where it settles onto a
 * slowly growing stack of monthly pages. Calm on purpose: one document in
 * flight per line, long gaps, stroke ≈0.16 / fill ≤0.06.
 *
 * Laid out for RTL reading and for the page's cards covering the top: the
 * action sits mostly in the lower half.
 *
 * Loop-perfect: 1800 frames; every line's cycle is 600 frames (divides 1800),
 * the vault breathes 3× and the stack pulses 3× per loop.
 */
export const MASLAKA_BG_FRAMES = 1800 // 60s @ 30fps
export const MASLAKA_BG_W = 1600
export const MASLAKA_BG_H = 900

const TAU = Math.PI * 2
const CYCLE = 600   // frames per line cycle (20s)
const LEG1 = 130    // insurer → vault
const HOLD = 40     // a beat inside the vault
const LEG2 = 110    // vault → the agent's file

// The page's cards cover the top ~80%, so the scene lives in the bottom band.
const VAULT = { x: 860, y: 815 }
const FILE = { x: 1380, y: 800 }
const BODIES = [
  { x: 110, y: 830, delay: 0 },
  { x: 250, y: 760, delay: 100 },
  { x: 390, y: 845, delay: 200 },
  { x: 520, y: 770, delay: 300 },
  { x: 640, y: 860, delay: 400 },
  { x: 1120, y: 865, delay: 500 },
]

const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)

function curve(a: { x: number; y: number }, b: { x: number; y: number }, bow: number) {
  return { x: (a.x + b.x) / 2, y: Math.min(a.y, b.y) - bow }
}
function at(a: { x: number; y: number }, b: { x: number; y: number }, k: { x: number; y: number }, t: number) {
  const u = 1 - t
  return { x: u * u * a.x + 2 * u * t * k.x + t * t * b.x, y: u * u * a.y + 2 * u * t * k.y + t * t * b.y }
}

// An insurer: a small classical building (pediment + three columns + base).
const Building: React.FC<{ x: number; y: number; color: string; glow: number }> = ({ x, y, color, glow }) => (
  <g stroke={color} strokeOpacity={0.22 + glow * 0.3} strokeWidth={2} fill="none" strokeLinejoin="round">
    <circle cx={x} cy={y} r={34 + glow * 10} fill={color} fillOpacity={0.035 + glow * 0.06} stroke="none" />
    <path d={`M${x - 22},${y - 8} L${x},${y - 22} L${x + 22},${y - 8} Z`} />
    {[-14, 0, 14].map((dx) => <line key={dx} x1={x + dx} y1={y - 5} x2={x + dx} y2={y + 12} />)}
    <line x1={x - 24} y1={y + 15} x2={x + 24} y2={y + 15} />
  </g>
)

// A document: a page with a folded corner and two text lines.
const Doc: React.FC<{ x: number; y: number; s: number; color: string; ink: string; opacity: number }> = ({ x, y, s, color, ink, opacity }) => (
  <g opacity={opacity} transform={`translate(${x},${y}) scale(${s})`}>
    <path d="M-8,-11 L4,-11 L9,-6 L9,11 L-8,11 Z" fill={color} fillOpacity={0.08} stroke={ink} strokeWidth={1.4} />
    <path d="M4,-11 L4,-6 L9,-6" fill="none" stroke={ink} strokeWidth={1.2} />
    <line x1={-4} y1={-1} x2={5} y2={-1} stroke={color} strokeWidth={1.4} />
    <line x1={-4} y1={4} x2={3} y2={4} stroke={color} strokeWidth={1.4} />
  </g>
)

type Props = { color?: string; ink?: string }

export const MaslakaBackdrop: React.FC<Props> = ({ color = '#2C5F6B', ink = '#2C5F6B' }) => {
  const frame = useCurrentFrame() % MASLAKA_BG_FRAMES
  const breathe = 0.5 + 0.5 * Math.sin((frame / MASLAKA_BG_FRAMES) * TAU * 3)
  const k2 = curve(VAULT, FILE, 90)
  // the stack takes a small hop each time a document lands
  let land = 0

  const lines = BODIES.map((b, i) => {
    const k1 = curve(b, VAULT, 110 + (i % 3) * 30)
    const local = (frame - b.delay + MASLAKA_BG_FRAMES) % CYCLE
    const sent = local < 24 ? 1 - local / 24 : 0
    let pulse: React.ReactNode = null
    if (local < LEG1) {
      const p = at(b, VAULT, k1, ease(local / LEG1))
      pulse = <Doc x={p.x} y={p.y} s={1.1} color={color} ink={ink} opacity={Math.min(1, local / 18) * 0.6} />
    } else if (local >= LEG1 + HOLD && local < LEG1 + HOLD + LEG2) {
      const t = (local - LEG1 - HOLD) / LEG2
      const p = at(VAULT, FILE, k2, ease(t))
      pulse = <Doc x={p.x} y={p.y} s={1.1} color={color} ink={ink} opacity={0.6} />
    } else if (local >= LEG1 + HOLD + LEG2 && local < LEG1 + HOLD + LEG2 + 30) {
      land = Math.max(land, 1 - (local - LEG1 - HOLD - LEG2) / 30)
    }
    return (
      <g key={i}>
        <path d={`M${b.x},${b.y} Q${k1.x},${k1.y} ${VAULT.x},${VAULT.y}`} fill="none" stroke={color}
              strokeOpacity={0.14} strokeWidth={1.6} strokeDasharray="2 8" strokeLinecap="round" />
        <Building x={b.x} y={b.y} color={color} glow={sent} />
        {pulse}
      </g>
    )
  })

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent' }}>
      <svg width={MASLAKA_BG_W} height={MASLAKA_BG_H} viewBox={`0 0 ${MASLAKA_BG_W} ${MASLAKA_BG_H}`}>
        {/* vault → the agent's file */}
        <path d={`M${VAULT.x},${VAULT.y} Q${k2.x},${k2.y} ${FILE.x},${FILE.y}`} fill="none" stroke={color}
              strokeOpacity={0.16} strokeWidth={2} strokeDasharray="2 8" strokeLinecap="round" />
        {lines}

        {/* the clearinghouse: a breathing vault (ring + dial + spokes) */}
        <circle cx={VAULT.x} cy={VAULT.y} r={88 + breathe * 12} fill={color} fillOpacity={0.04 + breathe * 0.025} />
        <g stroke={color} fill="none" strokeOpacity={0.3}>
          <rect x={VAULT.x - 52} y={VAULT.y - 52} width={104} height={104} rx={14} fill={color} fillOpacity={0.05} strokeWidth={2.2} />
          <circle cx={VAULT.x} cy={VAULT.y} r={26} strokeWidth={2} />
          <g transform={`rotate(${(frame / MASLAKA_BG_FRAMES) * 360} ${VAULT.x} ${VAULT.y})`}>
            {[0, 60, 120, 180, 240, 300].map((a) => (
              <line key={a} x1={VAULT.x} y1={VAULT.y} x2={VAULT.x + 22 * Math.cos((a * Math.PI) / 180)}
                    y2={VAULT.y + 22 * Math.sin((a * Math.PI) / 180)} strokeWidth={1.8} />
            ))}
          </g>
          <circle cx={VAULT.x} cy={VAULT.y} r={5} fill={color} fillOpacity={0.35} stroke="none" />
        </g>

        {/* the agent's file: monthly pages settling onto a stack */}
        <g transform={`translate(0, ${-land * 6})`}>
          {[3, 2, 1, 0].map((n) => (
            <g key={n} transform={`translate(${FILE.x + n * 7}, ${FILE.y + n * 7})`}>
              <rect x={-46} y={-60} width={92} height={120} rx={8} fill={color} fillOpacity={0.05}
                    stroke={color} strokeOpacity={0.18 + (n === 0 ? 0.14 + land * 0.2 : 0)} strokeWidth={2} />
              {n === 0 && [-26, -12, 2, 16, 30].map((ly, j) => (
                <line key={ly} x1={-24} y1={ly} x2={j % 2 ? 10 : 22} y2={ly} stroke={color} strokeOpacity={0.22} strokeWidth={3} strokeLinecap="round" />
              ))}
            </g>
          ))}
        </g>
      </svg>
    </AbsoluteFill>
  )
}
