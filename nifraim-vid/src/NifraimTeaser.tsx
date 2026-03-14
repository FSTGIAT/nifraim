import { AbsoluteFill, Audio, useCurrentFrame, spring, interpolate, staticFile } from 'remotion';
import { COLORS, BRAND_GRADIENT } from './constants/colors';
import { SPRING, FPS, fontFamily } from './constants/tokens';
import { NifraimLogo } from './components/NifraimLogo';
import { BlurCircle } from './components/BlurCircle';

// Circle definitions: size, x offset, y offset, spawn delay, opacity
const CIRCLES = [
  { size: 260, x: -350, y: -200, delay: 0, opacity: 0.55 },
  { size: 80, x: 400, y: -150, delay: 3, opacity: 0.70 },
  { size: 200, x: -150, y: 250, delay: 5, opacity: 0.60 },
  { size: 120, x: 300, y: 200, delay: 8, opacity: 0.65 },
  { size: 300, x: -500, y: 50, delay: 10, opacity: 0.45 },
  { size: 60, x: 200, y: -300, delay: 13, opacity: 0.80 },
  { size: 180, x: 500, y: 100, delay: 16, opacity: 0.55 },
  { size: 100, x: -250, y: -350, delay: 19, opacity: 0.70 },
  { size: 240, x: 100, y: 350, delay: 22, opacity: 0.50 },
  { size: 70, x: -400, y: 300, delay: 25, opacity: 0.75 },
  { size: 150, x: 450, y: -250, delay: 28, opacity: 0.60 },
  { size: 40, x: -100, y: -100, delay: 31, opacity: 0.80 },
  { size: 220, x: -300, y: 150, delay: 34, opacity: 0.50 },
  { size: 90, x: 350, y: -50, delay: 37, opacity: 0.70 },
];

export const NifraimTeaser: React.FC = () => {
  const frame = useCurrentFrame();

  // === Phase 2: Camera zoom + rotation (frames 40–120) ===
  const cameraScale = interpolate(frame, [40, 120], [1, 1.3], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const cameraRotation = interpolate(frame, [40, 120], [0, 3], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // === Phase 3: Glow burst at convergence (frame ~120) ===
  const burstScale = interpolate(
    frame,
    [115, 120, 125, 135],
    [0, 1.8, 1.2, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );
  const burstOpacity = interpolate(frame, [115, 120, 130, 140], [0, 0.9, 0.5, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // === Phase 3: Text reveal (frames 125 onward) ===
  const textSpring = spring({
    fps: FPS,
    frame: frame - 125,
    config: SPRING.SNAPPY,
  });
  const textOpacity = interpolate(frame, [125, 140], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Logo slam in at center
  const logoEntrance = spring({
    fps: FPS,
    frame: frame - 120,
    config: { damping: 10, mass: 0.6 },
  });

  // Logo moves to top-right corner (frames 150–180)
  const logoMove = spring({
    fps: FPS,
    frame: frame - 150,
    config: SPRING.SMOOTH,
  });
  // Start: center-ish above text (880, 340), End: top-right corner (1820, 30)
  const logoLeft = interpolate(logoMove, [0, 1], [880, 1820]);
  const logoTop = interpolate(logoMove, [0, 1], [340, 30]);
  const logoSizeAnim = interpolate(logoMove, [0, 1], [120, 80]);

  // Continuous shimmer sweep — loops through entire hold period
  const shimmerCycle = ((frame - 135) % 90) / 90;
  const shimmerX = frame < 135 ? -100 : interpolate(shimmerCycle, [0, 1], [-100, 200]);

  // === Phase 4: Hold with glow pulse (frames 150–240) ===
  const glowPulse = frame > 140 ? Math.sin((frame - 140) * 0.08) * 0.3 + 0.7 : 0;

  // No fade — last scene stays visible

  // Background transition: grey → orange after convergence
  const bgTransition = interpolate(frame, [115, 135], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: '#1a1a1a',
        fontFamily,
        overflow: 'hidden',
      }}
    >
      {/* Background music */}
      <Audio
        src={staticFile('teaser-music.mp3')}
        volume={1}
      />

      {/* Orange background that fades in after convergence */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: BRAND_GRADIENT,
          opacity: bgTransition,
        }}
      />

      {/* Camera transform wrapper */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          transform: `scale(${cameraScale}) rotate(${cameraRotation}deg)`,
        }}
      >
        {/* Animated blur circles */}
        {CIRCLES.map((circle, i) => (
          <BlurCircle
            key={i}
            size={circle.size}
            x={circle.x}
            y={circle.y}
            delay={circle.delay}
            opacity={circle.opacity}
            color="rgba(245,124,0,0.6)"
            convergeStart={100}
            convergeEnd={130}
          />
        ))}

        {/* Glow burst at convergence */}
        <div
          style={{
            position: 'absolute',
            width: 400,
            height: 400,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${COLORS.primary} 0%, rgba(245,124,0,0.3) 40%, transparent 70%)`,
            transform: `scale(${burstScale})`,
            opacity: burstOpacity,
            filter: 'blur(30px)',
            pointerEvents: 'none',
          }}
        />
      </div>

      {/* Logo — starts above text at center, flies to top-right corner */}
      <div
        style={{
          position: 'absolute',
          left: logoLeft,
          top: logoTop,
          transform: `scale(${logoEntrance})`,
          opacity: logoEntrance,
          zIndex: 10,
        }}
      >
        <NifraimLogo size={logoSizeAnim} color="#FFFFFF" />
      </div>

      {/* Text reveal layer (outside camera transform) */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 20,
        }}
      >
        {/* "Nifraim.com" brand text with shimmer */}
        <div
          style={{
            fontSize: 140,
            fontWeight: 800,
            color: '#FFFFFF',
            direction: 'ltr',
            letterSpacing: -3,
            lineHeight: 1,
            opacity: textOpacity,
            transform: `scale(${0.6 + textSpring * 0.4})`,
            textShadow: `0 0 ${40 * glowPulse}px rgba(255,255,255,${0.15 * glowPulse}), 0 4px 30px rgba(0,0,0,0.15)`,
            position: 'relative',
          }}
        >
          <span style={{ position: 'relative' }}>
            Nifraim.com
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
              Nifraim.com
            </span>
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
