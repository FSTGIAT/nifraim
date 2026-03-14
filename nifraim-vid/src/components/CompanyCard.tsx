import { useCurrentFrame, spring } from 'remotion';
import { SPRING, FPS } from '../constants/tokens';
import { TOKENS } from '../constants/tokens';
import { COLORS } from '../constants/colors';

interface CompanyCardProps {
  name: string;
  products: number;
  accumulation: string;
  active: number;
  inactive: number;
  delay?: number;
}

export const CompanyCard: React.FC<CompanyCardProps> = ({
  name,
  products,
  accumulation,
  active,
  inactive,
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
        backdropFilter: 'blur(8px)',
        border: `1px solid ${COLORS.glassBorder}`,
        borderRadius: TOKENS.radiusMd,
        padding: '18px 24px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
        opacity: progress,
        transform: `translateY(${(1 - progress) * 40}px)`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderRight: `4px solid ${COLORS.primary}`,
      }}
    >
      <div>
        <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.textOnDark }}>{name}</div>
        <div style={{ fontSize: 15, color: COLORS.textOnDarkMuted, marginTop: 3 }}>
          <span style={{ direction: 'ltr', unicodeBidi: 'embed' }}>{products}</span> מוצרים · {accumulation}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        <span
          style={{
            fontSize: 14,
            fontWeight: 600,
            padding: '3px 12px',
            borderRadius: 999,
            background: 'rgba(46,132,74,0.2)',
            color: '#4ADE80',
          }}
        >
          {active} פעיל
        </span>
        {inactive > 0 && (
          <span
            style={{
              fontSize: 14,
              fontWeight: 600,
              padding: '3px 12px',
              borderRadius: 999,
              background: 'rgba(234,0,30,0.15)',
              color: '#FB7185',
            }}
          >
            {inactive} לא פעיל
          </span>
        )}
      </div>
    </div>
  );
};
