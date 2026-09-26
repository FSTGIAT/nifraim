import React from 'react'
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig, Easing } from 'remotion'

/**
 * PortalFeatureScene — one animated card per slide of the customer-portal
 * "what your customer sees" slider (PortalLinksManager.vue). `step` picks the
 * scene; each is a short, loop-safe vignette of that feature as the customer
 * sees it: summary tiles fill · charts draw · a new change slides in · a
 * question gets answered · the מסלקה pension report's accumulation line rises. Abstract shapes only, never fake numbers or names.
 *
 * Colours are hexes (Remotion can't read CSS vars): the portal's sky palette.
 */
export const PORTAL_SCENE_FRAMES = 84 // 2.8s @ 30fps — the slide's length
export const PORTAL_SCENE_W = 360
export const PORTAL_SCENE_H = 220

const SKY = '#4E9DD0'
const INK = '#35719A'
const WASH = '#EAF3F9'
const SOFT = '#9CC6E3'
const LINE = '#DCEAF4'

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const
const out = Easing.bezier(0.16, 1, 0.3, 1)

type Props = { step?: number }

const Card: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      position: 'absolute', inset: 10, borderRadius: 18, background: '#fff',
      border: `1px solid ${LINE}`, boxShadow: '0 14px 34px rgba(53,113,154,0.14)', overflow: 'hidden',
      display: 'flex', flexDirection: 'column', padding: 18, gap: 12,
    }}
  >
    {children}
  </div>
)

// 0 · תמונת מצב — three summary tiles whose bars fill, one after another.
const Summary: React.FC<{ f: number }> = ({ f }) => (
  <Card>
    <div style={{ display: 'flex', gap: 10, flex: 1 }}>
      {[0, 1, 2].map((i) => {
        const p = interpolate(f, [6 + i * 8, 34 + i * 8], [0, 1], { ...clamp, easing: out })
        return (
          <div key={i} style={{ flex: 1, borderRadius: 12, background: WASH, padding: 12, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div style={{ width: 22, height: 22, borderRadius: 7, background: i === 1 ? INK : SKY, opacity: 0.9 }} />
            <div style={{ height: 12, borderRadius: 6, background: '#fff', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${[78, 62, 88][i] * p}%`, background: i === 1 ? INK : SKY, borderRadius: 6 }} />
            </div>
            <div style={{ height: 7, width: '55%', borderRadius: 4, background: SOFT, opacity: 0.6 }} />
          </div>
        )
      })}
    </div>
  </Card>
)

// 1 · גרפים — a donut draws in beside bars that grow.
const Charts: React.FC<{ f: number }> = ({ f }) => {
  const C = 2 * Math.PI * 34
  const segs = [0.44, 0.3, 0.26]
  let acc = 0
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', gap: 18, flex: 1 }}>
        <svg width={112} height={112} viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
          <circle cx="50" cy="50" r="34" fill="none" stroke={WASH} strokeWidth="14" />
          {segs.map((v, i) => {
            const p = interpolate(f, [4 + i * 6, 30 + i * 6], [0, 1], { ...clamp, easing: out })
            const el = (
              <circle key={i} cx="50" cy="50" r="34" fill="none" stroke={[SKY, INK, SOFT][i]} strokeWidth="14"
                strokeDasharray={`${C * v * p} ${C}`} strokeDashoffset={-C * acc} />
            )
            acc += v
            return el
          })}
        </svg>
        <div style={{ flex: 1, height: 110, display: 'flex', alignItems: 'flex-end', gap: 7 }}>
          {[40, 58, 50, 70, 64, 90].map((h, i) => {
            const p = interpolate(f, [10 + i * 4, 36 + i * 4], [0, 1], { ...clamp, easing: out })
            return <div key={i} style={{ flex: 1, height: `${h * p}%`, borderRadius: '5px 5px 0 0', background: i === 5 ? INK : SKY, opacity: i === 5 ? 1 : 0.75 }} />
          })}
        </div>
      </div>
    </Card>
  )
}

// 2 · מה השתנה — a new row slides in at the top, highlighted, with an up tick.
const Changes: React.FC<{ f: number; fps: number }> = ({ f, fps }) => {
  const s = spring({ frame: f - 10, fps, config: { damping: 16, stiffness: 120 } })
  const glow = interpolate(f, [30, 60], [1, 0.35], clamp)
  const row = (w: number, hi = false) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 10, background: hi ? `rgba(78,157,208,${0.16 * glow + 0.06})` : '#F6FAFD', border: hi ? `1px solid ${SOFT}` : `1px solid ${LINE}` }}>
      <div style={{ width: 18, height: 18, borderRadius: 6, background: hi ? INK : SOFT }} />
      <div style={{ height: 8, width: `${w}%`, borderRadius: 4, background: hi ? SKY : LINE }} />
      {hi && (
        <svg width="16" height="16" viewBox="0 0 24 24" style={{ marginInlineStart: 'auto' }}>
          <path d="M12 19V5M5 12l7-7 7 7" fill="none" stroke={INK} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </div>
  )
  return (
    <Card>
      <div style={{ transform: `translateY(${(1 - s) * -46}px)`, opacity: Math.min(1, s * 1.4) }}>{row(56, true)}</div>
      <div style={{ transform: `translateY(${(1 - s) * -46}px)`, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {row(70)}
        {row(48)}
      </div>
    </Card>
  )
}

// 3 · שאלות ל-AI — the customer's question pops in, the AI types, the answer appears.
const Ask: React.FC<{ f: number; fps: number }> = ({ f, fps }) => {
  const q = spring({ frame: f - 4, fps, config: { damping: 14, stiffness: 150 } })
  const typing = f > 18 && f < 44
  const a = spring({ frame: f - 44, fps, config: { damping: 16, stiffness: 140 } })
  return (
    <Card>
      <div style={{ alignSelf: 'flex-end', transform: `scale(${q})`, transformOrigin: 'right bottom', background: INK, color: '#fff', borderRadius: '16px 16px 4px 16px', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 90, height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.75)' }} />
        <svg width="16" height="16" viewBox="0 0 24 24"><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </div>
      {typing && (
        <div style={{ alignSelf: 'flex-start', background: WASH, borderRadius: '16px 16px 16px 4px', padding: '12px 16px', display: 'flex', gap: 5 }}>
          {[0, 1, 2].map((i) => (
            <div key={i} style={{ width: 7, height: 7, borderRadius: '50%', background: SKY, opacity: 0.35 + 0.65 * Math.max(0, Math.sin(((f - 18) / 5 - i) )) }} />
          ))}
        </div>
      )}
      {f >= 44 && (
        <div style={{ alignSelf: 'flex-start', transform: `scale(${a})`, transformOrigin: 'left top', background: WASH, borderRadius: '16px 16px 16px 4px', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 7, width: '72%' }}>
          <div style={{ height: 8, width: '100%', borderRadius: 4, background: SKY, opacity: 0.8 }} />
          <div style={{ height: 8, width: '82%', borderRadius: 4, background: SKY, opacity: 0.55 }} />
          <div style={{ height: 8, width: '54%', borderRadius: 4, background: SKY, opacity: 0.35 }} />
        </div>
      )}
    </Card>
  )
}

// 4 · דוח מסלקה — the clearinghouse pension report: a report sheet whose
// accumulation line draws upward, with the latest point pulsing.
const Maslaka: React.FC<{ f: number }> = ({ f }) => {
  const pts = [[8, 78], [22, 70], [36, 72], [50, 58], [64, 50], [78, 38], [92, 22]]
  const p = interpolate(f, [8, 50], [0, 1], { ...clamp, easing: out })
  const d = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x} ${y}`).join(' ')
  const area = `${d} L92 90 L8 90 Z`
  const pulse = 1 + 0.25 * Math.max(0, Math.sin((f - 50) / 4))
  return (
    <Card>
      <div style={{ display: 'flex', gap: 14, flex: 1 }}>
        <div style={{ width: 92, borderRadius: 10, background: '#F6FAFD', border: `1px solid ${LINE}`, padding: 10, display: 'flex', flexDirection: 'column', gap: 7 }}>
          <div style={{ width: 26, height: 26, borderRadius: 8, background: INK }} />
          {[92, 70, 84, 56, 76].map((w, i) => (
            <div key={i} style={{ height: 6, width: `${w}%`, borderRadius: 3, background: i === 0 ? SKY : LINE }} />
          ))}
        </div>
        {/* sized by its box, not by the SVG's own height — it overflowed the card */}
        <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible' }}>
          <defs>
            <clipPath id="pfs-reveal"><rect x="0" y="0" width={100 * p} height="100" /></clipPath>
            <linearGradient id="pfs-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={SKY} stopOpacity="0.28" /><stop offset="100%" stopColor={SKY} stopOpacity="0" />
            </linearGradient>
          </defs>
          {[30, 55, 80].map((y) => <line key={y} x1="4" x2="96" y1={y} y2={y} stroke={LINE} strokeWidth="0.8" />)}
          <g clipPath="url(#pfs-reveal)">
            <path d={area} fill="url(#pfs-area)" />
            <path d={d} fill="none" stroke={INK} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          </g>
          {p > 0.98 && <circle cx="92" cy="22" r={3.2 * pulse} fill={SKY} />}
        </svg>
        </div>
      </div>
    </Card>
  )
}

export const PortalFeatureScene: React.FC<Props> = ({ step = 0 }) => {
  const f = useCurrentFrame()
  const { fps } = useVideoConfig()
  // Fade the last few frames so the slider's swap to the next scene is soft.
  const fade = interpolate(f, [PORTAL_SCENE_FRAMES - 8, PORTAL_SCENE_FRAMES - 1], [1, 0.0], clamp)
  return (
    <AbsoluteFill style={{ background: 'transparent', opacity: fade, direction: 'ltr' }}>
      {step === 0 && <Summary f={f} />}
      {step === 1 && <Charts f={f} />}
      {step === 2 && <Changes f={f} fps={fps} />}
      {step === 3 && <Ask f={f} fps={fps} />}
      {step === 4 && <Maslaka f={f} />}
    </AbsoluteFill>
  )
}
