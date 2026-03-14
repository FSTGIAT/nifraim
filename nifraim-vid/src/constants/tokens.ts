import { loadFont } from '@remotion/google-fonts/Heebo';

export const { fontFamily } = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['hebrew', 'latin'],
});

// Spring presets
export const SPRING = {
  SNAPPY: { damping: 12, mass: 0.5 },
  SMOOTH: { damping: 20, mass: 1 },
  BOUNCY: { damping: 10, mass: 0.8 },
} as const;

// Scene timing (frames)
// Scene durations managed in NifraimCommercial.tsx scenes array
// These are approximate references only
export const SCENES = {
  BRAND_INTRO: { from: 0, duration: 90 },
  CH_PROBLEM: { from: 90, duration: 45 },
  PROBLEM: { from: 135, duration: 100 },
  CH_UPLOAD: { from: 235, duration: 45 },
  UPLOAD_INSIGHTS: { from: 280, duration: 110 },
  CH_COMPARISON: { from: 390, duration: 45 },
  FILE_COMPARISON: { from: 435, duration: 110 },
  CH_COMMISSION: { from: 545, duration: 45 },
  COMMISSION_DASHBOARD: { from: 590, duration: 110 },
  CH_PORTAL: { from: 700, duration: 45 },
  CUSTOMER_PORTAL: { from: 745, duration: 110 },
  METRICS_CTA: { from: 855, duration: 110 },
} as const;

export const FPS = 30;
export const TOTAL_FRAMES = 910;
export const FADE_FRAMES = 5;

// Design tokens
export const TOKENS = {
  radiusSm: 8,
  radiusMd: 12,
  radiusLg: 16,
  radiusXl: 24,
  shadowSm: '0 1px 3px rgba(0, 0, 0, 0.08)',
  shadowMd: '0 2px 8px rgba(0, 0, 0, 0.06)',
  shadowLg: '0 4px 14px rgba(0, 0, 0, 0.1)',
  shadowGlow: '0 0 0 3px rgba(245, 124, 0, 0.15)',
} as const;
