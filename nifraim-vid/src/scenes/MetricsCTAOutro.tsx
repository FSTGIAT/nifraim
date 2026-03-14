import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { BRAND_GRADIENT } from '../constants/colors';
import { SPRING, FPS, fontFamily, TOKENS } from '../constants/tokens';
import { SCENE7 } from '../constants/mockData';
import { NifraimLogo } from '../components/NifraimLogo';
import { CountUp } from '../components/CountUp';

export const MetricsCTAOutro: React.FC = () => {
  const frame = useCurrentFrame();

  // Phase 1: Metrics cards fly in from different directions with 3D
  const metricsScale = interpolate(frame, [0, 35], [0.6, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const metricsRotX = interpolate(frame, [0, 30], [10, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 2: Metrics zoom out and fade
  const metricsExit = interpolate(frame, [65, 85], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const metricsExitScale = interpolate(frame, [65, 85], [1, 0.7], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 3: CTA - logo slams in with bounce
  const logoScale = spring({ fps: FPS, frame: frame - 80, config: SPRING.BOUNCY });
  const logoRotate = interpolate(frame, [80, 100], [360, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 4: Brand text
  const brandScale = spring({ fps: FPS, frame: frame - 88, config: SPRING.SNAPPY });
  const brandY = interpolate(frame, [88, 108], [100, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 5: Subtitle
  const subtitleOpacity = interpolate(frame, [100, 118], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 6: CTA button
  const btnProgress = spring({ fps: FPS, frame: frame - 115, config: SPRING.BOUNCY });
  const btnPulse = 1 + Math.sin(frame * 0.15) * 0.02;

  // Phase 7: URL
  const urlOpacity = interpolate(frame, [130, 150], [0, 0.8], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Shimmer on brand text
  const shimmerX = interpolate(frame, [95, 160], [-100, 200], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

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
        gap: 32,
      }}
    >
      {/* Metric cards — fly in with 3D perspective */}
      <div
        style={{
          display: 'flex',
          gap: 40,
          opacity: metricsExit,
          transform: `perspective(1200px) rotateX(${metricsRotX}deg) scale(${metricsScale * metricsExitScale})`,
          position: 'absolute',
          top: '50%',
          left: '50%',
          translate: '-50% -50%',
        }}
      >
        {SCENE7.metrics.map((metric, i) => {
          const cardY = interpolate(
            frame,
            [i * 5, i * 5 + 15],
            [150, 0],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          const cardOpacity = interpolate(
            frame,
            [i * 5, i * 5 + 10],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          const cardScale = spring({
            fps: FPS,
            frame: frame - i * 5,
            config: SPRING.SNAPPY,
          });

          return (
            <div
              key={metric.label}
              style={{
                background: 'rgba(255,255,255,0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: TOKENS.radiusLg,
                padding: '40px 52px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                minWidth: 220,
                opacity: cardOpacity,
                transform: `translateY(${cardY}px) scale(${0.5 + cardScale * 0.5})`,
              }}
            >
              <CountUp
                value={metric.value}
                suffix={metric.suffix}
                startFrame={i * 5 + 5}
                duration={20}
                style={{ fontSize: 80, fontWeight: 800, color: '#FFFFFF' }}
              />
              <div style={{ fontSize: 24, fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                {metric.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* CTA section */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 24,
          opacity: 1 - metricsExit,
        }}
      >
        {/* Logo — spins in */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 20,
          }}
        >
          <div style={{ transform: `scale(${logoScale}) rotate(${logoRotate}deg)` }}>
            <NifraimLogo size={160} color="#FFFFFF" />
          </div>
          <span
            style={{
              fontSize: 140,
              fontWeight: 800,
              letterSpacing: -3,
              lineHeight: 1,
              color: '#FFFFFF',
              opacity: brandScale,
              transform: `translateY(${brandY}px) scale(${0.5 + brandScale * 0.5})`,
              textShadow: '0 4px 30px rgba(0,0,0,0.15)',
              position: 'relative',
              display: 'inline-block',
            }}
          >
            Nifraim
            <span
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: `linear-gradient(105deg, transparent ${shimmerX - 5}%, rgba(255,255,255,0.4) ${shimmerX}%, transparent ${shimmerX + 5}%)`,
                pointerEvents: 'none',
              }}
            />
          </span>
        </div>

        {/* CTA Button — bouncy with pulse */}
        <div
          style={{
            background: '#FFFFFF',
            borderRadius: TOKENS.radiusLg,
            padding: '20px 72px',
            opacity: btnProgress,
            transform: `translateY(${(1 - btnProgress) * 60}px) scale(${(0.5 + btnProgress * 0.5) * btnPulse})`,
            boxShadow: '0 8px 40px rgba(0,0,0,0.15)',
          }}
        >
          <span
            style={{
              fontSize: 32,
              fontWeight: 700,
              color: '#E65100',
            }}
          >
            {SCENE7.cta}
          </span>
        </div>

        {/* URL */}
        <div
          style={{
            fontSize: 36,
            color: 'rgba(255,255,255,0.7)',
            opacity: urlOpacity,
            fontWeight: 400,
            direction: 'ltr',
            unicodeBidi: 'embed' as const,
            letterSpacing: 1,
          }}
        >
          {SCENE7.url}
        </div>
      </div>
    </AbsoluteFill>
  );
};
