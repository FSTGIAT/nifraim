// Brand palette sourced from the Nifraim app (App.vue CSS variables)

export const COLORS = {
  // Core Brand
  primary: '#F57C00',
  primaryDeep: '#E65100',
  primaryLight: '#FFF3E0',
  secondary: '#FF9800',
  warmHighlight: '#FFB74D',

  // Status & Accent
  green: '#2E844A',
  greenDeep: '#1B5E20',
  greenLight: '#EBF7EE',
  amber: '#E8720A',
  amberLight: '#FFF3E0',
  red: '#EA001E',
  redDeep: '#C23934',
  violet: '#7F56D9',
  rose: '#E3066A',
  teal: '#06A59A',

  // Neutrals
  text: '#181818',
  textSecondary: '#3E3E3C',
  textMuted: '#706E6B',
  bg: '#F3F3F3',
  cardBg: '#FFFFFF',
  border: '#DDDBDA',

  // Backgrounds
  darkBg: '#181818',
  lightBg: '#F3F3F3',
  warmBg: '#FFF8F0',
  warmBgDeep: '#FFF0E0',
  // Cinematic dark dashboard bg
  sceneBg: '#0d0d0d',
  sceneBgWarm: '#0f0a08',
  // Glass card on dark — gray tinted
  glass: 'rgba(140,140,140,0.08)',
  glassBorder: 'rgba(180,180,180,0.12)',
  glassShadow: '0 8px 32px rgba(0,0,0,0.5)',
  // Text on dark — gray/white tones
  textOnDark: '#F0F0F0',
  textOnDarkMuted: 'rgba(200,200,200,0.6)',
  // Gray accents
  gray400: '#9CA3AF',
  gray500: '#6B7280',
  gray600: '#4B5563',
} as const;

export const CHART_COLORS = [
  '#F57C00', // Orange (primary)
  '#2E844A', // Green
  '#7F56D9', // Violet
  '#06A59A', // Teal
  '#E8720A', // Amber
  '#C23934', // Red
  '#38BDF8', // Light Blue
  '#F472B6', // Pink
  '#6366F1', // Indigo
] as const;

export const BRAND_GRADIENT =
  'linear-gradient(135deg, #E65100 0%, #F57C00 40%, #FF9800 70%, #FFB74D 100%)';

export const BUTTON_GRADIENT = 'linear-gradient(135deg, #F57C00, #FF9800)';
