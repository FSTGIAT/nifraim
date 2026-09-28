import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame, Easing } from 'remotion'

/**
 * Mailbox-connect window (Nifraim Mail Agent): what the agent gets, as a loop.
 *
 *   👤 customer ──mail──► ✉ agent's inbox ── AI draft (from Nifraim's data) ──►
 *   reply ──► 👤 customer ✓      ·      🏛 insurer ──agreement──► shelf ✓
 *
 * Mail Agent reads mail from the senders the agent approved, drafts answers
 * (e.g. a customer asking about their policy/savings), sends on approval, and
 * loads agreements insurers send back. Loop-perfect over 300 frames (10s).
 */
export const MAIL_AGENT_LOOP_FRAMES = 300
export const MAIL_AGENT_LOOP_SIZE = { width: 480, height: 720 }

type Props = { accent?: string; deep?: string; soft?: string }

const ease = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) })
const win = (f: number, a: number, b: number, c: number, d: number) =>
  interpolate(f, [a, b, c, d], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
const qb = (t: number, p0: number[], p1: number[], p2: number[]) => [
  (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
  (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1],
]

const INBOX = [360, 250]     // the agent's mailbox (right — RTL start)
const CUSTOMER = [120, 150]  // a customer (left, top)
const INSURER = [120, 380]   // an insurer (left, bottom)
const SHELF = [330, 470]     // where agreements land

export const MailAgentLoop: React.FC<Props> = ({ accent = '#4E9DD0', deep = '#2F6C94', soft = '#E8F1F8' }) => {
  const f = useCurrentFrame()
  const t = f / MAIL_AGENT_LOOP_FRAMES
  const bob = Math.sin(t * Math.PI * 2 * 2) * 5

  // 1. a customer's question arrives (10–60)
  const inT = ease(f, 10, 60)
  const [ix, iy] = qb(inT, [CUSTOMER[0] + 40, CUSTOMER[1]], [250, 120], [INBOX[0] - 60, INBOX[1] - 20])
  const inOp = win(f, 8, 16, 56, 64)
  // 2. Mail Agent reads + drafts from the data (64–130): inbox glows, draft types itself
  const glow = win(f, 60, 72, 120, 132)
  const draftOp = win(f, 66, 78, 150, 162)
  const typed = ease(f, 78, 124)
  const spark = win(f, 80, 92, 118, 130)
  // 3. the reply goes back to the customer, approved (132–182)
  const outT = ease(f, 132, 182)
  const [ox, oy] = qb(outT, [INBOX[0] - 60, INBOX[1] + 10], [240, 230], [CUSTOMER[0] + 44, CUSTOMER[1] + 20])
  const outOp = win(f, 128, 136, 178, 186)
  const custCheck = interpolate(f, [182, 192, 196, 280, 292], [0, 1.15, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  // 4. an insurer sends the agreement → shelf (190–250)
  const aT = ease(f, 190, 250)
  const [ax, ay] = qb(aT, [INSURER[0] + 40, INSURER[1] + 10], [230, 520], [SHELF[0], SHELF[1] - 36])
  const aOp = win(f, 186, 194, 284, 296)
  const shelfCheck = interpolate(f, [250, 260, 264, 282, 294], [0, 1.15, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })

  const cap = (a: number, b: number) =>
    interpolate(f, [a, a + 10, b, b + 10], [0.35, 1, 1, 0.35], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  const caps = [
    { label: 'קורא את המיילים', o: cap(10, 62) },
    { label: 'מנסח תשובה מהנתונים', o: cap(66, 128) },
    { label: 'שולח באישורכם', o: cap(132, 184) },
    { label: 'טוען הסכמים', o: cap(190, 262) },
  ]

  return (
    <AbsoluteFill style={{ background: `linear-gradient(170deg, #FFFFFF 0%, ${soft} 100%)`, fontFamily: 'Heebo, sans-serif' }}>
      {[[70, 640, 130], [400, 670, 160], [250, 700, 120]].map(([cx, cy, r], i) => (
        <div key={i} style={{ position: 'absolute', left: cx - r, top: cy - r / 2, width: r * 2, height: r, borderRadius: '50%',
          background: '#fff', opacity: 0.85, filter: 'blur(6px)', transform: `translateY(${Math.sin(t * Math.PI * 2 + i) * 4}px)` }} />
      ))}

      <svg width={480} height={600} viewBox="40 60 440 550" style={{ position: 'absolute', left: 0, top: 10 }}>
        {/* routes */}
        <path d={`M${CUSTOMER[0] + 40} ${CUSTOMER[1]} Q 250 120 ${INBOX[0] - 60} ${INBOX[1] - 20}`} fill="none" stroke={accent} strokeOpacity={0.3} strokeWidth={2.5} strokeDasharray="4 9" strokeDashoffset={-f * 1.2} />
        <path d={`M${INSURER[0] + 40} ${INSURER[1] + 10} Q 230 520 ${SHELF[0]} ${SHELF[1] - 36}`} fill="none" stroke={deep} strokeOpacity={0.25} strokeWidth={2.5} strokeDasharray="4 9" strokeDashoffset={-f * 1.2} />

        {/* the customer */}
        <g transform={`translate(${CUSTOMER[0]} ${CUSTOMER[1] + bob * 0.6})`}>
          <circle r={44} fill="#fff" stroke={accent} strokeWidth={3} />
          <circle cy={-10} r={13} fill={soft} stroke={deep} strokeWidth={2.6} />
          <path d="M-22 26 a22 18 0 0 1 44 0" fill={soft} stroke={deep} strokeWidth={2.6} />
          <g transform={`translate(30 -32) scale(${custCheck})`}>
            <circle r={14} fill="#2E844A" />
            <path d="M-6 0 l4 4 l8 -9" stroke="#fff" strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </g>
        </g>

        {/* the insurer */}
        <g transform={`translate(${INSURER[0]} ${INSURER[1] - bob * 0.6})`}>
          <path d="M-48 -18 L0 -50 L48 -18 Z" fill={soft} stroke={deep} strokeWidth={3} strokeLinejoin="round" />
          <rect x={-44} y={-18} width={88} height={7} fill={deep} />
          {[-30, -10, 10, 30].map((x) => <rect key={x} x={x - 4.5} y={-7} width={9} height={42} rx={3} fill="#fff" stroke={deep} strokeWidth={2.2} />)}
          <rect x={-52} y={36} width={104} height={8} rx={3} fill={deep} />
        </g>

        {/* the agent's inbox (Mail Agent) */}
        <g transform={`translate(${INBOX[0]} ${INBOX[1] + bob})`}>
          <circle r={86} fill={accent} opacity={0.14 * glow} />
          <rect x={-62} y={-44} width={124} height={88} rx={14} fill="#fff" stroke={accent} strokeWidth={3} />
          <path d="M-62 -36 L0 10 L62 -36" fill="none" stroke={deep} strokeWidth={3.5} strokeLinejoin="round" />
          <circle cx={46} cy={-40} r={13} fill={deep} />
          <text x={46} y={-35} textAnchor="middle" fontSize={14} fontWeight={800} fill="#fff">@</text>
        </g>

        {/* the AI draft, typing itself from the data */}
        <g opacity={draftOp} transform={`translate(${INBOX[0]} ${INBOX[1] + 96})`}>
          <rect x={-70} y={-26} width={140} height={62} rx={12} fill="#fff" stroke={deep} strokeWidth={2.4} />
          <rect x={-54} y={-12} width={108 * Math.min(1, typed * 1.4)} height={6} rx={3} fill={accent} />
          <rect x={-54} y={2} width={92 * Math.max(0, Math.min(1, typed * 1.4 - 0.3))} height={6} rx={3} fill={accent} opacity={0.75} />
          <rect x={-54} y={16} width={70 * Math.max(0, Math.min(1, typed * 1.4 - 0.6))} height={6} rx={3} fill={accent} opacity={0.55} />
          <g opacity={spark} transform={`translate(64 -30) rotate(${f * 3})`}>
            <path d="M0 -12 L3 -3 L12 0 L3 3 L0 12 L-3 3 L-12 0 L-3 -3 Z" fill={deep} />
          </g>
        </g>

        {/* the shelf */}
        <rect x={SHELF[0] - 74} y={SHELF[1] - 6} width={148} height={14} rx={7} fill="#fff" stroke={accent} strokeOpacity={0.6} strokeWidth={2.5} />
        <g transform={`translate(${SHELF[0] + 70} ${SHELF[1] - 26}) scale(${shelfCheck})`}>
          <circle r={14} fill="#2E844A" />
          <path d="M-6 0 l4 4 l8 -9" stroke="#fff" strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>

        {/* incoming question */}
        <g opacity={inOp} transform={`translate(${ix} ${iy})`}>
          <rect x={-20} y={-14} width={40} height={28} rx={6} fill="#fff" stroke={accent} strokeWidth={2.4} />
          <path d="M-20 -10 L0 4 L20 -10" fill="none" stroke={accent} strokeWidth={2.2} />
        </g>
        {/* outgoing reply */}
        <g opacity={outOp} transform={`translate(${ox} ${oy}) rotate(${160 + outT * 30})`}>
          <path d="M-18 0 L18 -12 L6 14 L2 4 Z" fill={deep} />
        </g>
        {/* the agreement */}
        <g opacity={aOp} transform={`translate(${ax} ${ay}) rotate(${(1 - aT) * -14})`}>
          <path d="M-20 -28 h28 l12 12 v44 h-40 z" fill="#fff" stroke={deep} strokeWidth={2.4} strokeLinejoin="round" />
          <path d="M-12 -6 h22 M-12 4 h18 M-12 14 h22" stroke={accent} strokeWidth={2.2} strokeLinecap="round" />
        </g>
      </svg>

      <div style={{ position: 'absolute', left: 14, right: 14, bottom: 40, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10, direction: 'rtl' }}>
        {caps.map((c) => (
          <div key={c.label} style={{ opacity: c.o, transform: `translateY(${(1 - c.o) * 6}px)`, padding: '9px 16px', borderRadius: 999,
            background: '#fff', border: `1.5px solid ${accent}55`, color: deep, fontSize: 19, fontWeight: 800,
            boxShadow: `0 6px 18px ${accent}33` }}>
            {c.label}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  )
}
