import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, spring, interpolate } from 'remotion';
import { COLORS } from '../constants/colors';
import { FPS, fontFamily, SPRING } from '../constants/tokens';
import { NifraimLogo } from '../components/NifraimLogo';
import { MARKETING_OUTRO } from '../constants/marketingData';

export const LumaOutroScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Video overlay darkens over time
  const overlayOpacity = interpolate(frame, [0, 60], [0.2, 0.65], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Logo slam entrance
  const logoSpring = spring({ fps: FPS, frame: frame - 20, config: { damping: 8, mass: 0.6 } });
  const logoScale = interpolate(logoSpring, [0, 1], [3, 1]);
  const logoOpacity = interpolate(frame, [20, 30], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Brand name after logo
  const brandOpacity = interpolate(frame, [35, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const brandY = interpolate(frame, [35, 50], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // CTA button
  const ctaSpring = spring({ fps: FPS, frame: frame - 70, config: SPRING.BOUNCY });
  const ctaOpacity = interpolate(frame, [70, 85], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // URL shimmer
  const urlOpacity = interpolate(frame, [95, 110], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const shimmerX = interpolate(frame, [110, 179], [-200, 200], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Tagline
  const taglineOpacity = interpolate(frame, [115, 130], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: '#000', fontFamily }}>
      {/* Luma AI outro video */}
      <OffthreadVideo
        src={staticFile('luma-outro.mp4')}
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />

      {/* Dark overlay */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at center, rgba(0,0,0,${overlayOpacity * 0.5}) 0%, rgba(0,0,0,${overlayOpacity}) 100%)`,
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 20,
          direction: 'rtl',
        }}
      >
        {/* Logo slam */}
        <div
          style={{
            opacity: logoOpacity,
            transform: `scale(${logoScale})`,
          }}
        >
          <NifraimLogo size={80} color={COLORS.primary} />
        </div>

        {/* Brand name */}
        <div
          style={{
            fontSize: 80,
            fontWeight: 800,
            color: '#FFFFFF',
            letterSpacing: 6,
            textShadow: '0 4px 30px rgba(245,124,0,0.4)',
            opacity: brandOpacity,
            transform: `translateY(${brandY}px)`,
          }}
        >
          Nifraim
        </div>

        {/* CTA button */}
        <div
          style={{
            opacity: ctaOpacity,
            transform: `scale(${0.5 + ctaSpring * 0.5})`,
            padding: '18px 48px',
            borderRadius: 16,
            background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.secondary})`,
            fontSize: 32,
            fontWeight: 700,
            color: '#FFFFFF',
            boxShadow: `0 8px 30px rgba(245,124,0,0.4)`,
          }}
        >
          {MARKETING_OUTRO.cta}
        </div>

        {/* URL with shimmer */}
        <div
          style={{
            position: 'relative',
            opacity: urlOpacity,
            fontSize: 28,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.8)',
            letterSpacing: 3,
            overflow: 'hidden',
          }}
        >
          <span>{MARKETING_OUTRO.url}</span>
          {/* Shimmer sweep */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              background: `linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)`,
              transform: `translateX(${shimmerX}px)`,
              pointerEvents: 'none',
            }}
          />
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 22,
            fontWeight: 400,
            color: 'rgba(255,255,255,0.6)',
            opacity: taglineOpacity,
            marginTop: 8,
          }}
        >
          {MARKETING_OUTRO.tagline}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
