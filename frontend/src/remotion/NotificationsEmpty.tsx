import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion'

/**
 * NotificationsEmpty — loops behind the "all clear" state of the bell panel.
 * 5-second loop with a pulsing checkmark, orbital dots, and warm-cream wash
 * matching the app palette.
 */

const CREAM = '#FFFBF4'
const INK = '#1A1410'
const INK_SOFT = '#6B5F50'
const BRAND = '#F57C00'
const EMERALD = '#10B981'
const EMERALD_DEEP = '#047857'

export const NOTIFICATIONS_EMPTY_DURATION = 150  // 5s @ 30fps — loops cleanly

export function NotificationsEmpty() {
  const frame = useCurrentFrame()
  const { width, height, fps } = useVideoConfig()

  const checkScale = spring({ frame: frame % 150, fps, config: { damping: 14, mass: 0.8 } })
  const checkOpacity = interpolate(frame % 150, [0, 12, 130, 150], [0, 1, 1, 0], { extrapolateRight: 'clamp' })
  const ringOpacity = interpolate(frame % 150, [0, 20, 70], [0, 0.85, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  const ringScale = interpolate(frame % 150, [0, 70], [0.6, 2.6], { extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) })

  const cx = width / 2
  const cy = height / 2

  // Three orbital dots that travel around the check
  const orbitR = Math.min(width, height) * 0.28
  const orbitAngles = [0, 120, 240]

  return (
    <AbsoluteFill style={{
      background: `radial-gradient(circle at 50% 35%, rgba(245, 124, 0, 0.06) 0%, transparent 60%), ${CREAM}`,
      fontFamily: "'Heebo', sans-serif",
      direction: 'rtl',
      overflow: 'hidden',
    }}>
      {/* Subtle hairline grid texture */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `linear-gradient(rgba(0,0,0,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.018) 1px, transparent 1px)`,
        backgroundSize: '24px 24px',
        opacity: 0.4,
        maskImage: 'radial-gradient(ellipse at center, #000 30%, transparent 80%)',
      }} />

      {/* Outgoing pulse ring */}
      <div style={{
        position: 'absolute',
        left: cx - 60,
        top: cy - 60,
        width: 120,
        height: 120,
        borderRadius: '50%',
        border: `2px solid ${EMERALD}`,
        opacity: ringOpacity,
        transform: `scale(${ringScale})`,
      }} />

      {/* Orbital dots */}
      {orbitAngles.map((startDeg, i) => {
        const angle = (startDeg + (frame * 1.8)) % 360
        const rad = (angle * Math.PI) / 180
        const dx = Math.cos(rad) * orbitR
        const dy = Math.sin(rad) * orbitR
        const dotOpacity = interpolate((frame + i * 12) % 60, [0, 30, 60], [0.3, 1, 0.3], { extrapolateRight: 'clamp' })
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: cx + dx - 4,
              top: cy + dy - 4,
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: i === 0 ? BRAND : i === 1 ? EMERALD : '#3B82F6',
              opacity: dotOpacity,
              boxShadow: `0 0 12px currentColor`,
            }}
          />
        )
      })}

      {/* Check circle */}
      <div style={{
        position: 'absolute',
        left: cx - 36,
        top: cy - 36,
        width: 72,
        height: 72,
        borderRadius: '50%',
        background: `linear-gradient(135deg, ${EMERALD} 0%, ${EMERALD_DEEP} 100%)`,
        display: 'grid',
        placeItems: 'center',
        boxShadow: `0 8px 24px rgba(16, 185, 129, 0.32), inset 0 -2px 0 rgba(0,0,0,0.12)`,
        transform: `scale(${checkScale})`,
        opacity: checkOpacity,
      }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>

      {/* Caption */}
      <div style={{
        position: 'absolute',
        insetInline: 0,
        bottom: 18,
        textAlign: 'center',
        color: INK_SOFT,
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: 0.3,
        opacity: interpolate(frame % 150, [10, 30], [0, 1], { extrapolateRight: 'clamp' }),
      }}>
        כל הנפרעים תואמים את הפרודוקציה
      </div>
    </AbsoluteFill>
  )
}
