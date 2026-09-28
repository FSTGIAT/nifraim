import React from 'react'
import { AbsoluteFill, interpolate, spring, useCurrentFrame, Easing } from 'remotion'

/**
 * "The machine did its part — the next gear is yours." Shown in the cycle
 * notification when the month's נפרעים are in and production is still missing.
 *
 *   (right) נפרעים gear — green, turning, ✓ in the hub
 *   (mid)   the agent's production gear — hovers ABOVE its slot, upload arrow,
 *           a dashed ghost marks where it clicks in
 *   (left)  השוואה gear — grey, still, waiting for the machine to close
 *
 * `celebrate` (the agent's very first cycle) prepends an assembly intro: the
 * נפרעים gear drops in and lands with a ripple, the slot draws itself, the
 * production gear flies in, the first gear spins up and a light sweep crowns it
 * with the ✓. No confetti — the celebration IS the machine coming together.
 *
 * After the intro the scene loops seamlessly every LOOP frames (whole turns,
 * whole bob cycles). The Player's duration is very long so the intro plays once.
 */
export const CYCLE_GEARS_W = 560
export const CYCLE_GEARS_H = 320
const LOOP = 240
const INTRO = 96
export const CYCLE_GEARS_FRAMES = INTRO + LOOP * 450 // ~1h; the modal never lives that long
export const CYCLE_GEARS_FRAMES_PLAIN = LOOP * 450

const TAU = Math.PI * 2
const MODULE = 6

function gearPath(teeth: number): string {
  const r = (MODULE * teeth) / 2
  const tip = r + MODULE * 0.9
  const root = r - MODULE * 1.1
  const p = TAU / teeth
  const pts: string[] = []
  const at = (ang: number, rad: number) => `${(Math.cos(ang) * rad).toFixed(2)},${(Math.sin(ang) * rad).toFixed(2)}`
  for (let k = 0; k < teeth; k++) {
    const a = k * p
    pts.push(at(a - p * 0.28, root), at(a - p * 0.14, tip), at(a + p * 0.14, tip), at(a + p * 0.28, root))
  }
  return `M${pts.join('L')}Z`
}

const T1 = 20, T2 = 14, T3 = 12
const R1 = (MODULE * T1) / 2, R2 = (MODULE * T2) / 2, R3 = (MODULE * T3) / 2
const G1 = { x: 346, y: 160 }
const B1 = Math.PI - 0.62 // G1 → slot: left and down
const SLOT = { x: G1.x + Math.cos(B1) * (R1 + R2), y: G1.y + Math.sin(B1) * (R1 + R2) }
const B2 = Math.PI + 0.55 // slot → G3: left and up
const G3 = { x: SLOT.x + Math.cos(B2) * (R2 + R3), y: SLOT.y + Math.sin(B2) * (R2 + R3) }
const HOVER = 150 // how far the production gear floats above its slot (clears both neighbours)
const P1 = gearPath(T1), P2 = gearPath(T2), P3 = gearPath(T3)
const V = TAU / LOOP // G1 angular speed in the loop: one turn per loop

type Props = {
  celebrate?: boolean
  accent?: string // the agent's gear (production blue)
  done?: string // green
  idle?: string
  ink?: string
  labelDone?: string
  labelNow?: string
  labelNext?: string
}

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

const Hub: React.FC<{ r: number; color: string; children?: React.ReactNode }> = ({ r, color, children }) => (
  <>
    <circle r={r * 0.46} fill="#fff" stroke={color} strokeWidth={2.4} />
    {children}
  </>
)

export const CycleGears: React.FC<Props> = ({
  celebrate = false,
  accent = '#2F73C4',
  done = '#2E844A',
  idle = '#B7B4B0',
  ink = '#181818',
  labelDone = 'נפרעים',
  labelNow = 'הפרודוקציה שלך',
  labelNext = 'השוואה',
}) => {
  const frame = useCurrentFrame()
  const intro = celebrate ? INTRO : 0
  const f = frame // absolute frame
  const lf = Math.max(0, f - intro) % LOOP // loop frame
  const inLoop = f >= intro

  // ── intro choreography (only when celebrate) ──
  const s1 = celebrate ? spring({ frame: f, fps: 30, config: { damping: 11, stiffness: 120 } }) : 1
  const g1Drop = interpolate(s1, [0, 1], [-190, 0])
  const land = celebrate ? interpolate(f, [16, 44], [0, 1], clamp) : 1
  const ghostDraw = celebrate ? interpolate(f, [22, 46], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) }) : 1
  const g3In = celebrate ? interpolate(f, [26, 44], [0, 1], clamp) : 1
  const s2 = celebrate ? spring({ frame: f - 34, fps: 30, config: { damping: 13, stiffness: 90 } }) : 1
  const sweep = celebrate ? interpolate(f, [60, 88], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) }) : 1
  const sweepOp = celebrate ? interpolate(f, [60, 66, 84, 96], [0, 1, 1, 0], clamp) : 0
  const checkPop = celebrate ? spring({ frame: f - 70, fps: 30, config: { damping: 9, stiffness: 160 } }) : 1

  // G1 angle: quadratic spin-up over [56, 96] then constant V (C1-continuous).
  const SPIN_START = 56
  const spinUp = INTRO - SPIN_START
  let a1: number
  if (!celebrate) a1 = lf * V
  else if (!inLoop) a1 = f < SPIN_START ? 0 : (V * (f - SPIN_START) ** 2) / (2 * spinUp)
  else a1 = (V * spinUp) / 2 + lf * V

  // production gear: flies in from the top-left, then bobs (2 cycles/loop)
  const t = lf / LOOP
  const bob = inLoop ? Math.sin(t * TAU * 2) * 6 : 0
  const g2x = interpolate(s2, [0, 1], [SLOT.x - 170, SLOT.x])
  const g2y = interpolate(s2, [0, 1], [-80, SLOT.y - HOVER]) + bob
  const g2rot = inLoop ? Math.sin(t * TAU) * 6 : interpolate(s2, [0, 1], [-120, 0])
  const pulse = inLoop ? (Math.sin(t * TAU * 2 - Math.PI / 2) + 1) / 2 : 0

  // a נפרעים "sheet" drifts from G1 to the hovering gear each loop
  const dT = interpolate(lf, [30, 120], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) })
  const dOp = inLoop ? interpolate(lf, [24, 36, 112, 128], [0, 1, 1, 0], clamp) : 0
  const from = [G1.x - R1 * 0.45, G1.y - R1 - 10], to = [SLOT.x + R2 + 10, SLOT.y - HOVER + 4]
  const ctrl = [(from[0] + to[0]) / 2, Math.min(from[1], to[1]) - 22]
  const qb = (k: number, i: 0 | 1) => (1 - k) ** 2 * from[i] + 2 * (1 - k) * k * ctrl[i] + k ** 2 * to[i]

  const ripple = celebrate ? interpolate(f, [16, 46], [0, 1], clamp) : 1

  return (
    <AbsoluteFill style={{ fontFamily: 'Heebo, sans-serif' }}>
      <svg width={CYCLE_GEARS_W} height={CYCLE_GEARS_H} viewBox={`0 0 ${CYCLE_GEARS_W} ${CYCLE_GEARS_H}`}>
        <defs>
          <radialGradient id="cg-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={accent} stopOpacity={0.22} />
            <stop offset="100%" stopColor={accent} stopOpacity={0} />
          </radialGradient>
        </defs>

        {/* dotted path the נפרעים travel along */}
        <path
          d={`M${from[0]} ${from[1]} Q ${ctrl[0]} ${ctrl[1]} ${to[0]} ${to[1]}`}
          fill="none" stroke={accent} strokeOpacity={0.28 * g3In} strokeWidth={2} strokeDasharray="3 8"
          strokeDashoffset={-lf * 0.55}
        />

        {/* G3 — השוואה, waits */}
        <g opacity={g3In} transform={`translate(${G3.x} ${G3.y})`}>
          <path d={P3} fill="#fff" stroke={idle} strokeWidth={2.2} strokeLinejoin="round" />
          <Hub r={R3} color={idle}>
            <path d="M-6 -3 h12 l-3 -3 M6 3 h-12 l3 3" stroke={idle} strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </Hub>
        </g>

        {/* the empty slot the agent's gear clicks into */}
        <g transform={`translate(${SLOT.x} ${SLOT.y})`}>
          <circle
            r={R2 + MODULE * 0.9} fill={accent} fillOpacity={0.05} stroke={accent} strokeOpacity={0.55}
            strokeWidth={2} strokeDasharray="6 7" pathLength={100}
            strokeDashoffset={inLoop ? -lf * (13 / LOOP) * 4 : 0}
            style={{ strokeDasharray: ghostDraw < 1 ? `${ghostDraw * 100} 100` : '6 7' }}
          />
        </g>

        {/* G1 — נפרעים, done and turning */}
        <g transform={`translate(${G1.x} ${G1.y + g1Drop})`}>
          <circle r={R1 + 16 + ripple * 34} fill="none" stroke={done} strokeOpacity={(1 - ripple) * 0.5} strokeWidth={3} />
          <g transform={`rotate(${(a1 * 180) / Math.PI})`}>
            <path d={P1} fill={done} fillOpacity={0.12 + 0.1 * land} stroke={done} strokeWidth={2.4} strokeLinejoin="round" />
            {[0, 1, 2, 3, 4].map((k) => (
              <line key={k} x1={0} y1={0} x2={Math.cos((k * TAU) / 5) * R1 * 0.72} y2={Math.sin((k * TAU) / 5) * R1 * 0.72}
                stroke={done} strokeOpacity={0.35} strokeWidth={2} />
            ))}
          </g>
          {/* light sweep crowning the first cycle */}
          <circle r={R1 + 12} fill="none" stroke={done} strokeWidth={3.5} strokeLinecap="round" pathLength={100}
            strokeDasharray={`${sweep * 100} 100`} opacity={sweepOp} transform="rotate(-90)" />
          <g transform={`scale(${checkPop})`}>
            <circle r={R1 * 0.46} fill={done} />
            <path d="M-9 0 l6 6 l12 -13" stroke="#fff" strokeWidth={4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </g>
        </g>

        {/* the agent's production gear, hovering above its slot */}
        <g transform={`translate(${g2x} ${g2y})`}>
          <circle r={R2 + 30} fill="url(#cg-glow)" opacity={0.6 + pulse * 0.4} />
          <circle r={R2 + 9 + pulse * 8} fill="none" stroke={accent} strokeOpacity={0.35 * (1 - pulse)} strokeWidth={2} />
          <g transform={`rotate(${g2rot})`}>
            <path d={P2} fill={accent} stroke={accent} strokeWidth={2} strokeLinejoin="round" />
          </g>
          <Hub r={R2} color={accent}>
            <path d="M0 7 V-7 M-6 -1 L0 -7 L6 -1" stroke={accent} strokeWidth={2.8} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </Hub>
        </g>

        {/* the travelling נפרעים sheet */}
        <g opacity={dOp} transform={`translate(${qb(dT, 0)} ${qb(dT, 1)}) rotate(${(1 - dT) * 10})`}>
          <path d="M-10 -13 h13 l7 7 v19 h-20 z" fill="#fff" stroke={done} strokeWidth={2} strokeLinejoin="round" />
          <path d="M-5 -1 h10 M-5 4 h8" stroke={done} strokeWidth={1.8} strokeLinecap="round" />
        </g>

        {/* labels */}
        <g style={{ direction: 'rtl' }} fontSize={15} fontWeight={800} textAnchor="middle">
          <text x={G1.x} y={G1.y + R1 + 34} fill={ink} opacity={land}>{labelDone}</text>
          <text x={SLOT.x} y={SLOT.y + R2 + 34} fill={accent} opacity={inLoop ? 1 : s2}>{labelNow}</text>
          <text x={G3.x - 10} y={G3.y + R3 + 34} fill={idle} opacity={g3In}>{labelNext}</text>
        </g>
      </svg>
    </AbsoluteFill>
  )
}
