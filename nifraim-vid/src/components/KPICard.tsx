import { useCurrentFrame, spring } from 'remotion';
import { SPRING, FPS } from '../constants/tokens';
import { TOKENS } from '../constants/tokens';
import { COLORS } from '../constants/colors';
import { CountUp } from './CountUp';

interface KPICardProps {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  color: string;
  delay?: number;
}

export const KPICard: React.FC<KPICardProps> = ({
  label,
  value,
  prefix = '',
  suffix = '',
  color,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const progress = spring({
    fps: FPS,
    frame: frame - delay,
    config: SPRING.SNAPPY,
  });

  return (
    <div
      style={{
        background: COLORS.glass,
        backdropFilter: 'blur(12px)',
        border: `1px solid ${COLORS.glassBorder}`,
        borderRadius: TOKENS.radiusMd,
        padding: '28px 36px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 10,
        minWidth: 180,
        boxShadow: COLORS.glassShadow,
        opacity: progress,
        transform: `translateY(${(1 - progress) * 80}px) scale(${0.5 + progress * 0.5})`,
        borderTop: `3px solid ${color}`,
      }}
    >
      <CountUp
        value={value}
        prefix={prefix}
        suffix={suffix}
        startFrame={delay + 5}
        duration={25}
        style={{
          fontSize: 44,
          fontWeight: 800,
          color: COLORS.primary,
        }}
      />
      <div
        style={{
          fontSize: 18,
          fontWeight: 600,
          color: COLORS.textOnDarkMuted,
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </div>
    </div>
  );
};
