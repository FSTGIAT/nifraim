import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'

/**
 * Background of the customer-portal tab: the agent (a softly breathing hub)
 * connected to their customers (small nodes) by faint curved lines. Every few
 * seconds a small dot travels from the agent to one customer, and that
 * customer's node glows as it arrives — "the agent shares a portal with the
 * customer". Calm on purpose: one pulse in flight at a time per line, long
 * gaps, low opacity. Not the hero's figure-and-ring loop.
 *
 * Laid out for RTL reading: the agent sits on the right, customers fan out to
 * the left, mostly in the lower half (the page's cards cover the top).
 *
 * Loop-perfect: 1800 frames; each line's cycle is 600 frames (divides 1800)
 * and the hub breathes 3× per loop, so frame N equals frame 0.
 */
export const PORTAL_CONN_FRAMES = 1800 // 60s @ 30fps
export const PORTAL_CONN_W = 1600
export const PORTAL_CONN_H = 900

const TAU = Math.PI * 2
const CYCLE = 600          // frames per line cycle (20s)
const TRAVEL = 150         // frames a pulse takes to reach the customer
const GLOW = 90            // frames the customer glows after arrival

const HUB = { x: 1290, y: 640 }
// Customers + a stagger (frames) so pulses leave one after another, never at once.
const CUSTOMERS = [
  { x: 1010, y: 520, delay: 0 },
  { x: 860, y: 700, delay: 85 },
  { x: 640, y: 560, delay: 170 },
  { x: 470, y: 760, delay: 255 },
  { x: 300, y: 600, delay: 340 },
  { x: 1080, y: 810, delay: 425 },
  { x: 180, y: 420, delay: 510 },
]

// Quadratic curve hub → customer, bowed upward for a soft arc.
function ctrl(c: { x: number; y: number }) {
  return { x: (HUB.x + c.x) / 2, y: Math.min(HUB.y, c.y) - 120 - Math.abs(HUB.x - c.x) * 0.08 }
}
function pointAt(c: { x: number; y: number }, t: number) {
  const k = ctrl(c)
  const u = 1 - t
  return {
    x: u * u * HUB.x + 2 * u * t * k.x + t * t * c.x,
    y: u * u * HUB.y + 2 * u * t * k.y + t * t * c.y,
  }
}
const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)

// A person silhouette (head + filled shoulders) centred in a node, clipped to
// the node's circle so the shoulders sit on its lower edge. `s` scales it.
const Person: React.FC<{ x: number; y: number; s: number; fill: string; opacity: number }> = ({ x, y, s, fill, opacity }) => {
  const id = `pc-${Math.round(x)}-${Math.round(y)}`
  return (
    <g opacity={opacity}>
      <clipPath id={id}><circle cx={x} cy={y} r={9 * s} /></clipPath>
      <g clipPath={`url(#${id})`}>
        <circle cx={x} cy={y - 2.2 * s} r={3.3 * s} fill={fill} />
        <ellipse cx={x} cy={y + 7.2 * s} rx={6.4 * s} ry={4.6 * s} fill={fill} />
      </g>
    </g>
  )
}

type Props = { color?: string; ink?: string }

export const PortalConnectionsBackdrop: React.FC<Props> = ({ color = '#4E9DD0', ink = '#35719A' }) => {
  const frame = useCurrentFrame() % PORTAL_CONN_FRAMES
  const breathe = 0.5 + 0.5 * Math.sin((frame / PORTAL_CONN_FRAMES) * TAU * 3)

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent' }}>
      <svg width={PORTAL_CONN_W} height={PORTAL_CONN_H} viewBox={`0 0 ${PORTAL_CONN_W} ${PORTAL_CONN_H}`}>
        {CUSTOMERS.map((c, i) => {
          const k = ctrl(c)
          const local = (frame - c.delay + PORTAL_CONN_FRAMES) % CYCLE
          const inFlight = local < TRAVEL
          const t = ease(Math.min(1, local / TRAVEL))
          const p = pointAt(c, t)
          const glowT = local >= TRAVEL && local < TRAVEL + GLOW ? 1 - (local - TRAVEL) / GLOW : 0
          return (
            <g key={i}>
              {/* the connection */}
              <path
                d={`M${HUB.x},${HUB.y} Q${k.x},${k.y} ${c.x},${c.y}`}
                fill="none" stroke={color} strokeOpacity={0.14} strokeWidth={1.6} strokeDasharray="2 7" strokeLinecap="round"
              />
              {/* pulse travelling agent → customer */}
              {inFlight && (
                <g opacity={Math.min(1, local / 20) * 0.55}>
                  <circle cx={p.x} cy={p.y} r={9} fill={color} fillOpacity={0.12} />
                  <circle cx={p.x} cy={p.y} r={3.5} fill={ink} />
                </g>
              )}
              {/* customer node + arrival glow */}
              <circle cx={c.x} cy={c.y} r={18 + glowT * 14} fill={color} fillOpacity={0.05 + glowT * 0.1} />
              <circle cx={c.x} cy={c.y} r={10} fill="#fff" fillOpacity={0.7} stroke={color} strokeOpacity={0.35 + glowT * 0.35} strokeWidth={1.6} />
              <Person x={c.x} y={c.y} s={1} fill={ink} opacity={0.3 + glowT * 0.3} />
            </g>
          )
        })}

        {/* the agent: a breathing hub */}
        <circle cx={HUB.x} cy={HUB.y} r={58 + breathe * 10} fill={color} fillOpacity={0.05 + breathe * 0.03} />
        <circle cx={HUB.x} cy={HUB.y} r={34} fill="#fff" fillOpacity={0.75} stroke={color} strokeOpacity={0.45} strokeWidth={2} />
        <Person x={HUB.x} y={HUB.y} s={2.6} fill={ink} opacity={0.42} />
      </svg>
    </AbsoluteFill>
  )
}
