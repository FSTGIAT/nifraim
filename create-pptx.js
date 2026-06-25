const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Nifraim";
pres.title = "Nifraim — AWS Cloud Architecture";

// Constants
const ORANGE = "F57C00";
const DARK = "1a1a1a";
const GRAY = "666666";
const LIGHT_GRAY = "999999";
const PEACH = "f5e0cc";
const LIGHT_BLUE = "dce8f5";
const CARD_BORDER = "b0c4de";
const LABEL_BG = "fff3e0";
const LABEL_BORDER = "ffcc80";
const GREEN_BG = "e8f5e9";
const GREEN_BORDER = "a5d6a7";
const VPC_BORDER = "d4a574";
const WHITE = "FFFFFF";
const BEIGE_BG = "faf3e6";
const BEIGE_BORDER = "d7ccc8";

const companies = [
  { name: "פניקס", color: "c62828" },
  { name: "מגדל", color: "1565c0" },
  { name: "כלל", color: "2e7d32" },
  { name: "מנורה", color: "f9a825", textColor: DARK },
  { name: "הראל", color: "6a1b9a" },
  { name: "אלטשולר", color: "00838f" },
  { name: "איילון", color: "e65100" },
  { name: "הכשרה", color: "37474f" },
  { name: "מור", color: "ad1457" },
];

function makeShadow() {
  return { type: "outer", blur: 4, offset: 2, angle: 135, color: "000000", opacity: 0.08 };
}

// Helper: add decorative circles
function addDecoCircles(slide, variant) {
  if (variant === 1) {
    slide.addShape(pres.shapes.OVAL, { x: -0.3, y: 4.8, w: 1.5, h: 1.5, fill: { color: "8B4513", transparency: 30 } });
    slide.addShape(pres.shapes.OVAL, { x: 9.2, y: -0.2, w: 1.2, h: 1.2, fill: { color: "D2691E", transparency: 50 } });
    slide.addShape(pres.shapes.OVAL, { x: 8.8, y: 4.9, w: 0.9, h: 0.9, fill: { color: ORANGE, transparency: 60 } });
  } else if (variant === 2) {
    slide.addShape(pres.shapes.OVAL, { x: 9.3, y: 4.7, w: 1.3, h: 1.3, fill: { color: "8B4513", transparency: 35 } });
    slide.addShape(pres.shapes.OVAL, { x: -0.2, y: -0.3, w: 0.8, h: 0.8, fill: { color: "D2691E", transparency: 60 } });
  } else if (variant === 3) {
    slide.addShape(pres.shapes.OVAL, { x: 9.0, y: -0.2, w: 1.1, h: 1.1, fill: { color: "D2691E", transparency: 55 } });
    slide.addShape(pres.shapes.OVAL, { x: -0.3, y: 4.6, w: 1.5, h: 1.5, fill: { color: "8B4513", transparency: 40 } });
    slide.addShape(pres.shapes.OVAL, { x: 0.3, y: 4.2, w: 0.6, h: 0.6, fill: { color: ORANGE, transparency: 60 } });
  }
}

// Helper: Nifraim logo badge (top-right)
function addLogoBadge(slide) {
  slide.addText("Nifraim", {
    x: 7.8, y: 0.2, w: 2, h: 0.4,
    fontSize: 18, fontFace: "Arial", bold: true, color: ORANGE,
    align: "right", margin: 0,
  });
}

// Helper: add a card (light blue rect with label)
function addCard(slide, x, y, w, h, label) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: LIGHT_BLUE },
    line: { color: CARD_BORDER, width: 1 }, rectRadius: 0.08,
    shadow: makeShadow(),
  });
  if (label) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.1, y: y - 0.1, w: label.length * 0.08 + 0.3, h: 0.22,
      fill: { color: LABEL_BG }, line: { color: LABEL_BORDER, width: 0.5 },
    });
    slide.addText(label, {
      x: x + 0.1, y: y - 0.12, w: label.length * 0.08 + 0.3, h: 0.22,
      fontSize: 8, fontFace: "Arial", bold: true, color: DARK, align: "center", margin: 0,
    });
  }
}

// Helper: inner white box
function addInnerBox(slide, x, y, w, h, text, opts = {}) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: WHITE },
    line: { color: opts.borderColor || "999999", width: 0.8, dashType: opts.dashed ? "dash" : "solid" },
  });
  slide.addText(text, {
    x, y, w, h,
    fontSize: opts.fontSize || 9, fontFace: "Arial", bold: opts.bold !== false,
    color: opts.textColor || "333333", align: "center", valign: "middle", margin: 0,
  });
}

// =====================================================
// SLIDE 1: WELCOME
// =====================================================
const s1 = pres.addSlide();
s1.background = { color: WHITE };
addDecoCircles(s1, 1);

// Title
s1.addText("Nifraim", {
  x: 0, y: 1.2, w: 10, h: 1,
  fontSize: 52, fontFace: "Arial", bold: true, color: ORANGE,
  align: "center", margin: 0,
});
s1.addText("סוכן AI לסוכני ביטוח", {
  x: 0, y: 2.1, w: 10, h: 0.5,
  fontSize: 22, fontFace: "Arial", bold: true, color: DARK,
  align: "center", margin: 0,
});
s1.addText("ניהול נפרעים, עמלות ופרודוקציה", {
  x: 0, y: 2.6, w: 10, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: GRAY,
  align: "center", margin: 0,
});

// Divider
s1.addShape(pres.shapes.LINE, {
  x: 3.5, y: 3.15, w: 3, h: 0,
  line: { color: ORANGE, width: 1.5, transparency: 50 },
});

s1.addText("מצגת למערכות מידע — חברות ביטוח", {
  x: 0, y: 3.3, w: 10, h: 0.4,
  fontSize: 14, fontFace: "Arial", color: LIGHT_GRAY,
  align: "center", margin: 0,
});

// Company circles
const startX1 = 0.8;
const spacing1 = 0.95;
companies.forEach((c, i) => {
  const cx = startX1 + i * spacing1;
  s1.addShape(pres.shapes.OVAL, {
    x: cx, y: 4.2, w: 0.55, h: 0.55,
    fill: { color: c.color },
  });
  s1.addText(c.name, {
    x: cx - 0.1, y: 4.28, w: 0.75, h: 0.4,
    fontSize: 7, fontFace: "Arial", bold: true,
    color: c.textColor || WHITE, align: "center", margin: 0,
  });
});

// =====================================================
// SLIDE 2: AWS ARCHITECTURE
// =====================================================
const s2 = pres.addSlide();
s2.background = { color: WHITE };

// Decorative circles
s2.addShape(pres.shapes.OVAL, { x: -0.3, y: 4.5, w: 1.3, h: 1.3, fill: { color: "8B4513", transparency: 35 } });
s2.addShape(pres.shapes.OVAL, { x: 0.2, y: 4.2, w: 0.5, h: 0.5, fill: { color: "D2691E", transparency: 55 } });

addLogoBadge(s2);
s2.addText("Nifraim — AWS Cloud Architecture", {
  x: 0.3, y: 0.15, w: 7, h: 0.4,
  fontSize: 18, fontFace: "Arial", bold: true, color: ORANGE, margin: 0,
});

// Users box
s2.addShape(pres.shapes.RECTANGLE, {
  x: 0.2, y: 1.6, w: 1.5, h: 1.2, fill: { color: GREEN_BG },
  line: { color: GREEN_BORDER, width: 1.5 }, shadow: makeShadow(),
});
s2.addShape(pres.shapes.RECTANGLE, {
  x: 0.3, y: 1.52, w: 0.6, h: 0.2,
  fill: { color: LABEL_BG }, line: { color: LABEL_BORDER, width: 0.5 },
});
s2.addText("USERS", {
  x: 0.3, y: 1.5, w: 0.6, h: 0.22,
  fontSize: 7, fontFace: "Arial", bold: true, color: DARK, align: "center", margin: 0,
});
s2.addText("סוכן ביטוח\nHTTPS", {
  x: 0.3, y: 1.9, w: 1.3, h: 0.7,
  fontSize: 10, fontFace: "Arial", bold: true, color: "333333", align: "center", valign: "middle", margin: 0,
});

// Arrow: Users → CloudFront
s2.addShape(pres.shapes.LINE, {
  x: 1.7, y: 2.2, w: 0.8, h: 0,
  line: { color: DARK, width: 3 },
});
s2.addText("TLS 1.3 →", {
  x: 1.7, y: 1.95, w: 0.8, h: 0.2,
  fontSize: 7, fontFace: "Arial", bold: true, color: "e65100", align: "center", margin: 0,
});

// AWS Cloud area
s2.addShape(pres.shapes.RECTANGLE, {
  x: 2.6, y: 0.6, w: 7.2, h: 4.8,
  fill: { color: PEACH }, line: { color: VPC_BORDER, width: 1.5 },
  shadow: makeShadow(),
});
s2.addShape(pres.shapes.RECTANGLE, {
  x: 5.5, y: 0.52, w: 1.1, h: 0.22,
  fill: { color: LABEL_BG }, line: { color: LABEL_BORDER, width: 0.5 },
});
s2.addText("AWS CLOUD", {
  x: 5.5, y: 0.5, w: 1.1, h: 0.22,
  fontSize: 9, fontFace: "Arial", bold: true, color: DARK, align: "center", margin: 0,
});

// CloudFront card
addCard(s2, 2.9, 0.9, 2.2, 0.9, "CLOUDFRONT");
addInnerBox(s2, 3.7, 1.1, 0.55, 0.35, "WAF\nfirewall", { fontSize: 7 });
addInnerBox(s2, 4.35, 1.1, 0.55, 0.35, "S3\nstatic", { fontSize: 7 });

// Arrow: CloudFront → VPC
s2.addShape(pres.shapes.LINE, {
  x: 4.0, y: 1.8, w: 0, h: 0.5,
  line: { color: "4a7c9b", width: 3 },
});

// VPC boundary
s2.addShape(pres.shapes.RECTANGLE, {
  x: 2.8, y: 2.35, w: 6.8, h: 3.0,
  fill: { color: WHITE, transparency: 65 },
  line: { color: VPC_BORDER, width: 1.5, dashType: "dash" },
});
s2.addShape(pres.shapes.RECTANGLE, {
  x: 5.5, y: 2.27, w: 0.5, h: 0.2,
  fill: { color: WHITE }, line: { color: VPC_BORDER, width: 0.5 },
});
s2.addText("VPC", {
  x: 5.5, y: 2.25, w: 0.5, h: 0.2,
  fontSize: 8, fontFace: "Arial", bold: true, color: DARK, align: "center", margin: 0,
});

// ECS Fargate card
addCard(s2, 3.0, 2.6, 2.6, 1.15, "ECS FARGATE");
addInnerBox(s2, 3.6, 2.85, 0.85, 0.42, "FastApi 1", { fontSize: 9 });
addInnerBox(s2, 4.55, 2.85, 0.85, 0.42, "FastApi 2", { fontSize: 9, dashed: true });

// Arrow ECS → DB
s2.addShape(pres.shapes.LINE, {
  x: 4.3, y: 3.75, w: 0, h: 0.35,
  line: { color: DARK, width: 3 },
});

// Database card
addCard(s2, 3.0, 4.15, 2.6, 0.95, "DATABASE");
addInnerBox(s2, 3.6, 4.38, 0.9, 0.4, "postgresSQL", { fontSize: 8 });
addInnerBox(s2, 4.6, 4.38, 0.7, 0.4, "REDIS", { fontSize: 9, borderColor: "ef5350", textColor: "ef5350" });

// Arrows ECS → right cards
s2.addShape(pres.shapes.LINE, {
  x: 5.6, y: 3.1, w: 0.8, h: 0,
  line: { color: DARK, width: 2.5 },
});
s2.addShape(pres.shapes.LINE, {
  x: 5.6, y: 3.3, w: 0.5, h: 0,
  line: { color: DARK, width: 2 },
});
s2.addShape(pres.shapes.LINE, {
  x: 6.1, y: 3.3, w: 0, h: 0.85,
  line: { color: DARK, width: 2 },
});
s2.addShape(pres.shapes.LINE, {
  x: 6.1, y: 4.15, w: 0.3, h: 0,
  line: { color: DARK, width: 2 },
});
s2.addShape(pres.shapes.LINE, {
  x: 5.6, y: 3.5, w: 0.3, h: 0,
  line: { color: DARK, width: 1.5 },
});
s2.addShape(pres.shapes.LINE, {
  x: 5.9, y: 3.5, w: 0, h: 1.45,
  line: { color: DARK, width: 1.5 },
});
s2.addShape(pres.shapes.LINE, {
  x: 5.9, y: 4.95, w: 0.5, h: 0,
  line: { color: DARK, width: 1.5 },
});

// Bedrock card
addCard(s2, 6.4, 2.6, 2.4, 0.9, "BEDROCK");
addInnerBox(s2, 7.1, 2.85, 0.7, 0.38, "Claude AI", { fontSize: 9 });

// Encryption card
addCard(s2, 6.4, 3.65, 2.4, 0.75, "ENCRYPTION");
addInnerBox(s2, 7.0, 3.85, 0.6, 0.28, "KMS", { fontSize: 8 });
addInnerBox(s2, 7.7, 3.85, 0.85, 0.28, "SecretManager", { fontSize: 7 });

// Storage card
addCard(s2, 6.4, 4.55, 2.4, 0.65, "STORAGE");
addInnerBox(s2, 7.0, 4.72, 0.55, 0.28, "S3", { fontSize: 9 });

// =====================================================
// SLIDES 3-5: BULLET CONTENT SLIDES
// =====================================================
function addBulletSlide(title, bullets, bottomContent, variant) {
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  addDecoCircles(slide, variant);
  addLogoBadge(slide);

  // Title
  slide.addText(title, {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Arial", bold: true, color: DARK,
    align: "right", margin: 0,
  });

  // Orange underline
  slide.addShape(pres.shapes.LINE, {
    x: 2.5, y: 0.95, w: 5, h: 0,
    line: { color: ORANGE, width: 2, transparency: 55 },
  });

  // Bullets
  const startY = 1.2;
  const lineH = 0.68;
  bullets.forEach((b, i) => {
    const by = startY + i * lineH;
    // Orange dot
    slide.addShape(pres.shapes.OVAL, {
      x: 9.1, y: by + 0.08, w: 0.14, h: 0.14,
      fill: { color: ORANGE },
    });
    // Bold header
    slide.addText(b.header, {
      x: 0.5, y: by, w: 8.5, h: 0.28,
      fontSize: 15, fontFace: "Arial", bold: true, color: DARK,
      align: "right", margin: 0,
    });
    // Description
    slide.addText(b.desc, {
      x: 0.5, y: by + 0.28, w: 8.5, h: 0.3,
      fontSize: 11, fontFace: "Arial", color: GRAY,
      align: "right", margin: 0,
    });
  });

  if (bottomContent) {
    bottomContent(slide);
  }

  return slide;
}

function addCompanyRow(slide) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.7, w: 9, h: 0.65,
    fill: { color: BEIGE_BG }, line: { color: BEIGE_BORDER, width: 0.8 },
  });
  slide.addText(":חברות נתמכות", {
    x: 8.2, y: 4.72, w: 1.2, h: 0.25,
    fontSize: 8, fontFace: "Arial", bold: true, color: LIGHT_GRAY,
    align: "right", margin: 0,
  });
  const startX = 0.7;
  const sp = 0.85;
  companies.forEach((c, i) => {
    const cx = startX + i * sp;
    slide.addShape(pres.shapes.OVAL, {
      x: cx, y: 4.85, w: 0.42, h: 0.42,
      fill: { color: c.color },
    });
    slide.addText(c.name, {
      x: cx - 0.1, y: 4.9, w: 0.62, h: 0.32,
      fontSize: 6, fontFace: "Arial", bold: true,
      color: c.textColor || WHITE, align: "center", margin: 0,
    });
  });
}

// SLIDE 3: Onboarding
addBulletSlide(
  "הצטרפות וכניסה למערכת",
  [
    { header: "הרשמה מאובטחת", desc: "סוכן ביטוח נרשם עם אימייל וסיסמה — אימות מיידי" },
    { header: "כניסה מוגנת", desc: "אימות JWT מאובטח עם תוקף מוגבל" },
    { header: "הגדרת פורטלים — פרטי גישה לכל חברת ביטוח", desc: "הסוכן מזין שם משתמש וסיסמה לכל פורטל חברה להורדת קבצי פרודוקציה ונפרעים" },
    { header: "אימות OTP", desc: "קבלת קוד חד-פעמי ב-SMS — תמיכה ב-Twilio, העברת שיחה, או הזנה ידנית" },
    { header: "תזמון הורדות אוטומטי", desc: "הגדרת תדירות: ידני / יומי / שבועי / חודשי — המערכת מורידה קבצים בלי התערבות" },
  ],
  addCompanyRow,
  2
);

// SLIDE 4: Upload & Rates
addBulletSlide(
  "העלאת קבצים והגדרת עמלות",
  [
    { header: "העלאת פרודוקציה", desc: "גרירת קובץ אקסל — המערכת מזהה אוטומטית את פורמט החברה ומנתחת את הנתונים" },
    { header: "העלאת נפרעים (עמלות)", desc: "העלאת קבצי עמלות ממספר חברות ביטוח במקביל — תמיכה בכל הפורמטים" },
    { header: "זיהוי אוטומטי של 14+ פורמטים", desc: "אקסלנס, פניקס, מגדל, כלל, מנורה, הראל, אלטשולר, איילון, הכשרה, מור ועוד" },
    { header: "טבלת הסכמי עמלות", desc: "הגדרת אחוזי עמלה לכל חברה ומוצר — חודשי, רבעוני, או שנתי" },
    { header: "חישוב עמלות צפויות אוטומטי", desc: "המערכת מחשבת את העמלה הצפויה לפי ההסכם ומשווה לעמלה שהתקבלה בפועל" },
  ],
  (slide) => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 4.7, w: 9, h: 0.55,
      fill: { color: BEIGE_BG }, line: { color: BEIGE_BORDER, width: 0.8 },
    });
    slide.addText("פורמטים נתמכים:  .xlsx  ·  .xls  ·  .xls (password protected)  ·  Multi-sheet  ·  Hebrew columns auto-mapped", {
      x: 0.7, y: 4.75, w: 8.6, h: 0.4,
      fontSize: 9, fontFace: "Arial", color: "555555", align: "center", margin: 0,
    });
  },
  3
);

// SLIDE 5: Reconciliation & Alerts
addBulletSlide(
  "התאמות, התראות ותהליכים אוטונומיים",
  [
    { header: "השוואת פרודוקציה מול נפרעים", desc: "זיהוי אוטומטי של לקוחות משלמים, לא משלמים, וחסרים — לפי תעודת זהות" },
    { header: "ניתוח פערי עמלות", desc: "חישוב הפרש בין עמלה צפויה (לפי ההסכם) לעמלה שהתקבלה בפועל מהחברה" },
    { header: "התראות חכמות", desc: "זיהוי לקוחות שנעלמו מהנפרעים, שינויי פרמיה חריגים, עמלות שלא שולמו" },
    { header: "תהליכים אוטונומיים", desc: "הורדה אוטומטית מפורטלי חברות ביטוח, עדכון פרודוקציה, ריענון השוואות — ללא התערבות" },
    { header: "בינה מלאכותית — Claude AI", desc: "ניתוח מגמות, זיהוי הזדמנויות, והמלצות פעולה מותאמות לסוכן — מונע על ידי Bedrock" },
  ],
  (slide) => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 1.2, y: 4.7, w: 7.6, h: 0.6,
      fill: { color: BEIGE_BG }, line: { color: BEIGE_BORDER, width: 0.8 },
    });
    slide.addText("המערכת עובדת 24/7 — הסוכן מתעורר לנתונים מעודכנים כל בוקר", {
      x: 1.5, y: 4.72, w: 7, h: 0.3,
      fontSize: 13, fontFace: "Arial", bold: true, color: ORANGE,
      align: "center", margin: 0,
    });
    slide.addText("פרודוקציה · נפרעים · עמלות · התראות · תובנות AI", {
      x: 1.5, y: 5.02, w: 7, h: 0.22,
      fontSize: 9, fontFace: "Arial", color: LIGHT_GRAY,
      align: "center", margin: 0,
    });
  },
  2
);

// Write file
const outPath = path.join(__dirname, "nifraim-presentation.pptx");
pres.writeFile({ fileName: outPath }).then(() => {
  console.log("Created: " + outPath);
}).catch(err => {
  console.error("Error:", err);
});
