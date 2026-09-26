import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'

/**
 * Background of the home "הפעלת האוטומציה" setup card: three meshing gears
 * turning slowly — the machine is being assembled. Tinted by `color` (the
 * next setup step's accent) and kept faint so the card's text and CTA stay
 * primary.
 *
 * The gears really mesh: a shared module (tooth size) sets each pitch radius,
 * centres sit exactly r1 + r2 apart, the driven gear starts with a GAP facing
 * the driver's tooth, and each turns at −N_driver/N_self of its driver.
 *
 * Loop-perfect: 48 teeth pass every contact point per loop (LCM of 24/16/12),
 * so the gears make exactly 2 / 3 / 4 turns and frame N equals frame 0.
 */
export const SETUP_GEARS_FRAMES = 900 // 30s @ 30fps — slow on purpose
export const SETUP_GEARS_W = 260
export const SETUP_GEARS_H = 100

const TAU = Math.PI * 2
const MODULE = 4 // px of pitch diameter per tooth
const TEETH_PER_LOOP = 48

type GearSpec = { teeth: number; cx: number; cy: number; phase: number; dir: 1 | -1 }

function gearPath(teeth: number): string {
  const r = (MODULE * teeth) / 2
  const tip = r + MODULE * 0.9
  const root = r - MODULE * 1.1
  const p = TAU / teeth
  const pts: string[] = []
  for (let k = 0; k < teeth; k++) {
    const a = k * p
    const at = (ang: number, rad: number) =>
      `${(Math.cos(ang) * rad).toFixed(2)},${(Math.sin(ang) * rad).toFixed(2)}`
    pts.push(at(a - p * 0.29, root), at(a - p * 0.15, tip), at(a + p * 0.15, tip), at(a + p * 0.29, root))
  }
  return `M${pts.join('L')}Z`
}

// Driver → driven chain. `beta` is the centre-line angle from driver to driven.
function layout(): GearSpec[] {
  const big = { teeth: 24, cx: 78, cy: 78 }
  const rBig = (MODULE * big.teeth) / 2
  const mid = { teeth: 16 }
  const rMid = (MODULE * mid.teeth) / 2
  const small = { teeth: 12 }
  const rSmall = (MODULE * small.teeth) / 2

  const beta1 = -0.52 // up-and-right from the big gear
  const midC = { cx: big.cx + Math.cos(beta1) * (rBig + rMid), cy: big.cy + Math.sin(beta1) * (rBig + rMid) }
  const beta2 = 0.35 // down-and-right from the middle gear
  const smallC = { cx: midC.cx + Math.cos(beta2) * (rMid + rSmall), cy: midC.cy + Math.sin(beta2) * (rMid + rSmall) }

  // Driver tooth points along beta; driven gear shows a gap back along beta+π.
  const bigPhase = beta1
  const midPhase = beta1 + Math.PI + Math.PI / mid.teeth
  // Mid's phase is already fixed by the first mesh, so its nearest tooth to
  // beta2 sits `delta` off the centre line (tooth at beta2 − delta). The small
  // gear's gap must follow it — rotated the opposite way, scaled by the ratio.
  const midPitch = TAU / mid.teeth
  const k = (beta2 - midPhase) / midPitch
  const delta = (k - Math.round(k)) * midPitch
  const smallPhase = beta2 + Math.PI + Math.PI / small.teeth + delta * (mid.teeth / small.teeth)

  return [
    { teeth: big.teeth, cx: big.cx, cy: big.cy, phase: bigPhase, dir: 1 },
    { teeth: mid.teeth, cx: midC.cx, cy: midC.cy, phase: midPhase, dir: -1 },
    { teeth: small.teeth, cx: smallC.cx, cy: smallC.cy, phase: smallPhase, dir: 1 },
  ]
}

const GEARS = layout()
const PATHS = GEARS.map((g) => gearPath(g.teeth))

type Props = { color?: string }

export const SetupGears: React.FC<Props> = ({ color = '#0E8C8A' }) => {
  const frame = useCurrentFrame()
  const t = (frame % SETUP_GEARS_FRAMES) / SETUP_GEARS_FRAMES
  const teethPassed = t * TEETH_PER_LOOP

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent' }}>
      <svg width={SETUP_GEARS_W} height={SETUP_GEARS_H} viewBox={`0 0 ${SETUP_GEARS_W} ${SETUP_GEARS_H}`}>
        {GEARS.map((g, i) => {
          // Same linear tooth speed at every contact → angle = teeth / N turns.
          const angle = g.phase + g.dir * (teethPassed / g.teeth) * TAU
          const r = (MODULE * g.teeth) / 2
          return (
            <g key={i} transform={`translate(${g.cx} ${g.cy}) rotate(${(angle * 180) / Math.PI})`}>
              <path d={PATHS[i]} fill={color} fillOpacity={0.07} stroke={color} strokeOpacity={0.32} strokeWidth={1.4} strokeLinejoin="round" />
              <circle r={r * 0.42} fill="none" stroke={color} strokeOpacity={0.26} strokeWidth={1.2} />
              {[0, 1, 2, 3].map((s) => (
                <line
                  key={s}
                  x1={0}
                  y1={0}
                  x2={Math.cos((s * TAU) / 4) * r * 0.42}
                  y2={Math.sin((s * TAU) / 4) * r * 0.42}
                  stroke={color}
                  strokeOpacity={0.2}
                  strokeWidth={1.2}
                />
              ))}
              <circle r={r * 0.14} fill={color} fillOpacity={0.22} />
            </g>
          )
        })}
      </svg>
    </AbsoluteFill>
  )
}
