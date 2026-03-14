import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { COLORS } from '../constants/colors';
import { SPRING, FPS, fontFamily } from '../constants/tokens';
import { SCENE4 } from '../constants/mockData';
import { StatusPill } from '../components/StatusPill';
import { DonutChart } from '../components/DonutChart';

const SCENE_BG = '#242424';

export const FileComparisonScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Phase 1: Dashboard zooms in with perspective
  const entryScale = interpolate(frame, [0, 40], [0.72, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryRotX = interpolate(frame, [0, 30], [7, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 2: Title slams in
  const titleScale = spring({ fps: FPS, frame: frame - 3, config: { damping: 14, mass: 0.5 } });

  // Phase 3: Main donut zoom + rotate
  const donutScale = spring({ fps: FPS, frame: frame - 18, config: SPRING.BOUNCY });
  const donutRotate = interpolate(frame, [18, 50], [-180, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 4: Mini donuts fly in from sides
  const mini1X = interpolate(frame, [50, 68], [-300, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const mini2X = interpolate(frame, [55, 73], [300, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const miniOpacity = interpolate(frame, [50, 62], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const miniScale = spring({ fps: FPS, frame: frame - 52, config: SPRING.SMOOTH });

  // Ken Burns
  const kenZoom = interpolate(frame, [70, 119], [1, 1.08], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const kenPanY = interpolate(frame, [70, 119], [0, -18], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: SCENE_BG, fontFamily, direction: 'rtl' }}>
      <div
        style={{
          width: '100%',
          height: '100%',
          padding: '50px 80px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 24,
          opacity: entryOpacity,
          transform: `perspective(1400px) rotateX(${entryRotX}deg) scale(${entryScale * kenZoom}) translateY(${kenPanY}px)`,
          transformOrigin: 'center top',
        }}
      >
        {/* Title */}
        <div
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: COLORS.primary,
            transform: `scale(${0.3 + titleScale * 0.7})`,
            opacity: titleScale,
          }}
        >
          {SCENE4.title}
        </div>

        {/* Status pills */}
        <div style={{ display: 'flex', gap: 20 }}>
          {SCENE4.pills.map((pill, i) => (
            <StatusPill
              key={pill.label}
              label={pill.label}
              value={pill.value}
              color={pill.color}
              bg={pill.bg}
              delay={5 + i * 4}
            />
          ))}
        </div>

        {/* Main donut */}
        <div
          style={{
            marginTop: 4,
            transform: `scale(${donutScale}) rotate(${donutRotate}deg)`,
            opacity: donutScale,
          }}
        >
          <DonutChart
            segments={SCENE4.mainDonut.segments}
            total={SCENE4.mainDonut.total}
            centerLabel={SCENE4.mainDonut.centerLabel}
            size={350}
            strokeWidth={46}
            delay={18}
          />
        </div>

        {/* Mini donuts — fly from sides */}
        <div style={{ display: 'flex', gap: 100, justifyContent: 'center', opacity: miniOpacity }}>
          {SCENE4.miniDonuts.map((mini, i) => (
            <div
              key={mini.title}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                transform: `translateX(${i === 0 ? mini1X : mini2X}px) scale(${0.7 + miniScale * 0.3})`,
              }}
            >
              <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.textOnDarkMuted }}>{mini.title}</div>
              <DonutChart
                segments={mini.segments}
                total={mini.total}
                size={200}
                strokeWidth={30}
                delay={55 + i * 5}
              />
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
