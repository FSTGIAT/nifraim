import { useCurrentFrame, spring } from 'remotion';
import { SPRING, FPS } from '../constants/tokens';
import { TOKENS } from '../constants/tokens';

interface StatusPillProps {
  label: string;
  value: number;
  color: string;
  bg: string;
  delay?: number;
}

export const StatusPill: React.FC<StatusPillProps> = ({
  label,
  value,
  color,
  bg,
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
        display: 'inline-flex',
        alignItems: 'center',
        gap: 12,
        padding: '14px 32px',
        borderRadius: 999,
        background: bg,
        opacity: progress,
        transform: `scale(${0.5 + progress * 0.5})`,
        boxShadow: TOKENS.shadowSm,
      }}
    >
      <span
        style={{
          fontSize: 32,
          fontWeight: 800,
          color,
          direction: 'ltr',
          unicodeBidi: 'embed',
        }}
      >
        {value}
      </span>
      <span style={{ fontSize: 24, fontWeight: 600, color }}>
        {label}
      </span>
    </div>
  );
};
