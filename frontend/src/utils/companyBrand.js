// Visual identity per insurance/pension company.
// Colors chosen to evoke each brand without lifting their actual logos.
// Each `iconPath` is a 24x24 viewBox SVG path string — Lucide-style stroke
// silhouettes (the matching component sets stroke-width / linecap).
//
// Sources informing colour choice (well-known brand reds/blues/greens):
//  - Migdal (מגדל)        — red tower mark
//  - Phoenix (הפניקס)     — deep navy with rising bird
//  - Clal (כלל)            — corporate blue
//  - Menora (מנורה)        — royal blue, 7-branch candelabrum
//  - Altshuler Shaham      — graphite / navy
//  - Hachshara (הכשרה)    — emerald green
//  - Excellence (אקסלנס)   — red accent
//  - Mor (מור)             — teal
//  - Ayalon (איילון)       — sunset orange (gazelle)
//  - Clal Health           — blue with health-cross accent

export const COMPANY_BRAND = {
  migdal: {
    label: 'מגדל',
    color: '#C8102E',
    // 3 ascending bars + flag — a tower
    iconPath: 'M5 21V11l4-3v13M9 21V8l4-3v16M13 21V5l4 4v12M3 21h18',
  },
  phoenix: {
    label: 'הפניקס',
    color: '#2E5BBF',
    // Rising phoenix — flame above wing
    iconPath: 'M12 4 8 11h8L12 4Zm0 7c2 0 4 2 4 4s-2 5-4 5-4-2-4-5 2-4 4-4Zm-7 9h14',
  },
  clal: {
    label: 'כלל',
    color: '#1B5BC9',
    // Concentric arcs — "all/inclusive"
    iconPath: 'M4 12a8 8 0 0 1 16 0M7 12a5 5 0 0 1 10 0M10 12a2 2 0 0 1 4 0',
  },
  clal_nifraim: {
    label: 'כלל — עמלות (נפרעים)',
    color: '#1B5BC9',
    // Same concentric-arcs mark as `clal` (same portal, נפרעים report family)
    iconPath: 'M4 12a8 8 0 0 1 16 0M7 12a5 5 0 0 1 10 0M10 12a2 2 0 0 1 4 0',
  },
  clal_health: {
    label: 'כלל בריאות',
    color: '#0073C7',
    // Cross + heartbeat
    iconPath: 'M12 4v16M4 12h16M2 18h4l2-3 4 6 2-3h6',
  },
  menora: {
    label: 'מנורה',
    color: '#2E73C7',
    // 7-branch menorah
    iconPath: 'M12 4v14M9 7v9M6 10v6M3 13v3M15 7v9M18 10v6M21 13v3M3 20h18',
  },
  menora_nifraim: {
    label: 'מנורה — נפרעים',
    color: '#2E73C7',
    // Same menorah mark as `menora` (same portal, נפרעים report family)
    iconPath: 'M12 4v14M9 7v9M6 10v6M3 13v3M15 7v9M18 10v6M21 13v3M3 20h18',
  },
  altshuler: {
    label: 'אלטשולר',
    color: '#4A5A7A',
    // Diamond + ascending bars (financial growth)
    iconPath: 'M4 20V13M9 20V9M14 20V5M19 20v-9M4 9 12 3l8 6',
  },
  hachshara: {
    label: 'הכשרה',
    color: '#0E7C3A',
    // Shield with check — "preparation/protection"
    iconPath: 'M12 3 4 6v6c0 4 3 7 8 9 5-2 8-5 8-9V6l-8-3Zm-3 9 2 2 4-4',
  },
  excellence: {
    label: 'אקסלנס',
    color: '#D62828',
    // 4-point sparkle / excellence star
    iconPath: 'M12 3v18M3 12h18M5 5l14 14M19 5 5 19',
  },
  mor: {
    label: 'מור',
    color: '#0E8A8E',
    // Sunrise rays (Mor = morning/myrrh)
    iconPath: 'M3 18h18M5 14l1.5-1.5M19 14l-1.5-1.5M12 6v3M8 9l1.5 2M16 9l-1.5 2M6 18a6 6 0 0 1 12 0',
  },
  ayalon: {
    label: 'איילון',
    color: '#E76F00',
    // Gazelle silhouette (איל = stag/gazelle)
    iconPath: 'M5 18c2-1 3-3 4-5 1 2 3 4 5 5M9 8 7 5h2l1 2M15 8l2-3h-2l-1 2M9 8c0 2 1 4 3 5 2-1 3-3 3-5',
  },
  harel: {
    label: 'הראל',
    color: '#E0301E',
    // Mountain silhouette (ה־ראל = the mountain)
    iconPath: 'M3 20h18M3 20l5-9 4 6 3-4 6 7M3 20l5-12 4 8 3-5 6 9',
  },
  yelin: {
    label: 'ילין לפידות',
    color: '#2F7A5E',
    // Stylized "Y" mark
    iconPath: 'M12 21V12M12 12 6 4M12 12l6-8M4 21h16',
  },
  meitav: {
    label: 'מיטב דש',
    color: '#1F77B4',
    // Stacked layers (financial growth)
    iconPath: 'M3 17l9-5 9 5M3 12l9-5 9 5M3 7l9-5 9 5',
  },
  ibi: {
    label: 'אי.בי.אי',
    color: '#5E4FA2',
    // Ascending columns
    iconPath: 'M5 21V11M11 21V7M17 21V4M3 21h18',
  },
  analyst: {
    label: 'אנליסט',
    color: '#0F9D58',
    // Magnifying glass + chart
    iconPath: 'M11 19a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm5.5-2.5L21 21M8 11l2 2 4-4',
  },
}

const FALLBACK = { label: '?', color: '#6B7280', iconPath: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 5v6M12 17h.01' }

export function brandFor(portalKind) {
  return COMPANY_BRAND[portalKind] || FALLBACK
}

/** Look up brand from a Hebrew company label (file_uploads.company_source).
 *  Tolerates "הראל מגוון" → matches "הראל" by substring. */
export function brandForLabel(label) {
  if (!label) return FALLBACK
  const norm = String(label).trim().toLowerCase()
  for (const brand of Object.values(COMPANY_BRAND)) {
    const bl = brand.label.toLowerCase()
    if (norm === bl || norm.includes(bl) || bl.includes(norm)) return brand
  }
  return FALLBACK
}
