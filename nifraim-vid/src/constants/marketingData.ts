// Marketing video Hebrew strings and mock data

export const MARKETING = {
  brandName: 'Nifraim',
  tagline: 'ניהול עמלות. חכם.',
  taglineLong: 'מערכת ניהול עמלות חכמה לסוכני ביטוח',
  url: 'nifraim.com',
  ctaPrimary: 'התחילו היום בחינם',
  ctaSecondary: 'גלו את Nifraim',
};

export const MARKETING_INTRO = {
  headline: 'Nifraim',
  subtitle: 'ניהול עמלות. חכם.',
  description: 'הפלטפורמה המובילה לסוכני ביטוח',
};

export const MARKETING_COMPARISON = {
  title: 'השוואה מיידית',
  subtitle: 'זיהוי פערים בין פרודוקציה לנפרעים — תוך שניות',
  pills: [
    { label: 'חדשים', value: 41, color: '#4ADE80', bg: 'rgba(46,132,74,0.2)' },
    { label: 'הוסרו', value: 47, color: '#FB7185', bg: 'rgba(234,0,30,0.15)' },
    { label: 'שונו', value: 510, color: '#F57C00', bg: 'rgba(245,124,0,0.15)' },
    { label: 'ללא שינוי', value: 123, color: 'rgba(255,255,255,0.5)', bg: 'rgba(255,255,255,0.06)' },
  ],
  donut: {
    title: 'התפלגות לקוחות',
    centerLabel: 'סה"כ',
    total: 184,
    segments: [
      { label: 'נמצא בנפרעים', value: 165, color: '#2E844A' },
      { label: 'רק בנפרעים', value: 10, color: '#7F56D9' },
      { label: 'לא שולם', value: 1, color: '#E8720A' },
      { label: 'רק בפרודוקציה', value: 8, color: '#F57C00' },
    ],
  },
  kpis: [
    { label: 'לקוחות בנפרעים', value: 175, color: '#F57C00' },
    { label: 'לא שולם', value: 1, color: '#EA001E' },
    { label: 'סה"כ עמלה', value: 16659, prefix: '₪', color: '#7F56D9' },
    { label: 'סה"כ יתרה', value: 90402488, prefix: '₪', color: '#2E844A' },
  ],
  barChart: {
    title: 'לקוחות לפי צבירה',
    bars: [
      { label: 'שרה לוי', value: 6.4, color: '#F57C00' },
      { label: 'משה אברהם', value: 3.9, color: '#2E844A' },
      { label: 'רחל ישראלי', value: 3.3, color: '#FFB74D' },
      { label: 'יוסי דוידי', value: 2.8, color: '#7F56D9' },
      { label: 'נועה גולדברג', value: 2.1, color: '#06A59A' },
    ],
  },
};

export const MARKETING_PORTAL = {
  greeting: 'שלום, דוד כהן',
  badge: 'פורטל לקוחות',
  tagline: 'שתפו דשבורד אישי עם כל לקוח',
  shareText: 'שליחת קישור מאובטח',
  kpis: [
    { label: 'מוצרים', value: 31, color: '#F57C00' },
    { label: 'פרמיה חודשית', value: 701, prefix: '₪', color: '#7F56D9' },
    { label: 'צבירה כוללת', value: 9731021, prefix: '₪', color: '#2E844A' },
  ],
  companies: [
    { name: 'מור', products: 11, accumulation: '₪3.9M', active: 11, inactive: 0 },
    { name: 'הפניקס', products: 16, accumulation: '₪3.5M', active: 7, inactive: 9 },
  ],
};

export const MARKETING_OUTRO = {
  cta: 'התחילו היום בחינם',
  url: 'nifraim.com',
  tagline: 'ניהול עמלות חכם לסוכני ביטוח',
};

export const VALUE_PROPS = [
  { icon: '📊', title: 'ניתוח אוטומטי', desc: 'העלו קובץ אקסל — קבלו תובנות מיידיות' },
  { icon: '🔍', title: 'השוואת נפרעים', desc: 'זיהוי פערים בין פרודוקציה לעמלות' },
  { icon: '🔗', title: 'פורטל לקוחות', desc: 'דשבורד אישי לכל לקוח עם קישור מאובטח' },
  { icon: '🏢', title: '11+ חברות ביטוח', desc: 'תמיכה בכל הפורמטים המובילים בישראל' },
];
