import { AbsoluteFill, useCurrentFrame, spring, interpolate } from 'remotion';
import { COLORS } from '../constants/colors';
import { SPRING, FPS, fontFamily, TOKENS } from '../constants/tokens';
import { SCENE6 } from '../constants/mockData';
import { NifraimLogo } from '../components/NifraimLogo';
import { KPIStrip } from '../components/KPIStrip';
import { DonutChart } from '../components/DonutChart';
import { CompanyCard } from '../components/CompanyCard';

const SCENE_BG = '#242424';

export const CustomerPortalScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Phase 1: Portal zooms in with perspective
  const entryScale = interpolate(frame, [0, 45], [0.7, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryRotX = interpolate(frame, [0, 35], [7, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const entryOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 2: Header drops
  const headerY = interpolate(frame, [3, 15], [-60, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const headerOpacity = interpolate(frame, [3, 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 3: Greeting scales in
  const greetScale = spring({ fps: FPS, frame: frame - 8, config: SPRING.SNAPPY });
  const greetY = interpolate(frame, [8, 22], [80, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Phase 4: Panels fly in from sides
  const leftPanelX = interpolate(frame, [38, 56], [-250, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const rightPanelX = interpolate(frame, [43, 61], [250, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const panelsOpacity = interpolate(frame, [38, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const panelScale = spring({ fps: FPS, frame: frame - 40, config: SPRING.SMOOTH });

  // Phase 5: Tagline
  const taglineOpacity = interpolate(frame, [80, 95], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const taglineScale = spring({ fps: FPS, frame: frame - 80, config: SPRING.SNAPPY });

  // Ken Burns
  const kenZoom = interpolate(frame, [60, 119], [1, 1.06], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const kenPanY = interpolate(frame, [60, 119], [0, -12], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: SCENE_BG, fontFamily, direction: 'rtl' }}>
      <div
        style={{
          width: '100%',
          height: '100%',
          padding: '40px 70px',
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
          opacity: entryOpacity,
          transform: `perspective(1400px) rotateX(${entryRotX}deg) scale(${entryScale * kenZoom}) translateY(${kenPanY}px)`,
          transformOrigin: 'center center',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            opacity: headerOpacity,
            transform: `translateY(${headerY}px)`,
          }}
        >
          <NifraimLogo size={40} color={COLORS.primary} />
          <span style={{ fontSize: 28, fontWeight: 700, color: COLORS.primary }}>Nifraim</span>
        </div>

        {/* Greeting */}
        <div
          style={{
            opacity: greetScale,
            transform: `translateY(${greetY}px) scale(${0.7 + greetScale * 0.3})`,
          }}
        >
          <div style={{ fontSize: 42, fontWeight: 700, color: COLORS.textOnDark }}>
            {SCENE6.greeting}
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 4 }}>
            <span style={{ fontSize: 18, color: COLORS.textOnDarkMuted, direction: 'ltr', unicodeBidi: 'embed' as const }}>
              {SCENE6.idNumber}
            </span>
            <span
              style={{
                fontSize: 15,
                fontWeight: 600,
                padding: '4px 14px',
                borderRadius: 999,
                background: 'rgba(46,132,74,0.2)',
                color: '#4ADE80',
              }}
            >
              {SCENE6.dateBadge}
            </span>
          </div>
        </div>

        {/* KPIs */}
        <KPIStrip items={SCENE6.kpis} baseDelay={22} stagger={5} />

        {/* Two panels — fly from sides */}
        <div style={{ display: 'flex', gap: 28, flex: 1, opacity: panelsOpacity }}>
          {/* Products list */}
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
              gap: 10,
              transform: `translateX(${leftPanelX}px) scale(${0.85 + panelScale * 0.15})`,
            }}
          >
            <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.textOnDark, marginBottom: 6 }}>
              {SCENE6.productsTitle}
            </div>
            {SCENE6.companies.map((c, i) => (
              <CompanyCard
                key={c.name}
                name={c.name}
                products={c.products}
                accumulation={c.accumulation}
                active={c.active}
                inactive={c.inactive}
                delay={44 + i * 6}
              />
            ))}
          </div>

          {/* Donut */}
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
              gap: 8,
              transform: `translateX(${rightPanelX}px) scale(${0.85 + panelScale * 0.15})`,
            }}
          >
            <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.textOnDark }}>
              {SCENE6.donutTitle}
            </div>
            <DonutChart
              segments={SCENE6.donut.segments}
              total={100}
              centerLabel={SCENE6.donut.centerLabel}
              size={240}
              strokeWidth={34}
              delay={48}
            />
          </div>
        </div>

      </div>
    </AbsoluteFill>
  );
};
