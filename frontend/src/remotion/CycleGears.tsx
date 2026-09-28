import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame, Easing } from 'remotion'

/**
 * "The machine did its part — the next gear is yours", as a hand DRAWING (the
 * same ink line-art as CycleCountdown's strip). Shown in the upload_production
 * cycle notice.
 *
 *   right: the נפרעים gear — ink outline, turning, a green ✓ drawn in its hub
 *   mid:   the agent's production gear — blue outline + upload arrow, floating
 *          above the dashed empty slot it clicks into
 *   left:  the השוואה gear — faint ink, still, waiting for the machine to close
 *
 * Every stroke draws itself on first (pathLength=1 dash trick), then the scene
 * loops seamlessly every LOOP frames (whole turns, whole bob cycles).
 * `celebrate` (the agent's very first cycle): a slower draw, and hand-drawn
 * emphasis strokes burst around the ✓ — no confetti.
 */
export const CYCLE_GEARS_W = 560
export const CYCLE_GEARS_H = 320
const LOOP = 240
const INTRO_PLAIN = 60
const INTRO_CELEBRATE = 110
export const CYCLE_GEARS_FRAMES = INTRO_CELEBRATE + LOOP * 450 // ~1h; the notice never lives that long
export const CYCLE_GEARS_FRAMES_PLAIN = INTRO_PLAIN + LOOP * 450

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
const circle = (r: number) => `M${r} 0 A${r} ${r} 0 1 1 ${-r} 0 A${r} ${r} 0 1 1 ${r} 0`

const T1 = 20, T2 = 14, T3 = 12
const R1 = (MODULE * T1) / 2, R2 = (MODULE * T2) / 2, R3 = (MODULE * T3) / 2
const G1 = { x: 346, y: 150 }
const B1 = Math.PI - 0.62 // G1 → slot: left and down
const SLOT = { x: G1.x + Math.cos(B1) * (R1 + R2), y: G1.y + Math.sin(B1) * (R1 + R2) }
const B2 = Math.PI + 0.55 // slot → G3: left and up
const G3 = { x: SLOT.x + Math.cos(B2) * (R2 + R3), y: SLOT.y + Math.sin(B2) * (R2 + R3) }
const HOVER = 150 // the production gear floats clear of both neighbours
const P1 = gearPath(T1), P2 = gearPath(T2), P3 = gearPath(T3)
const V = TAU / LOOP // G1: one turn per loop

type Props = {
  celebrate?: boolean
  accent?: string // the agent's gear (production blue)
  done?: string // green ✓
  ink?: string
  faint?: string
  labelDone?: string
  labelNext?: string
}

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

function Draw({ d, p, stroke, width = 2.6, dash }: { d: string; p: number; stroke: string; width?: number; dash?: string }) {
  // Dashed strokes can't use the dash trick for drawing → fade them in instead.
  if (dash) {
    return <path d={d} fill="none" stroke={stroke} strokeWidth={width} strokeLinecap="round" strokeDasharray={dash} opacity={p} />
  }
  return (
    <path d={d} pathLength={1} fill="none" stroke={stroke} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round"
      strokeDasharray="1" strokeDashoffset={1 - Math.max(0, Math.min(1, p))} />
  )
}

export const CycleGears: React.FC<Props> = ({
  celebrate = false,
  accent = '#2F73C4',
  done = '#2E844A',
  ink = '#181818',
  faint = '#A9A6A2',
  labelDone = 'נפרעים',
  labelNext = 'השוואה',
}) => {
  const f = useCurrentFrame()
  const INTRO = celebrate ? INTRO_CELEBRATE : INTRO_PLAIN
  const k = INTRO / INTRO_PLAIN // stretch the draw for the celebration
  const inLoop = f >= INTRO
  const lf = inLoop ? (f - INTRO) % LOOP : 0
  const t = lf / LOOP

  const seg = (a: number, b: number) => interpolate(f, [a * k, b * k], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) })
  const pG1 = seg(0, 22)
  const pG3 = seg(8, 26)
  const pSlot = seg(14, 30)
  const pG2 = seg(20, 42)
  const pCheck = seg(38, 52)
  const pLabels = seg(30, 46)
  const pPath = seg(40, 58)

  // G1 spins up over the last 30 intro frames (quadratic), then turns at V.
  const SPIN = 30
  const a1 = !inLoop
    ? f < INTRO - SPIN ? 0 : (V * (f - (INTRO - SPIN)) ** 2) / (2 * SPIN)
    : (V * SPIN) / 2 + lf * V

  // production gear bobs 2x per loop and rocks gently once per loop
  const bob = inLoop ? Math.sin(t * TAU * 2) * 5 : 0
  const rock = inLoop ? Math.sin(t * TAU) * 7 : 0
  const g2 = { x: SLOT.x, y: SLOT.y - HOVER + bob }

  // the נפרעים sheet drifts from G1 to the floating gear, every loop
  const from = [G1.x - R1 * 0.45, G1.y - R1 - 12], to = [SLOT.x + R2 + 14, SLOT.y - HOVER + 6]
  const ctrl = [(from[0] + to[0]) / 2, Math.min(from[1], to[1]) - 24]
  const dT = interpolate(lf, [30, 130], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) })
  const dOp = inLoop ? interpolate(lf, [24, 38, 118, 136], [0, 1, 1, 0], clamp) : 0
  const qb = (s: number, i: 0 | 1) => (1 - s) ** 2 * from[i] + 2 * (1 - s) * s * ctrl[i] + s ** 2 * to[i]

  // celebration: hand-drawn emphasis strokes burst out around the ✓ once
  const burst = !celebrate
    ? 0
    : inLoop
      ? f - INTRO < LOOP ? interpolate(lf, [0, 26, 60], [1, 1, 0], clamp) : 0
      : interpolate(f, [52 * k, 70 * k], [0, 1], clamp)
  const BURST = [-150, -118, -86, -54, -22, 12, 44].map((deg) => (deg * Math.PI) / 180)

  return (
    <AbsoluteFill style={{ fontFamily: 'Heebo, sans-serif' }}>
      <svg width={CYCLE_GEARS_W} height={CYCLE_GEARS_H} viewBox={`0 0 ${CYCLE_GEARS_W} ${CYCLE_GEARS_H}`}>
        {/* dotted route the נפרעים take */}
        <Draw d={`M${from[0]} ${from[1]} Q ${ctrl[0]} ${ctrl[1]} ${to[0]} ${to[1]}`} p={pPath} stroke={accent} width={2} dash="2 9" />

        {/* השוואה gear — faint, still */}
        <g transform={`translate(${G3.x} ${G3.y})`}>
          <Draw d={P3} p={pG3} stroke={faint} width={2.2} />
          <Draw d={circle(R3 * 0.42)} p={pG3} stroke={faint} width={2.2} />
          <Draw d="M-7 -3 h14 l-4 -4 M7 4 h-14 l4 4" p={pG3} stroke={faint} width={2} />
        </g>

        {/* the empty slot the agent's gear clicks into */}
        <g transform={`translate(${SLOT.x} ${SLOT.y})`}>
          <Draw d={circle(R2 + MODULE * 0.9)} p={pSlot} stroke={accent} width={2} dash="5 8" />
        </g>

        {/* נפרעים gear — ink, turning, ✓ drawn in the hub */}
        <g transform={`translate(${G1.x} ${G1.y})`}>
          <g transform={`rotate(${(a1 * 180) / Math.PI})`}>
            <Draw d={P1} p={pG1} stroke={ink} width={2.6} />
            <Draw
              d={[0, 1, 2, 3, 4].map((i) => {
                const c = Math.cos((i * TAU) / 5), s = Math.sin((i * TAU) / 5)
                return `M${(c * R1 * 0.42).toFixed(1)} ${(s * R1 * 0.42).toFixed(1)} L${(c * R1 * 0.74).toFixed(1)} ${(s * R1 * 0.74).toFixed(1)}`
              }).join(' ')}
              p={pG1} stroke={ink} width={2}
            />
          </g>
          <Draw d={circle(R1 * 0.42)} p={pG1} stroke={ink} width={2.6} />
          <Draw d="M-11 1 l7 7 l15 -16" p={pCheck} stroke={done} width={4.2} />
          {celebrate && BURST.map((a, i) => {
            const r0 = R1 + 16, r1 = R1 + 30 + (i % 2) * 8
            return (
              <Draw key={i} p={burst} stroke={done} width={2.6}
                d={`M${(Math.cos(a) * r0).toFixed(1)} ${(Math.sin(a) * r0).toFixed(1)} L${(Math.cos(a) * r1).toFixed(1)} ${(Math.sin(a) * r1).toFixed(1)}`} />
            )
          })}
        </g>

        {/* the agent's production gear, floating above its slot */}
        <g transform={`translate(${g2.x} ${g2.y})`}>
          <g transform={`rotate(${rock})`}>
            <Draw d={P2} p={pG2} stroke={accent} width={2.8} />
          </g>
          <Draw d={circle(R2 * 0.44)} p={pG2} stroke={accent} width={2.6} />
          <Draw d="M0 8 V-8 M-7 -1 L0 -8 L7 -1" p={pG2} stroke={accent} width={3} />
          {/* motion ticks under it: it floats, it isn't fixed yet */}
          <Draw d={`M-16 ${R2 + 16} h10 M6 ${R2 + 16} h10`} p={pG2} stroke={accent} width={2} />
        </g>

        {/* the travelling נפרעים sheet, in ink */}
        <g opacity={dOp} transform={`translate(${qb(dT, 0)} ${qb(dT, 1)}) rotate(${(1 - dT) * 10})`}>
          <path d="M-10 -13 h13 l7 7 v19 h-20 z M3 -13 v7 h7" fill="#fff" stroke={ink} strokeWidth={2} strokeLinejoin="round" />
          <path d="M-5 0 h10 M-5 5 h8" stroke={done} strokeWidth={1.8} strokeLinecap="round" />
        </g>

        {/* labels — well below the drawings */}
        <g style={{ direction: 'rtl' }} fontSize={15} fontWeight={700} textAnchor="middle" opacity={pLabels}>
          <text x={G1.x + 6} y={G1.y + R1 + 50} fill={ink}>{labelDone}</text>
          <text x={G3.x - 12} y={G3.y + R3 + 46} fill={faint}>{labelNext}</text>
        </g>
      </svg>
    </AbsoluteFill>
  )
}
