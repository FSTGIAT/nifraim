import { useCurrentFrame, spring, interpolate } from 'remotion';
import { SPRING, FPS } from '../constants/tokens';
import { COLORS } from '../constants/colors';
import { CountUp } from './CountUp';

interface DonutSegment {
  label: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  segments: DonutSegment[];
  total: number;
  centerLabel?: string;
  size?: number;
  strokeWidth?: number;
  delay?: number;
  showLegend?: boolean;
}

export const DonutChart: React.FC<DonutChartProps> = ({
  segments,
  total,
  centerLabel,
  size = 400,
  strokeWidth = 52,
  delay = 0,
  showLegend = true,
}) => {
  const frame = useCurrentFrame();
  const progress = spring({
    fps: FPS,
    frame: frame - delay,
    config: SPRING.SMOOTH,
  });

  const legendOpacity = interpolate(
    frame,
    [delay + 25, delay + 40],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const cx = size / 2;
  const cy = size / 2;

  const sumValues = segments.reduce((acc, s) => acc + s.value, 0);
  let accumulatedOffset = 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          {segments.map((segment) => {
            const segmentFraction = segment.value / sumValues;
            const dashLength = circumference * segmentFraction * progress;
            const dashGap = circumference - dashLength;
            const offset = -circumference * accumulatedOffset * progress;
            accumulatedOffset += segmentFraction;

            return (
              <circle
                key={segment.label}
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke={segment.color}
                strokeWidth={strokeWidth}
                strokeDasharray={`${dashLength} ${dashGap}`}
                strokeDashoffset={offset}
                strokeLinecap="butt"
                style={{ filter: `drop-shadow(0 0 6px ${segment.color}40)` }}
              />
            );
          })}
        </svg>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <CountUp
            value={total}
            startFrame={delay + 5}
            duration={25}
            style={{ fontSize: 56, fontWeight: 800, color: COLORS.textOnDark }}
          />
          {centerLabel && (
            <div style={{ fontSize: 20, color: COLORS.textOnDarkMuted, fontWeight: 600, marginTop: 4 }}>
              {centerLabel}
            </div>
          )}
        </div>
      </div>

      {showLegend && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '10px 24px',
            justifyContent: 'center',
            opacity: legendOpacity,
          }}
        >
          {segments.map((segment) => (
            <div
              key={segment.label}
              style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 16, color: COLORS.textOnDarkMuted }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: segment.color,
                  flexShrink: 0,
                  boxShadow: `0 0 6px ${segment.color}60`,
                }}
              />
              {segment.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
