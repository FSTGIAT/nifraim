// The page background ("canvas") the agent picks in Settings → מראה.
// Stored per user (userFlags) on this device and applied as --app-canvas on
// <html>, which body and the sticky tab strip paint with. Default = App.vue's.
import { getUserFlag, setUserFlag } from './userFlags.js'

const KEY = 'app_canvas'
// Graphite for a logged-in agent who never picked one (user's call, 2026-09-29).
// Public pages (login, customer portal, /privacy) keep the light stone.
export const DEFAULT_CANVAS = '#2A2C31'
const PUBLIC_CANVAS = '#EEEBE5'

// Light tones + a dark row. The cards stay white either way; on a dark canvas
// <html data-canvas="dark"> lets page-level text (the few labels that sit
// directly on the canvas) switch to light — see App.vue.
export const CANVAS_GROUPS = [
  {
    id: 'neutral', label: 'ניטרליים',
    swatches: [
      { hex: '#EEEBE5', name: 'אבן חמה' },
      { hex: '#F3F3F3', name: 'אפור קלאסי' },
      { hex: '#FAFAF9', name: 'לבן' },
      { hex: '#F4EFE6', name: 'חול' },
      { hex: '#E7E8EB', name: 'גרפיט בהיר' },
    ],
  },
  {
    id: 'palette', label: 'מהפלטה של Nifraim',
    swatches: [
      { hex: '#EAF1FA', name: 'פרודוקציה', accent: '#2F73C4' },
      { hex: '#EAF4EC', name: 'השוואת נפרעים', accent: '#2E844A' },
      { hex: '#F3EDF7', name: 'מדף ההסכמים', accent: '#8E44AD' },
      { hex: '#FBEFF4', name: 'אנשי קשר', accent: '#D6336C' },
      { hex: '#E7F5F4', name: 'תיק אישי', accent: '#0FA39B' },
      { hex: '#EAF4FA', name: 'פורטל לקוחות', accent: '#4E9DD0' },
      { hex: '#F2EEFB', name: 'ספריית AI', accent: '#B79CEB' },
      { hex: '#E8EFF0', name: 'מסלקה', accent: '#2C5F6B' },
      { hex: '#E6F3F2', name: 'אוטומציה', accent: '#0E8C8A' },
    ],
  },
  {
    id: 'dark', label: 'כהים',
    swatches: [
      { hex: '#0F0F10', name: 'שחור' },
      { hex: '#1C1D20', name: 'פחם' },
      { hex: '#2A2C31', name: 'גרפיט' },
      { hex: '#16202E', name: 'כחול לילה' },
      { hex: '#13231E', name: 'ירוק לילה' },
      { hex: '#221A2B', name: 'שזיף' },
    ],
  },
]

const HEX = /^#[0-9a-f]{6}$/i

export function getCanvas() {
  const v = getUserFlag(KEY)
  if (v && HEX.test(v)) return v.toUpperCase()
  let loggedIn = false
  try { loggedIn = !!localStorage.getItem('token') } catch { /* private mode */ }
  return loggedIn ? DEFAULT_CANVAS : PUBLIC_CANVAS
}

export function isDarkCanvas(hex) {
  return luminance(hex) < 0.2
}

export function applyCanvas(hex = getCanvas()) {
  try {
    const root = document.documentElement
    root.style.setProperty('--app-canvas', hex)
    root.dataset.canvas = isDarkCanvas(hex) ? 'dark' : 'light'
  } catch { /* SSR / no DOM */ }
}

export function setCanvas(hex) {
  if (!HEX.test(hex || '')) return
  setUserFlag(KEY, hex.toUpperCase())
  applyCanvas(hex.toUpperCase())
}

/** Relative luminance 0..1 — the custom picker warns below ~0.72 (too dark for ink text). */
export function luminance(hex) {
  const c = [1, 3, 5].map((i) => {
    const v = parseInt(hex.slice(i, i + 2), 16) / 255
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
}
