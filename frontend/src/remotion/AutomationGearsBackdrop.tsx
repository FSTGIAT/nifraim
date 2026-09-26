import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'

/**
 * Background of the automation tab: big gears stacked down the page, turning
 * slowly — "the machine is working". The page grows with every portal the
 * agent adds, so the host passes `count` (one gear per segment of page height)
 * and sizes the composition to AUTOMATION_GEARS_W × SEGMENT_H·count.
 * Kept VERY faint so the company panels on top stay primary.
 *
 * Neighbours really mesh: same tooth count, centres exactly 2R apart (zig-zag
 * left/right), each driven gear starts with a gap facing its driver's tooth,
 * and turns the opposite way at the same speed.
 *
 * Loop-perfect: every gear makes exactly one full turn per loop.
 */
export const AUTOMATION_GEARS_FRAMES = 1800 // 60s @ 30fps — slow on purpose
export const AUTOMATION_GEARS_W = 1600
export const AUTOMATION_GEARS_SEGMENT_H = 800

const TAU = Math.PI * 2
const TEETH = 40
const R = 460 // pitch radius
const MODULE = (2 * R) / TEETH
const SPOKES = 6
// Centres 2R apart: SEGMENT_H down, ±DX/2 across (zig-zag).
const DX = Math.sqrt((2 * R) ** 2 - AUTOMATION_GEARS_SEGMENT_H ** 2)

export function automationGearsHeight(count: number): number {
  return AUTOMATION_GEARS_SEGMENT_H * Math.max(1, count)
}

function gearPath(): string {
  const tip = R + MODULE * 0.9
  const root = R - MODULE * 1.1
  const p = TAU / TEETH
  const pts: string[] = []
  for (let k = 0; k < TEETH; k++) {
    const a = k * p
    const at = (ang: number, rad: number) =>
      `${(Math.cos(ang) * rad).toFixed(2)},${(Math.sin(ang) * rad).toFixed(2)}`
    pts.push(at(a - p * 0.29, root), at(a - p * 0.15, tip), at(a + p * 0.15, tip), at(a + p * 0.29, root))
  }
  return `M${pts.join('L')}Z`
}
const PATH = gearPath()

type GearSpec = { cx: number; cy: number; phase: number; dir: 1 | -1 }

function layout(count: number): GearSpec[] {
  const out: GearSpec[] = []
  const mid = AUTOMATION_GEARS_W / 2
  for (let i = 0; i < count; i++) {
    const cx = mid + (i % 2 === 0 ? -DX / 2 : DX / 2)
    const cy = AUTOMATION_GEARS_SEGMENT_H * i + AUTOMATION_GEARS_SEGMENT_H / 2
    if (i === 0) {
      out.push({ cx, cy, phase: 0, dir: 1 })
      continue
    }
    const drv = out[i - 1]
    const beta = Math.atan2(cy - drv.cy, cx - drv.cx) // centre line driver → driven
    const pitch = TAU / TEETH
    const k = (beta - drv.phase) / pitch
    const delta = (k - Math.round(k)) * pitch
    out.push({
      cx,
      cy,
      phase: beta + Math.PI + Math.PI / TEETH + delta, // equal teeth → ratio 1
      dir: drv.dir === 1 ? -1 : 1,
    })
  }
  return out
}

type Props = { color?: string; count?: number }

export const AutomationGearsBackdrop: React.FC<Props> = ({ color = '#0E8C8A', count = 1 }) => {
  const frame = useCurrentFrame()
  const turn = ((frame % AUTOMATION_GEARS_FRAMES) / AUTOMATION_GEARS_FRAMES) * TAU
  const gears = layout(Math.max(1, count))
  const h = automationGearsHeight(count)

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent' }}>
      <svg width={AUTOMATION_GEARS_W} height={h} viewBox={`0 0 ${AUTOMATION_GEARS_W} ${h}`}>
        {gears.map((g, i) => {
          const deg = ((g.phase + g.dir * turn) * 180) / Math.PI
          return (
            <g key={i} transform={`translate(${g.cx} ${g.cy}) rotate(${deg})`}>
              <path d={PATH} fill={color} fillOpacity={0.035} stroke={color} strokeOpacity={0.12} strokeWidth={2.5} strokeLinejoin="round" />
              <circle r={R * 0.72} fill="none" stroke={color} strokeOpacity={0.1} strokeWidth={2.5} />
              <circle r={R * 0.2} fill={color} fillOpacity={0.05} stroke={color} strokeOpacity={0.12} strokeWidth={2.5} />
              <circle r={R * 0.07} fill={color} fillOpacity={0.08} />
              {Array.from({ length: SPOKES }, (_, s) => {
                const a = (s * TAU) / SPOKES
                return (
                  <line
                    key={s}
                    x1={Math.cos(a) * R * 0.2}
                    y1={Math.sin(a) * R * 0.2}
                    x2={Math.cos(a) * R * 0.72}
                    y2={Math.sin(a) * R * 0.72}
                    stroke={color}
                    strokeOpacity={0.09}
                    strokeWidth={10}
                    strokeLinecap="round"
                  />
                )
              })}
            </g>
          )
        })}
      </svg>
    </AbsoluteFill>
  )
}
