import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { COLORS } from '../constants/colors';
import { SPRING, FPS, fontFamily, TOKENS } from '../constants/tokens';
import { MARKETING_PORTAL } from '../constants/marketingData';
import { NifraimLogo } from '../components/NifraimLogo';
import { KPIStrip } from '../components/KPIStrip';
import { CompanyCard } from '../components/CompanyCard';

const SCENE_BG = '#242424';

export const MarketingPortalScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Phase 1: Portal entry
  const entryScale = interpolate(frame, [0, 40], [0.72, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryRotX = interpolate(frame, [0, 30], [6, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 2: Header
  const headerY = interpolate(frame, [3, 14], [-50, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const headerOpacity = interpolate(frame, [3, 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 3: Greeting + badge
  const greetSpring = spring({ fps: FPS, frame: frame - 8, config: SPRING.SNAPPY });
  const greetY = interpolate(frame, [8, 20], [60, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 4: Portal content
  const contentOpacity = interpolate(frame, [30, 42], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const contentY = interpolate(frame, [30, 45], [80, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const contentScale = spring({ fps: FPS, frame: frame - 32, config: SPRING.SMOOTH });

  // Phase 5: Share link animation
  const shareOpacity = interpolate(frame, [65, 78], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const shareScale = spring({ fps: FPS, frame: frame - 65, config: SPRING.BOUNCY });
  const shareGlow = frame > 75 ? Math.sin((frame - 75) * 0.1) * 0.3 + 0.7 : 0;

  // Phase 6: Tagline
  const taglineOpacity = interpolate(frame, [85, 100], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const taglineSpring = spring({ fps: FPS, frame: frame - 85, config: SPRING.SNAPPY });

  // Ken Burns
  const kenZoom = interpolate(frame, [55, 119], [1, 1.05], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: SCENE_BG, fontFamily, direction: 'rtl' }}>
      <div
        style={{
          width: '100%',
          height: '100%',
          padding: '40px 70px',
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
          opacity: entryOpacity,
          transform: `perspective(1400px) rotateX(${entryRotX}deg) scale(${entryScale * kenZoom})`,
          transformOrigin: 'center center',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            opacity: headerOpacity,
            transform: `translateY(${headerY}px)`,
          }}
        >
          <NifraimLogo size={36} color={COLORS.primary} />
          <span style={{ fontSize: 24, fontWeight: 700, color: COLORS.primary }}>Nifraim</span>
          <span
            style={{
              fontSize: 14,
              fontWeight: 600,
              padding: '4px 14px',
              borderRadius: 999,
              background: 'rgba(245,124,0,0.15)',
              color: COLORS.primary,
              marginRight: 8,
            }}
          >
            {MARKETING_PORTAL.badge}
          </span>
        </div>

        {/* Greeting */}
        <div style={{ opacity: greetSpring, transform: `translateY(${greetY}px) scale(${0.7 + greetSpring * 0.3})` }}>
          <div style={{ fontSize: 38, fontWeight: 700, color: COLORS.textOnDark }}>
            {MARKETING_PORTAL.greeting}
          </div>
        </div>

        {/* KPIs */}
        <KPIStrip items={MARKETING_PORTAL.kpis} baseDelay={20} stagger={5} />

        {/* Portal content: Companies */}
        <div
          style={{
            flex: 1,
            background: COLORS.glass,
            backdropFilter: 'blur(12px)',
            border: `1px solid ${COLORS.glassBorder}`,
            borderRadius: TOKENS.radiusMd,
            padding: 20,
            boxShadow: COLORS.glassShadow,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            opacity: contentOpacity,
            transform: `translateY(${contentY}px) scale(${0.85 + contentScale * 0.15})`,
          }}
        >
          {MARKETING_PORTAL.companies.map((c, i) => (
            <CompanyCard
              key={c.name}
              name={c.name}
              products={c.products}
              accumulation={c.accumulation}
              active={c.active}
              inactive={c.inactive}
              delay={36 + i * 6}
            />
          ))}
        </div>

        {/* Share link button animation */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            opacity: shareOpacity,
            transform: `scale(${0.6 + shareScale * 0.4})`,
          }}
        >
          {/* WhatsApp-style icon */}
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: '50%',
              background: '#25D366',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 ${shareGlow * 30}px rgba(37,211,102,${shareGlow * 0.5})`,
            }}
          >
            <svg width={28} height={28} viewBox="0 0 24 24" fill="white">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
              <path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18a8 8 0 01-4.243-1.214l-.252-.149-2.738.813.813-2.738-.149-.252A7.996 7.996 0 014 12a8 8 0 1116 0 8 8 0 01-8 8z" />
            </svg>
          </div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 600,
              color: COLORS.textOnDark,
              padding: '10px 28px',
              borderRadius: 12,
              background: 'rgba(245,124,0,0.15)',
              border: `1px solid ${COLORS.primary}`,
            }}
          >
            {MARKETING_PORTAL.shareText}
          </div>
        </div>

        {/* Tagline */}
        <div
          style={{
            textAlign: 'center',
            fontSize: 26,
            fontWeight: 700,
            color: COLORS.primary,
            opacity: taglineOpacity,
            transform: `scale(${0.8 + taglineSpring * 0.2})`,
          }}
        >
          {MARKETING_PORTAL.tagline}
        </div>
      </div>
    </AbsoluteFill>
  );
};
