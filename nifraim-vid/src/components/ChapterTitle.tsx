import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { BRAND_GRADIENT } from '../constants/colors';
import { FPS, fontFamily } from '../constants/tokens';

interface ChapterTitleProps {
  title: string;
  subtitle?: string;
}

export const ChapterTitle: React.FC<ChapterTitleProps> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();

  // Orange line sweeps in from right
  const lineWidth = interpolate(frame, [0, 18], [0, 200], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Title slams in
  const titleScale = spring({ fps: FPS, frame: frame - 4, config: { damping: 14, mass: 0.5 } });
  const titleOpacity = interpolate(frame, [4, 14], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Subtitle fades in
  const subOpacity = interpolate(frame, [12, 22], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const subY = interpolate(frame, [12, 22], [30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Exit fade
  const exitOpacity = interpolate(frame, [35, 44], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

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
        gap: 24,
        opacity: exitOpacity,
      }}
    >
      {/* Orange line accent */}
      <div
        style={{
          width: lineWidth,
          height: 5,
          borderRadius: 3,
          background: 'rgba(255,255,255,0.5)',
        }}
      />

      {/* Chapter title — massive */}
      <div
        style={{
          fontSize: 80,
          fontWeight: 800,
          color: '#FFFFFF',
          opacity: titleOpacity,
          transform: `scale(${0.5 + titleScale * 0.5})`,
          textAlign: 'center',
          textShadow: '0 4px 30px rgba(0,0,0,0.15)',
          lineHeight: 1.2,
        }}
      >
        {title}
      </div>

      {subtitle && (
        <div
          style={{
            fontSize: 32,
            fontWeight: 400,
            color: 'rgba(255,255,255,0.7)',
            opacity: subOpacity,
            transform: `translateY(${subY}px)`,
            textAlign: 'center',
          }}
        >
          {subtitle}
        </div>
      )}
    </AbsoluteFill>
  );
};
