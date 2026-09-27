import React from 'react'
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion'

/**
 * Live preview in the portal setup wizard: a phone showing what THIS customer
 * will see, rebuilt from the agent's choices (sections, product scope, hidden
 * amounts, offers). The Vue host seeks to 0 and replays whenever a choice
 * changes; only the block named by `highlight` animates in (the rest stay
 * put), so a toggle reads as "that part just appeared / changed". On first
 * mount `highlight` is 'all' and every block staggers in.
 *
 * Colours come in as props — Remotion can't read the app's CSS variables.
 */
export const PORTAL_PREVIEW_FRAMES = 45
export const PORTAL_PREVIEW_W = 300
export const PORTAL_PREVIEW_H = 600

export type PortalPreviewProps = {
  customerName?: string
  sections?: Record<string, boolean>
  scope?: 'all' | 'savings' | 'insurance'
  showPremium?: boolean
  showAccumulation?: boolean
  offers?: string[]
  highlight?: string
  ink?: string
  accent?: string
  wash?: string
  palette?: string[]
}

const ORDER = ['summary', 'changes', 'products', 'companies', 'trend', 'offers', 'agent_card'] as const

export const PortalPreviewPhone: React.FC<PortalPreviewProps> = ({
  customerName = 'הלקוח שלך',
  sections = {},
  scope = 'all',
  showPremium = true,
  showAccumulation = true,
  offers = [],
  highlight = 'all',
  ink = '#35719A',
  accent = '#4E9DD0',
  wash = 'rgba(78,157,208,0.12)',
  palette = ['#4E9DD0', '#2E844A', '#8E44AD', '#0FA39B', '#7A7F2A'],
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const on = (k: string) => sections[k] !== false
  const visible = ORDER.filter((k) => (k === 'offers' ? offers.length > 0 : on(k)))

  // Entrance: the highlighted block (or every block, staggered) springs in.
  const enter = (key: string) => {
    const idx = visible.indexOf(key as (typeof ORDER)[number])
    if (highlight !== 'all' && highlight !== key) return { opacity: 1, transform: 'none' }
    const delay = highlight === 'all' ? Math.max(0, idx) * 3 : 0
    const s = spring({ frame: frame - delay, fps, config: { damping: 16, mass: 0.7 } })
    return {
      opacity: interpolate(s, [0, 1], [0, 1]),
      transform: `translateY(${interpolate(s, [0, 1], [10, 0])}px) scale(${interpolate(s, [0, 1], [0.97, 1])})`,
      boxShadow: highlight === key ? `0 0 0 ${interpolate(s, [0, 0.6, 1], [0, 3, 0])}px ${accent}55` : undefined,
    }
  }

  const hidden = '•••'
  const card: React.CSSProperties = {
    background: '#fff', borderRadius: 11, padding: '6px 9px',
    border: '1px solid rgba(24,24,24,0.06)', boxShadow: '0 2px 6px rgba(24,24,24,0.05)',
  }
  const label: React.CSSProperties = { fontSize: 9.5, color: '#706E6B', fontWeight: 600 }
  const value: React.CSSProperties = { fontSize: 13, fontWeight: 800, color: '#181818' }
  const title: React.CSSProperties = { fontSize: 10, fontWeight: 800, color: '#181818', marginBottom: 4 }
  const scopeLabel = scope === 'savings' ? 'חיסכון בלבד' : scope === 'insurance' ? 'ביטוח בלבד' : null
  const products = scope === 'savings'
    ? [['קרן השתלמות', 0], ['קופת גמל', 1], ['קרן פנסיה', 3]]
    : scope === 'insurance'
      ? [['ביטוח חיים', 2], ['ביטוח בריאות', 4], ['ביטוח מנהלים', 0]]
      : [['קרן השתלמות', 0], ['ביטוח חיים', 2], ['קרן פנסיה', 3]]

  return (
    <AbsoluteFill style={{ background: 'transparent', alignItems: 'center', justifyContent: 'center' }}>
      {/* Phone frame */}
      <div style={{
        width: 276, height: 580, borderRadius: 36, background: '#181818', padding: 9,
        boxShadow: '0 24px 50px -12px rgba(24,24,24,0.35)',
      }}>
        <div style={{
          width: '100%', height: '100%', borderRadius: 28, overflow: 'hidden', position: 'relative',
          background: '#F4F6F8', direction: 'rtl', fontFamily: 'Heebo, sans-serif',
          display: 'flex', flexDirection: 'column',
        }}>
          {/* notch */}
          <div style={{ position: 'absolute', top: 6, left: '50%', transform: 'translateX(-50%)', width: 70, height: 16, borderRadius: 10, background: '#181818', zIndex: 2 }} />
          {/* header */}
          <div style={{ background: ink, color: '#fff', padding: '28px 14px 9px' }}>
            <div style={{ fontSize: 9.5, opacity: 0.8, fontWeight: 600 }}>התיק הביטוחי שלך</div>
            <div style={{ fontSize: 15, fontWeight: 800 }}>שלום, {customerName}</div>
            {scopeLabel && (
              <span style={{ display: 'inline-block', marginTop: 5, fontSize: 9, fontWeight: 700, background: 'rgba(255,255,255,0.18)', borderRadius: 999, padding: '2px 8px' }}>{scopeLabel}</span>
            )}
          </div>

          <div style={{ padding: 9, display: 'flex', flexDirection: 'column', gap: 6, flex: 1, overflow: 'hidden' }}>
            {on('summary') && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, ...enter('summary') }}>
                {[
                  ['מוצרים', '6'],
                  ['פרמיה חודשית', showPremium ? '₪1,240' : hidden],
                  ['צבירה כוללת', showAccumulation ? '₪412K' : hidden],
                  ['חברות', '3'],
                ].map(([l, v]) => (
                  <div key={l} style={card}>
                    <div style={label}>{l}</div>
                    <div style={{ ...value, color: v === hidden ? '#A8A6A3' : '#181818' }}>{v}</div>
                  </div>
                ))}
              </div>
            )}

            {on('changes') && (
              <div style={{ ...card, background: wash, border: `1px solid ${accent}40`, fontSize: 9.5, fontWeight: 700, color: ink, ...enter('changes') }}>
                מה השתנה מאז הפעם הקודמת · מוצר אחד חדש
              </div>
            )}

            {on('products') && (
              <div style={{ ...card, ...enter('products') }}>
                <div style={title}>המוצרים שלי</div>
                {products.map(([name, c], i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0', borderTop: i ? '1px solid rgba(24,24,24,0.05)' : 'none' }}>
                    <span style={{ width: 7, height: 7, borderRadius: '50%', background: palette[(c as number) % palette.length] }} />
                    <span style={{ fontSize: 10, color: '#181818', flex: 1 }}>{name}</span>
                    <span style={{ fontSize: 10, fontWeight: 700, color: showAccumulation ? '#3E3E3C' : '#A8A6A3', direction: 'ltr' }}>
                      {showAccumulation ? `₪${(i + 1) * 38}K` : hidden}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {(on('companies') || on('trend')) && (
              <div style={{ display: 'grid', gridTemplateColumns: on('companies') && on('trend') ? '1fr 1fr' : '1fr', gap: 6 }}>
                {on('companies') && (
                  <div style={{ ...card, ...enter('companies') }}>
                    <div style={title}>פיזור לפי חברות</div>
                    <svg width="38" height="38" viewBox="0 0 42 42" style={{ display: 'block', margin: '0 auto' }}>
                      {[[0, 45], [45, 30], [75, 25]].map(([start, len], i) => (
                        <circle key={i} cx="21" cy="21" r="15.9" fill="none" stroke={palette[i]} strokeWidth="6"
                          strokeDasharray={`${len} ${100 - (len as number)}`} strokeDashoffset={25 - (start as number)} />
                      ))}
                    </svg>
                  </div>
                )}
                {on('trend') && (
                  <div style={{ ...card, ...enter('trend') }}>
                    <div style={title}>מגמה</div>
                    <svg width="100%" height="38" viewBox="0 0 100 40" preserveAspectRatio="none">
                      <path d="M0,34 L20,30 L40,26 L60,20 L80,16 L100,8" fill="none" stroke={accent} strokeWidth="2.5" strokeLinecap="round" />
                      <path d="M0,34 L20,30 L40,26 L60,20 L80,16 L100,8 L100,40 L0,40 Z" fill={accent} opacity="0.12" />
                    </svg>
                  </div>
                )}
              </div>
            )}

            {offers.length > 0 && (
              <div style={{ ...enter('offers') }}>
                <div style={{ ...title, marginBottom: 4 }}>שירותים נוספים עבורך</div>
                <div style={{ display: 'flex', gap: 6, overflow: 'hidden' }}>
                  {offers.slice(0, 3).map((o, i) => (
                    <div key={o} style={{ ...card, flex: '0 0 auto', minWidth: 78, borderTop: `3px solid ${palette[(i + 1) % palette.length]}` }}>
                      <div style={{ fontSize: 9.5, fontWeight: 700, color: '#181818', whiteSpace: 'nowrap' }}>{o}</div>
                      <div style={{ fontSize: 8.5, color: ink, fontWeight: 700, marginTop: 2 }}>לפרטים ←</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {on('agent_card') && (
              <div style={{ ...card, display: 'flex', alignItems: 'center', gap: 8, ...enter('agent_card') }}>
                <span style={{ width: 24, height: 24, borderRadius: '50%', background: wash, border: `1.5px solid ${accent}` }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, fontWeight: 800, color: '#181818' }}>הסוכן שלך</div>
                  <div style={{ fontSize: 9, color: '#706E6B' }}>זמין לכל שאלה</div>
                </div>
                <span style={{ fontSize: 9, fontWeight: 700, color: '#fff', background: ink, borderRadius: 999, padding: '3px 9px' }}>חיוג</span>
              </div>
            )}
          </div>

          {on('ai_chat') && (
            <div style={{
              position: 'absolute', bottom: 12, left: 12, width: 34, height: 34, borderRadius: '50%',
              background: ink, display: 'grid', placeItems: 'center', boxShadow: '0 6px 14px rgba(24,24,24,0.25)',
              ...enter('ai_chat'),
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  )
}
