// RadialOrbital — light-themed orbital launcher mounted in the bottom-left of
// the workspace. Adapted from the user-provided shadcn radial-orbital-timeline
// component, but:
//   1. No Tailwind. All styling is inline using the app's CSS variables.
//   2. No shadcn Card/Badge/Button — plain divs.
//   3. Light/bright orange palette (matches AiInsightCard / AiVizPanel) instead
//      of the original's bg-black space aesthetic.
//   4. Compact (300×300) so it fits comfortably in the bottom-left corner.
//   5. RTL labels in Heebo.
//   6. onSelect(itemId) callback fires when a node is clicked — Vue/Pinia owns
//      the modal state, not React.
'use client'

import * as React from 'react'
import { useState, useEffect, useRef, type ElementType, type MouseEvent } from 'react'
import { CHART_PALETTE } from '../../utils/chartPalette.js'

export interface OrbitalItem {
  id: number
  title: string
  description?: string
  icon: ElementType   // a lucide-react icon component
  energy?: number     // 0..100 — drives node halo size
}

interface RadialOrbitalProps {
  items: OrbitalItem[]
  onSelect?: (id: number) => void
  size?: number          // outer container size (default 300)
  orbitRadius?: number   // orbit radius (default 96)
  autoRotate?: boolean
}

const COLORS = {
  // Pulled from App.vue :root — re-asserted as literals because React island
  // is rendered outside of Vue's scoped-style scope.
  primary: '#F57C00',
  primaryDeep: '#E65100',
  primaryGlow: 'rgba(245, 124, 0, 0.18)',
  primaryLight: '#FFF3E0',
  surface: '#FFFFFF',
  border: '#DDDBDA',
  text: '#181818',
  textMuted: '#706E6B',
  shadowLg: '0 12px 32px rgba(245, 124, 0, 0.25), 0 4px 14px rgba(0, 0, 0, 0.08)',
  shadowSm: '0 2px 6px rgba(0, 0, 0, 0.08)',
}

export default function RadialOrbital({
  items,
  onSelect,
  size = 300,
  orbitRadius = 96,
  autoRotate: autoRotateProp = true,
}: RadialOrbitalProps) {
  const [rotationAngle, setRotationAngle] = useState(0)
  const [autoRotate, setAutoRotate] = useState(autoRotateProp)
  const [hoveredId, setHoveredId] = useState<number | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!autoRotate) return
    const t = setInterval(() => {
      setRotationAngle((prev) => (prev + 0.25) % 360)
    }, 50)
    return () => clearInterval(t)
  }, [autoRotate])

  const calculatePosition = (index: number, total: number) => {
    const angle = ((index / total) * 360 + rotationAngle) % 360
    const radian = (angle * Math.PI) / 180
    const x = orbitRadius * Math.cos(radian)
    const y = orbitRadius * Math.sin(radian)
    const z = Math.round(100 + 50 * Math.cos(radian))
    const opacity = Math.max(0.55, Math.min(1, 0.55 + 0.45 * ((1 + Math.sin(radian)) / 2)))
    return { x, y, z, opacity }
  }

  const handleNodeClick = (e: MouseEvent, id: number) => {
    e.stopPropagation()
    onSelect?.(id)
  }

  // Hovering pauses the rotation so the user can read labels without chasing them.
  const handleEnter = () => setAutoRotate(false)
  const handleLeave = () => setAutoRotate(autoRotateProp)

  return (
    <div
      ref={containerRef}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      style={{
        position: 'relative',
        width: size,
        height: size,
        direction: 'rtl',
        fontFamily: "'Heebo', sans-serif",
        userSelect: 'none',
      }}
    >
      {/* Faint outer ring — the orbit's visual track. */}
      <div
        style={{
          position: 'absolute',
          inset: `${size / 2 - orbitRadius - 4}px`,
          borderRadius: '50%',
          border: `1px dashed ${COLORS.border}`,
          pointerEvents: 'none',
        }}
      />
      {/* Center orb — the calm focal point. */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 48,
          height: 48,
          marginLeft: -24,
          marginTop: -24,
          borderRadius: '50%',
          background: `linear-gradient(135deg, ${COLORS.primary} 0%, #FFA040 50%, #FFD180 100%)`,
          boxShadow: COLORS.shadowLg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10,
        }}
      >
        {/* Inner halo + ping rings */}
        <div
          style={{
            position: 'absolute',
            inset: -8,
            borderRadius: '50%',
            border: `1px solid ${COLORS.primaryGlow}`,
            opacity: 0.7,
            animation: 'orb-ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: -16,
            borderRadius: '50%',
            border: `1px solid ${COLORS.primaryGlow}`,
            opacity: 0.5,
            animation: 'orb-ping 2s cubic-bezier(0, 0, 0.2, 1) 0.6s infinite',
          }}
        />
        <div
          style={{
            width: 20,
            height: 20,
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.92)',
            boxShadow: 'inset 0 0 8px rgba(245, 124, 0, 0.35)',
          }}
        />
      </div>

      {/* Inline keyframes — once-per-mount style tag, scoped to the orbit. */}
      <style>{`
        @keyframes orb-ping {
          75%, 100% { transform: scale(1.6); opacity: 0; }
        }
        @keyframes orb-node-pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.08); }
        }
      `}</style>

      {items.map((item, i) => {
        const { x, y, z, opacity } = calculatePosition(i, items.length)
        const Icon = item.icon
        const hovered = hoveredId === item.id
        const energy = item.energy ?? 60
        const haloSize = 38 + energy * 0.18  // 38..56px
        // Each node gets a distinct bright-palette color (shared CHART_PALETTE).
        const nodeColor = CHART_PALETTE[i % CHART_PALETTE.length]

        return (
          <div
            key={item.id}
            onClick={(e) => handleNodeClick(e, item.id)}
            onMouseEnter={() => setHoveredId(item.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
              zIndex: hovered ? 50 : z,
              opacity: hovered ? 1 : opacity,
              cursor: 'pointer',
              transition: 'opacity 0.35s ease',
            }}
          >
            {/* Halo behind the node */}
            <div
              aria-hidden
              style={{
                position: 'absolute',
                left: '50%',
                top: '50%',
                width: haloSize,
                height: haloSize,
                marginLeft: -haloSize / 2,
                marginTop: -haloSize / 2,
                borderRadius: '50%',
                background: `radial-gradient(circle, ${nodeColor}3D 0%, ${nodeColor}00 70%)`,
                animation: hovered ? 'orb-node-pulse 1.6s ease-in-out infinite' : undefined,
                pointerEvents: 'none',
              }}
            />
            {/* The node itself */}
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: '50%',
                background: hovered ? nodeColor : COLORS.surface,
                color: hovered ? '#FFFFFF' : nodeColor,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: `2px solid ${hovered ? nodeColor : nodeColor + '55'}`,
                boxShadow: hovered ? `0 10px 26px ${nodeColor}59, 0 4px 12px rgba(0,0,0,0.08)` : COLORS.shadowSm,
                transition: 'background 0.18s ease, color 0.18s ease, transform 0.18s ease',
                transform: hovered ? 'scale(1.12)' : 'scale(1)',
              }}
            >
              <Icon size={16} strokeWidth={2.3} />
            </div>
            {/* Label below the node */}
            <div
              style={{
                position: 'absolute',
                top: 46,
                left: '50%',
                transform: 'translateX(-50%)',
                whiteSpace: 'nowrap',
                fontSize: 11,
                fontWeight: 600,
                color: hovered ? nodeColor : COLORS.textMuted,
                background: hovered ? `${nodeColor}1A` : 'transparent',
                padding: hovered ? '3px 8px' : 0,
                borderRadius: 6,
                transition: 'all 0.18s ease',
                pointerEvents: 'none',
              }}
            >
              {item.title}
            </div>
          </div>
        )
      })}
    </div>
  )
}
