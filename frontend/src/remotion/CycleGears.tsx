import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame, Easing } from 'remotion'

/**
 * ONE big hand-drawn gear that is missing ONE tooth — the agent's production.
 * Shown in the upload_production cycle notice (same ink line-art as
 * CycleCountdown's strip).
 *
 *   - the gear's hub carries a green ✓ (the month's נפרעים are in)
 *   - an inner ring is drawn almost all the way round in green; the stretch
 *     under the gap stays blue and dashed — the month closes except your part
 *   - the missing tooth floats above the gap, blue, with an upload arrow
 *   - the gear keeps TRYING to turn: it creeps forward, catches on the gap and
 *     snaps back — it needs that tooth
 *
 * Every stroke draws itself on first (pathLength=1 dash trick), then the scene
 * loops seamlessly every LOOP frames. `celebrate` (the agent's very first
 * cycle): a slower draw and hand-drawn emphasis strokes burst around the gear
 * once — no confetti.
 */
export const CYCLE_GEARS_W = 560
export const CYCLE_GEARS_H = 320
const LOOP = 240
const DRAW = 64 // the plain draw-on length the stroke timings are written against
const SPIN_FRAMES = 90 // opening spin: fast, easing to a stop over 3s
const SPIN_TURNS = 3 // whole turns, so the gap ends back at the top
const INTRO_PLAIN = SPIN_FRAMES
const INTRO_CELEBRATE = 112
export const CYCLE_GEARS_FRAMES = INTRO_CELEBRATE + LOOP * 450 // ~1h; the notice never lives that long
export const CYCLE_GEARS_FRAMES_PLAIN = INTRO_PLAIN + LOOP * 450

const TAU = Math.PI * 2
const C = { x: 280, y: 192 }
const TEETH = 12
const R = 96 // pitch radius
const TIP = R + 28
const ROOT = R - 8
const PITCH = TAU / TEETH
const GAP_ANGLE = -Math.PI / 2 // the missing tooth is at the top
const GAP_K = Math.round(((GAP_ANGLE + TAU) % TAU) / PITCH)

const at = (ang: number, rad: number) => `${(Math.cos(ang) * rad).toFixed(2)},${(Math.sin(ang) * rad).toFixed(2)}`

// The gear outline with tooth GAP_K left out (just the root line there).
const GEAR = (() => {
  const pts: string[] = []
  for (let k = 0; k < TEETH; k++) {
    const a = k * PITCH
    if (k === GAP_K) pts.push(at(a - PITCH * 0.3, ROOT), at(a + PITCH * 0.3, ROOT))
    else pts.push(at(a - PITCH * 0.3, ROOT), at(a - PITCH * 0.17, TIP), at(a + PITCH * 0.17, TIP), at(a + PITCH * 0.3, ROOT))
  }
  return `M${pts.join('L')}Z`
})()
// The dashed ghost of the missing tooth, in place.
const GHOST = `M${at(GAP_ANGLE - PITCH * 0.3, ROOT)}L${at(GAP_ANGLE - PITCH * 0.17, TIP)}L${at(GAP_ANGLE + PITCH * 0.17, TIP)}L${at(GAP_ANGLE + PITCH * 0.3, ROOT)}`
// The loose tooth itself, drawn around its own origin (base at y=0, tip up).
const TOOTH = (() => {
  const w0 = 2 * ROOT * Math.sin(PITCH * 0.3), w1 = 2 * TIP * Math.sin(PITCH * 0.17), h = TIP - ROOT
  return `M${-w0 / 2} 0 L${-w1 / 2} ${-h} L${w1 / 2} ${-h} L${w0 / 2} 0 Z`
})()

const arc = (r: number, a0: number, a1: number) =>
  `M${at(a0, r)} A${r} ${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${at(a1, r)}`
const circle = (r: number) => `M${r} 0 A${r} ${r} 0 1 1 ${-r} 0 A${r} ${r} 0 1 1 ${r} 0`

type Props = {
  celebrate?: boolean
  accent?: string // the agent's tooth (production blue)
  done?: string // green
  ink?: string
  faint?: string
  hoverStartMs?: number | null // the pointer entered the gear (Date.now())
  hoverEndMs?: number | null // …and left it
}

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

function Draw({ d, p, stroke, width = 2.8, dash }: { d: string; p: number; stroke: string; width?: number; dash?: string }) {
  if (dash) {
    // dashed strokes can't use the dash trick for drawing → fade them in
    return <path d={d} fill="none" stroke={stroke} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash} opacity={p} />
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
  hoverStartMs = null,
  hoverEndMs = null,
}) => {
  const f = useCurrentFrame()
  const INTRO = celebrate ? INTRO_CELEBRATE : INTRO_PLAIN
  const k = celebrate ? INTRO_CELEBRATE / DRAW : 1
  const inLoop = f >= INTRO
  const lf = inLoop ? (f - INTRO) % LOOP : 0
  const t = lf / LOOP

  const seg = (a: number, b: number) => interpolate(f, [a * k, b * k], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) })
  const pGear = seg(0, 30)
  const pInner = seg(14, 34)
  const pGreen = seg(28, 48)
  const pBlue = seg(36, 46)
  const pCheck = seg(44, 56)
  const pTooth = seg(42, 60)

  // The gear tries to turn: creeps forward ~7°, catches, snaps back with a
  // small overshoot. Twice per loop; 0 at the loop seam.
  const hitch = (x: number) =>
    interpolate(x, [0, 44, 52, 60, 68], [0, 7, -1.6, 0.6, 0], { ...clamp, easing: Easing.inOut(Easing.quad) })
  const rot = inLoop ? (lf < 120 ? hitch(lf - 20) : hitch(lf - 140)) : 0
  // Opening: the gear spins FAST and slows to a stop over 3s (ease-out cubic),
  // landing after whole turns so the gap is back at the top for the loop.
  const spin = interpolate(f, [0, SPIN_FRAMES], [0, SPIN_TURNS * 360], { ...clamp, easing: Easing.out(Easing.cubic) })
  // Hover: the gear spins while the pointer is on it (real time, like the
  // countdown), and on leave eases to a stop on a whole turn — gap back on top.
  let hoverSpin = 0
  if (hoverStartMs) {
    const now = Date.now()
    const W = 0.6 // deg per ms (~1.7 turns/s)
    const end = hoverEndMs && hoverEndMs >= hoverStartMs ? hoverEndMs : null
    const aEnd = W * ((end ?? now) - hoverStartMs)
    if (!end) hoverSpin = aEnd
    else {
      const target = Math.ceil((aEnd + 120) / 360) * 360
      const D = (3 * (target - aEnd)) / W // ms: ease-out cubic starting at speed W
      const p = Math.min(1, (now - end) / D)
      hoverSpin = aEnd + (target - aEnd) * (1 - (1 - p) ** 3)
    }
  }

  // the loose tooth floats above the gap (bobs 2x per loop), leaning in as
  // the gear creeps toward it
  const float = 16 + (inLoop ? Math.sin(t * TAU * 2) * 6 : 0) - rot * 1.2
  const toothIn = interpolate(pTooth, [0, 1], [26, 0]) // drops into place on draw

  // celebration: emphasis strokes burst around the gear once
  const burst = !celebrate ? 0 : inLoop
    ? (f - INTRO < LOOP ? interpolate(lf, [0, 30, 70], [1, 1, 0], clamp) : 0)
    : interpolate(f, [56 * k, 74 * k], [0, 1], clamp)
  const BURST = [150, 172, 196, 218, -28, -6, 18, 40].map((d) => (d * Math.PI) / 180)

  // little "trying" motion marks beside the gear while it creeps
  const effort = inLoop ? Math.max(0, rot / 7) : 0

  return (
    <AbsoluteFill style={{ fontFamily: 'Heebo, sans-serif' }}>
      <svg width={CYCLE_GEARS_W} height={CYCLE_GEARS_H} viewBox={`0 0 ${CYCLE_GEARS_W} ${CYCLE_GEARS_H}`}>
        <g transform={`translate(${C.x} ${C.y})`}>
          {/* motion marks: the gear straining to turn */}
          <g opacity={effort}>
            <path d={arc(TIP + 18, -0.35, 0.25)} fill="none" stroke={faint} strokeWidth={2.4} strokeLinecap="round" />
            <path d={arc(TIP + 30, -0.2, 0.12)} fill="none" stroke={faint} strokeWidth={2.4} strokeLinecap="round" />
          </g>

          {celebrate && BURST.map((a, i) => {
            const r0 = TIP + 10, r1 = TIP + 24 + (i % 2) * 8
            return (
              <Draw key={i} p={burst} stroke={done} width={2.8}
                d={`M${at(a, r0)} L${at(a, r1)}`} />
            )
          })}

          <g transform={`rotate(${rot + spin + hoverSpin})`}>
            <Draw d={GEAR} p={pGear} stroke={ink} width={3} />
            <Draw d={GHOST} p={pTooth} stroke={accent} width={2} dash="4 6" />
            {/* inner ring: green all round except under the gap (blue, dashed) */}
            <Draw d={arc(R * 0.64, GAP_ANGLE + 0.42, GAP_ANGLE + TAU - 0.42)} p={pGreen} stroke={done} width={4} />
            <Draw d={arc(R * 0.64, GAP_ANGLE - 0.36, GAP_ANGLE + 0.36)} p={pBlue} stroke={accent} width={4} dash="2 8" />
            {/* spokes */}
            <Draw
              d={[0, 1, 2, 3, 4, 5].map((i) => {
                const a = GAP_ANGLE + Math.PI / 6 + (i * TAU) / 6
                return `M${at(a, R * 0.3)} L${at(a, R * 0.5)}`
              }).join(' ')}
              p={pInner} stroke={ink} width={2.4}
            />
            <Draw d={circle(R * 0.3)} p={pInner} stroke={ink} width={2.8} />
          </g>
          {/* ✓ stays upright */}
          <Draw d="M-15 2 l10 10 l21 -23" p={pCheck} stroke={done} width={5} />

          {/* the missing tooth, floating above its gap */}
          <g transform={`rotate(${rot}) translate(0 ${-(TIP + float + toothIn)})`}>
            <g transform={`translate(0 ${TIP - ROOT})`}>
              <Draw d={TOOTH} p={pTooth} stroke={accent} width={3} />
            </g>
            <Draw d="M0 -10 V-32 M-7 -25 L0 -32 L7 -25" p={pTooth} stroke={accent} width={3} />
          </g>
        </g>
      </svg>
    </AbsoluteFill>
  )
}
