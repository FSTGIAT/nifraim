import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { COLORS } from '../constants/colors';
import { SPRING, FPS, fontFamily } from '../constants/tokens';

// Scattered file names that drift in the background — feels chaotic
const SCATTERED_FILES = [
  { name: 'נפרעים_מור_דצמ.xlsx', x: 120, y: 140, rot: -8, delay: 0 },
  { name: 'פרודוקציה_הפניקס.xls', x: 1400, y: 100, rot: 12, delay: 3 },
  { name: 'עמלות_כלל_Q4.xlsx', x: 200, y: 750, rot: 5, delay: 6 },
  { name: 'גמל_מנורה_2025.xlsx', x: 1300, y: 680, rot: -11, delay: 2 },
  { name: 'הכשרה_נפרעים.xlsx', x: 750, y: 80, rot: 3, delay: 8 },
  { name: 'ביטוח_אלטשולר.xlsx', x: 900, y: 820, rot: -6, delay: 5 },
  { name: 'השתלמות_הראל.xls', x: 60, y: 460, rot: 9, delay: 4 },
  { name: 'Excellence_dec.xlsx', x: 1500, y: 420, rot: -4, delay: 7 },
];

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Entry
  const entryOpacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Headline — massive, center stage
  const headlineOpacity = interpolate(frame, [8, 22], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const headlineScale = spring({ fps: FPS, frame: frame - 6, config: { damping: 12, mass: 0.7 } });

  // Subtext
  const subOpacity = interpolate(frame, [25, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const subY = interpolate(frame, [25, 40], [40, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Orange glow pulse behind headline
  const glowPulse = Math.sin(frame * 0.08) * 0.3 + 0.7;

  return (
    <AbsoluteFill
      style={{
        background: COLORS.darkBg,
        fontFamily,
        direction: 'rtl',
        opacity: entryOpacity,
      }}
    >
      {/* Scattered file names — chaotic background */}
      {SCATTERED_FILES.map((file, i) => {
        const fileProgress = spring({
          fps: FPS,
          frame: frame - file.delay,
          config: SPRING.SMOOTH,
        });
        const floatY = Math.sin((frame + i * 20) * 0.04) * 6;

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: file.x,
              top: file.y,
              transform: `rotate(${file.rot}deg) translateY(${floatY}px)`,
              opacity: fileProgress * 0.12,
              fontSize: 20,
              fontWeight: 600,
              color: COLORS.warmHighlight,
              whiteSpace: 'nowrap',
              direction: 'ltr',
              unicodeBidi: 'embed' as const,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <svg width={18} height={18} viewBox="0 0 24 24" fill="none">
              <rect x={2} y={2} width={20} height={20} rx={3} fill={COLORS.primary} opacity={0.4} />
              <text x={12} y={16} textAnchor="middle" fill="#fff" fontSize={11} fontWeight="bold">X</text>
            </svg>
            {file.name}
          </div>
        );
      })}

      {/* Center content */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 32,
          zIndex: 10,
        }}
      >
        {/* Orange glow behind text */}
        <div
          style={{
            position: 'absolute',
            width: 800,
            height: 800,
            borderRadius: '50%',
            background: `radial-gradient(circle, rgba(245,124,0,${glowPulse * 0.12}) 0%, transparent 60%)`,
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        />

        {/* Main headline — huge */}
        <div
          style={{
            fontSize: 92,
            fontWeight: 800,
            color: '#FFFFFF',
            opacity: headlineOpacity,
            transform: `scale(${0.5 + headlineScale * 0.5})`,
            textAlign: 'center',
            lineHeight: 1.2,
            position: 'relative',
          }}
        >
          מנהלים עמלות{' '}
          <span style={{ color: COLORS.primary }}>בידיים</span>?
        </div>

        {/* Subtext — the pain */}
        <div
          style={{
            fontSize: 36,
            fontWeight: 400,
            color: 'rgba(255,255,255,0.45)',
            opacity: subOpacity,
            transform: `translateY(${subY}px)`,
            textAlign: 'center',
            maxWidth: 900,
            lineHeight: 1.5,
          }}
        >
          עשרות קבצי אקסל. פורמטים שונים. שעות של עבודה ידנית.
        </div>
      </div>
    </AbsoluteFill>
  );
};
