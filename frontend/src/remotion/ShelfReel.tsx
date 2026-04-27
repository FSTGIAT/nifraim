import { useCurrentFrame, useVideoConfig, interpolate, AbsoluteFill } from 'remotion'

export type ShelfReelType =
  | 'lost'
  | 'agents'
  | 'upload'
  | 'bonus'
  | 'invites'
  | 'ai'

export interface ShelfReelProps {
  type: ShelfReelType
}

const FONT = 'Heebo, sans-serif'

/**
 * Decorative looping animations for each agency "book".
 *
 * IMPORTANT: shapes are sized in pixels relative to a 400×240 composition
 * canvas. The Remotion Player scales that canvas to fit whatever container
 * we mount it in (via compositionWidth/compositionHeight on the Player). So
 * "big" here is what fills the design canvas — final on-screen size depends
 * on the host element.
 */
export function ShelfReel({ type }: ShelfReelProps) {
  const frame = useCurrentFrame()
  const { width, height, fps, durationInFrames } = useVideoConfig()
  const t = frame / Math.max(1, durationInFrames - 1)

  const wrap = (children: React.ReactNode) => (
    <AbsoluteFill style={{ background: 'transparent', fontFamily: FONT, overflow: 'hidden' }}>
      {children}
    </AbsoluteFill>
  )

  const args: ReelArgs = { frame, fps, width, height, t }

  switch (type) {
    case 'lost':    return wrap(<LostReel {...args} />)
    case 'agents':  return wrap(<AgentsReel {...args} />)
    case 'upload':  return wrap(<UploadReel {...args} />)
    case 'bonus':   return wrap(<BonusReel {...args} />)
    case 'invites': return wrap(<InvitesReel {...args} />)
    case 'ai':      return wrap(<AiReel {...args} />)
  }
}

interface ReelArgs {
  frame: number
  fps: number
  width: number
  height: number
  t: number
}

// ─── 1) Lost money ─────────────────────────────────────────────────────────
//      Big falling coins onto a fat declining bar chart that fills the stage.
function LostReel({ frame, width, height }: ReelArgs) {
  const bars = [0.92, 0.78, 0.62, 0.48, 0.32, 0.20]
  const slot = width / (bars.length + 0.5)
  const barW = slot * 0.7
  const baseY = height - 6

  return (
    <>
      {/* Falling coins — 6 large ones */}
      {[0, 1, 2, 3, 4, 5].map((i) => {
        const period = 90
        const local = (frame + i * 14) % period
        const fy = interpolate(local, [0, period], [-40, height - 30], { extrapolateRight: 'clamp' })
        const fx = (i + 0.7) * (width / 7) + Math.sin((local + i * 30) / 7) * 8
        const op = interpolate(local, [0, 6, 78, 90], [0, 1, 1, 0], { extrapolateRight: 'clamp' })
        const size = 30
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: fx, top: fy,
              width: size, height: size, borderRadius: '50%',
              background: 'radial-gradient(circle at 30% 30%, #FFE0B2, #C85A00)',
              boxShadow: '0 4px 10px rgba(184, 60, 0, 0.5), inset 0 0 0 2px #FFB74D',
              opacity: op,
              transform: 'translate(-50%, -50%)',
            }}
          />
        )
      })}
      {/* Declining bars */}
      {bars.map((h, i) => {
        const target = h * height * 0.78
        const grow = interpolate(frame, [10 + i * 4, 32 + i * 4], [0, target], { extrapolateRight: 'clamp' })
        return (
          <div
            key={`b${i}`}
            style={{
              position: 'absolute',
              top: baseY - grow,
              left: slot * 0.4 + i * slot,
              width: barW,
              height: grow,
              background: `linear-gradient(180deg,
                rgba(140, 29, 42, 0.92) 0%,
                rgba(232, 102, 10, 0.78) 100%)`,
              borderRadius: '8px 8px 0 0',
              boxShadow: 'inset 0 0 0 1.5px rgba(255,255,255,0.22)',
            }}
          />
        )
      })}
      {/* Baseline */}
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 4, height: 2, background: 'rgba(45, 37, 34, 0.18)' }}/>
    </>
  )
}

// ─── 2) Agents ─────────────────────────────────────────────────────────────
//      Big silhouettes stacking left-to-right, fills the stage.
function AgentsReel({ frame, width, height }: ReelArgs) {
  const count = 7
  const slot = width / (count + 0.5)
  return (
    <>
      {Array.from({ length: count }).map((_, i) => {
        const delay = i * 9
        const local = Math.max(0, frame - delay)
        const op = interpolate(local, [0, 12], [0, 1], { extrapolateRight: 'clamp' })
        const dy = interpolate(local, [0, 18], [40, 0], { extrapolateRight: 'clamp' })
        const cx = slot * (i + 0.7)
        const headSize = 26 + (i % 3) * 2
        const bodyW = 50
        const bodyH = 70
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: cx, bottom: 16,
              transform: `translate(-50%, ${dy}px)`,
              opacity: op,
              display: 'flex', flexDirection: 'column', alignItems: 'center',
            }}
          >
            {/* Head */}
            <div style={{
              width: headSize, height: headSize, borderRadius: '50%',
              background: 'linear-gradient(180deg, #5C2400 0%, #3B1500 100%)',
              boxShadow: '0 4px 8px rgba(45, 37, 34, 0.35)',
              marginBottom: 6,
            }} />
            {/* Body */}
            <div style={{
              width: bodyW, height: bodyH,
              background: 'linear-gradient(180deg, #FF9800 0%, #E8660A 100%)',
              borderRadius: '14px 14px 6px 6px',
              boxShadow: '0 6px 14px rgba(232, 102, 10, 0.4), inset 0 0 0 1.5px rgba(255,255,255,0.25)',
            }} />
          </div>
        )
      })}
    </>
  )
}

// ─── 3) Upload ─────────────────────────────────────────────────────────────
//      Big folder at top, large files flying upward.
function UploadReel({ frame, width, height }: ReelArgs) {
  const folderW = 140
  const folderH = 90
  return (
    <>
      {/* Folder at top center */}
      <div style={{ position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)' }}>
        <div style={{ position: 'relative' }}>
          {/* Tab */}
          <div style={{
            position: 'absolute', top: -14, right: 14, width: 60, height: 16,
            background: '#FFA726', borderRadius: '6px 6px 0 0',
          }} />
          {/* Folder body */}
          <div style={{
            width: folderW, height: folderH,
            background: 'linear-gradient(180deg, #FFCC80 0%, #FF9800 100%)',
            borderRadius: '12px 12px 6px 6px',
            boxShadow: '0 12px 24px rgba(232, 102, 10, 0.45), inset 0 0 0 2px rgba(255,255,255,0.3)',
          }} />
        </div>
      </div>
      {/* 5 large files flying up */}
      {[0, 1, 2, 3, 4].map((i) => {
        const period = 100
        const delay = i * 18
        const local = (frame + delay) % period
        const fy = interpolate(local, [0, period], [height + 20, folderH + 20], { extrapolateRight: 'clamp' })
        const fx = 30 + i * ((width - 60) / 4)
        const op = interpolate(local, [0, 8, 78, 100], [0, 1, 1, 0], { extrapolateRight: 'clamp' })
        const fw = 36, fh = 48
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: fx - fw/2, top: fy - fh/2,
              width: fw, height: fh,
              background: '#FFFFFF',
              border: '2px solid #C85A00',
              borderRadius: 6,
              boxShadow: '0 6px 12px rgba(184, 60, 0, 0.3)',
              opacity: op,
            }}
          >
            <div style={{ position: 'absolute', top: 8, left: 6, right: 6, height: 3, background: '#FFB74D', borderRadius: 2 }} />
            <div style={{ position: 'absolute', top: 18, left: 6, right: 12, height: 3, background: '#FFB74D', borderRadius: 2 }} />
            <div style={{ position: 'absolute', top: 28, left: 6, right: 9, height: 3, background: '#FFB74D', borderRadius: 2 }} />
            <div style={{ position: 'absolute', top: 38, left: 6, right: 14, height: 3, background: '#FFB74D', borderRadius: 2 }} />
          </div>
        )
      })}
    </>
  )
}

// ─── 4) Bonus ─────────────────────────────────────────────────────────────
//      Big trophy + sparkles all over the stage.
function BonusReel({ frame, width, height }: ReelArgs) {
  const trophyRise = interpolate(frame, [0, 28], [60, 0], { extrapolateRight: 'clamp' })
  const trophyScale = interpolate(frame, [0, 28], [0.6, 1.2], { extrapolateRight: 'clamp' })
  return (
    <>
      {/* 10 sparkles scattered */}
      {Array.from({ length: 10 }).map((_, i) => {
        const localT = ((frame + i * 9) % 60) / 60
        const op = Math.sin(localT * Math.PI)
        const px = (i % 5) * (width / 5) + width / 10
        const py = (i < 5 ? 30 : height - 40) + ((i % 3) - 1) * 12
        const size = 16 + (i % 3) * 4
        return (
          <div
            key={i}
            style={{
              position: 'absolute', left: px, top: py,
              width: size, height: size,
              background: `radial-gradient(circle, rgba(255, 235, 59, ${op}) 0%, transparent 70%)`,
              transform: 'translate(-50%, -50%)',
            }}
          />
        )
      })}
      {/* Big trophy in the middle */}
      <div style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: `translate(-50%, calc(-50% + ${trophyRise}px)) scale(${trophyScale})`,
      }}>
        <svg width="160" height="160" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="trgrad" x1="0" y1="0" x2="24" y2="24">
              <stop offset="0" stopColor="#FFD54F"/>
              <stop offset="1" stopColor="#E8660A"/>
            </linearGradient>
          </defs>
          <path d="M6 4h12v3a4 4 0 01-4 4H10a4 4 0 01-4-4V4z" fill="url(#trgrad)" stroke="#5C2400" strokeWidth="0.4"/>
          <path d="M9 12h6v4H9z" fill="#C85A00"/>
          <path d="M7 18h10v2H7z" fill="#5C2400"/>
          <path d="M6 5H4v1a2 2 0 002 2V5z" fill="#FFB74D"/>
          <path d="M18 5h2v1a2 2 0 01-2 2V5z" fill="#FFB74D"/>
          {/* Star on the cup */}
          <path d="M12 5.5l.6 1.2 1.3.2-.95.92.22 1.3L12 8.5l-1.17.62.22-1.3-.95-.92 1.3-.2z" fill="#FFFFFF"/>
        </svg>
      </div>
    </>
  )
}

// ─── 5) Invites ────────────────────────────────────────────────────────────
//      Big plane sweeping with long trail.
function InvitesReel({ frame, width, height }: ReelArgs) {
  const period = 100
  const local = frame % period
  const x = interpolate(local, [0, period], [-60, width + 60], { extrapolateRight: 'clamp' })
  const y = height / 2 + Math.sin((local / period) * Math.PI * 2) * 32

  return (
    <>
      {/* Trail dots */}
      {Array.from({ length: 8 }).map((_, i) => {
        const tx = x - i * 22 - 18
        const op = interpolate(i, [0, 7], [0.65, 0], { extrapolateRight: 'clamp' })
        const size = interpolate(i, [0, 7], [10, 4], { extrapolateRight: 'clamp' })
        return (
          <div
            key={i}
            style={{
              position: 'absolute', left: tx, top: y,
              width: size, height: size, borderRadius: '50%',
              background: '#FF9800',
              boxShadow: '0 0 8px rgba(232, 102, 10, 0.6)',
              opacity: op,
              transform: 'translate(-50%, -50%)',
            }}
          />
        )
      })}
      {/* Big paper plane */}
      <div style={{
        position: 'absolute', left: x, top: y,
        transform: 'translate(-50%, -50%) rotate(-12deg)',
      }}>
        <svg width="84" height="60" viewBox="0 0 40 28" fill="none">
          <path d="M2 4l36-2-14 24-6-10z" fill="#FF9800" stroke="#5C2400" strokeWidth="1.5" strokeLinejoin="round"/>
          <path d="M2 4l16 12 6 10" fill="#FFCC80" stroke="#5C2400" strokeWidth="1.5" strokeLinejoin="round"/>
        </svg>
      </div>
    </>
  )
}

// ─── 6) AI ────────────────────────────────────────────────────────────────
//      Big pulsing center node with wide network of outer nodes.
function AiReel({ frame, width, height }: ReelArgs) {
  const cx = width / 2
  const cy = height / 2
  // Spread the network wide so it visibly fills the stage.
  const radius = Math.min(width, height) * 0.36
  const outerCount = 6
  const outers = Array.from({ length: outerCount }).map((_, i) => {
    const ang = (i / outerCount) * Math.PI * 2 - Math.PI / 2
    return { x: cx + Math.cos(ang) * radius, y: cy + Math.sin(ang) * radius }
  })

  const pulse = Math.sin((frame / 30) * Math.PI * 2) * 0.5 + 0.5

  return (
    <>
      {/* Lines from center to outers */}
      <svg width={width} height={height} style={{ position: 'absolute', inset: 0 }}>
        {outers.map((n, i) => {
          const op = interpolate((frame + i * 10) % 60, [0, 30, 60], [0.2, 0.7, 0.2], { extrapolateRight: 'clamp' })
          return (
            <line
              key={i}
              x1={cx} y1={cy} x2={n.x} y2={n.y}
              stroke="#E8660A"
              strokeWidth={2.5}
              opacity={op}
            />
          )
        })}
      </svg>

      {/* Outer nodes */}
      {outers.map((n, i) => {
        const size = 22
        const localPulse = Math.sin(((frame + i * 8) / 30) * Math.PI * 2) * 0.3 + 0.7
        return (
          <div
            key={i}
            style={{
              position: 'absolute', left: n.x, top: n.y,
              width: size, height: size, borderRadius: '50%',
              background: 'linear-gradient(135deg, #FF9800 0%, #C85A00 100%)',
              transform: 'translate(-50%, -50%)',
              boxShadow: `0 0 ${10 + localPulse * 12}px rgba(232, 102, 10, 0.55)`,
              border: '2px solid rgba(255, 255, 255, 0.6)',
            }}
          />
        )
      })}

      {/* Big center node */}
      <div
        style={{
          position: 'absolute', left: cx, top: cy,
          width: 56 + pulse * 14, height: 56 + pulse * 14, borderRadius: '50%',
          background: 'radial-gradient(circle at 30% 30%, #FFFFFF 0%, #FFD180 35%, #E8660A 100%)',
          transform: 'translate(-50%, -50%)',
          boxShadow: `0 0 ${22 + pulse * 26}px rgba(232, 102, 10, 0.7)`,
        }}
      />
    </>
  )
}
