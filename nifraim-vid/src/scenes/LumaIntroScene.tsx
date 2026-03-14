import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, interpolate } from 'remotion';
import { fontFamily } from '../constants/tokens';
import { MARKETING } from '../constants/marketingData';

export const LumaIntroScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Dark vignette fades in
  const vignetteOpacity = interpolate(frame, [0, 30], [0.3, 0.7], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Brand name fades in
  const titleOpacity = interpolate(frame, [40, 65], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const titleY = interpolate(frame, [40, 65], [30, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const titleScale = interpolate(frame, [40, 65], [0.9, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Tagline fades in after title
  const taglineOpacity = interpolate(frame, [70, 95], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const taglineY = interpolate(frame, [70, 95], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Exit fade
  const exitOpacity = interpolate(frame, [130, 149], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ background: '#000', fontFamily }}>
      {/* Luma AI generated video */}
      <OffthreadVideo
        src={staticFile('luma-intro.mp4')}
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />

      {/* Warm amber tint to match brand palette */}
      <AbsoluteFill
        style={{
          background: 'rgba(245, 124, 0, 0.12)',
          mixBlendMode: 'color',
        }}
      />

      {/* Dark vignette overlay */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,${vignetteOpacity}) 100%)`,
        }}
      />

      {/* Content overlay */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          opacity: exitOpacity,
        }}
      >
        {/* Brand name */}
        <div
          style={{
            fontSize: 120,
            fontWeight: 800,
            color: '#FFFFFF',
            letterSpacing: 8,
            textShadow: '0 4px 40px rgba(245,124,0,0.5), 0 0 80px rgba(245,124,0,0.3)',
            opacity: titleOpacity,
            transform: `translateY(${titleY}px) scale(${titleScale})`,
          }}
        >
          {MARKETING.brandName}
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 36,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.85)',
            marginTop: 16,
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
            direction: 'rtl',
          }}
        >
          {MARKETING.tagline}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
