// Data-driven storyboard for the commercial "where to press" walkthrough video.
// Two kinds of steps:
//   - 'shot' : a screenshot with a click target + caption (cursor presses it)
//   - 'card' : a full-screen narration title card (no screenshot, no cursor)
// `target` coordinates are in the SCREENSHOT's own natural pixel space — the
// composition maps them to canvas space via the shared fit transform, so they
// never need hand-tuning to 1920×1080.

export interface ShotStep {
  kind?: 'shot'
  /** staticFile path under public/, e.g. "walkthrough/home.png" */
  image: string
  /** natural pixel dimensions of the screenshot */
  imgW: number
  imgH: number
  /** click point in IMAGE pixels */
  target: { x: number; y: number }
  /** false = focus only, no cursor press / ripple (e.g. a progress screen) */
  click?: boolean
  /** Hebrew RTL caption (shown as a prominent banner at the top of the slide) */
  caption: string
  /** override duration in frames (default STEP_FRAMES) */
  frames?: number
}

export type CardIcon = 'vault' | 'download' | 'merge' | 'doc' | 'report' | 'chart' | 'shield'

export interface CardStep {
  kind: 'card'
  /** Hebrew RTL title */
  title: string
  /** optional paragraph under the title */
  body?: string
  /** optional bullet list */
  bullets?: string[]
  /** optional highlighted footer note (rendered with a mail icon) */
  note?: string
  /** optional orange pill badge */
  badge?: string
  /** inline-SVG icon glyph */
  icon?: CardIcon
  /** override the pastel theme (defaults by icon) */
  tint?: { bg: string; accent: string }
  /** override duration in frames */
  frames?: number
}

export type Step = ShotStep | CardStep

export const isCard = (s: Step): s is CardStep => s.kind === 'card'

/** Frames per screenshot screen. 150 @ 30fps = 5s. */
export const STEP_FRAMES = 150
/** Default frames per narration card. ~3.7s. */
export const CARD_FRAMES = 110

export const stepFrames = (s: Step): number =>
  isCard(s) ? s.frames ?? CARD_FRAMES : s.frames ?? STEP_FRAMES

export const steps: Step[] = [
  {
    image: 'walkthrough/home.png',
    imgW: 2476,
    imgH: 1411,
    target: { x: 2327, y: 1322 },
    caption: 'מתחברים ל-Nifraim בלחיצה אחת',
  },
  {
    image: 'walkthrough/mainScreen.png',
    imgW: 2482,
    imgH: 1414,
    target: { x: 845, y: 395 },
    caption: 'נכנסים ל"אוטומציה"',
  },
  {
    kind: 'card',
    icon: 'vault',
    title: 'מילוי שם וסיסמה לכספות של חברות הביטוח',
    badge: 'חד פעמי',
  },
  {
    image: 'walkthrough/addPortal.png',
    imgW: 1240,
    imgH: 1144,
    target: { x: 630, y: 317 },
    caption: 'מוסיפים פורטל — וה-OTP מגיע אוטומטית לטלפון',
  },
  {
    image: 'walkthrough/button.png',
    imgW: 1204,
    imgH: 483,
    target: { x: 955, y: 195 },
    caption:
      'המערכת מבצעת הורדה אוטומטית של כל דוחות הפרודוקציה ודוחות הנפרעים מכל החברות, ומשווה ביניהם באופן עצמאי',
    frames: 240,
  },
  {
    kind: 'card',
    icon: 'download',
    title: 'התחלת הורדה של קבצי נפרעים ופרודוקציה',
    badge: 'מתוזמן',
  },
  {
    kind: 'card',
    icon: 'merge',
    title: 'המערכת מבצעת בדיקת נפרעים אוטומטית',
  },
  {
    kind: 'card',
    icon: 'doc',
    title: 'קריאת הסכמי עמלות אוטומטית',
    body: 'המערכת קוראת את הסכמי העמלות של כל החברות, מזהה את אחוזי הנפרעים בהתאם להסכם הרלוונטי ולשנת ההסכם, ומיישמת אותם באופן אוטומטי.',
    frames: 200,
  },
  {
    image: 'walkthrough/production.png',
    imgW: 1587,
    imgH: 1378,
    target: { x: 1360, y: 52 },
    caption: 'הכול נטען אוטומטית ללשונית פרודוקציה',
  },
  {
    image: 'walkthrough/resaults.png',
    imgW: 2389,
    imgH: 936,
    target: { x: 1020, y: 723 },
    caption: 'תוצאות ההשוואה — נפרעים מול פרודוקציה',
  },
  {
    kind: 'card',
    icon: 'report',
    title: 'המערכת מפיקה דוח מרכז הכולל:',
    bullets: [
      'כל הלקוחות שלא שולם בגינם נפרע',
      'כל הלקוחות שקיבלת בגינם נפרעים אך אינך רשום כמיופה כוח',
      'כל הלקוחות שקיבלת בגינם תשלום',
    ],
    note: 'ניתן לשלוח מייל ישירות לחברה עם הלקוחות שלא התקבל בגינם תשלום',
    frames: 200,
  },
  {
    kind: 'card',
    icon: 'chart',
    title: 'כל חיתוך וניתוח שתרצו',
    body: 'פילוח הנתונים לפי חברה, מוצר, אפיק השקעה, מספר סוכן, תקופה — או כל חתך אחר שתרצו.',
    frames: 150,
  },
  {
    image: 'walkthrough/ai.png',
    imgW: 1717,
    imgH: 1072,
    target: { x: 858, y: 812 },
    caption: 'עוזר AI — שואלים בשפה חופשית ומקבלים תשובה על הנתונים שלכם',
  },
  {
    kind: 'card',
    icon: 'shield',
    title: 'המידע שלך — שלך בלבד',
    bullets: ['הנתונים שלך', 'הסוכן שלך', 'אבטחה מלאה'],
    frames: 170,
  },
]

/** Cumulative start frame of each step. */
export const offsets: number[] = (() => {
  const out: number[] = []
  let acc = 0
  for (const s of steps) {
    out.push(acc)
    acc += stepFrames(s)
  }
  return out
})()

export const WALKTHROUGH_DURATION = offsets[offsets.length - 1] + stepFrames(steps[steps.length - 1])

/** Total number of screenshot (shot) steps — used for the "N/total" counter. */
export const SHOT_TOTAL = steps.filter((s) => !isCard(s)).length

/** 1-based shot number for a shot step at array index `i` (cards don't count). */
export function shotNumber(i: number): number {
  let n = 0
  for (let k = 0; k <= i; k++) if (!isCard(steps[k])) n++
  return n
}

// ── Shared canvas + fit geometry ───────────────────────────────────────────
export const CANVAS = { width: 1920, height: 1080 } as const

// Captions sit in a prominent banner at the TOP of the slide; the screenshot is
// fit (contain) inside the box BELOW it.
const BOX = { x: 120, y: 172, w: 1680, h: 838 } as const

export interface FitInfo {
  scale: number
  drawX: number
  drawY: number
  drawW: number
  drawH: number
}

export function fitInfo(step: ShotStep): FitInfo {
  const scale = Math.min(BOX.w / step.imgW, BOX.h / step.imgH)
  const drawW = step.imgW * scale
  const drawH = step.imgH * scale
  const drawX = BOX.x + (BOX.w - drawW) / 2
  const drawY = BOX.y + (BOX.h - drawH) / 2
  return { scale, drawX, drawY, drawW, drawH }
}

/** Map an in-image pixel point to canvas-space pixels. */
export function toCanvas(step: ShotStep, pt: { x: number; y: number }): { x: number; y: number } {
  const f = fitInfo(step)
  return { x: f.drawX + pt.x * f.scale, y: f.drawY + pt.y * f.scale }
}
