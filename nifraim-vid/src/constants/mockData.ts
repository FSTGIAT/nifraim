// All Hebrew strings and numeric data for scenes

export const SCENE1 = {
  brandName: 'Nifraim',
  tagline: 'ניהול עמלות. חכם.',
  url: 'nifraim.com',
};

export const SCENE2 = {
  headline: 'מנהלים עמלות בידיים?',
  subtext: 'עשרות קבצי אקסל. פורמטים שונים. שעות של עבודה ידנית.',
};

export const SCENE3 = {
  kpis: [
    { label: 'מוצרים', value: 2157, prefix: '', color: '#F57C00' },
    { label: 'לקוחות', value: 674, prefix: '', color: '#F57C00' },
    { label: 'סה"כ פרמיה', value: 159, prefix: '₪', suffix: 'K', color: '#7F56D9' },
    { label: 'סה"כ צבירה', value: 303.6, prefix: '₪', suffix: 'M', color: '#F57C00' },
    { label: 'חברות', value: 16, prefix: '', color: '#F57C00' },
    { label: 'מוצרים פעילים', value: 74, prefix: '', suffix: '%', color: '#2E844A' },
  ],
  productTypeChart: {
    title: 'התפלגות לפי סוג מוצר',
    bars: [
      { label: 'קופת גמל לתגמולים ופיצויים', value: 500 },
      { label: 'קרן השתלמות', value: 380 },
      { label: 'ביטוח בריאות', value: 370 },
      { label: 'פנסיה מקיפה', value: 310 },
      { label: 'ביטוח חיים', value: 250 },
    ],
  },
  companyChart: {
    title: 'התפלגות לפי חברה',
    bars: [
      { label: 'מור גמל ופנסיה', value: 91.2, color: '#2E844A' },
      { label: 'הפניקס אקסלנס', value: 63.7, color: '#F57C00' },
      { label: 'הראל', value: 45.3, color: '#7F56D9' },
      { label: 'כלל', value: 38.1, color: '#06A59A' },
      { label: 'מנורה מבטחים', value: 32.8, color: '#E8720A' },
    ],
  },
};

export const SCENE4 = {
  title: 'תוצאות השוואה',
  pills: [
    { label: 'חדשים', value: 41, color: '#4ADE80', bg: 'rgba(46,132,74,0.2)' },
    { label: 'הוסרו', value: 47, color: '#FB7185', bg: 'rgba(234,0,30,0.15)' },
    { label: 'שונו', value: 510, color: '#F57C00', bg: 'rgba(245,124,0,0.15)' },
    { label: 'ללא שינוי', value: 123, color: 'rgba(255,255,255,0.5)', bg: 'rgba(255,255,255,0.06)' },
  ],
  mainDonut: {
    title: 'התפלגות שינויים',
    centerLabel: 'סה"כ לקוחות',
    total: 721,
    segments: [
      { label: 'שונו', value: 510, color: '#F57C00' },
      { label: 'ללא שינוי', value: 123, color: '#B0B0B0' },
      { label: 'הוסרו', value: 47, color: '#EA001E' },
      { label: 'חדשים', value: 41, color: '#2E844A' },
    ],
  },
  miniDonuts: [
    {
      title: 'חדשים לפי חברה',
      total: 41,
      segments: [
        { label: 'מגדל חברה לביטוח', value: 32, color: '#38BDF8' },
        { label: 'מור גמל ופנסיה', value: 6, color: '#F57C00' },
        { label: 'אחר', value: 3, color: '#B0B0B0' },
      ],
    },
    {
      title: 'הוסרו לפי חברה',
      total: 47,
      segments: [
        { label: 'מנורה מבטחים', value: 41, color: '#38BDF8' },
        { label: 'הפניקס אקסלנס', value: 3, color: '#F57C00' },
        { label: 'אחר', value: 3, color: '#B0B0B0' },
      ],
    },
  ],
};

export const SCENE5 = {
  companyName: 'מור',
  categoryBadge: 'גמל והשתלמות',
  donutTitle: 'התפלגות לקוחות',
  donut: {
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
    { label: 'סה"כ חוב לא משולם', value: 30, prefix: '₪', color: '#E8720A' },
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
  alert: {
    count: 1,
    text: 'לקוחות ללא תשלום עמלה',
    loss: '₪30',
  },
};

export const SCENE6 = {
  greeting: 'שלום, דוד כהן',
  idNumber: 'ת.ז: 123456789',
  dateBadge: 'דצמבר 2025',
  kpis: [
    { label: 'מוצרים', value: 31, color: '#F57C00' },
    { label: 'פרמיה חודשית', value: 701, prefix: '₪', color: '#7F56D9' },
    { label: 'צבירה כוללת', value: 9731021, prefix: '₪', color: '#2E844A' },
    { label: 'חברות ביטוח', value: 5, color: '#F57C00' },
  ],
  companies: [
    { name: 'מור', products: 11, accumulation: '₪3.9M', active: 11, inactive: 0 },
    { name: 'הפניקס אקסלנס', products: 16, accumulation: '₪3.5M', active: 7, inactive: 9 },
    { name: 'הראל', products: 2, accumulation: '₪2.2M', active: 1, inactive: 0 },
    { name: 'כלל', products: 1, accumulation: '₪141K', active: 1, inactive: 0 },
  ],
  donut: {
    centerLabel: 'סה"כ צבירה ₪9.7M',
    segments: [
      { label: 'מור', value: 40, color: '#F57C00' },
      { label: 'הפניקס אקסלנס', value: 36, color: '#7F56D9' },
      { label: 'הראל', value: 22, color: '#2E844A' },
      { label: 'כלל', value: 2, color: '#F472B6' },
    ],
  },
  tagline: 'לכל לקוח — דשבורד אישי',
  productsTitle: 'המוצרים שלך',
  donutTitle: 'התפלגות לפי חברה',
};

export const SCENE7 = {
  metrics: [
    { value: 95, suffix: '%', label: 'חיסכון בזמן' },
    { value: 7, suffix: '+', label: 'פורמטים נתמכים' },
    { value: 1000, suffix: '+', label: 'קבצים עובדו' },
    { value: 50, suffix: '+', label: 'חברות ביטוח' },
  ],
  subtitle: 'העלו קבצים, השוו נתונים, גלו פערים — תוך שניות',
  cta: 'התחילו עכשיו',
  url: 'nifraim.com',
};
