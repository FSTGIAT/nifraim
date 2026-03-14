import { useCurrentFrame, spring } from 'remotion';
import { SPRING, FPS } from '../constants/tokens';
import { TOKENS } from '../constants/tokens';
import { COLORS } from '../constants/colors';

interface BarItem {
  label: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  title: string;
  bars: BarItem[];
  delay?: number;
  suffix?: string;
}

export const BarChart: React.FC<BarChartProps> = ({
  title,
  bars,
  delay = 0,
  suffix = '',
}) => {
  const frame = useCurrentFrame();
  const maxValue = Math.max(...bars.map((b) => b.value));

  return (
    <div
      style={{
        background: COLORS.glass,
        backdropFilter: 'blur(12px)',
        border: `1px solid ${COLORS.glassBorder}`,
        borderRadius: TOKENS.radiusMd,
        padding: 32,
        boxShadow: COLORS.glassShadow,
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.textOnDark, marginBottom: 20 }}>
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {bars.map((bar, i) => {
          const barDelay = delay + i * 3;
          const progress = spring({
            fps: FPS,
            frame: frame - barDelay,
            config: SPRING.SMOOTH,
          });
          const width = (bar.value / maxValue) * 100 * progress;

          return (
            <div key={bar.label} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 160,
                  fontSize: 16,
                  fontWeight: 600,
                  color: COLORS.textOnDarkMuted,
                  textAlign: 'left',
                  flexShrink: 0,
                  overflow: 'hidden',
                  whiteSpace: 'nowrap',
                  textOverflow: 'ellipsis',
                }}
              >
                {bar.label}
              </div>
              <div style={{ flex: 1, height: 28, background: 'rgba(255,255,255,0.06)', borderRadius: 8, overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${width}%`,
                    height: '100%',
                    background: bar.color || COLORS.primary,
                    borderRadius: 8,
                    transition: 'none',
                    boxShadow: `0 0 12px ${bar.color || COLORS.primary}40`,
                  }}
                />
              </div>
              <div
                style={{
                  fontSize: 16,
                  fontWeight: 700,
                  color: COLORS.textOnDark,
                  minWidth: 60,
                  direction: 'ltr',
                  unicodeBidi: 'embed',
                  textAlign: 'right',
                  opacity: progress,
                }}
              >
                {Math.round(bar.value * progress).toLocaleString('en-US')}{suffix}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
