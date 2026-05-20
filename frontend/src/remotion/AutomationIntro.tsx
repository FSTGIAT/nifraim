import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion'

/**
 * AutomationIntro
 * Empty-state showcase for the portal-automation tab. Visualises the
 * drag-into-schedule interaction so a first-time user understands what to do.
 * Loops cleanly: idle → card slides into daily zone → success ping → reset.
 */

const FONT = "'Heebo', sans-serif"

const CREAM_BG = '#FFFBF4'
const INK = '#1A1410'
const INK_SOFT = '#6B5F50'
const HAIRLINE = '#EADFCC'

const BRAND = '#F57C00'
const BRAND_DEEP = '#E65100'

const CAD_DAILY = '#C2410C'
const CAD_WEEKLY = '#0E7490'
const CAD_MONTHLY = '#4338CA'

interface ZoneSpec {
  kind: 'daily' | 'weekly' | 'monthly'
  label: string
  sub: string
  color: string
  y: number
}

const ZONES: ZoneSpec[] = [
  { kind: 'daily',   label: 'יומי',   sub: 'כל יום · 09:00',     color: CAD_DAILY,   y: 64 },
  { kind: 'weekly',  label: 'שבועי',  sub: 'כל יום ראשון',        color: CAD_WEEKLY,  y: 232 },
  { kind: 'monthly', label: 'חודשי',  sub: 'בתחילת כל חודש',     color: CAD_MONTHLY, y: 400 },
]

interface BrandSpec {
  name: string
  color: string
  initial: string
}

const BRANDS: BrandSpec[] = [
  { name: 'מגדל',     color: '#1E3A8A', initial: 'מ' },
  { name: 'הפניקס',   color: '#7C2D12', initial: 'פ' },
  { name: 'הראל',     color: '#065F46', initial: 'ה' },
]

// Card "home" positions on the right pane (relative to right-pane origin).
// In RTL the visual right-edge is the inline-start; we draw with absolute
// pixel coordinates so the composition reads identically regardless of locale.
const CARD_HOME: { x: number; y: number }[] = [
  { x: 24,  y: 48 },
  { x: 268, y: 48 },
  { x: 24,  y: 200 },
]

const RIGHT_PANE_X = 320     // right pane starts at x=320, runs to width-40
const LEFT_RAIL_X = 32       // left rail x-origin
const LEFT_RAIL_W = 264

const CARD_W = 220
const CARD_H = 124

function easeOutBack(t: number) {
  // Standard back ease — gives the card a small overshoot on landing.
  const c1 = 1.70158
  const c3 = c1 + 1
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
}

function PortalCardArt({
  brand,
  x,
  y,
  scale = 1,
  rotate = 0,
  opacity = 1,
  lifted = false,
  cadenceColor,
}: {
  brand: BrandSpec
  x: number
  y: number
  scale?: number
  rotate?: number
  opacity?: number
  lifted?: boolean
  cadenceColor?: string
}) {
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: CARD_W,
        height: CARD_H,
        background: '#FFFFFF',
        borderRadius: 14,
        border: `1px solid ${HAIRLINE}`,
        boxShadow: lifted
          ? '0 24px 48px rgba(26, 20, 16, 0.18), 0 4px 12px rgba(245, 124, 0, 0.12)'
          : '0 2px 6px rgba(26, 20, 16, 0.04), 0 8px 18px rgba(26, 20, 16, 0.05)',
        transform: `scale(${scale}) rotate(${rotate}deg)`,
        transformOrigin: 'center',
        opacity,
        padding: '14px 14px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {cadenceColor ? (
        <div
          style={{
            position: 'absolute',
            insetBlock: 0,
            insetInlineStart: 0,
            width: 3,
            background: cadenceColor,
          }}
        />
      ) : null}

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: brand.color,
            display: 'grid',
            placeItems: 'center',
            color: '#fff',
            fontWeight: 800,
            fontSize: 16,
            boxShadow: '0 3px 8px rgba(0,0,0,0.18), inset 0 -1px 0 rgba(0,0,0,0.18)',
          }}
        >
          {brand.initial}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
          <span style={{ fontSize: 15, fontWeight: 800, color: INK, lineHeight: 1.1 }}>
            {brand.name}
          </span>
          <span
            style={{
              fontSize: 11,
              color: INK_SOFT,
              fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
              letterSpacing: 0.3,
            }}
          >
            agent@portal
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 'auto' }}>
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: cadenceColor || INK_SOFT,
            boxShadow: cadenceColor ? `0 0 0 3px ${cadenceColor}22` : 'none',
          }}
        />
        <span style={{ fontSize: 11, color: INK_SOFT, fontWeight: 700 }}>
          {cadenceColor ? 'מתוזמן' : 'טרם הופעל'}
        </span>
      </div>
    </div>
  )
}

function ScheduleZone({
  zone,
  active,
  filled,
  filledBy,
  ripple,
}: {
  zone: ZoneSpec
  active: boolean
  filled: boolean
  filledBy: BrandSpec | null
  ripple: number
}) {
  // ripple ∈ [0,1]; 0 = no pulse, 1 = peak
  return (
    <div
      style={{
        position: 'absolute',
        left: LEFT_RAIL_X,
        top: zone.y,
        width: LEFT_RAIL_W,
        height: 156,
        background: '#FFFFFF',
        borderRadius: 16,
        border: `1.5px solid ${active ? zone.color : HAIRLINE}`,
        boxShadow: active
          ? `0 0 0 4px ${zone.color}1F, 0 12px 28px rgba(26,20,16,0.08)`
          : '0 2px 6px rgba(26, 20, 16, 0.04)',
        padding: '14px 14px 12px',
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {/* hairline grid texture */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `linear-gradient(${HAIRLINE}55 1px, transparent 1px), linear-gradient(90deg, ${HAIRLINE}55 1px, transparent 1px)`,
          backgroundSize: '20px 20px',
          opacity: 0.35,
          maskImage: 'radial-gradient(ellipse at top right, #000 30%, transparent 80%)',
          pointerEvents: 'none',
        }}
      />

      {/* ripple */}
      {ripple > 0 ? (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'grid',
            placeItems: 'center',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: '50%',
              border: `2px solid ${zone.color}`,
              transform: `scale(${1 + ripple * 6})`,
              opacity: (1 - ripple) * 0.6,
            }}
          />
        </div>
      ) : null}

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, position: 'relative' }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 9,
            background: `${zone.color}14`,
            color: zone.color,
            display: 'grid',
            placeItems: 'center',
            border: `1px solid ${zone.color}22`,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
          <span style={{ fontSize: 14, fontWeight: 800, color: INK, lineHeight: 1.15 }}>
            {zone.label}
          </span>
          <span style={{ fontSize: 11, color: INK_SOFT }}>{zone.sub}</span>
        </div>
        <span
          style={{
            fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
            fontSize: 11,
            fontWeight: 700,
            color: filled ? zone.color : INK_SOFT,
            background: filled ? `${zone.color}10` : '#F7F2EA',
            border: `1px solid ${filled ? zone.color + '33' : HAIRLINE}`,
            padding: '3px 8px',
            borderRadius: 6,
            letterSpacing: 0.4,
          }}
        >
          {filled ? '01' : '00'}
        </span>
      </div>

      {/* slot — empty hint or filled chip */}
      <div
        style={{
          marginTop: 10,
          height: 64,
          borderRadius: 10,
          border: filled ? 'none' : `1.5px dashed ${active ? zone.color + 'AA' : HAIRLINE}`,
          background: filled ? 'transparent' : (active ? `${zone.color}08` : 'transparent'),
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: filled ? 0 : '0 12px',
          color: active ? zone.color : INK_SOFT,
          fontSize: 12,
          fontWeight: 700,
          position: 'relative',
        }}
      >
        {filled && filledBy ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 10px',
              background: '#FFFFFF',
              border: `1px solid ${HAIRLINE}`,
              borderInlineStart: `3px solid ${zone.color}`,
              borderRadius: 8,
              fontSize: 12,
              boxShadow: '0 2px 6px rgba(26,20,16,0.05)',
              width: '100%',
            }}
          >
            <span
              style={{
                width: 18,
                height: 18,
                borderRadius: 5,
                background: filledBy.color,
                color: '#fff',
                display: 'grid',
                placeItems: 'center',
                fontWeight: 800,
                fontSize: 10,
              }}
            >
              {filledBy.initial}
            </span>
            <span style={{ fontWeight: 800, color: INK }}>{filledBy.name}</span>
            <span style={{ marginInlineStart: 'auto', color: zone.color, fontWeight: 800 }}>✓</span>
          </div>
        ) : (
          <>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M5 12h14M12 5v14" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>גרור פורטל לכאן</span>
          </>
        )}
      </div>
    </div>
  )
}

function RightPaneFrame({ width, height }: { width: number; height: number }) {
  return (
    <div
      style={{
        position: 'absolute',
        left: RIGHT_PANE_X,
        top: 24,
        width: width - RIGHT_PANE_X - 24,
        height: height - 48,
        background: '#FFFFFF',
        borderRadius: 18,
        border: `1px solid ${HAIRLINE}`,
        boxShadow: '0 1px 0 rgba(26,20,16,0.02), 0 14px 30px rgba(26,20,16,0.04)',
        padding: '18px 20px',
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', borderBottom: `1px dashed ${HAIRLINE}`, paddingBottom: 10 }}>
        <span style={{ fontSize: 14, fontWeight: 800, color: INK }}>פורטלים לתזמון</span>
        <span style={{ fontSize: 11, color: INK_SOFT }}>גרור שמאלה כדי לתזמן</span>
      </div>
    </div>
  )
}

function LeftRailLabel() {
  return (
    <div
      style={{
        position: 'absolute',
        left: LEFT_RAIL_X,
        top: 24,
        width: LEFT_RAIL_W,
        height: 28,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT,
        direction: 'rtl',
      }}
    >
      <span style={{ fontSize: 13, fontWeight: 800, color: INK, letterSpacing: -0.2 }}>תזמון</span>
      <span style={{ fontSize: 10, color: INK_SOFT, fontWeight: 700, letterSpacing: 0.8, textTransform: 'uppercase' }}>
        SCHEDULES
      </span>
    </div>
  )
}

function buildPath(start: { x: number; y: number }, end: { x: number; y: number }, t: number) {
  // Quadratic-ish arc with a slight upward bow so the card "lifts" before landing.
  const mx = (start.x + end.x) / 2
  const my = Math.min(start.y, end.y) - 60
  const ix = (1 - t) * (1 - t) * start.x + 2 * (1 - t) * t * mx + t * t * end.x
  const iy = (1 - t) * (1 - t) * start.y + 2 * (1 - t) * t * my + t * t * end.y
  return { x: ix, y: iy }
}

interface AnimSegment {
  cardIdx: number   // which of BRANDS
  zoneIdx: number   // which of ZONES
  liftStart: number
  travelStart: number
  landStart: number
  landEnd: number   // end of bounce
}

const SEGMENTS: AnimSegment[] = [
  { cardIdx: 0, zoneIdx: 0, liftStart: 18,  travelStart: 28,  landStart: 60,  landEnd: 80  },
  { cardIdx: 1, zoneIdx: 1, liftStart: 96,  travelStart: 106, landStart: 138, landEnd: 158 },
  { cardIdx: 2, zoneIdx: 2, liftStart: 174, travelStart: 184, landStart: 216, landEnd: 236 },
]

export const AUTOMATION_INTRO_DURATION = 290

export function AutomationIntro() {
  const frame = useCurrentFrame()
  const { width, height, fps } = useVideoConfig()

  // Static introduction fade-in
  const headOpacity = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) })

  // For each segment, derive: card position, scale, rotation, opacity, and zone fill state.
  const cardStates = BRANDS.map((_, i) => {
    const seg = SEGMENTS.find((s) => s.cardIdx === i)
    if (!seg) {
      return {
        x: CARD_HOME[i].x + RIGHT_PANE_X + 28,
        y: CARD_HOME[i].y + 24 + 60,
        scale: 1,
        rotate: 0,
        opacity: 1,
        lifted: false,
        landedZoneIdx: -1,
      }
    }
    const home = {
      x: CARD_HOME[i].x + RIGHT_PANE_X + 28,
      y: CARD_HOME[i].y + 24 + 60,
    }
    const target = {
      x: LEFT_RAIL_X + 22,
      y: ZONES[seg.zoneIdx].y + 86,
    }

    const lifting = frame >= seg.liftStart && frame < seg.travelStart
    const traveling = frame >= seg.travelStart && frame < seg.landStart
    const landing = frame >= seg.landStart && frame < seg.landEnd
    const landed = frame >= seg.landEnd

    let x = home.x
    let y = home.y
    let scale = 1
    let rotate = 0
    let opacity = 1
    let lifted = false
    let landedZoneIdx = -1

    if (lifting) {
      const t = interpolate(frame, [seg.liftStart, seg.travelStart], [0, 1], { extrapolateRight: 'clamp' })
      scale = 1 + 0.04 * t
      rotate = -2 * t
      lifted = true
    } else if (traveling) {
      const raw = interpolate(frame, [seg.travelStart, seg.landStart], [0, 1], { extrapolateRight: 'clamp' })
      const eased = Easing.bezier(0.34, 0.05, 0.2, 1)(raw)
      const pos = buildPath(home, target, eased)
      x = pos.x
      y = pos.y
      scale = 1.04
      rotate = -2 + eased * 4 // -2deg → +2deg
      lifted = true
    } else if (landing) {
      const t = interpolate(frame, [seg.landStart, seg.landEnd], [0, 1], { extrapolateRight: 'clamp' })
      const eased = easeOutBack(t)
      x = target.x
      y = target.y
      scale = 1.04 - 0.04 * eased
      rotate = 2 - 2 * t
      lifted = false
      if (t > 0.4) landedZoneIdx = seg.zoneIdx
    } else if (landed) {
      x = target.x
      y = target.y
      scale = 1
      rotate = 0
      lifted = false
      landedZoneIdx = seg.zoneIdx
      // Fade out the floating card a frame after landing so the "chip inside zone" reads as the resting state.
      opacity = interpolate(frame, [seg.landEnd, seg.landEnd + 4], [1, 0], { extrapolateRight: 'clamp' })
    }

    return { x, y, scale, rotate, opacity, lifted, landedZoneIdx }
  })

  // Per-zone state
  const zoneStates = ZONES.map((_, zi) => {
    const seg = SEGMENTS.find((s) => s.zoneIdx === zi)!
    const active = frame >= seg.travelStart - 8 && frame < seg.landEnd
    const filled = frame >= seg.landStart + 6  // after the bounce starts
    const filledBy = filled ? BRANDS[seg.cardIdx] : null
    const ripple = interpolate(
      frame,
      [seg.landStart, seg.landStart + 18],
      [0, 1],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
    )
    const rippleOut = frame < seg.landStart || frame > seg.landStart + 22 ? 0 : ripple
    return { active, filled, filledBy, ripple: rippleOut }
  })

  // Spring intro for the panel frame
  const panelEnter = spring({ frame, fps, from: 0, to: 1, config: { damping: 22, mass: 0.7 } })

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 80% at 70% 0%, ${BRAND}10 0%, transparent 60%), ${CREAM_BG}`,
        fontFamily: FONT,
        direction: 'rtl',
        overflow: 'hidden',
      }}
    >
      {/* atmospheric blur blobs */}
      <div
        style={{
          position: 'absolute',
          width: 380,
          height: 380,
          borderRadius: '50%',
          background: `${BRAND}1A`,
          filter: 'blur(60px)',
          top: -120,
          left: -120,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 320,
          height: 320,
          borderRadius: '50%',
          background: `${CAD_MONTHLY}14`,
          filter: 'blur(70px)',
          bottom: -100,
          right: -80,
        }}
      />

      {/* hairline title strip */}
      <div
        style={{
          position: 'absolute',
          top: 16,
          left: LEFT_RAIL_X,
          right: 24,
          height: 28,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          opacity: headOpacity,
        }}
      />

      <div style={{ transform: `scale(${0.96 + 0.04 * panelEnter})`, transformOrigin: 'center' }}>
        <LeftRailLabel />
        <RightPaneFrame width={width} height={height} />

        {/* Zones */}
        {ZONES.map((zone, zi) => (
          <ScheduleZone
            key={zone.kind}
            zone={zone}
            active={zoneStates[zi].active}
            filled={zoneStates[zi].filled}
            filledBy={zoneStates[zi].filledBy}
            ripple={zoneStates[zi].ripple}
          />
        ))}

        {/* Phantom outlines at card home positions (visible after card has been moved) */}
        {BRANDS.map((_, i) => {
          const seg = SEGMENTS.find((s) => s.cardIdx === i)
          if (!seg) return null
          const visible = frame >= seg.liftStart + 2
          if (!visible) return null
          const phantomOpacity = interpolate(frame, [seg.liftStart + 2, seg.liftStart + 12], [0, 1], { extrapolateRight: 'clamp' })
          return (
            <div
              key={`phantom-${i}`}
              style={{
                position: 'absolute',
                left: CARD_HOME[i].x + RIGHT_PANE_X + 28,
                top: CARD_HOME[i].y + 24 + 60,
                width: CARD_W,
                height: CARD_H,
                borderRadius: 14,
                border: `1.5px dashed ${HAIRLINE}`,
                background: 'transparent',
                opacity: phantomOpacity * 0.65,
                pointerEvents: 'none',
              }}
            />
          )
        })}

        {/* Floating cards */}
        {BRANDS.map((brand, i) => (
          <PortalCardArt
            key={brand.name}
            brand={brand}
            x={cardStates[i].x}
            y={cardStates[i].y}
            scale={cardStates[i].scale}
            rotate={cardStates[i].rotate}
            opacity={cardStates[i].opacity}
            lifted={cardStates[i].lifted}
            cadenceColor={cardStates[i].landedZoneIdx >= 0 ? ZONES[cardStates[i].landedZoneIdx].color : undefined}
          />
        ))}
      </div>

      {/* Bottom caption */}
      <div
        style={{
          position: 'absolute',
          bottom: 20,
          insetInline: 0,
          display: 'flex',
          justifyContent: 'center',
          opacity: interpolate(frame, [4, 18], [0, 1], { extrapolateRight: 'clamp' }),
        }}
      >
        <span
          style={{
            fontFamily: FONT,
            direction: 'rtl',
            fontSize: 12,
            color: INK_SOFT,
            letterSpacing: 0.4,
            background: '#FFFFFFAA',
            border: `1px solid ${HAIRLINE}`,
            borderRadius: 999,
            padding: '6px 14px',
            backdropFilter: 'blur(8px)',
            fontWeight: 600,
          }}
        >
          גרור פורטל אל אחד התזמונים כדי להפעיל אוטומציה
        </span>
      </div>
    </AbsoluteFill>
  )
}
