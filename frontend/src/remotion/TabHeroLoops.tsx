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
          <g transform={`scale(1 ${flap})`}>
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

/* ═══════════════════ מסלקה פנסיונית — deep teal ═══════════════════ */
export function ClearingHouseLoop() {
  const frame = useCurrentFrame()
  const ACC = '#2C5F6B', SOFT = '#5E9BA8', MINT = '#8FD9C6', PALE = '#DCEEEF'

  // Left: the managing bodies (גופים מנהלים). Centre: the clearing house.
  // Right: the one complete pension picture it returns. Authored left-to-right;
  // TabHeroLoop mirrors it so the flow reads right-to-left with the Hebrew UI.
  const PROVIDERS = [54, 116, 178, 240] // tile centre-y
  const HUB_X = 210, HUB_Y = 150

  // provider → hub: each body answers once per 120-frame cycle (2 per loop)
  const inbound = (i: number) => {
    const p = loopPhase(frame + i * 30, 120)
    const travel = interpolate(p, [0, 0.55], [0, 1], {
      extrapolateRight: 'clamp',
      easing: Easing.bezier(0.4, 0, 0.35, 1),
    })
    const op = interpolate(p, [0, 0.08, 0.46, 0.55], [0, 1, 1, 0], { extrapolateRight: 'clamp' })
    return { travel, op }
  }

  // hub → card: the merged picture leaves once the answers are in
  const outP = loopPhase(frame, 120)
  const outTravel = interpolate(outP, [0.55, 0.9], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.3, 0, 0.3, 1),
  })
  const outOp = interpolate(outP, [0.55, 0.62, 0.84, 0.9], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  })

  // hub: 4 request pulses per loop, ring turns once per loop
  const pulse = loopPhase(frame, 60)
  const pulseR = interpolate(pulse, [0, 1], [46, 98])
  const pulseOp = interpolate(pulse, [0, 0.16, 1], [0, 0.45, 0])
  const ringAngle = loopPhase(frame, 240) * 360

  // portfolio bars grow then settle back to the floor — no seam at the loop point
  const barP = loopPhase(frame, 120)
  const barH = (base: number, i: number) =>
    interpolate(barP, [0.12 + i * 0.07, 0.64 + i * 0.07, 0.94, 1], [4, base, base, 4], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    })
  const twinkle = 0.5 + 0.5 * Math.abs(Math.sin((frame / 240) * Math.PI * 4)) // 2 twinkles/loop

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* wiring (static) */}
        {PROVIDERS.map((cy, i) => (
          <line
            key={`w${i}`}
            x1={88} y1={cy} x2={166} y2={HUB_Y}
            stroke={PALE} strokeWidth={3} strokeLinecap="round" strokeDasharray="5 8"
          />
        ))}
        <line x1={258} y1={HUB_Y} x2={302} y2={HUB_Y} stroke={PALE} strokeWidth={3} strokeLinecap="round" strokeDasharray="5 8" />

        {/* managing bodies */}
        {PROVIDERS.map((cy, i) => (
          <g key={`p${i}`}>
            <path d={`M28 ${cy - 13} L58 ${cy - 28} L88 ${cy - 13} Z`} fill={i % 2 ? SOFT : ACC} />
            <rect x={33} y={cy - 13} width={50} height={32} rx={7} fill={i % 2 ? SOFT : ACC} />
            {[0, 1, 2].map((c) => (
              <rect key={c} x={41 + c * 13} y={cy - 6} width={8} height={18} rx={3} fill={PALE} />
            ))}
          </g>
        ))}

        {/* answers travelling in to the clearing house */}
        {PROVIDERS.map((cy, i) => {
          const { travel, op } = inbound(i)
          const x = 88 + travel * 78
          const y = cy + travel * (HUB_Y - cy)
          const s = 1 - 0.3 * travel
          return (
            <g key={`d${i}`} transform={`translate(${x} ${y}) scale(${s})`} opacity={op}>
              <Doc w={22} h={30} fill={MINT} line={ACC} x={-11} y={-15} />
            </g>
          )
        })}

        {/* clearing house */}
        <g transform={`translate(${HUB_X} ${HUB_Y})`}>
          <circle r={pulseR} fill="none" stroke={MINT} strokeWidth={3} opacity={pulseOp} />
          <circle
            r={62} fill="none" stroke={MINT} strokeWidth={2.5}
            strokeDasharray="5 11" transform={`rotate(${ringAngle})`}
          />
          <circle r={46} fill={ACC} />
          <circle r={28} fill={PALE} />
          {[-9, -1, 7].map((y, i) => (
            <rect key={i} x={-13} y={y} width={26} height={5} rx={2.5} fill={i === 1 ? SOFT : ACC} />
          ))}
          <rect x={-13} y={-17} width={16} height={5} rx={2.5} fill={MINT} />
        </g>

        {/* the merged picture on its way out */}
        <g transform={`translate(${258 + outTravel * 62} ${HUB_Y})`} opacity={outOp}>
          <Doc w={26} h={34} fill={ACC} line={MINT} x={-13} y={-17} />
        </g>

        {/* one complete pension picture */}
        <g>
          <rect x={306} y={94} width={84} height={112} rx={14} fill={PALE} stroke={ACC} strokeWidth={3} />
          <rect x={318} y={108} width={46} height={8} rx={4} fill={ACC} />
          <rect x={318} y={122} width={30} height={6} rx={3} fill={SOFT} />
          {[30, 46, 22, 38].map((base, i) => {
            const h = barH(base, i)
            return <rect key={i} x={317 + i * 17} y={190 - h} width={11} height={h} rx={4} fill={i % 2 ? MINT : ACC} />
          })}
          <rect x={317} y={190} width={62} height={3} rx={1.5} fill={SOFT} opacity={0.5} />
          <Spark cx={384} cy={100} r={9} fill={MINT} k={twinkle} />
        </g>
      </svg>
    </AbsoluteFill>
  )
}

/* ═══════════════════ COMPARISON — green ═══════════════════ */
// Production records (right — read first in Hebrew) and נפרעים records (left)
// pair up one row at a time: a link draws right→left, the pair turns solid,
// and a check lands on it. Authored RTL natively — mount with flow="ltr" so
// the check glyph is never mirrored.
// Three rows × 80 frames = one 240-frame loop; every row resets at loop end.
export function ComparisonMatchLoop() {
  const frame = useCurrentFrame()
  const ACC = '#2E844A', INK = '#1F5A35', MINT = '#9BD3AE', PALE = '#E3F2E8'
  const ROWS = [74, 136, 198]
  const LX = 24, RX = 266, W = 130, H = 38

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* column headers */}
        <rect x={RX} y={40} width={W * 0.62} height={12} rx={6} fill={INK} opacity={0.85} />
        <rect x={LX} y={40} width={W * 0.62} height={12} rx={6} fill={ACC} opacity={0.85} />
        {ROWS.map((y, i) => {
          const local = frame - i * 80
          const link = interpolate(local, [4, 34], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            easing: Easing.bezier(0.4, 0, 0.2, 1),
          })
          const solid = interpolate(local, [30, 42], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
          const pop = interpolate(local, [36, 46, 54], [0, 1.18, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
          // everything eases back out in the loop's last 20 frames
          const out = interpolate(frame, [220, 240], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
          const x1 = LX + W, x2 = RX, cy = y + H / 2
          return (
            <g key={i}>
              <rect x={LX} y={y} width={W} height={H} rx={8} fill={PALE} />
              <rect x={LX} y={y} width={W} height={H} rx={8} fill={MINT} opacity={solid * out} />
              <rect x={LX + 16} y={cy - 4} width={70} height={8} rx={4} fill={ACC} opacity={0.6} />
              <rect x={RX} y={y} width={W} height={H} rx={8} fill={PALE} />
              <rect x={RX} y={y} width={W} height={H} rx={8} fill={MINT} opacity={solid * out} />
              <rect x={RX + 16} y={cy - 4} width={56} height={8} rx={4} fill={INK} opacity={0.55} />
              <line
                x1={x2} y1={cy} x2={x2 - (x2 - x1) * link * out} y2={cy}
                stroke={ACC} strokeWidth={4} strokeLinecap="round" strokeDasharray="2 8"
              />
              <g transform={`translate(${(x1 + x2) / 2} ${cy}) scale(${pop * out})`}>
                <circle r={17} fill={ACC} />
                <path d="M-7 0 l5 5 l9 -10" fill="none" stroke="#FFFFFF" strokeWidth={3.6}
                      strokeLinecap="round" strokeLinejoin="round" />
              </g>
            </g>
          )
        })}
      </svg>
    </AbsoluteFill>
  )
}

/* ═══════════════════ MAIL AGENT / דואר — sky ═══════════════════ */
// Envelopes fly into the AI core and come out the other side as sorted,
// summarised cards — one of them writing its draft. Every motion runs a whole
// number of cycles in 240 frames, so the loop seam is invisible.
export function AiInboxLoop() {
  const frame = useCurrentFrame()
  const ACC = '#4E9DD0', INK = '#2F6C94', SOFT = '#A9CFEA', PALE = '#DDEDF8', MINT = '#8FD9C6'
  const spin = loopPhase(frame, 240) * 360
  const pulse = 1 + 0.08 * Math.sin((frame / 240) * Math.PI * 6)          // 3 pulses/loop
  const twinkle = 0.6 + 0.4 * Math.abs(Math.sin((frame / 240) * Math.PI * 4))

  // envelope i enters from the left and is absorbed by the core
  const env = (offset: number, y0: number) => {
    const p = loopPhase(frame + offset, 240)
    const x = interpolate(p, [0, 0.42], [18, 176], { extrapolateRight: 'clamp', easing: Easing.bezier(0.4, 0, 0.6, 1) })
    const y = interpolate(p, [0, 0.42], [y0, 150], { extrapolateRight: 'clamp' })
    const sc = interpolate(p, [0.3, 0.42], [1, 0.35], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
    const op = interpolate(p, [0, 0.06, 0.36, 0.43, 1], [0, 1, 1, 0, 0])
    return { x, y, sc, op }
  }
  const e1 = env(0, 86), e2 = env(80, 150), e3 = env(160, 214)

  // the matching output card slides in after its envelope is absorbed
  const card = (offset: number) => {
    const p = loopPhase(frame + offset, 240)
    const slide = interpolate(p, [0.45, 0.58], [-26, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) })
    const op = interpolate(p, [0.45, 0.56, 0.92, 1], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
    const check = interpolate(p, [0.6, 0.68], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
    const type = interpolate(p, [0.58, 0.86], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
    return { slide, op, check, type }
  }
  const c1 = card(0), c2 = card(80), c3 = card(160)

  const Env = ({ x, y, sc, op }: { x: number; y: number; sc: number; op: number }) => (
    <g transform={`translate(${x} ${y}) scale(${sc})`} opacity={op}>
      <rect x={-22} y={-15} width={44} height={30} rx={6} fill={ACC} />
      <path d="M-22 -10 L0 5 L22 -10" fill="none" stroke={PALE} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
    </g>
  )
  const Card = ({ y, c, draft }: { y: number; c: ReturnType<typeof card>; draft?: boolean }) => (
    <g transform={`translate(${300 + c.slide} ${y})`} opacity={c.op}>
      <rect x={-54} y={-22} width={108} height={44} rx={10} fill="#FFFFFF" stroke={SOFT} strokeWidth={2} />
      <circle cx={-36} cy={0} r={9} fill={PALE} />
      <circle cx={-36} cy={0} r={9} fill={MINT} opacity={c.check} />
      <path d="M-40 0 l3 3 l6 -6" fill="none" stroke="#FFFFFF" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" opacity={c.check} />
      <rect x={-20} y={-9} width={draft ? 60 * c.type : 58} height={5} rx={2.5} fill={draft ? INK : SOFT} />
      <rect x={-20} y={3} width={draft ? 40 * c.type : 40} height={5} rx={2.5} fill={PALE} />
    </g>
  )

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* guide rails: in → core → out */}
        <path d="M24 150 H180 M240 150 H250" stroke={PALE} strokeWidth={3} strokeDasharray="3 10" strokeLinecap="round"
              strokeDashoffset={-loopPhase(frame, 30) * 26} />
        <Env {...e1} /><Env {...e2} /><Env {...e3} />
        {/* AI core */}
        <g transform="translate(210 150)">
          <circle r={58} fill="none" stroke={SOFT} strokeWidth={2} strokeDasharray="4 9" transform={`rotate(${spin})`} opacity={0.8} />
          <g transform={`scale(${pulse})`}>
            <rect x={-38} y={-38} width={76} height={76} rx={20} fill={INK} />
            <rect x={-38} y={-38} width={76} height={76} rx={20} fill="none" stroke={ACC} strokeWidth={3} />
            <Spark cx={0} cy={0} r={20} fill="#FFFFFF" />
          </g>
        </g>
        {/* sorted output */}
        <Card y={92} c={c1} />
        <Card y={150} c={c2} draft />
        <Card y={208} c={c3} />
        <Spark cx={262} cy={60} r={8} fill={ACC} k={twinkle} />
        <Spark cx={150} cy={250} r={6} fill={MINT} k={2 - twinkle} />
      </svg>
    </AbsoluteFill>
  )
}

/* ═══════════════════ PRODUCTION — cobalt ═══════════════════ */
// A spreadsheet fills row by row, a file flies along the dashed path, and the
// bars it feeds rise. Every motion completes whole cycles in 240 frames.
export function ProductionLoop() {
  const frame = useCurrentFrame()
  const ACC = '#2F73C4', INK = '#1F5496', SOFT = '#9DBFE6', PALE = '#DCE8F7', MINT = '#8FD9C6'
  const p = loopPhase(frame, 240)
  const twinkle = 0.6 + 0.4 * Math.abs(Math.sin((frame / 240) * Math.PI * 4))

  // sheet rows fill in (0–40%), hold, fade (90–100%)
  const row = (i: number) => interpolate(p, [0.04 + i * 0.08, 0.12 + i * 0.08], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  const sheetOp = interpolate(p, [0, 0.04, 0.9, 1], [0, 1, 1, 0])
  // the file flies (40–62%)
  const f = interpolate(p, [0.4, 0.62], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.4, 0, 0.6, 1) })
  const fx = interpolate(f, [0, 1], [150, 262]), fy = interpolate(f, [0, 0.5, 1], [150, 104, 150])
  const fileOp = interpolate(p, [0.39, 0.42, 0.6, 0.63], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  // bars rise (62–80%)
  const bar = (i: number) => interpolate(p, [0.62 + i * 0.04, 0.74 + i * 0.04, 0.9, 1], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) })
  const HEIGHTS = [44, 70, 56, 92]

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 420 300" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* spreadsheet */}
        <g transform="translate(40 78)" opacity={sheetOp}>
          <rect width={112} height={144} rx={12} fill="#FFFFFF" stroke={SOFT} strokeWidth={3} />
          <rect width={112} height={26} rx={12} fill={ACC} />
          <rect y={14} width={112} height={12} fill={ACC} />
          {[0, 1, 2, 3].map((i) => (
            <g key={i} transform={`translate(12 ${40 + i * 24})`}>
              <rect width={18} height={10} rx={3} fill={PALE} />
              <rect x={26} width={62 * row(i)} height={10} rx={3} fill={i % 2 ? SOFT : ACC} opacity={0.85} />
            </g>
          ))}
        </g>
        {/* path */}
        <path d="M150 150 Q 206 70 262 150" fill="none" stroke={PALE} strokeWidth={3} strokeDasharray="3 10"
              strokeLinecap="round" strokeDashoffset={-loopPhase(frame, 30) * 26} />
        {/* flying file */}
        <g transform={`translate(${fx} ${fy})`} opacity={fileOp}>
          <Doc x={-15} y={-20} w={30} h={40} fill={INK} line={PALE} />
        </g>
        {/* chart */}
        <g transform="translate(262 222)">
          <rect x={-6} y={0} width={132} height={4} rx={2} fill={SOFT} />
          {HEIGHTS.map((h, i) => {
            const k = bar(i)
            return <rect key={i} x={i * 32} y={-h * k} width={22} height={h * k} rx={6} fill={i === 3 ? INK : ACC} opacity={0.45 + i * 0.18} />
          })}
        </g>
        <Spark cx={372} cy={96} r={9} fill={ACC} k={twinkle} />
        <Spark cx={206} cy={242} r={6} fill={MINT} k={2 - twinkle} />
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
  maslaka: ClearingHouseLoop,
  comparison: ComparisonMatchLoop,
  mail: AiInboxLoop,
  production: ProductionLoop,
} as const

export type TabHeroScene = keyof typeof TAB_HERO_SCENES
