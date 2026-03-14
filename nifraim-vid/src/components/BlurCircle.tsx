import { useCurrentFrame, spring, interpolate } from 'remotion';
import { FPS, SPRING } from '../constants/tokens';

interface BlurCircleProps {
  size: number;
  x: number;
  y: number;
  delay: number;
  opacity: number;
  color?: string;
  /** Frame at which circles start converging to center */
  convergeStart: number;
  /** Frame at which circles fully converge */
  convergeEnd: number;
}

export const BlurCircle: React.FC<BlurCircleProps> = ({
  size,
  x,
  y,
  delay,
  opacity,
  color = 'rgba(245,124,0,0.08)',
  convergeStart,
  convergeEnd,
}) => {
  const frame = useCurrentFrame();

  // Spring entrance
  const entrance = spring({
    fps: FPS,
    frame: frame - delay,
    config: SPRING.BOUNCY,
  });

  // Sine-wave float drift
  const floatX = Math.sin((frame - delay) * 0.03 + x) * 20;
  const floatY = Math.cos((frame - delay) * 0.025 + y) * 15;

  // Converge toward center (0,0 in parent coordinate space = center)
  const converge = interpolate(frame, [convergeStart, convergeEnd], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  // Ease-in for acceleration effect
  const convergeEased = converge * converge;

  const currentX = x + floatX - (x + floatX) * convergeEased;
  const currentY = y + floatY - (y + floatY) * convergeEased;

  // Scale shrinks as circles converge
  const convergeScale = interpolate(converge, [0.6, 1], [1, 0.2], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Glow increases as circles approach center
  const glowIntensity = interpolate(converge, [0, 0.8], [0, 30], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Fade out at convergence end
  const fadeOut = interpolate(frame, [convergeEnd - 10, convergeEnd], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        width: size,
        height: size,
        borderRadius: '50%',
        background: `radial-gradient(circle, rgba(245,124,0,0.6) 0%, rgba(245,124,0,0.25) 50%, transparent 75%)`,
        border: `1.5px solid rgba(245,124,0,0.3)`,
        boxShadow: `0 0 ${20 + glowIntensity}px rgba(245,124,0,0.4), inset 0 0 ${size * 0.3}px rgba(245,124,0,0.15)`,
        filter: `blur(${size * 0.08}px)`,
        transform: `translate(${currentX}px, ${currentY}px) scale(${entrance * convergeScale})`,
        opacity: opacity * fadeOut,
        left: '50%',
        top: '50%',
        marginLeft: -size / 2,
        marginTop: -size / 2,
        pointerEvents: 'none',
      }}
    />
  );
};
