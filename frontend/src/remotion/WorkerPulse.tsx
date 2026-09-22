import React from 'react'
import { AbsoluteFill, useCurrentFrame } from 'remotion'

/**
 * Heartbeat rings behind the local-worker icon.
 *
 * This is a STATUS signal, not decoration: the worker posts a heartbeat every
 * ≤15s and the card is green only while `last_seen` is inside the 90s window,
 * so a pulse that keeps beating is literally what "still reporting" looks like.
 * It is mounted ONLY in the online state — the offline card is completely
 * still, which is what makes the two states read as different things rather
 * than the same card in a different colour.
 *
 * Loop-perfect: three rings share one cycle, staggered by a third of it. Each
 * ring scales outward while fading to 0, so ring N's disappearance coincides
 * with ring N+1's birth and the wrap is seamless.
 */
export const WORKER_PULSE_FRAMES = 90 // 3s @ 30fps — one calm beat

type Props = { color?: string }

const RINGS = [0, 1 / 3, 2 / 3]

export const WorkerPulse: React.FC<Props> = ({ color = '#1B5E20' }) => {
  const frame = useCurrentFrame()
  const t = frame / WORKER_PULSE_FRAMES // 0..1

  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
      {RINGS.map((phase, i) => {
        // Each ring runs its own 0..1 life, offset by its phase.
        const life = (t + phase) % 1
        // ease-out expansion: fast at birth, settling as it fades.
        const eased = 1 - Math.pow(1 - life, 2)
        const scale = 0.55 + eased * 0.95
        // Fade in over the first 12% so a ring never pops into existence.
        const fadeIn = Math.min(1, life / 0.12)
        const opacity = 0.42 * fadeIn * (1 - life)
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              width: 54,
              height: 54,
              borderRadius: '50%',
              border: `2px solid ${color}`,
              transform: `scale(${scale})`,
              opacity,
            }}
          />
        )
      })}
    </AbsoluteFill>
  )
}
