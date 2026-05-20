// MonthlyCommission — Remotion composition. Three calendar months
// (newest on the right in RTL), each with a paired bar group: צפוי (orange)
// vs בפועל (green). Empty months show a dashed placeholder. A top KPI strip
// shows totals + the aggregate gap. Designed to be readable as a single
// composition rather than 3 disconnected cards.
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion'

const FONT = 'Heebo, sans-serif'

export interface MonthlyCommissionMonth {
  period_month: string
  label: string
  production_uploaded: boolean
  commission_uploaded: boolean
  expected_total: number | null
  actual_total: number | null
  gap_total: number | null
}

export interface MonthlyCommissionProps {
  months: MonthlyCommissionMonth[]    // oldest → newest (callers reverse if needed)
  title?: string
}

const COLORS = {
  expected: '#F57C00',
  expectedDeep: '#E65100',
  expectedSoft: 'rgba(245, 124, 0, 0.16)',
  actual: '#2E844A',
  actualDeep: '#1B5E20',
  actualSoft: 'rgba(46, 132, 74, 0.16)',
  gap: '#EA001E',
  gapSoft: 'rgba(234, 0, 30, 0.10)',
  ok: '#2E844A',
  text: '#181818',
  textMuted: '#706E6B',
  border: '#E5E5E5',
  bg: '#FFFFFF',
  bgWarm: '#FFFBF4',
}

function formatMoney(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return '₪' + Math.round(v).toLocaleString('he-IL')
}

export function MonthlyCommissionComposition(props: MonthlyCommissionProps) {
  const frame = useCurrentFrame()
  const { width, height, fps } = useVideoConfig()
  const months = props.months || []

  // Aggregate KPIs
  const totalExpected = months.reduce((s, m) => s + (m.expected_total ?? 0), 0)
  const totalActual = months.reduce((s, m) => s + (m.actual_total ?? 0), 0)
  const totalGap = months.reduce((s, m) => s + (m.gap_total ?? 0), 0)
  const hasAnyExpected = months.some((m) => m.expected_total != null)
  const hasAnyActual = months.some((m) => m.actual_total != null)

  // ── Layout ────────────────────────────────────────────────────────────
  const padX = 56
  const titleY = 38
  const subtitleY = 70
  const kpiTopY = 100
  const kpiHeight = 80
  const chartTopY = kpiTopY + kpiHeight + 24
  const chartBottomY = height - 80
  const chartLeftX = padX + 60       // room for y-axis on RIGHT (RTL)
  const chartRightX = width - padX
  const chartWidth = chartRightX - chartLeftX
  const chartHeight = chartBottomY - chartTopY
  const valueAreaH = chartHeight - 50  // headroom for bar value labels

  const groupCount = Math.max(1, months.length)
  const groupWidth = chartWidth / groupCount
  const barWidth = Math.min(44, (groupWidth - 32) / 2)
  const barGap = 10

  // Scale anchored on max across both metrics. Round up to a clean tick.
  const maxValueRaw = Math.max(
    1,
    ...months.flatMap((m) => [m.expected_total ?? 0, m.actual_total ?? 0]),
  )
  const niceCeiling = (v: number): number => {
    if (v <= 0) return 1
    const order = Math.pow(10, Math.floor(Math.log10(v)))
    const norm = v / order
    const stepped = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10
    return stepped * order
  }
  const yMax = niceCeiling(maxValueRaw * 1.1)
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((p) => Math.round(yMax * p))

  // ── Entrance animations ───────────────────────────────────────────────
  const titleOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' })
  const titleSlide = interpolate(frame, [0, 14], [-8, 0], { extrapolateRight: 'clamp' })
  const kpiOpacity = interpolate(frame, [10, 26], [0, 1], { extrapolateRight: 'clamp' })

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <div
      style={{
        width,
        height,
        direction: 'rtl',
        fontFamily: FONT,
        background: `linear-gradient(135deg, ${COLORS.bg} 0%, ${COLORS.bgWarm} 100%)`,
        color: COLORS.text,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative orb */}
      <div
        style={{
          position: 'absolute',
          width: 320,
          height: 320,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(245,124,0,0.14), transparent 70%)',
          top: -110,
          insetInlineEnd: -90,
          pointerEvents: 'none',
        }}
      />

      {/* Title */}
      <div
        style={{
          position: 'absolute',
          insetInlineStart: padX,
          insetInlineEnd: padX,
          top: titleY + titleSlide,
          fontSize: 22,
          fontWeight: 800,
          opacity: titleOpacity,
          color: COLORS.text,
        }}
      >
        {props.title || 'השוואת עמלות — 3 חודשים אחרונים'}
      </div>
      <div
        style={{
          position: 'absolute',
          insetInlineStart: padX,
          insetInlineEnd: padX,
          top: subtitleY,
          fontSize: 13,
          color: COLORS.textMuted,
          opacity: titleOpacity,
        }}
      >
        עמלה צפויה (פרודוקציה × עמלות מוסכמות) מול עמלה בפועל (סך נפרעים)
      </div>

      {/* KPI strip */}
      <div
        style={{
          position: 'absolute',
          insetInlineStart: padX,
          insetInlineEnd: padX,
          top: kpiTopY,
          height: kpiHeight,
          display: 'flex',
          gap: 14,
          opacity: kpiOpacity,
        }}
      >
        <KpiCell
          label="סה״כ צפוי"
          value={hasAnyExpected ? formatMoney(totalExpected) : '—'}
          color={COLORS.expectedDeep}
          tint={COLORS.expectedSoft}
        />
        <KpiCell
          label="סה״כ בפועל"
          value={hasAnyActual ? formatMoney(totalActual) : '—'}
          color={COLORS.actualDeep}
          tint={COLORS.actualSoft}
        />
        <KpiCell
          label={totalGap > 0 ? 'פער (חוסר עמלה)' : 'פער'}
          value={hasAnyExpected && hasAnyActual ? formatMoney(totalGap) : '—'}
          color={totalGap > 0 ? COLORS.gap : COLORS.ok}
          tint={totalGap > 0 ? COLORS.gapSoft : COLORS.actualSoft}
        />
      </div>

      {/* Chart axes + gridlines */}
      {ticks.map((t, i) => {
        const y = chartTopY + valueAreaH * (1 - t / yMax)
        return (
          <div key={`tick-${i}`}>
            <div
              style={{
                position: 'absolute',
                left: chartLeftX,
                right: padX,
                top: y,
                height: 1,
                background: i === 0 ? COLORS.border : 'rgba(229, 229, 229, 0.55)',
                opacity: kpiOpacity,
              }}
            />
            <div
              style={{
                position: 'absolute',
                top: y - 8,
                insetInlineEnd: chartRightX + 8,
                width: 56,
                textAlign: 'left',
                fontSize: 11,
                color: COLORS.textMuted,
                direction: 'ltr',
                opacity: kpiOpacity,
              }}
            >
              {t === 0 ? '0' : '₪' + (t >= 1000 ? Math.round(t / 1000) + 'K' : t)}
            </div>
          </div>
        )
      })}

      {/* Month groups */}
      {months.map((m, gi) => {
        const groupStartFrame = 24 + gi * 6
        const groupIntro = spring({
          frame: frame - groupStartFrame,
          fps,
          config: { damping: 200, stiffness: 100, mass: 0.6 },
        })

        // RTL: index 0 (oldest) sits on the LEFT; newest on the RIGHT.
        // groupLeftX is computed in LTR pixels.
        const groupLeftX = chartLeftX + gi * groupWidth
        const groupCenter = groupLeftX + groupWidth / 2

        const isEmpty = !m.production_uploaded && !m.commission_uploaded

        // Expected bar
        const expVal = m.expected_total ?? 0
        const expHeight = m.production_uploaded ? (expVal / yMax) * valueAreaH : 0
        const expGrow = spring({
          frame: frame - (groupStartFrame + 8),
          fps,
          config: { damping: 200, stiffness: 80, mass: 0.7 },
        })
        const expDrawn = expHeight * expGrow

        // Actual bar
        const actVal = m.actual_total ?? 0
        const actHeight = m.commission_uploaded ? (actVal / yMax) * valueAreaH : 0
        const actGrow = spring({
          frame: frame - (groupStartFrame + 14),
          fps,
          config: { damping: 200, stiffness: 80, mass: 0.7 },
        })
        const actDrawn = actHeight * actGrow

        // Bar centers: two bars side-by-side around groupCenter
        const expBarLeft = groupCenter + barGap / 2
        const actBarLeft = groupCenter - barGap / 2 - barWidth

        return (
          <div key={m.period_month} style={{ opacity: groupIntro }}>
            {/* X-axis label */}
            <div
              style={{
                position: 'absolute',
                top: chartBottomY + 4,
                left: groupLeftX,
                width: groupWidth,
                textAlign: 'center',
                fontSize: 13,
                fontWeight: 700,
                color: COLORS.text,
              }}
            >
              {m.label}
            </div>
            <div
              style={{
                position: 'absolute',
                top: chartBottomY + 22,
                left: groupLeftX,
                width: groupWidth,
                textAlign: 'center',
                fontSize: 10,
                color: COLORS.textMuted,
              }}
            >
              {isEmpty
                ? 'אין נתונים'
                : m.production_uploaded && m.commission_uploaded
                  ? 'הכל הועלה'
                  : m.production_uploaded
                    ? 'חסר נפרעים'
                    : 'חסרה פרודוקציה'}
            </div>

            {/* Expected bar (orange) */}
            {m.production_uploaded ? (
              <>
                <div
                  style={{
                    position: 'absolute',
                    left: expBarLeft,
                    top: chartTopY + valueAreaH - expDrawn,
                    width: barWidth,
                    height: expDrawn,
                    background: `linear-gradient(180deg, ${COLORS.expected} 0%, ${COLORS.expectedDeep} 100%)`,
                    borderRadius: '6px 6px 0 0',
                    boxShadow: '0 -2px 8px rgba(245, 124, 0, 0.25)',
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    left: expBarLeft - 16,
                    top: chartTopY + valueAreaH - expDrawn - 18,
                    width: barWidth + 32,
                    textAlign: 'center',
                    fontSize: 10,
                    fontWeight: 700,
                    color: COLORS.expectedDeep,
                    direction: 'ltr',
                    opacity: groupIntro,
                  }}
                >
                  {formatMoney(expVal)}
                </div>
              </>
            ) : (
              <div
                style={{
                  position: 'absolute',
                  left: expBarLeft,
                  top: chartTopY + valueAreaH - valueAreaH * 0.18,
                  width: barWidth,
                  height: valueAreaH * 0.18,
                  border: `1.5px dashed ${COLORS.textMuted}`,
                  borderRadius: '6px 6px 0 0',
                  background: 'rgba(112, 110, 107, 0.05)',
                }}
              />
            )}

            {/* Actual bar (green) */}
            {m.commission_uploaded ? (
              <>
                <div
                  style={{
                    position: 'absolute',
                    left: actBarLeft,
                    top: chartTopY + valueAreaH - actDrawn,
                    width: barWidth,
                    height: actDrawn,
                    background: `linear-gradient(180deg, ${COLORS.actual} 0%, ${COLORS.actualDeep} 100%)`,
                    borderRadius: '6px 6px 0 0',
                    boxShadow: '0 -2px 8px rgba(46, 132, 74, 0.25)',
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    left: actBarLeft - 16,
                    top: chartTopY + valueAreaH - actDrawn - 18,
                    width: barWidth + 32,
                    textAlign: 'center',
                    fontSize: 10,
                    fontWeight: 700,
                    color: COLORS.actualDeep,
                    direction: 'ltr',
                    opacity: groupIntro,
                  }}
                >
                  {formatMoney(actVal)}
                </div>
              </>
            ) : (
              <div
                style={{
                  position: 'absolute',
                  left: actBarLeft,
                  top: chartTopY + valueAreaH - valueAreaH * 0.18,
                  width: barWidth,
                  height: valueAreaH * 0.18,
                  border: `1.5px dashed ${COLORS.textMuted}`,
                  borderRadius: '6px 6px 0 0',
                  background: 'rgba(112, 110, 107, 0.05)',
                }}
              />
            )}
          </div>
        )
      })}

      {/* Legend (bottom-left in RTL = bottom-RIGHT visually) */}
      <div
        style={{
          position: 'absolute',
          bottom: 16,
          insetInlineStart: padX,
          display: 'flex',
          gap: 18,
          fontSize: 11,
          color: COLORS.textMuted,
          opacity: kpiOpacity,
        }}
      >
        <LegendSwatch color={COLORS.expected} label="צפוי" />
        <LegendSwatch color={COLORS.actual} label="בפועל" />
        <LegendSwatch dashed label="אין נתונים" />
      </div>
    </div>
  )
}

function KpiCell({
  label, value, color, tint,
}: { label: string; value: string; color: string; tint: string }) {
  return (
    <div
      style={{
        flex: 1,
        background: tint,
        borderRadius: 12,
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap: 4,
      }}
    >
      <span style={{ fontSize: 11, fontWeight: 600, color: '#706E6B' }}>{label}</span>
      <span style={{ fontSize: 22, fontWeight: 800, color, direction: 'ltr', textAlign: 'right' }}>{value}</span>
    </div>
  )
}

function LegendSwatch({
  color, label, dashed = false,
}: { color?: string; label: string; dashed?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span
        style={{
          width: 12,
          height: 12,
          borderRadius: 3,
          background: dashed ? 'transparent' : color,
          border: dashed ? `1.5px dashed ${'#706E6B'}` : 'none',
          display: 'inline-block',
        }}
      />
      <span>{label}</span>
    </div>
  )
}

export const MONTHLY_COMMISSION_DURATION_FRAMES = 110
export const MONTHLY_COMMISSION_FPS = 30
