import { AbsoluteFill, Img, useCurrentFrame, spring, interpolate, staticFile } from 'remotion';
import { BRAND_GRADIENT } from './constants/colors';
import { FPS, fontFamily } from './constants/tokens';

// Fox image is 540x727. Paw layer is same canvas size, pivot at wrist (~420, 365)
const FOX_W = 540;
const FOX_H = 727;
// Wrist pivot point (where paw connects to arm)
const PIVOT_X = 420;
const PIVOT_Y = 365;

export const FoxAnimation: React.FC = () => {
  const frame = useCurrentFrame();

  // === Phase 1: Fox bounces in from below (frames 0–30) ===
  const entranceSpring = spring({
    fps: FPS,
    frame,
    config: { damping: 8, mass: 0.7 },
  });
  const foxY = interpolate(entranceSpring, [0, 1], [600, 0]);
  const foxScale = interpolate(entranceSpring, [0, 1], [0.3, 1]);

  // === Phase 2: Idle floating bob (frames 30+) ===
  const bobAmount = frame > 20 ? Math.sin((frame - 20) * 0.06) * 12 : 0;

  // === Paw waving animation — quick wrist tilts like a real wave ===
  const waveStart = 25;
  let handRotation = 0;
  if (frame > waveStart) {
    const t = frame - waveStart;
    if (t < 80) {
      // Active waving: quick small tilts from the wrist
      const waveSpeed = 0.55;
      const waveAmplitude = interpolate(t, [0, 8, 60, 80], [0, 15, 12, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      handRotation = Math.sin(t * waveSpeed) * waveAmplitude;
    } else {
      // Gentle idle wiggle
      handRotation = Math.sin((t - 80) * 0.06) * 2;
    }
  }

  // === Gentle body sway ===
  const bodySway = frame > waveStart + 70
    ? Math.sin((frame - waveStart) * 0.04) * 1
    : 0;

  // === Shadow under the fox ===
  const shadowScale = interpolate(entranceSpring, [0, 1], [0.2, 1]);
  const shadowOpacity = interpolate(entranceSpring, [0, 1], [0, 0.3]);
  const shadowSqueeze = frame > 20 ? 1 - Math.sin((frame - 20) * 0.06) * 0.15 : 1;

  // === Background glow pulse ===
  const glowPulse = frame > 30 ? Math.sin((frame - 30) * 0.05) * 0.15 + 0.85 : 0;

  // === Sparkles ===
  const sparkles = [
    { x: -120, y: -180, delay: 35, size: 8 },
    { x: 140, y: -140, delay: 50, size: 6 },
    { x: -90, y: 80, delay: 65, size: 10 },
    { x: 160, y: 40, delay: 80, size: 7 },
    { x: -40, y: -220, delay: 95, size: 5 },
    { x: 100, y: 120, delay: 110, size: 9 },
  ];

  return (
    <AbsoluteFill
      style={{
        background: BRAND_GRADIENT,
        fontFamily,
        overflow: 'hidden',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      {/* Radial glow behind the fox */}
      <div
        style={{
          position: 'absolute',
          width: 600,
          height: 600,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.1) 40%, transparent 70%)`,
          opacity: glowPulse,
          filter: 'blur(40px)',
          transform: `translateY(${bobAmount * 0.5}px)`,
        }}
      />

      {/* Shadow on the ground */}
      <div
        style={{
          position: 'absolute',
          bottom: 220,
          width: 200,
          height: 30,
          borderRadius: '50%',
          background: 'rgba(0,0,0,0.25)',
          filter: 'blur(12px)',
          transform: `scaleX(${shadowScale * shadowSqueeze}) scaleY(${shadowScale * 0.6})`,
          opacity: shadowOpacity,
        }}
      />

      {/* Fox container — body + hand layered */}
      <div
        style={{
          position: 'relative',
          width: FOX_W,
          height: FOX_H,
          transform: `translateY(${foxY + bobAmount}px) scale(${foxScale * 1.1}) rotate(${bodySway}deg)`,
          transformOrigin: 'center bottom',
          marginTop: -40,
        }}
      >
        {/* Full fox as base — always visible, no gaps */}
        <Img
          src={staticFile('fox2.png')}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: FOX_W,
            height: FOX_H,
          }}
        />

        {/* Hand/arm layer — rotates around shoulder pivot */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: FOX_W,
            height: FOX_H,
            transformOrigin: `${PIVOT_X}px ${PIVOT_Y}px`,
            transform: `rotate(${handRotation}deg)`,
          }}
        >
          <Img
            src={staticFile('fox-hand.png')}
            style={{
              width: FOX_W,
              height: FOX_H,
            }}
          />
        </div>
      </div>

      {/* Sparkles */}
      {sparkles.map((s, i) => {
        const sparkleSpring = spring({
          fps: FPS,
          frame: frame - s.delay,
          config: { damping: 15, mass: 0.3 },
        });
        const sparkleFloat = frame > s.delay ? Math.sin((frame - s.delay) * 0.08 + i) * 8 : 0;
        const sparkleFade = interpolate(
          frame,
          [s.delay, s.delay + 10, s.delay + 60, s.delay + 80],
          [0, 1, 1, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              width: s.size,
              height: s.size,
              borderRadius: '50%',
              background: '#FFFFFF',
              boxShadow: `0 0 ${s.size * 2}px ${s.size}px rgba(255,255,255,0.6)`,
              transform: `translate(${s.x}px, ${s.y + sparkleFloat + bobAmount * 0.3}px) scale(${sparkleSpring})`,
              opacity: sparkleFade,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
