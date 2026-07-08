import React from 'react'
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from 'remotion'

/**
 * TabHeroLoops
 * ------------
 * One looping decorative scene per workspace tab, each in its tab-identity
 * palette (see App.vue --tab-*). Same spirit as AutomationHeroLoop: flat
 * shapes, transparent background (bleeds into the white hero card), and
 * loop-perfect motion — every animated quantity completes a whole number of
 * cycles across LOOP_FRAMES so the restart seam is invisible.
 *
 * Mounted through TabHeroLoop.vue (React island); that wrapper applies the
 * direction:ltr fix Remotion Player needs under the app's RTL root.
 */

export const TAB_HERO_LOOP_FRAMES = 240 // 8s @ 30fps

/* ── shared primitives ─────────────────────────────────────────── */

function loopPhase(frame: number, cycle: number) {
  return (frame % cycle) / cycle // 0..1
}

function Doc({
  w = 34, h = 46, fill, line, x = 0, y = 0, rot = 0, opacity = 1,
}: {
  w?: number; h?: number; fill: string; line: string
  x?: number; y?: number; rot?: number; opacity?: number
}) {
  const fold = w * 0.26
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot})`} opacity={opacity}>
      <path
        d={`M0 6 q0 -6 6 -6 h${w - fold - 6} l${fold} ${fold} v${h - fold - 6} q0 6 -6 6 h-${w - 12} q-6 0 -6 -6 z`}
        fill={fill}
      />
      <rect x={w * 0.18} y={h * 0.44} width={w * 0.58} height={4.5} rx={2.25} fill={line} />
      <rect x={w * 0.18} y={h * 0.62} width={w * 0.42} height={4.5} rx={2.25} fill={line} />
    </g>
  )
}

function Spark({ cx, cy, r, fill, k = 1 }: { cx: number; cy: number; r: number; fill: string; k?: number }) {
  // four-point sparkle (concave star)
  const o = r
  const i = r * 0.32
  const pts = [
    [0, -o], [i, -i], [o, 0], [i, i],
    [0, o], [-i, i], [-o, 0], [-i, -i],
  ].map(([x, y]) => `${x * k},${y * k}`).join(' ')
  return <polygon points={pts} fill={fill} transform={`translate(${cx} ${cy})`} />
}

/* ═══════════════════ AI LIBRARY — lavender ═══════════════════ */
export function AiKnowledgeLoop() {
  const frame = useCurrentFrame()
  const spin = loopPhase(frame, 240) * 360
  const pulse = 1 + 0.12 * Math.sin((frame / 240) * Math.PI * 4) // 2 pulses/loop
  const twinkle = 0.6 + 0.4 * Math.abs(Math.sin((frame / 240) * Math.PI * 6))

  const ACC = '#B79CEB', INK = '#6A48C9', SOFT = '#C9B6EE', PALE = '#E9E0F9', MINT = '#8FD9C6'

  // three cards feed toward the core, staggered
  const feed = (offset: number) => {
    const p = loopPhase(frame + offset, 240)
    const t = interpolate(p, [0, 0.55, 0.7, 1], [1, 0, 0, 1], { extrapolateRight: 'clamp' })
    const op = interpolate(p, [0, 0.5, 0.62, 0.72, 1], [1, 1, 0, 0, 1])
    return { t, op }
  }
  const c1 = feed(0), c2 = feed(80), c3 = feed(160)

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* orbit ring */}
        <g transform="translate(210 150)" opacity={0.5}>
          <circle r={112} fill="none" stroke={PALE} strokeWidth={2} strokeDasharray="4 10" transform={`rotate(${spin})`} />
        </g>
        {/* feeding cards */}
        <g><Doc x={interpolate(c1.t, [0, 1], [200, 60])} y={70} fill={ACC} line={PALE} opacity={c1.op} /></g>
        <g><Doc x={interpolate(c2.t, [0, 1], [40, 150])} y={200} fill={INK} line={PALE} opacity={c2.op} /></g>
        <g><Doc x={interpolate(c3.t, [0, 1], [330, 250])} y={190} fill={SOFT} line={INK} opacity={c3.op} /></g>
        {/* knowledge core */}
        <g transform={`translate(210 150) scale(${pulse})`}>
          <rect x={-52} y={-52} width={104} height={104} rx={26} fill={INK} />
          <rect x={-52} y={-52} width={104} height={104} rx={26} fill="none" stroke={ACC} strokeWidth={3} />
          <Spark cx={0} cy={-4} r={26} fill="#FFFFFF" />
        </g>
        <Spark cx={300} cy={70} r={10} fill={ACC} k={twinkle} />
        <Spark cx={118} cy={232} r={7} fill={MINT} k={2 - twinkle} />
      </svg>
    </AbsoluteFill>
  )
}

/* ═══════════════════ PORTAL — sky ═══════════════════ */
export function PortalShareLoop() {
  const frame = useCurrentFrame()
  const ringSpin = loopPhase(frame, 240) * 360
  const ACC = '#4E9DD0', INK = '#35719A', DEEP = '#2C5F6B', MINT = '#8FD9C6', PALE = '#DCEBF6'

  // portfolio card travels center → through ring → to the customer, 2×/loop
  const p = loopPhase(frame, 120)
  const cardX = interpolate(p, [0, 0.8], [150, 300], { extrapolateRight: 'clamp', easing: Easing.bezier(0.4, 0, 0.4, 1) })
  const cardScale = interpolate(p, [0, 0.4, 0.8], [0.6, 1, 0.7], { extrapolateRight: 'clamp' })
  const cardOp = interpolate(p, [0, 0.1, 0.72, 0.85], [0, 1, 1, 0], { extrapolateRight: 'clamp' })
  const recv = interpolate(p, [0.6, 0.8, 1], [1, 1.16, 1], { extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* portal ring */}
        <g transform="translate(150 150)">
          <circle r={78} fill={PALE} />
          <g transform={`rotate(${ringSpin})`}>
            <circle r={78} fill="none" stroke={ACC} strokeWidth={10} strokeDasharray="70 40" strokeLinecap="round" />
            <circle r={62} fill="none" stroke={INK} strokeWidth={5} strokeDasharray="34 28" strokeLinecap="round" transform="rotate(30)" />
          </g>
          <circle r={44} fill="#FFFFFF" />
        </g>
        {/* traveling portfolio card */}
        <g transform={`translate(${cardX} 150) scale(${cardScale})`} opacity={cardOp}>
          <rect x={-26} y={-32} width={52} height={64} rx={9} fill={INK} />
          <rect x={-16} y={-20} width={32} height={6} rx={3} fill={MINT} />
          <rect x={-16} y={-6} width={24} height={6} rx={3} fill={PALE} />
          <circle cx={0} cy={14} r={9} fill={ACC} />
        </g>
        {/* customer glyph */}
        <g transform="translate(330 150)">
          <g transform={`scale(${recv})`}>
            <circle cx={0} cy={-14} r={16} fill={DEEP} />
            <path d="M-26 34 a26 26 0 0 1 52 0 z" fill={DEEP} />
          </g>
        </g>
      </svg>
    </AbsoluteFill>
  )
}

/* ═══════════════════ COMPANY EMAILS — magenta ═══════════════════ */
export function MailFlowLoop() {
  const frame = useCurrentFrame()
  const ACC = '#E84A7F', INK = '#C42B60', SOFT = '#F3A9C4', PALE = '#FADCE7'

  // paper plane flies an arc, 2×/loop, leaving a dashed trail
  const p = loopPhase(frame, 120)
  const px = interpolate(p, [0, 0.82], [120, 330], { extrapolateRight: 'clamp', easing: Easing.bezier(0.3, 0, 0.5, 1) })
  const py = interpolate(p, [0, 0.4, 0.82], [170, 96, 120], { extrapolateRight: 'clamp' })
  const planeOp = interpolate(p, [0, 0.08, 0.78, 0.9], [0, 1, 1, 0], { extrapolateRight: 'clamp' })
  const flap = 1 + 0.14 * Math.sin((frame / 240) * Math.PI * 16)
  const dash = -loopPhase(frame, 30) * 20

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* trail */}
        <path d="M120 170 Q 220 60 330 120" fill="none" stroke={SOFT} strokeWidth={3}
              strokeDasharray="3 11" strokeLinecap="round" strokeDashoffset={dash} opacity={0.7} />
        {/* open envelope (source) */}
        <g transform="translate(74 150)">
          <rect x={-40} y={-28} width={80} height={58} rx={10} fill={INK} />
          <path d="M-40 -20 L0 12 L40 -20" fill="none" stroke={PALE} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
          <rect x={-40} y={-28} width={80} height={58} rx={10} fill="none" stroke={ACC} strokeWidth={3} />
        </g>
        {/* stacked inbox (target) */}
        <g transform="translate(346 176)">
          <rect x={-38} y={-6} width={76} height={44} rx={9} fill={INK} />
          <rect x={-30} y={-16} width={60} height={12} rx={5} fill={SOFT} />
          <rect x={-24} y={-26} width={48} height={12} rx={5} fill={PALE} />
        </g>
        {/* paper plane */}
        <g transform={`translate(${px} ${py}) rotate(-24)`} opacity={planeOp}>
          <g transform={`scaleY(${flap})`}>
            <path d="M-18 0 L18 -12 L2 2 L18 12 Z" fill={ACC} />
            <path d="M-18 0 L2 2 L4 12 Z" fill={INK} />
          </g>
        </g>
      </svg>
    </AbsoluteFill>
  )
}

/* ═══════════════════ RECRUITS / תיק אישי — turquoise ═══════════════════ */
export function PortfolioLoop() {
  const frame = useCurrentFrame()
  const ACC = '#3DB6B0', INK = '#1E7D78', DEEP = '#2C5F6B', MINT = '#8FD9C6', PALE = '#D6F0EE'

  // client cards fan out of the folder, staggered, loop
  const fan = (i: number) => {
    const p = loopPhase(frame + i * 26, 240)
    const rise = interpolate(p, [0, 0.4, 0.85, 1], [0, 1, 1, 0], { extrapolateRight: 'clamp' })
    return rise
  }
  // rising mini bars — grow then reset, 2×/loop
  const barP = loopPhase(frame, 120)
  const barH = (base: number) => interpolate(barP, [0, 0.5, 0.9, 1], [8, base, base, 8], { extrapolateRight: 'clamp' })

  const cards = [
    { dx: -70, dy: -52, rot: -14, c: MINT },
    { dx: 0, dy: -70, rot: 0, c: ACC },
    { dx: 70, dy: -52, rot: 14, c: INK },
  ]

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* fanning client cards behind the folder */}
        {cards.map((c, i) => {
          const r = fan(i)
          return (
            <g key={i} transform={`translate(210 190) translate(${c.dx * r} ${c.dy * r}) rotate(${c.rot * r})`} opacity={r}>
              <rect x={-30} y={-40} width={60} height={74} rx={10} fill={c.c} />
              <circle cx={0} cy={-16} r={11} fill="#FFFFFF" opacity={0.9} />
              <path d="M-16 20 a16 16 0 0 1 32 0 z" fill="#FFFFFF" opacity={0.9} />
            </g>
          )
        })}
        {/* folder */}
        <g transform="translate(210 190)">
          <path d="M-92 -34 h40 l14 16 h38 q10 0 10 10 v58 q0 10 -10 10 h-92 q-10 0 -10 -10 v-64 q0 -10 10 -10 z" fill={DEEP} />
          <rect x={-100} y={-2} width={200} height={78} rx={12} fill={ACC} />
          <rect x={-100} y={-2} width={200} height={78} rx={12} fill="none" stroke={INK} strokeWidth={0} />
        </g>
        {/* mini rising bars on the folder face */}
        <g transform="translate(150 68)">
          {[26, 40, 30].map((b, i) => {
            const h = barH(b)
            return <rect key={i} x={i * 22} y={-h} width={13} height={h} rx={4} fill={PALE} />
          })}
        </g>
      </svg>
    </AbsoluteFill>
  )
}

/* ═══════════════════ COMMISSION SHELF / מדף הסכמים — purple ═══════════════════ */
export function ShelfLoop() {
  const frame = useCurrentFrame()
  const ACC = '#8E44AD', INK = '#6D2E8A', SOFT = '#C9A6DD', PALE = '#EBDDF3', GOLD = '#F4D35E'

  // agreement books slide onto the shelf one by one, each with a % tag pop
  const book = (i: number, targetX: number, h: number, fill: string) => {
    const p = loopPhase(frame + i * 18, 240)
    const slide = interpolate(p, [0, 0.42, 0.9, 1], [1, 0, 0, 1], { extrapolateRight: 'clamp', easing: Easing.bezier(0.3, 0, 0.3, 1) })
    const x = interpolate(slide, [0, 1], [targetX, 430])
    const op = interpolate(p, [0, 0.06, 0.92, 1], [0, 1, 1, 0])
    const tag = interpolate(p, [0.42, 0.56, 0.86, 0.94], [0, 1, 1, 0], { extrapolateRight: 'clamp' })
    return { x, op, tag, h }
  }
  const books = [
    book(0, 120, 96, ACC),
    book(1, 168, 80, INK),
    book(2, 216, 104, SOFT),
    book(3, 264, 86, ACC),
  ]

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* books */}
        {books.map((b, i) => (
          <g key={i} opacity={b.op}>
            <rect x={b.x} y={210 - b.h} width={36} height={b.h} rx={7} fill={i % 3 === 2 ? SOFT : (i % 2 ? INK : ACC)} />
            <rect x={b.x + 6} y={210 - b.h + 12} width={24} height={5} rx={2.5} fill={PALE} />
            <rect x={b.x + 6} y={210 - b.h + 24} width={18} height={5} rx={2.5} fill={PALE} />
            {/* % tag pop */}
            <g transform={`translate(${b.x + 18} ${210 - b.h - 16}) scale(${b.tag})`} opacity={b.tag}>
              <rect x={-18} y={-13} width={36} height={24} rx={12} fill={GOLD} />
              {/* counter-flip: the mount mirrors the whole scene (scaleX(-1)),
                  so flip the glyph back to keep "%" readable */}
              <text x={0} y={4} textAnchor="middle" fontSize={13} fontWeight={800} fill={INK} fontFamily="Heebo, sans-serif" transform="scale(-1 1)">%</text>
            </g>
          </g>
        ))}
        {/* shelf plank */}
        <rect x={86} y={210} width={248} height={16} rx={6} fill={INK} />
        <rect x={96} y={226} width={16} height={26} rx={4} fill={SOFT} />
        <rect x={308} y={226} width={16} height={26} rx={4} fill={SOFT} />
      </svg>
    </AbsoluteFill>
  )
}

/* ── registry consumed by TabHeroLoop.vue ─────────────────────── */
export const TAB_HERO_SCENES = {
  'ai-library': AiKnowledgeLoop,
  portal: PortalShareLoop,
  'company-emails': MailFlowLoop,
  recruits: PortfolioLoop,
  'commission-shelf': ShelfLoop,
} as const

export type TabHeroScene = keyof typeof TAB_HERO_SCENES
