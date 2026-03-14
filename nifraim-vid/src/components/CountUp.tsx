import { useCurrentFrame } from 'remotion';
import { interpolate } from 'remotion';

interface CountUpProps {
  value: number;
  startFrame?: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  style?: React.CSSProperties;
}

export const CountUp: React.FC<CountUpProps> = ({
  value,
  startFrame = 0,
  duration = 30,
  prefix = '',
  suffix = '',
  decimals = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const current = interpolate(
    frame,
    [startFrame, startFrame + duration],
    [0, value],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  const formatted = decimals > 0
    ? current.toFixed(decimals)
    : Math.round(current).toLocaleString('en-US');

  return (
    <span style={{ direction: 'ltr', unicodeBidi: 'embed', ...style }}>
      {prefix}{formatted}{suffix}
    </span>
  );
};
