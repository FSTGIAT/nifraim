import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion'
import type { CardIcon, CardStep } from './steps'

const FONT = "'Heebo', sans-serif"
const INK = '#1A1410'
const INK_SOFT = '#5A5044'

// Pastel tint per icon: soft background + a saturated accent.
const TINTS: Record<string, { bg: string; accent: string }> = {
  vault: { bg: '#EBF3FB', accent: '#3E7CB1' },
  download: { bg: '#FBF1E1', accent: '#D9831A' },
  merge: { bg: '#E9F6EE', accent: '#2E9E63' },
  doc: { bg: '#F2ECFB', accent: '#7E5BC2' },
  report: { bg: '#FCEEE2', accent: '#E0651C' },
  chart: { bg: '#E6F5F2', accent: '#1F9E8E' },
  shield: { bg: '#ECEEFB', accent: '#4E5BC6' },
}

function tintFor(step: CardStep): { bg: string; accent: string } {
  return step.tint ?? TINTS[step.icon ?? 'report'] ?? TINTS.report
}

function Icon({ name }: { name: CardIcon | undefined }) {
  const common = {
    width: 64,
    height: 64,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.7,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  }
  switch (name) {
    case 'vault':
      return (
        <svg {...common}>
          <rect x="3" y="3.5" width="18" height="15" rx="2" />
          <circle cx="9.5" cy="11" r="3.1" />
          <path d="M9.5 11l1.9-1.9" />
          <path d="M16 9v4" />
          <path d="M6 18.5V20M9 18.5V20" />
        </svg>
      )
    case 'download':
      return (
        <svg {...common}>
          <path d="M12 3v12" />
          <path d="M7 11l5 5 5-5" />
          <path d="M4 19h16" />
          <circle cx="18.5" cy="6.5" r="3.2" />
          <path d="M18.5 5.2v1.3l.9.7" />
        </svg>
      )
    case 'doc':
      return (
        <svg {...common}>
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5" />
          <path d="M8.5 13h7M8.5 16.5h5" />
          <path d="M9 9.5h2" />
        </svg>
      )
    case 'report':
      return (
        <svg {...common}>
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5" />
          <path d="M9 13l2 2 3.5-3.5" />
          <path d="M9 17.5h6" />
        </svg>
      )
    case 'chart':
      return (
        <svg {...common}>
          <path d="M4 4v16h16" />
          <rect x="7" y="11" width="3" height="6" rx="0.6" />
          <rect x="12" y="7" width="3" height="10" rx="0.6" />
          <rect x="17" y="13" width="3" height="4" rx="0.6" />
        </svg>
      )
    case 'shield':
      return (
        <svg {...common}>
          <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
          <path d="M9 12l2 2 4-4.5" />
        </svg>
      )
    case 'merge':
    default:
      return (
        <svg {...common}>
          <path d="M5 4v5a4 4 0 0 0 4 4h6" />
          <path d="M19 20v-5a4 4 0 0 0-4-4H9" />
          <path d="M12 9l3-3-3-3" />
          <path d="M12 15l-3 3 3 3" />
        </svg>
      )
  }
}

function Bullet({ text, accent, delay, local, fps }: { text: string; accent: string; delay: number; local: number; fps: number }) {
  const e = spring({ frame: local - delay, fps, from: 0, to: 1, config: { damping: 22, mass: 0.6 } })
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, opacity: e, transform: `translateX(${(1 - e) * 24}px)` }}>
      <span
        style={{
          flex: 'none',
          width: 38,
          height: 38,
          borderRadius: '50%',
          background: `${accent}1F`,
          border: `1.5px solid ${accent}66`,
          color: accent,
          display: 'grid',
          placeItems: 'center',
        }}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12l4 4 10-10" />
        </svg>
      </span>
      <span style={{ fontSize: 34, fontWeight: 700, color: INK, lineHeight: 1.25 }}>{text}</span>
    </div>
  )
}

/**
 * Full-screen narration card — Hebrew RTL. Sits between screenshot steps.
 * Runs inside a <Sequence>, so `useCurrentFrame()` is step-local.
 */
export function CardScreen({ step, durationInFrames }: { step: CardStep; durationInFrames: number }) {
  const local = useCurrentFrame()
  const { fps } = useVideoConfig()
  const { bg, accent } = tintFor(step)

  const enter = spring({ frame: local, fps, from: 0, to: 1, config: { damping: 20, mass: 0.7 } })
  const out = interpolate(local, [durationInFrames - 16, durationInFrames - 2], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  })
  const opacity = Math.min(enter, out)
  const scale = 0.92 + 0.08 * enter

  const ringScale = 0.7 + 0.3 * spring({ frame: local - 4, fps, from: 0, to: 1, config: { damping: 14 } })
  const hasList = !!step.bullets?.length
  const titleSize = hasList ? 46 : 54

  return (
    <AbsoluteFill style={{ display: 'grid', placeItems: 'center' }}>
      <div
        style={{
          direction: 'rtl',
          fontFamily: FONT,
          width: 1360,
          maxWidth: '84%',
          background: `linear-gradient(160deg, #FFFFFF 0%, ${bg} 100%)`,
          border: `1.5px solid ${accent}3A`,
          borderRadius: 32,
          padding: hasList ? '60px 84px' : '70px 80px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: hasList ? 'stretch' : 'center',
          gap: 28,
          textAlign: hasList ? 'right' : 'center',
          boxShadow: `0 40px 90px rgba(26,20,16,0.18), 0 10px 28px ${accent}1A`,
          opacity,
          transform: `scale(${scale})`,
        }}
      >
        {/* icon medallion */}
        <div
          style={{
            alignSelf: 'center',
            width: 120,
            height: 120,
            borderRadius: '50%',
            display: 'grid',
            placeItems: 'center',
            color: accent,
            background: `radial-gradient(circle at 50% 35%, ${accent}2E 0%, ${accent}14 60%, transparent 75%)`,
            border: `2px solid ${accent}66`,
            boxShadow: `0 0 0 10px ${accent}14`,
            transform: `scale(${ringScale})`,
          }}
        >
          <Icon name={step.icon} />
        </div>

        <span style={{ fontSize: titleSize, fontWeight: 800, color: INK, lineHeight: 1.2, letterSpacing: -0.5, alignSelf: 'center', textAlign: 'center' }}>
          {step.title}
        </span>

        {step.body ? (
          <span style={{ fontSize: 36, fontWeight: 600, color: INK_SOFT, lineHeight: 1.45, alignSelf: 'center', textAlign: 'center', maxWidth: 1100 }}>
            {step.body}
          </span>
        ) : null}

        {hasList ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 22, marginTop: 6, alignSelf: 'center' }}>
            {step.bullets!.map((b, i) => (
              <Bullet key={i} text={b} accent={accent} delay={10 + i * 9} local={local} fps={fps} />
            ))}
          </div>
        ) : null}

        {step.note ? (
          <div
            style={{
              alignSelf: 'center',
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              marginTop: 4,
              maxWidth: 1080,
              background: `${accent}14`,
              border: `1.5px solid ${accent}4D`,
              borderRadius: 18,
              padding: '18px 26px',
              opacity: spring({ frame: local - 40, fps, from: 0, to: 1, config: { damping: 22 } }),
            }}
          >
            <span style={{ flex: 'none', color: accent, display: 'grid', placeItems: 'center' }}>
              <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="M3.5 6.5l8.5 6 8.5-6" />
              </svg>
            </span>
            <span style={{ fontSize: 30, fontWeight: 700, color: accent, lineHeight: 1.3 }}>{step.note}</span>
          </div>
        ) : null}

        {step.badge ? (
          <span
            style={{
              alignSelf: 'center',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              fontSize: 26,
              fontWeight: 800,
              color: '#fff',
              background: accent,
              borderRadius: 999,
              padding: '12px 28px',
              boxShadow: `0 10px 24px ${accent}55`,
            }}
          >
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#fff', boxShadow: '0 0 0 4px rgba(255,255,255,0.35)' }} />
            {step.badge}
          </span>
        ) : null}
      </div>
    </AbsoluteFill>
  )
}
