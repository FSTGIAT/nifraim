import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from 'remotion'
import { fitInfo, toCanvas, type ShotStep } from './steps'
import { Ripple } from './Ripple'
import { Caption } from './Caption'

export const CLICK_AT = 46 // local frame the press lands on

/**
 * One screen of the walkthrough: the screenshot fit into a framed card with a
 * gentle Ken-Burns zoom toward the press point, the click ripple/glow, and the
 * caption. Runs inside a <Sequence>, so `useCurrentFrame()` is step-local.
 */
export function WalkthroughStep({
  step,
  index,
  total,
  durationInFrames,
}: {
  step: ShotStep
  index: number
  total: number
  durationInFrames: number
}) {
  const local = useCurrentFrame()
  const fit = fitInfo(step)
  const tc = toCanvas(step, step.target)
  const click = step.click !== false

  // Entrance: fade + settle.
  const opacity = interpolate(local, [0, 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  })

  // Ken-Burns: zoom IN to the target, then zoom OUT — a gentle in/out per slide.
  const ken = interpolate(
    local,
    [0, durationInFrames * 0.5, durationInFrames],
    [1.015, 1.06, 1.015],
    { extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) },
  )
  const originX = ((tc.x - fit.drawX) / fit.drawW) * 100
  const originY = ((tc.y - fit.drawY) / fit.drawH) * 100

  return (
    <AbsoluteFill>
      {/* framed screenshot */}
      <div
        style={{
          position: 'absolute',
          left: fit.drawX,
          top: fit.drawY,
          width: fit.drawW,
          height: fit.drawH,
          borderRadius: 18,
          overflow: 'hidden',
          background: '#fff',
          border: '1px solid rgba(234,223,204,0.9)',
          boxShadow: '0 30px 70px rgba(26,20,16,0.20), 0 8px 22px rgba(26,20,16,0.10)',
          opacity,
          transform: `scale(${ken})`,
          transformOrigin: `${originX}% ${originY}%`,
        }}
      >
        <Img src={staticFile(step.image)} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>

      {/* click ripple + glow at the target (canvas space, outside the zoomed card
          so it tracks the unscaled point cleanly) */}
      {click ? <Ripple x={tc.x} y={tc.y} frame={local} clickAt={CLICK_AT} /> : null}

      <Caption text={step.caption} index={index} total={total} local={local} durationInFrames={durationInFrames} />
    </AbsoluteFill>
  )
}
