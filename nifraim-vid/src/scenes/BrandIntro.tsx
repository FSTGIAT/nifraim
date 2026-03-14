import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { BRAND_GRADIENT } from '../constants/colors';
import { SPRING, FPS, fontFamily } from '../constants/tokens';
import { NifraimLogo } from '../components/NifraimLogo';

export const BrandIntro: React.FC = () => {
  const frame = useCurrentFrame();

  // Phase 1: URL fades in
  const urlOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const urlY = interpolate(frame, [0, 15], [40, 0], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Phase 2: Logo + brand name slam in
  const logoScale = spring({ fps: FPS, frame: frame - 10, config: { damping: 10, mass: 0.6 } });
  const brandOpacity = interpolate(frame, [14, 28], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const brandY = interpolate(frame, [14, 28], [120, 0], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const brandScale = spring({ fps: FPS, frame: frame - 14, config: SPRING.SNAPPY });

  // Shimmer sweep across brand text
  const shimmerX = interpolate(frame, [20, 70], [-100, 200], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 3: Tagline
  const taglineOpacity = interpolate(frame, [28, 42], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const taglineY = interpolate(frame, [28, 42], [60, 0], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Phase 4: Line sweep
  const lineWidth = interpolate(frame, [35, 65], [0, 700], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Glowing border pulse
  const glowIntensity = interpolate(frame, [10, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const glowPulse = Math.sin(frame * 0.08) * 0.3 + 0.7;

  // Exit fade
  const exitOpacity = interpolate(frame, [65, 74], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill
      style={{
        background: BRAND_GRADIENT,
        fontFamily,
        direction: 'rtl',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 20,
        opacity: exitOpacity,
      }}
    >
      {/* Sleek glowing border frame */}
      <div
        style={{
          position: 'absolute',
          inset: 30,
          borderRadius: 24,
          border: '1.5px solid rgba(255,255,255,0.25)',
          boxShadow: `inset 0 0 ${40 * glowPulse * glowIntensity}px rgba(255,255,255,${0.08 * glowPulse * glowIntensity}), 0 0 ${60 * glowPulse * glowIntensity}px rgba(255,200,120,${0.12 * glowPulse * glowIntensity})`,
          opacity: glowIntensity,
          pointerEvents: 'none',
        }}
      />

      {/* Logo */}
      <div style={{ transform: `scale(${logoScale})`, opacity: logoScale }}>
        <NifraimLogo size={160} color="#FFFFFF" />
      </div>

      {/* Brand name — massive with shimmer */}
      <div
        style={{
          fontSize: 140,
          fontWeight: 800,
          color: '#FFFFFF',
          opacity: brandOpacity,
          transform: `translateY(${brandY}px) scale(${0.6 + brandScale * 0.4})`,
          letterSpacing: -3,
          lineHeight: 1,
          textShadow: '0 4px 30px rgba(0,0,0,0.15)',
          position: 'relative',
        }}
      >
        <span style={{ position: 'relative' }}>
          Nifraim
          {/* Shimmer overlay */}
          <span
            style={{
              position: 'absolute',
              inset: 0,
              background: `linear-gradient(105deg, transparent 30%, rgba(255,255,255,0.5) 48%, rgba(255,255,255,0.7) 50%, rgba(255,255,255,0.5) 52%, transparent 70%)`,
              backgroundSize: '200% 100%',
              backgroundPosition: `${shimmerX}% 0`,
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mixBlendMode: 'overlay' as const,
            }}
          >
            Nifraim
          </span>
        </span>
      </div>

      {/* URL */}
      <div
        style={{
          fontSize: 36,
          fontWeight: 400,
          color: 'rgba(255,255,255,0.7)',
          opacity: urlOpacity,
          transform: `translateY(${urlY}px)`,
          direction: 'ltr',
          unicodeBidi: 'embed' as const,
          letterSpacing: 2,
        }}
      >
        nifraim.com
      </div>

      {/* White sweep line */}
      <div
        style={{
          width: lineWidth,
          height: 5,
          borderRadius: 3,
          background: 'rgba(255,255,255,0.5)',
          marginTop: 12,
        }}
      />

      {/* Tagline */}
      <div
        style={{
          fontSize: 48,
          fontWeight: 600,
          color: '#FFFFFF',
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          marginTop: 8,
          textShadow: '0 2px 20px rgba(0,0,0,0.1)',
        }}
      >
        ניהול עמלות. חכם.
      </div>
    </AbsoluteFill>
  );
};
