import { Easing, interpolate } from 'remotion'

// macOS-style arrow pointer. Tip (hotspot) sits at viewBox (4, 2).
const VB = 24
const SIZE = 52
const TIP_X = (4 / VB) * SIZE
const TIP_Y = (2 / VB) * SIZE

export function CursorArrow({ press }: { press: number }) {
  // press ∈ [0,1] — small dip + scale on click.
  const scale = 1 - press * 0.18
  return (
    <div style={{ transform: `scale(${scale})`, transformOrigin: `${TIP_X}px ${TIP_Y}px` }}>
      <svg
        width={SIZE}
        height={SIZE}
        viewBox="0 0 24 24"
        style={{ filter: 'drop-shadow(0 4px 10px rgba(26,20,16,0.45))' }}
      >
        <path
          d="M4 2 L4 19.5 L8.6 15.4 L11.6 21.6 L14.4 20.3 L11.4 14.3 L17.6 14.3 Z"
          fill="#FFFFFF"
          stroke="#1A1410"
          strokeWidth={1.4}
          strokeLinejoin="round"
        />
      </svg>
    </div>
  )
}

/**
 * Position the cursor at a canvas point, with the arrow tip on that point.
 * Renders the press ring underneath when pressing.
 */
export function Cursor({
  x,
  y,
  press,
}: {
  x: number
  y: number
  press: number
}) {
  return (
    <div
      style={{
        position: 'absolute',
        left: x - TIP_X,
        top: y - TIP_Y,
        pointerEvents: 'none',
      }}
    >
      {/* click pulse ring right under the tip */}
      {press > 0 ? (
        <div
          style={{
            position: 'absolute',
            left: TIP_X - 18,
            top: TIP_Y - 18,
            width: 36,
            height: 36,
            borderRadius: '50%',
            background: '#F57C0033',
            border: '2px solid #F57C00',
            transform: `scale(${0.6 + press * 0.8})`,
            opacity: press,
          }}
        />
      ) : null}
      <CursorArrow press={press} />
    </div>
  )
}

/**
 * Global cursor motion across the whole timeline. Given the current step index,
 * local frame, and the canvas-space targets, eases from the previous target to
 * the current one, then holds. Returns position + press amount.
 */
export function cursorState({
  prev,
  curr,
  local,
  travelFrames,
  clickAt,
  click,
}: {
  prev: { x: number; y: number }
  curr: { x: number; y: number }
  local: number
  travelFrames: number
  clickAt: number
  click: boolean
}): { x: number; y: number; press: number } {
  const t = interpolate(local, [0, travelFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.45, 0, 0.15, 1),
  })
  // slight upward bow so the move feels natural, not a straight slide
  const mx = (prev.x + curr.x) / 2
  const my = Math.min(prev.y, curr.y) - 90
  const x = (1 - t) * (1 - t) * prev.x + 2 * (1 - t) * t * mx + t * t * curr.x
  const y = (1 - t) * (1 - t) * prev.y + 2 * (1 - t) * t * my + t * t * curr.y

  const press = click
    ? interpolate(local, [clickAt - 4, clickAt, clickAt + 10], [0, 1, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 0

  return { x, y, press }
}
