import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { BRAND_GRADIENT } from '../constants/colors';
import { FPS, fontFamily } from '../constants/tokens';
import { NifraimLogo } from '../components/NifraimLogo';
import { MARKETING_INTRO } from '../constants/marketingData';

export const MarketingBrandIntro: React.FC = () => {
  const frame = useCurrentFrame();

  // Logo + brand text
  const logoSpring = spring({ fps: FPS, frame: frame - 10, config: { damping: 12, mass: 0.5 } });
  const logoY = interpolate(frame, [10, 25], [-50, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Tagline
  const taglineOpacity = interpolate(frame, [30, 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const taglineY = interpolate(frame, [30, 45], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Description
  const descOpacity = interpolate(frame, [45, 60], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Exit fade
  const exitOpacity = interpolate(frame, [75, 89], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Background glow
  const glowPulse = frame > 20 ? Math.sin((frame - 20) * 0.05) * 0.15 + 0.85 : 0;

  return (
    <AbsoluteFill style={{ background: BRAND_GRADIENT, fontFamily, overflow: 'hidden', direction: 'rtl' }}>
      {/* Radial glow */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '45%',
          width: 500,
          height: 500,
          marginLeft: -250,
          marginTop: -250,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%)',
          opacity: glowPulse,
          filter: 'blur(40px)',
        }}
      />

      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 24,
          opacity: exitOpacity,
        }}
      >
        {/* Logo + Brand */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 20,
            opacity: logoSpring,
            transform: `translateY(${logoY}px) scale(${0.7 + logoSpring * 0.3})`,
          }}
        >
          <NifraimLogo size={80} color="#FFFFFF" />
          <span style={{ fontSize: 90, fontWeight: 800, color: '#FFFFFF', letterSpacing: 6 }}>
            {MARKETING_INTRO.headline}
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 44,
            fontWeight: 700,
            color: 'rgba(255,255,255,0.95)',
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
            textAlign: 'center',
          }}
        >
          {MARKETING_INTRO.subtitle}
        </div>

        {/* Description */}
        <div
          style={{
            fontSize: 28,
            fontWeight: 400,
            color: 'rgba(255,255,255,0.75)',
            opacity: descOpacity,
            textAlign: 'center',
            maxWidth: 800,
          }}
        >
          {MARKETING_INTRO.description}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
