import { useCurrentFrame, spring } from 'remotion';
import { SPRING, FPS } from '../constants/tokens';
import { TOKENS } from '../constants/tokens';

interface ExcelCardProps {
  headers: string[];
  rotation?: number;
  delay?: number;
  fromX?: number;
  fromY?: number;
}

export const ExcelCard: React.FC<ExcelCardProps> = ({
  headers,
  rotation = 0,
  delay = 0,
  fromX = 0,
  fromY = -200,
}) => {
  const frame = useCurrentFrame();
  const progress = spring({
    fps: FPS,
    frame: frame - delay,
    config: SPRING.BOUNCY,
  });

  const x = fromX * (1 - progress);
  const y = fromY * (1 - progress);
  const rot = rotation * progress;

  return (
    <div
      style={{
        position: 'absolute',
        background: '#FFFFFF',
        borderRadius: TOKENS.radiusMd,
        padding: 16,
        boxShadow: TOKENS.shadowLg,
        opacity: progress,
        transform: `translate(${x}px, ${y}px) rotate(${rot}deg)`,
        width: 480,
      }}
    >
      {/* Green header bar */}
      <div
        style={{
          background: '#217346',
          borderRadius: '8px 8px 0 0',
          height: 36,
          display: 'flex',
          alignItems: 'center',
          padding: '0 14px',
          marginBottom: 8,
        }}
      >
        <div style={{ color: '#fff', fontSize: 16, fontWeight: 600 }}>Excel</div>
      </div>
      {/* Column headers */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${Math.min(headers.length, 4)}, 1fr)`,
          gap: 1,
          background: '#E0E0E0',
          borderRadius: 4,
          overflow: 'hidden',
        }}
      >
        {headers.slice(0, 4).map((h) => (
          <div
            key={h}
            style={{
              background: '#F5F5F5',
              padding: '8px 10px',
              fontSize: 14,
              fontWeight: 700,
              color: '#333',
              textAlign: 'center',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
            }}
          >
            {h}
          </div>
        ))}
        {/* Fake data rows */}
        {[0, 1, 2].map((row) =>
          headers.slice(0, 4).map((h) => (
            <div
              key={`${h}-${row}`}
              style={{
                background: '#FFFFFF',
                padding: '6px 10px',
                fontSize: 12,
                color: '#999',
                textAlign: 'center',
              }}
            >
              ···
            </div>
          )),
        )}
      </div>
    </div>
  );
};
