import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion'
import { VizBar, colorsFor, formatMoney } from './types'

const FONT = 'Heebo, sans-serif'

export function BarComposition(props: VizBar) {
  const frame = useCurrentFrame()
  const { fps, width, height } = useVideoConfig()

  const sorted = [...(props.data ?? [])]
    .filter((d) => Number.isFinite(d.value))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 10)

  const colors = colorsFor(props.direction)
  const maxAbs = Math.max(1, ...sorted.map((d) => Math.abs(d.value)))

  // Layout constants
  const pad = 42
  const titleY = 44
  const barStartY = 100
  const rowGap = 10
  const rowHeight = (height - barStartY - 80) / Math.max(1, sorted.length) - rowGap
  const labelW = 170

  // Title entrance
  const titleOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' })
  const titleY2 = interpolate(frame, [0, 14], [titleY - 10, titleY], {
    extrapolateRight: 'clamp',
  })

  return (
    <div
      style={{
        width,
        height,
        direction: 'rtl',
        fontFamily: FONT,
        background: 'linear-gradient(135deg, #ffffff 0%, #fff8f0 100%)',
        color: '#181818',
        padding: 0,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* decorative orb */}
      <div
        style={{
          position: 'absolute',
          width: 320,
          height: 320,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(245,124,0,0.15), transparent 70%)',
          top: -90,
          insetInlineStart: -60,
          pointerEvents: 'none',
        }}
      />

      {/* Title */}
      <div
        style={{
          position: 'absolute',
          insetInlineStart: pad,
          insetInlineEnd: pad,
          top: titleY2,
          fontSize: 24,
          fontWeight: 800,
          opacity: titleOpacity,
          color: '#181818',
        }}
      >
        {props.title}
      </div>

      {/* Bars */}
      {sorted.map((d, i) => {
        const barStart = 8 + i * 5 // stagger per bar
        const introProgress = spring({
          frame: frame - barStart,
          fps,
          config: { damping: 18, mass: 0.7, stiffness: 140 },
        })
        const valueProgress = interpolate(
          frame,
          [barStart + 4, barStart + 28],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        )
        const widthPct = (Math.abs(d.value) / maxAbs) * 100
        const barWidth = ((width - pad * 2 - labelW - 20) * widthPct) / 100
        const shownValue = d.value * valueProgress
        const isHighlight = d.label === props.highlight_label

        // Pulse for highlight
        const pulse = isHighlight
          ? 0.85 + 0.15 * Math.sin((frame - 30) * 0.25)
          : 1

        const y = barStartY + i * (rowHeight + rowGap)

        return (
          <div
            key={d.label}
            style={{
              position: 'absolute',
              top: y,
              insetInlineStart: pad,
              width: width - pad * 2,
              height: rowHeight,
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              opacity: introProgress,
              transform: `translateX(${(1 - introProgress) * -30}px)`,
            }}
          >
            <div
              style={{
                width: labelW,
                fontSize: 14,
                fontWeight: isHighlight ? 800 : 600,
                color: isHighlight ? colors.main : '#3E3E3C',
                overflow: 'hidden',
                whiteSpace: 'nowrap',
                textOverflow: 'ellipsis',
              }}
            >
              {d.label}
            </div>
            <div
              style={{
                flex: 1,
                height: rowHeight - 12,
                background: 'rgba(0,0,0,0.04)',
                borderRadius: 8,
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  insetInlineStart: 0,
                  top: 0,
                  bottom: 0,
                  width: barWidth * introProgress,
                  background: isHighlight
                    ? `linear-gradient(90deg, ${colors.main}, ${colors.main}cc)`
                    : `linear-gradient(90deg, ${colors.main}, ${colors.main}99)`,
                  borderRadius: 8,
                  boxShadow: isHighlight
                    ? `0 0 18px ${colors.main}66`
                    : 'none',
                  opacity: pulse,
                  transition: 'none',
                  direction: 'ltr',
                }}
              />
            </div>
            <div
              style={{
                width: 150,
                textAlign: 'start',
                fontSize: 14,
                fontWeight: 800,
                fontVariantNumeric: 'tabular-nums',
                color: isHighlight ? colors.main : '#181818',
                direction: 'ltr',
                textAlignLast: 'right',
              }}
            >
              {formatMoney(shownValue, props.unit ?? '₪')}
            </div>
          </div>
        )
      })}

      {/* Insight chip */}
      {props.insight ? (
        <div
          style={{
            position: 'absolute',
            insetInline: pad,
            bottom: 24,
            padding: '12px 16px',
            borderRadius: 12,
            background: colors.soft,
            color: colors.main,
            fontSize: 15,
            fontWeight: 700,
            opacity: interpolate(frame, [54, 74], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
            transform: `translateY(${interpolate(frame, [54, 74], [12, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })}px)`,
          }}
        >
          {props.insight}
        </div>
      ) : null}
    </div>
  )
}
