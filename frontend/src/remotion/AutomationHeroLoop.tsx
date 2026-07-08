import React from 'react'
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion'

/**
 * AutomationHeroLoop
 * ------------------
 * Looping decorative scene for the אוטומציה hero: documents ride a conveyor
 * into meshing gears and drop into the archive tray. Flat teal palette
 * (chart-12/7/14/15 + lavender accents), transparent background so it bleeds
 * into the white hero card.
 *
 * Loop-perfect at LOOP_FRAMES: every motion completes an integer number of
 * cycles per loop (gears: 1/-2/3 turns; docs: 3 belt-steps; treads: 8;
 * falling doc: 2), so the restart seam is invisible.
 */

export const AUTOMATION_HERO_LOOP_FRAMES = 240 // 8s @ 30fps

const TEAL = '#0E8C8A'
const TURQUOISE = '#3DB6B0'
const DEEP = '#2C5F6B'
const MINT = '#8FD9C6'
const LAVENDER = '#B79CEB'
const PAPER = '#EAF7F3'

function Gear({
  cx, cy, r, teeth, toothW, toothH, holeR, fill, angle,
}: {
  cx: number; cy: number; r: number; teeth: number
  toothW: number; toothH: number; holeR: number; fill: string; angle: number
}) {
  const step = 360 / teeth
  return (
    <g transform={`translate(${cx} ${cy}) rotate(${angle})`}>
      <g fill={fill}>
        {Array.from({ length: teeth }, (_, i) => (
          <rect
            key={i}
            x={-toothW / 2}
            y={-(r + toothH * 0.72)}
            width={toothW}
            height={toothH}
            rx={toothH * 0.24}
            transform={`rotate(${i * step})`}
          />
        ))}
      </g>
      <circle r={r} fill={fill} />
      <circle r={holeR} fill="#FFFFFF" />
    </g>
  )
}

function Doc({ w = 38, h = 56, fill = TEAL, line = MINT }: {
  w?: number; h?: number; fill?: string; line?: string
}) {
  const fold = w * 0.26
  return (
    <g>
      <path
        d={`M0 6 q0 -6 6 -6 h${w - fold - 6} l${fold} ${fold} v${h - fold - 6} q0 6 -6 6 h-${w - 12} q-6 0 -6 -6 z`}
        fill={fill}
      />
      <rect x={w * 0.18} y={h * 0.42} width={w * 0.6} height={5} rx={2.5} fill={line} />
      <rect x={w * 0.18} y={h * 0.6} width={w * 0.44} height={5} rx={2.5} fill={line} />
      <rect x={w * 0.18} y={h * 0.78} width={w * 0.52} height={5} rx={2.5} fill={line} />
    </g>
  )
}

export function AutomationHeroLoop() {
  const frame = useCurrentFrame()
  const t = frame / AUTOMATION_HERO_LOOP_FRAMES // 0..1 over one loop

  // Gears — integer turns per loop, neighbours counter-rotate.
  const bigAngle = t * 360
  const midAngle = -t * 720
  const smallAngle = t * 1080

  // Conveyor: docs advance one 92px step every 80 frames (3 steps/loop).
  const DOC_SPACING = 92
  const docShift = ((frame % 80) / 80) * DOC_SPACING
  // Treads: one 38px step every 30 frames (8 steps/loop).
  const treadShift = ((frame % 30) / 30) * 38

  // Falling document: 2 cycles per loop — drops INTO the tray (lands on the
  // paper stack at y≈+150), settles, then fades where it lies.
  const FALL_CYCLE = 120
  const fallFrame = frame % FALL_CYCLE
  const fallY = interpolate(fallFrame, [10, 78], [0, 150], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.45, 0, 0.85, 0.7),
  })
  const fallTilt = interpolate(fallFrame, [10, 78], [0, -8], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })
  const fallOpacity = interpolate(
    fallFrame,
    [0, 10, 18, 92, 108],
    [0, 0, 1, 1, 0],
    { extrapolateRight: 'clamp' },
  )

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent' }}>
      <svg viewBox="20 15 848 420" width="100%" height="100%" preserveAspectRatio="xMinYMid meet">
        {/* pipes (static) */}
        <path d="M 640 120 h 90 q 18 0 18 18 v 40" stroke={MINT} strokeWidth={13} strokeLinecap="round" fill="none" />
        <path d="M 560 330 h 96 q 16 0 16 -16 v -20" stroke={DEEP} strokeWidth={13} strokeLinecap="round" fill="none" />
        <circle cx={700} cy={120} r={9} fill={LAVENDER} />
        <circle cx={612} cy={330} r={9} fill={LAVENDER} />

        {/* conveyor */}
        <rect x={28} y={300} width={400} height={34} rx={17} fill={DEEP} />
        <clipPath id="ah-belt"><rect x={40} y={306} width={376} height={22} rx={11} /></clipPath>
        <g clipPath="url(#ah-belt)">
          <g transform={`translate(${treadShift} 0)`} fill={MINT} opacity={0.85}>
            {Array.from({ length: 12 }, (_, i) => (
              <rect key={i} x={-46 + i * 38} y={312} width={18} height={10} rx={5} />
            ))}
          </g>
        </g>
        <clipPath id="ah-docs"><rect x={18} y={230} width={420} height={72} /></clipPath>
        <g clipPath="url(#ah-docs)">
          <g transform={`translate(${docShift} 0)`}>
            {Array.from({ length: 6 }, (_, i) => (
              <g key={i} transform={`translate(${-152 + i * DOC_SPACING} 240)`}>
                <Doc />
              </g>
            ))}
          </g>
        </g>

        {/* gears */}
        <Gear cx={530} cy={210} r={96} teeth={10} toothW={28} toothH={26} holeR={42} fill={TEAL} angle={bigAngle} />
        {/* document held in the big gear's eye (does not rotate) */}
        <g transform="translate(530 210)">
          <g transform="translate(-16 -22)"><Doc w={32} h={44} /></g>
        </g>
        <Gear cx={672} cy={118} r={56} teeth={8} toothW={22} toothH={20} holeR={22} fill={TURQUOISE} angle={midAngle} />
        <Gear cx={662} cy={306} r={40} teeth={8} toothW={16} toothH={15} holeR={15} fill={DEEP} angle={smallAngle} />

        {/* falling document into the archive */}
        <g transform={`translate(776 ${140 + fallY}) rotate(${fallTilt})`} opacity={fallOpacity}>
          <Doc w={35} h={49} fill={TURQUOISE} line={PAPER} />
        </g>

        {/* archive tray */}
        <g transform="translate(742 300)">
          {Array.from({ length: 5 }, (_, i) => (
            <rect key={i} x={10} y={52 - (i + 1) * 11} width={92} height={8} rx={4} fill={(i + 1) % 2 ? TURQUOISE : MINT} />
          ))}
          <path d="M0 44 v36 q0 12 12 12 h88 q12 0 12 -12 v-36 h-16 v30 h-80 v-30 z" fill={DEEP} />
          <rect x={18} y={102} width={26} height={7} rx={3.5} fill={LAVENDER} />
        </g>
      </svg>
    </AbsoluteFill>
  )
}
