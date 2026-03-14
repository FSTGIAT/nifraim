import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { COLORS } from '../constants/colors';
import { SPRING, FPS, fontFamily, TOKENS } from '../constants/tokens';
import { SCENE5 } from '../constants/mockData';
import { KPIStrip } from '../components/KPIStrip';
import { DonutChart } from '../components/DonutChart';
import { BarChart } from '../components/BarChart';

const SCENE_BG = '#242424';

export const CommissionDashboardScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Phase 1: Dashboard zooms in with 3D tilt
  const entryScale = interpolate(frame, [0, 45], [0.68, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryRotX = interpolate(frame, [0, 35], [8, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryRotY = interpolate(frame, [0, 35], [-3, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 2: Banner slides from right
  const bannerX = interpolate(frame, [5, 22], [200, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const bannerOpacity = spring({ fps: FPS, frame: frame - 5, config: SPRING.SNAPPY });

  // Phase 3: Donut zooms with rotation
  const donutScale = spring({ fps: FPS, frame: frame - 20, config: SPRING.BOUNCY });
  const donutRotate = interpolate(frame, [20, 55], [-90, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 4: Right panel slides up
  const rightOpacity = interpolate(frame, [35, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const rightY = interpolate(frame, [35, 50], [100, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 5: Alert slams from bottom
  const alertProgress = spring({ fps: FPS, frame: frame - 70, config: SPRING.SNAPPY });
  const alertPulse = Math.sin(frame * 0.1) * 0.3 + 0.7;
  const alertY = interpolate(frame, [70, 82], [80, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Ken Burns
  const kenZoom = interpolate(frame, [55, 119], [1, 1.05], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const kenPanX = interpolate(frame, [55, 119], [0, 10], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: SCENE_BG, fontFamily, direction: 'rtl' }}>
      <div
        style={{
          width: '100%',
          height: '100%',
          padding: '40px 60px',
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
          opacity: entryOpacity,
          transform: `perspective(1400px) rotateX(${entryRotX}deg) rotateY(${entryRotY}deg) scale(${entryScale * kenZoom}) translateX(${kenPanX}px)`,
          transformOrigin: 'center center',
        }}
      >
        {/* Company banner */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            opacity: bannerOpacity,
            transform: `translateX(${bannerX}px)`,
          }}
        >
          <div style={{ width: 6, height: 44, borderRadius: 3, background: COLORS.primary }} />
          <div style={{ fontSize: 44, fontWeight: 700, color: COLORS.primary }}>
            {SCENE5.companyName}
          </div>
          <div
            style={{
              fontSize: 18,
              fontWeight: 600,
              padding: '6px 18px',
              borderRadius: 999,
              background: 'rgba(46,132,74,0.2)',
              color: '#4ADE80',
            }}
          >
            {SCENE5.categoryBadge}
          </div>
        </div>

        {/* Content row */}
        <div style={{ display: 'flex', gap: 36, flex: 1 }}>
          {/* Donut */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 8,
              transform: `scale(${donutScale}) rotate(${donutRotate}deg)`,
              opacity: donutScale,
            }}
          >
            <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.textOnDarkMuted, transform: `rotate(${-donutRotate}deg)` }}>
              {SCENE5.donutTitle}
            </div>
            <DonutChart
              segments={SCENE5.donut.segments}
              total={SCENE5.donut.total}
              centerLabel="סה״כ"
              size={300}
              strokeWidth={40}
              delay={22}
            />
          </div>

          {/* KPIs + Bar */}
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              gap: 20,
              opacity: rightOpacity,
              transform: `translateY(${rightY}px)`,
            }}
          >
            <KPIStrip items={SCENE5.kpis} baseDelay={35} stagger={4} />
            <BarChart title={SCENE5.barChart.title} bars={SCENE5.barChart.bars} delay={45} suffix="M" />
          </div>
        </div>

        {/* Alert banner */}
        <div
          style={{
            background: 'rgba(234,0,30,0.1)',
            border: `1px solid rgba(234,0,30,0.3)`,
            borderRadius: TOKENS.radiusMd,
            padding: '14px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            opacity: alertProgress,
            transform: `translateY(${alertY}px) scale(${0.9 + alertProgress * 0.1})`,
            boxShadow: `0 0 ${alertPulse * 20}px rgba(234, 0, 30, ${alertPulse * 0.15})`,
            backdropFilter: 'blur(8px)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke="#FB7185" strokeWidth={2}>
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <span style={{ fontSize: 18, fontWeight: 600, color: '#FB7185' }}>
              <span style={{ direction: 'ltr', unicodeBidi: 'embed' as const }}>{SCENE5.alert.count}</span>
              {' '}{SCENE5.alert.text} — הפסד משוער {SCENE5.alert.loss}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {['הצג', 'שלח מייל', 'Excel'].map((btn) => (
              <div
                key={btn}
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  padding: '7px 18px',
                  borderRadius: 6,
                  background: btn === 'הצג' ? COLORS.primary : 'rgba(255,255,255,0.06)',
                  color: btn === 'הצג' ? '#FFFFFF' : COLORS.textOnDarkMuted,
                  border: btn === 'הצג' ? 'none' : `1px solid ${COLORS.glassBorder}`,
                }}
              >
                {btn}
              </div>
            ))}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
