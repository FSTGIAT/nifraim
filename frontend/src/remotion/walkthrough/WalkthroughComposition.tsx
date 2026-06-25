import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame } from 'remotion'
import { steps, offsets, stepFrames, isCard, toCanvas, shotNumber, SHOT_TOTAL, WALKTHROUGH_DURATION, type ShotStep } from './steps'
import { WalkthroughStep, CLICK_AT } from './WalkthroughStep'
import { CardScreen } from './CardScreen'
import { Cursor, cursorState } from './Cursor'

const FONT = "'Heebo', sans-serif"
const CREAM = '#FFFBF4'
const BRAND = '#F57C00'
const BRAND_DEEP = '#E65100'
const INK_SOFT = '#6B5F50'

const TRAVEL_FRAMES = 40
// Cursor enters from off-canvas bottom-right on the very first step.
const START = { x: 1850, y: 1040 }

/** Resolve the cursor's current canvas position + press, skipping card steps. */
function useCursor(frame: number) {
  // which step are we in?
  let si = 0
  for (let k = 0; k < steps.length; k++) {
    if (frame >= offsets[k]) si = k
    else break
  }
  const step = steps[si]
  if (isCard(step)) return null // cursor hidden during narration cards

  const local = frame - offsets[si]
  const curr = toCanvas(step, step.target)

  // nearest previous SHOT target (skip cards); else the off-screen start
  let prev = START
  for (let k = si - 1; k >= 0; k--) {
    const p = steps[k]
    if (!isCard(p)) {
      prev = toCanvas(p, p.target)
      break
    }
  }

  return cursorState({
    prev,
    curr,
    local,
    travelFrames: TRAVEL_FRAMES,
    clickAt: CLICK_AT,
    click: step.click !== false,
  })
}

export function WalkthroughComposition() {
  const frame = useCurrentFrame()
  const cur = useCursor(frame)

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(130% 90% at 80% -10%, ${BRAND}1A 0%, transparent 55%), radial-gradient(120% 90% at 10% 110%, ${BRAND_DEEP}12 0%, transparent 55%), ${CREAM}`,
        fontFamily: FONT,
        overflow: 'hidden',
      }}
    >
      {/* background music — royalty-free, looped, gentle fade in/out */}
      <Audio
        src={staticFile('walkthrough/music.mp3')}
        loop
        volume={(f) =>
          interpolate(
            f,
            [0, 36, WALKTHROUGH_DURATION - 60, WALKTHROUGH_DURATION - 6],
            [0, 0.48, 0.48, 0],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          )
        }
      />

      {/* atmospheric blur blobs */}
      <div
        style={{
          position: 'absolute',
          width: 520,
          height: 520,
          borderRadius: '50%',
          background: `${BRAND}1F`,
          filter: 'blur(90px)',
          top: -180,
          right: -160,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 460,
          height: 460,
          borderRadius: '50%',
          background: `${BRAND_DEEP}14`,
          filter: 'blur(100px)',
          bottom: -180,
          left: -120,
        }}
      />

      {/* brand wordmark (bottom-right, clear of the top caption banner) */}
      <div
        style={{
          position: 'absolute',
          bottom: 26,
          right: 44,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          direction: 'rtl',
          opacity: 0.92,
        }}
      >
        <div
          style={{
            width: 14,
            height: 14,
            borderRadius: '50%',
            background: BRAND,
            boxShadow: `0 0 0 4px ${BRAND}22`,
          }}
        />
        <span style={{ fontSize: 24, fontWeight: 800, color: BRAND_DEEP, letterSpacing: 0.5 }}>Nifraim</span>
        <span style={{ fontSize: 15, fontWeight: 600, color: INK_SOFT }}>· סוכן AI</span>
      </div>

      {/* per-step screens (screenshots + narration cards) */}
      {steps.map((step, i) => (
        <Sequence
          key={i}
          from={offsets[i]}
          durationInFrames={stepFrames(step)}
          name={isCard(step) ? `card-${i}` : `shot-${i}`}
        >
          {isCard(step) ? (
            <CardScreen step={step} durationInFrames={stepFrames(step)} />
          ) : (
            <WalkthroughStep
              step={step as ShotStep}
              index={shotNumber(i) - 1}
              total={SHOT_TOTAL}
              durationInFrames={stepFrames(step)}
            />
          )}
        </Sequence>
      ))}

      {/* global cursor on top — only on screenshot steps */}
      {cur ? <Cursor x={cur.x} y={cur.y} press={cur.press} /> : null}
    </AbsoluteFill>
  )
}
