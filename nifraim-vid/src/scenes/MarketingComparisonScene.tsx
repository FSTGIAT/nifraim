import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { COLORS } from '../constants/colors';
import { SPRING, FPS, fontFamily, TOKENS } from '../constants/tokens';
import { MARKETING_COMPARISON } from '../constants/marketingData';
import { StatusPill } from '../components/StatusPill';
import { DonutChart } from '../components/DonutChart';
import { KPIStrip } from '../components/KPIStrip';
import { BarChart } from '../components/BarChart';

const SCENE_BG = '#242424';

export const MarketingComparisonScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Phase 1: Dashboard zoom in
  const zoomScale = interpolate(frame, [0, 40], [0.78, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const perspTilt = interpolate(frame, [0, 30], [5, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const dashOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 2: Title
  const titleSpring = spring({ fps: FPS, frame: frame - 5, config: SPRING.SNAPPY });
  const titleY = interpolate(frame, [5, 18], [60, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 3: Pills
  const pillsOpacity = interpolate(frame, [15, 25], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 4: Left panel (donut + KPIs)
  const leftPanelX = interpolate(frame, [35, 55], [-200, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const leftPanelOpacity = interpolate(frame, [35, 48], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const leftPanelScale = spring({ fps: FPS, frame: frame - 37, config: SPRING.SMOOTH });

  // Phase 5: Right panel (bar chart)
  const rightPanelX = interpolate(frame, [45, 65], [200, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const rightPanelOpacity = interpolate(frame, [45, 58], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const rightPanelScale = spring({ fps: FPS, frame: frame - 47, config: SPRING.SMOOTH });

  // Ken Burns
  const kenZoom = interpolate(frame, [70, 149], [1, 1.05], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const kenPanY = interpolate(frame, [70, 149], [0, -10], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: SCENE_BG, fontFamily, direction: 'rtl' }}>
      <div
        style={{
          width: '100%',
          height: '100%',
          padding: '50px 70px',
          display: 'flex',
          flexDirection: 'column',
          gap: 24,
          opacity: dashOpacity,
          transform: `perspective(1400px) rotateX(${perspTilt}deg) scale(${zoomScale * kenZoom}) translateY(${kenPanY}px)`,
          transformOrigin: 'center center',
        }}
      >
        {/* Title + subtitle */}
        <div style={{ opacity: titleSpring, transform: `translateY(${titleY}px) scale(${0.8 + titleSpring * 0.2})` }}>
          <div style={{ fontSize: 38, fontWeight: 700, color: COLORS.textOnDark }}>
            {MARKETING_COMPARISON.title}
          </div>
          <div style={{ fontSize: 20, color: COLORS.textOnDarkMuted, marginTop: 4 }}>
            {MARKETING_COMPARISON.subtitle}
          </div>
        </div>

        {/* Status pills row */}
        <div style={{ display: 'flex', gap: 16, opacity: pillsOpacity }}>
          {MARKETING_COMPARISON.pills.map((p, i) => (
            <StatusPill key={p.label} label={p.label} value={p.value} color={p.color} bg={p.bg} delay={18 + i * 4} />
          ))}
        </div>

        {/* KPI strip */}
        <KPIStrip items={MARKETING_COMPARISON.kpis} baseDelay={28} stagger={4} />

        {/* Two-panel layout: Donut + Bar chart */}
        <div style={{ display: 'flex', gap: 28, flex: 1 }}>
          {/* Left: Donut */}
          <div
            style={{
              flex: 1,
              background: COLORS.glass,
              backdropFilter: 'blur(12px)',
              border: `1px solid ${COLORS.glassBorder}`,
              borderRadius: TOKENS.radiusMd,
              padding: 20,
              boxShadow: COLORS.glassShadow,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: leftPanelOpacity,
              transform: `translateX(${leftPanelX}px) scale(${0.85 + leftPanelScale * 0.15})`,
            }}
          >
            <div style={{ fontSize: 18, fontWeight: 700, color: COLORS.textOnDark, marginBottom: 8 }}>
              {MARKETING_COMPARISON.donut.title}
            </div>
            <DonutChart
              segments={MARKETING_COMPARISON.donut.segments}
              total={MARKETING_COMPARISON.donut.total}
              centerLabel={MARKETING_COMPARISON.donut.centerLabel}
              size={200}
              strokeWidth={28}
              delay={42}
            />
          </div>

          {/* Right: Bar chart */}
          <div
            style={{
              flex: 1,
              opacity: rightPanelOpacity,
              transform: `translateX(${rightPanelX}px) scale(${0.85 + rightPanelScale * 0.15})`,
            }}
          >
            <BarChart
              title={MARKETING_COMPARISON.barChart.title}
              bars={MARKETING_COMPARISON.barChart.bars}
              delay={50}
              suffix="M"
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
