import React from 'react'
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from 'remotion'

/**
 * MailEnvelopeIntro
 * -----------------
 * One-shot opening played when the agent opens a mail the AI answered: the
 * envelope rises, the flap swings open, the reply slides out with its lines
 * "writing in", then the envelope drops away and the letter settles where
 * the real (editable) letter card takes over in MailTab.vue.
 *
 * Colours come from the host page's CSS variables (the Player renders inline
 * DOM, so `var(--tab-mail…)` resolves) — the envelope stays on the mail tab's
 * identity palette without duplicating hex values. The air-mail stripe is the
 * shared motif with the letter card's top edge.
 *
 * Mounted through MailEnvelopeIntro.vue (React island, direction:ltr fix).
 */

export const ENVELOPE_INTRO_FRAMES = 46 // ~1.5s @ 30fps
export const ENVELOPE_W = 640
export const ENVELOPE_H = 440

type Props = { name: string; initial: string }

const ACC = 'var(--tab-mail, #4E9DD0)'
const INK = 'var(--tab-mail-ink, #2F6C94)'
const PAPER = 'var(--card-bg, #fff)'
const BODY = 'color-mix(in srgb, var(--tab-mail, #4E9DD0) 16%, #fff)'
const POCKET = 'color-mix(in srgb, var(--tab-mail, #4E9DD0) 24%, #fff)'
const FLAP_OUT = 'color-mix(in srgb, var(--tab-mail, #4E9DD0) 34%, #fff)'
const FLAP_IN = 'color-mix(in srgb, var(--tab-mail, #4E9DD0) 10%, #fff)'
const LINE = 'color-mix(in srgb, var(--tab-mail-ink, #2F6C94) 22%, #fff)'

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const
const out = Easing.bezier(0.16, 1, 0.3, 1)
const inOut = Easing.bezier(0.65, 0, 0.35, 1)

// Envelope geometry (viewBox units)
const EX = 140, EY = 176, EW = 360, EH = 214
const CX = EX + EW / 2

export const MailEnvelopeIntro: React.FC<Props> = ({ name, initial }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  // 1. arrive
  const arrive = spring({ frame, fps, config: { damping: 16, stiffness: 140 } })
  // 2. flap: 1 (closed, pointing down) → -1 (open, pointing up)
  const flap = interpolate(frame, [8, 20], [1, -1], { ...clamp, easing: inOut })
  // 3. letter rises out of the pocket
  const rise = interpolate(frame, [17, 32], [0, 1], { ...clamp, easing: out })
  // 4. envelope drops away, letter settles centre-stage
  const settle = interpolate(frame, [31, 45], [0, 1], { ...clamp, easing: out })

  const envY = interpolate(arrive, [0, 1], [26, 0]) + settle * 70
  const envOpacity = Math.min(1, arrive * 1.4) * (1 - settle)
  const flapFront = flap > 0 // closed half: drawn over the letter

  const letterW = 316, letterH = 206
  const letterX = CX - letterW / 2
  const letterY = EY + 12 - rise * 150 + settle * 72
  const letterScale = 1 + settle * 0.42
  const sealOpacity = interpolate(frame, [6, 12], [1, 0], clamp)

  // The reply is already written (drafted when the mail arrived) — the lines
  // are there from the start; animating them in read as "AI writing now".
  const lines = [0.86, 0.94, 0.72, 0.9, 0.58]

  const flapTip = EY + 124 * flap
  const flapPath = `M${EX} ${EY} L${CX} ${flapTip} L${EX + EW} ${EY} Z`

  return (
    <AbsoluteFill style={{ background: 'transparent' }}>
      <svg viewBox={`0 0 ${ENVELOPE_W} ${ENVELOPE_H}`} width="100%" height="100%">
        <defs>
          <clipPath id="mei-env">
            <rect x={EX} y={EY} width={EW} height={EH} rx={14} />
          </clipPath>
        </defs>

        <g transform={`translate(0 ${envY})`} opacity={envOpacity}>
          {/* back of the envelope */}
          <rect x={EX} y={EY} width={EW} height={EH} rx={14} style={{ fill: BODY }} />
          {/* open flap sits behind the letter */}
          {!flapFront && <path d={flapPath} style={{ fill: FLAP_IN }} strokeLinejoin="round" />}
        </g>

        {/* the reply */}
        <g
          transform={`translate(${CX} ${letterY + letterH / 2}) scale(${letterScale}) translate(${-CX} ${-(letterY + letterH / 2)})`}
          opacity={interpolate(frame, [14, 18], [0, 1], clamp)}
        >
          <rect x={letterX} y={letterY} width={letterW} height={letterH} rx={10} style={{ fill: PAPER }}
                filter="drop-shadow(0 6px 14px rgba(20,50,80,.14))" />
          {/* air-mail edge */}
          <rect x={letterX} y={letterY} width={letterW} height={6} rx={3} style={{ fill: ACC }} />
          <rect x={letterX} y={letterY} width={letterW} height={6} rx={3}
                style={{ fill: 'none', stroke: INK, strokeWidth: 6, strokeDasharray: '12 12' }} />
          {/* addressee: avatar + name, right-aligned for Hebrew */}
          <circle cx={letterX + letterW - 34} cy={letterY + 38} r={15} style={{ fill: BODY }} />
          <text x={letterX + letterW - 34} y={letterY + 43} textAnchor="middle"
                style={{ fill: INK, fontSize: 14, fontWeight: 800, fontFamily: 'Heebo, sans-serif' }}>{initial}</text>
          <text x={letterX + letterW - 58} y={letterY + 44} textAnchor="end"
                style={{ fill: 'var(--text, #1f2933)', fontSize: 15, fontWeight: 800, fontFamily: 'Heebo, sans-serif' }}>
            {name}
          </text>
          {lines.map((w, i) => {
            const full = (letterW - 48) * w
            const cur = full
            return (
              <rect key={i} x={letterX + letterW - 24 - cur} y={letterY + 72 + i * 22} width={cur} height={7} rx={3.5}
                    style={{ fill: LINE }} />
            )
          })}
        </g>

        <g transform={`translate(0 ${envY})`} opacity={envOpacity}>
          {/* front pocket (V-notched), hides the letter's lower half */}
          <g clipPath="url(#mei-env)">
            <path d={`M${EX} ${EY + 30} L${CX} ${EY + 128} L${EX + EW} ${EY + 30} V${EY + EH} H${EX} Z`}
                  style={{ fill: POCKET }} />
            <path d={`M${EX} ${EY + EH} L${CX} ${EY + 118} L${EX + EW} ${EY + EH}`}
                  style={{ fill: 'none', stroke: BODY, strokeWidth: 2 }} />
          </g>
          {/* air-mail rim */}
          <rect x={EX + 3} y={EY + 3} width={EW - 6} height={EH - 6} rx={12}
                style={{ fill: 'none', stroke: ACC, strokeWidth: 6 }} />
          <rect x={EX + 3} y={EY + 3} width={EW - 6} height={EH - 6} rx={12}
                style={{ fill: 'none', stroke: INK, strokeWidth: 6, strokeDasharray: '14 14' }} />
          {/* closed flap + wax-style seal with the sender's initial */}
          {flapFront && (
            <>
              <path d={flapPath} style={{ fill: FLAP_OUT }} strokeLinejoin="round" />
              <g opacity={sealOpacity}>
                <circle cx={CX} cy={flapTip - 6} r={17} style={{ fill: INK }} />
                <text x={CX} y={flapTip - 1} textAnchor="middle"
                      style={{ fill: '#fff', fontSize: 15, fontWeight: 800, fontFamily: 'Heebo, sans-serif' }}>{initial}</text>
              </g>
            </>
          )}
        </g>
      </svg>
    </AbsoluteFill>
  )
}
