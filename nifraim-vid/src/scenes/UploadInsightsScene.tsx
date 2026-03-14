import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { COLORS } from '../constants/colors';
import { SPRING, FPS, fontFamily, TOKENS } from '../constants/tokens';
import { SCENE3 } from '../constants/mockData';
import { KPIStrip } from '../components/KPIStrip';
import { BarChart } from '../components/BarChart';

const SCENE_BG = '#242424';

export const UploadInsightsScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Phase 1: Dashboard zooms in from 80% with 3D tilt
  const zoomScale = interpolate(frame, [0, 50], [0.78, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const perspTilt = interpolate(frame, [0, 35], [5, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const dashOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 2: File drops with bounce
  const fileDrop = spring({ fps: FPS, frame: frame - 5, config: SPRING.BOUNCY });

  // Phase 3: Upload zone shrinks
  const zoneScale = interpolate(frame, [18, 32], [1, 0.55], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const zoneY = interpolate(frame, [18, 32], [0, -20], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 4: Charts slide up with scale
  const chart1Opacity = interpolate(frame, [45, 60], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const chart1Y = interpolate(frame, [45, 60], [120, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const chart1Scale = spring({ fps: FPS, frame: frame - 45, config: SPRING.SMOOTH });

  const chart2Opacity = interpolate(frame, [55, 70], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const chart2Y = interpolate(frame, [55, 70], [120, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const chart2Scale = spring({ fps: FPS, frame: frame - 55, config: SPRING.SMOOTH });

  // Ken Burns drift
  const kenBurns = interpolate(frame, [65, 119], [1, 1.06], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const kenPanX = interpolate(frame, [65, 119], [0, -12], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: SCENE_BG, fontFamily, direction: 'rtl' }}>
      <div
        style={{
          width: '100%',
          height: '100%',
          padding: '60px 70px',
          display: 'flex',
          flexDirection: 'column',
          gap: 32,
          opacity: dashOpacity,
          transform: `perspective(1400px) rotateX(${perspTilt}deg) scale(${zoomScale * kenBurns}) translateX(${kenPanX}px)`,
          transformOrigin: 'center center',
        }}
      >
        {/* Upload zone */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            transform: `scale(${zoneScale}) translateY(${zoneY}px)`,
          }}
        >
          <div
            style={{
              border: `2px dashed ${COLORS.primary}`,
              borderRadius: TOKENS.radiusLg,
              padding: '16px 40px',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              background: COLORS.glass,
              backdropFilter: 'blur(8px)',
              boxShadow: '0 0 30px rgba(245,124,0,0.1)',
            }}
          >
            <div style={{ transform: `translateY(${(1 - fileDrop) * -80}px)`, opacity: fileDrop }}>
              <svg width={48} height={48} viewBox="0 0 24 24" fill="none" stroke={COLORS.primary} strokeWidth={2}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <span style={{ fontSize: 24, fontWeight: 600, color: COLORS.textOnDarkMuted }}>
              גרירת קובץ פרודוקציה
            </span>
          </div>
        </div>

        {/* KPI Strip */}
        <KPIStrip items={SCENE3.kpis} baseDelay={18} stagger={5} />

        {/* Chart cards */}
        <div style={{ display: 'flex', gap: 32, flex: 1 }}>
          <div
            style={{
              flex: 1,
              opacity: chart1Opacity,
              transform: `translateY(${chart1Y}px) scale(${0.85 + chart1Scale * 0.15})`,
            }}
          >
            <BarChart title={SCENE3.productTypeChart.title} bars={SCENE3.productTypeChart.bars} delay={47} />
          </div>
          <div
            style={{
              flex: 1,
              opacity: chart2Opacity,
              transform: `translateY(${chart2Y}px) scale(${0.85 + chart2Scale * 0.15})`,
            }}
          >
            <BarChart
              title={SCENE3.companyChart.title}
              bars={SCENE3.companyChart.bars.map((b) => ({ ...b }))}
              delay={57}
              suffix="M"
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
