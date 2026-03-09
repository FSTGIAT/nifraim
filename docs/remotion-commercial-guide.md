# Nifraim — Remotion Commercial Video Guide (20 Seconds)

A complete creative brief and technical prompt for building a 20-second Remotion video commercial for **Nifraim** (ניפרעים) — an insurance commission management and reconciliation platform.

---

## 1. Project Setup

### Composition Config

```js
import { Composition } from 'remotion';

export const RemotionRoot = () => (
  <Composition
    id="NifraimCommercial"
    component={NifraimCommercial}
    durationInFrames={600}
    fps={30}
    width={1920}
    height={1080}
  />
);
```

### Font

**Heebo** from Google Fonts — the app's primary typeface (Hebrew + Latin).

```js
import { loadFont } from '@remotion/google-fonts/Heebo';
const { fontFamily } = loadFont();
```

Weights used: `400` (body), `600` (emphasis), `700` (headings), `800` (hero numbers).

### Global Styles

```js
const rootStyle = {
  fontFamily: "'Heebo', sans-serif",
  direction: 'rtl',
  backgroundColor: '#181818',
};
```

---

## 2. Brand Assets

### Logo SVG (Stacked Layers Icon)

From `frontend/src/components/workspace/WorkspaceHeader.vue`:

```svg
<svg width="48" height="48" viewBox="0 0 24 24" fill="none"
     stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
  <path d="M12 2L2 7l10 5 10-5-10-5z"/>
  <path d="M2 17l10 5 10-5"/>
  <path d="M2 12l10 5 10-5"/>
</svg>
```

### Brand Name

`Nifraim` — rendered in Heebo 700, white on dark / dark on light.

### Brand Gradient

From `frontend/src/views/LoginView.vue`:

```css
linear-gradient(135deg, #E65100 0%, #F57C00 40%, #FF9800 70%, #FFB74D 100%)
```

### Button Gradient

```css
linear-gradient(135deg, #F57C00, #FF9800)
```

---

## 3. Color Palette

All values sourced from `frontend/src/App.vue` `:root` CSS variables.

### Core Brand Colors

| Token             | Hex       | Usage                          |
|-------------------|-----------|--------------------------------|
| `--primary`       | `#F57C00` | Main brand orange              |
| `--primary-deep`  | `#E65100` | Dark orange, gradient start    |
| `--primary-light` | `#FFF3E0` | Light orange background        |
| Secondary         | `#FF9800` | Gradient end, secondary orange |
| Warm highlight    | `#FFB74D` | Gradient tail                  |

### Status & Accent Colors

| Token              | Hex       | Usage                          |
|--------------------|-----------|--------------------------------|
| `--green`          | `#2E844A` | Success, matched records       |
| `--green-deep`     | `#1B5E20` | Deep green                     |
| `--green-light`    | `#EBF7EE` | Green background               |
| `--amber`          | `#E8720A` | Warning, production-only       |
| `--amber-light`    | `#FFF3E0` | Amber background               |
| `--red`            | `#EA001E` | Error, alert                   |
| `--red-deep`       | `#C23934` | Dark red                       |
| `--accent-violet`  | `#7F56D9` | Info, commission-only          |
| `--accent-rose`    | `#E3066A` | Rose accent                    |
| Teal               | `#06A59A` | Teal accent                    |

### Neutrals

| Token              | Hex       | Usage               |
|--------------------|-----------|----------------------|
| `--text`           | `#181818` | Primary text / dark bg |
| `--text-secondary` | `#3E3E3C` | Secondary text       |
| `--text-muted`     | `#706E6B` | Muted text           |
| `--bg`             | `#F3F3F3` | App background       |
| `--card-bg`        | `#FFFFFF` | Card surfaces        |
| `--border`         | `#DDDBDA` | Default borders      |

### Chart Colors (for data visualization scenes)

```js
const CHART_COLORS = [
  '#F57C00', // Orange (primary)
  '#2E844A', // Green
  '#7F56D9', // Violet
  '#06A59A', // Teal
  '#E8720A', // Amber
  '#C23934', // Red
  '#38BDF8', // Light Blue
  '#F472B6', // Pink
  '#6366F1', // Indigo
];
```

### Design Tokens

```js
const TOKENS = {
  radiusSm: '8px',
  radiusMd: '12px',
  radiusLg: '16px',
  radiusXl: '24px',
  shadowSm: '0 1px 3px rgba(0, 0, 0, 0.08)',
  shadowMd: '0 2px 8px rgba(0, 0, 0, 0.06)',
  shadowLg: '0 4px 14px rgba(0, 0, 0, 0.1)',
  shadowGlow: '0 0 0 3px rgba(245, 124, 0, 0.15)',
};
```

---

## 4. Scene Breakdown

### Component Tree

```jsx
<AbsoluteFill style={rootStyle}>
  <Sequence from={0}   durationInFrames={75}>  <BrandIntro />                </Sequence>
  <Sequence from={75}  durationInFrames={75}>  <ProblemScene />              </Sequence>
  <Sequence from={150} durationInFrames={90}>  <UploadInsightsScene />       </Sequence>
  <Sequence from={240} durationInFrames={90}>  <FileComparisonScene />       </Sequence>
  <Sequence from={330} durationInFrames={90}>  <CommissionDashboardScene />  </Sequence>
  <Sequence from={420} durationInFrames={90}>  <CustomerPortalScene />       </Sequence>
  <Sequence from={510} durationInFrames={90}>  <MetricsCTAOutro />           </Sequence>
  <Audio src={staticFile('bg-music.mp3')} volume={0.6} />
</AbsoluteFill>
```

**Scene flow narrative:**
1. **Brand Intro** — Who we are
2. **The Problem** — Messy Excel chaos
3. **Upload & Insights** — Drop a file, get full production analytics (KPIs + charts)
4. **File Comparison** — Compare old vs new production: new/removed/changed clients
5. **Commission Dashboard** — Compare production vs commissions per company, find unpaid
6. **Customer Portal** — Every customer gets their own personal dashboard
7. **Metrics + CTA** — Impact numbers + call to action

---

### Scene 1 — Brand Intro (0s–2.5s)

| Property | Value |
|----------|-------|
| **Timing** | Frames 0–74 (0s–2.5s) |
| **Background** | Solid `#181818` (dark) |

**Visual Description:**

1. **Frame 0–30:** Dark screen. The stacked-layers SVG logo scales up from `0.3` to `1.0` at center using `spring()`. Stroke color: white.
2. **Frame 15–40:** "Nifraim" text fades in below the logo, Heebo 700, `48px`, white.
3. **Frame 25–55:** Tagline `ניהול עמלות. חכם.` fades in below, Heebo 600, `28px`, `#FFB74D` (warm gold).
4. **Frame 35–74:** An orange gradient line (`#E65100 → #FF9800`) sweeps from right to left beneath the text, `4px` tall.

**Animation Code Hints:**

```js
const frame = useCurrentFrame();
const logoScale = spring({ fps: 30, frame, config: { damping: 12, mass: 0.5 } });
const textOpacity = interpolate(frame, [15, 35], [0, 1], { extrapolateRight: 'clamp' });
const taglineOpacity = interpolate(frame, [25, 45], [0, 1], { extrapolateRight: 'clamp' });
const lineWidth = interpolate(frame, [35, 70], [0, 400], { extrapolateRight: 'clamp' });
```

---

### Scene 2 — The Problem (2.5s–5s)

| Property | Value |
|----------|-------|
| **Timing** | Frames 75–149 (2.5s–5s) |
| **Background** | Dark `#181818` with subtle noise texture |

**Visual Description:**

1. **Frame 0–20:** Simulated Excel spreadsheet cards slide in from various angles (top-right, bottom-left, right). Each card is a white rounded rectangle with a grid of Hebrew column headers from the actual app:
   - `שם לקוח` (Client Name)
   - `מספר זהות` (ID Number)
   - `פרמיה` (Premium)
   - `חברה מנהלת` (Managing Company)
   - `סוג מוצר` (Product Type)
   - `יתרת צבירה` (Accumulation Balance)
2. **Frame 15–30:** Cards overlap messily, slight rotation (`-5°` to `8°`), creating visual chaos.
3. **Frame 25–45:** A red warning icon scales up at center with a pulsing glow (`#EA001E` at 30% opacity).
4. **Frame 30–74:** Bold text overlays: `?מנהלים עמלות בידיים` — Heebo 700, `42px`, white. Fades in from below.

**Animation:**

```js
cards.forEach((card, i) => {
  const delay = i * 6;
  const progress = spring({ fps: 30, frame: frame - delay, config: { damping: 14 } });
});
const pulse = Math.sin(frame * 0.15) * 0.3 + 0.7;
```

---

### Scene 3 — Upload & Insights (5s–8s)

> **Reference screenshot:** Production tab — KPI strip + bar charts

| Property | Value |
|----------|-------|
| **Timing** | Frames 150–239 (5s–8s) |
| **Background** | Light `#F3F3F3` — mimics the actual app background |

**Visual Description:**

This scene shows the **production upload + insights dashboard** as seen in the real app.

1. **Frame 0–15:** Scene transitions from dark to light bg. A file icon drops into a dashed-border upload zone with spring bounce.
2. **Frame 10–25:** The upload zone shrinks to the top and the **KPI strip** materializes below it — 6 cards in a row (matching the actual app):

   | KPI | Value | Icon Color |
   |-----|-------|------------|
   | `מוצרים` (Products) | `2,157` | `#F57C00` (orange hexagon) |
   | `לקוחות` (Customers) | `674` | `#F57C00` (orange people) |
   | `סה"כ פרמיה` (Total Premium) | `₪159K` | `#7F56D9` (violet $) |
   | `סה"כ צבירה` (Total Accumulation) | `₪303.6M` | `#F57C00` (orange file) |
   | `חברות` (Companies) | `16` | `#F57C00` (orange building) |
   | `מוצרים פעילים` (Active Products) | `74%` | `#2E844A` (green chart) |

3. **Frame 25–50:** Below the KPIs, two chart cards fade in side by side:
   - **Left:** `התפלגות לפי סוג מוצר` (Distribution by Product Type) — horizontal blue bar chart showing: `קופת גמל לתגמולים ופיצויים` (~500), `קרן השתלמות` (~380), `ביטוח בריאות` (~370), etc.
   - **Right:** `התפלגות לפי חברה` (Distribution by Company) — horizontal colored bar chart showing companies: `מור גמל ופנסיה` (₪91.2M, green), `הפניקס אקסלנס` (₪63.7M, orange), etc.

4. **Frame 45–74:** A third chart card slides up: `לקוחות לפי פרמיה` (Customers by Premium) — horizontal teal/green bar chart with customer names and premium amounts (₪0 to ₪3,500). Toggle buttons `פרמיה | צבירה` visible at top-left.

**Animation:**

```js
const fileDrop = spring({ fps: 30, frame, config: { damping: 10, mass: 0.8 } });
// KPI cards: staggered fadeInUp, 4-frame delay each
// Bar chart bars: grow from 0 width using interpolate(), staggered by 2 frames per bar
// Numbers count up in KPI cards
```

---

### Scene 4 — File Comparison (8s–11s)

> **Reference screenshot:** השוואת קבצים tab — donut with 721 customers, company breakdown donuts

| Property | Value |
|----------|-------|
| **Timing** | Frames 240–329 (8s–11s) |
| **Background** | Light `#F3F3F3` |

**Visual Description:**

This scene recreates the **file comparison results** page from the actual app.

1. **Frame 0–10:** Title `תוצאות השוואה` (Comparison Results) fades in top-right. Below it, 4 status pills appear:
   - `41 חדשים` (New) — green bg
   - `47 הוסרו` (Removed) — red/amber bg
   - `510 שונו` (Changed) — orange bg
   - `123 ללא שינוי` (Unchanged) — gray bg

2. **Frame 5–35:** The **main donut chart** `התפלגות שינויים` (Change Distribution) animates in center:
   - **71%** — Changed (510) — `#F57C00` (orange, dominant segment)
   - **17%** — Unchanged (123) — `#B0B0B0` (gray)
   - **7%** — Removed (47) — `#EA001E` (red)
   - **6%** — New (41) — `#2E844A` (green)
   - Center text: `סה"כ לקוחות` + `721` counts up, Heebo 800

3. **Frame 30–60:** Below the main donut, two smaller company breakdown donuts slide up:
   - **Right:** `חדשים לפי חברה` (New by Company) — `41` center, showing `מגדל חברה לביטוח` (78%, blue), `מור גמל ופנסיה` (15%, orange), etc.
   - **Left:** `הוסרו לפי חברה` (Removed by Company) — `47` center, showing `מנורה מבטחים` (87%, blue), `הפניקס אקסלנס` (6%, multicolor)

4. **Frame 50–89:** Legend items fade in below each donut with colored dots and company names.

**Animation:**

```js
// Main donut: segments grow from 0° with spring()
const donutProgress = spring({ fps: 30, frame: frame - 5, config: { damping: 20, mass: 1 } });
const changedAngle = donutProgress * 255.6; // 71% of 360°
// Center number counts up: 0 → 721
const total = Math.round(interpolate(frame, [10, 35], [0, 721], { extrapolateRight: 'clamp' }));
// Mini donuts: spring with 25-frame delay
```

---

### Scene 5 — Commission Comparison Dashboard (11s–14s)

> **Reference screenshot:** השוואת נפרעים — per-company dashboard (מור), donut + KPIs + bar chart

| Property | Value |
|----------|-------|
| **Timing** | Frames 330–419 (11s–14s) |
| **Background** | Light `#F3F3F3` |

**Visual Description:**

This scene shows the **per-company commission comparison** — the core value proposition.

1. **Frame 0–10:** Company banner appears at top: `מור` with orange left border + `גמל והשתלמות` category badge (green). Beneath it: `התפלגות לקוחות` title.

2. **Frame 5–30:** The **customer distribution donut** animates center:
   - **90%** — `נמצא בנפרעים` (Found in commissions, 165) — `#2E844A` (green, dominant)
   - **5%** — `רק בנפרעים` (Commission only, 10) — `#7F56D9` (violet)
   - **1%** — `לא שולם` (Unpaid, 1) — `#E8720A` (amber)
   - Center text: `סה"כ` + `184` counts up

3. **Frame 20–45:** Five KPI cards slide in from bottom, matching actual app layout:

   | KPI | Value | Icon |
   |-----|-------|------|
   | `לקוחות בנפרעים` (Customers) | `175` | `#F57C00` people icon |
   | `לא שולם` (Unpaid) | `1` | `#EA001E` warning icon |
   | `סה"כ חוב לא משולם` (Total unpaid debt) | `₪30` | `#E8720A` alert triangle |
   | `סה"כ עמלה` (Total commission) | `₪16,659` | `#7F56D9` dollar icon |
   | `סה"כ יתרה` (Total balance) | `₪90,402,488` | `#2E844A` wallet icon |

4. **Frame 35–74:** The **customers by accumulation bar chart** `לקוחות לפי צבירה` fades in at bottom — colorful vertical bars (orange `₪6.4M`, green `₪3.9M`, yellow `₪3.3M`, etc.) with customer names below, showing top 15 customers.

5. **Frame 40–74:** A red alert banner animates in: `1 לקוחות ללא תשלום עמלה — הפסד משוער ₪30` (1 customer without commission payment — estimated loss ₪30) with action buttons `הצג | שלח מייל | Excel`.

**Animation:**

```js
// Donut segments grow from 0°
// 90% green = 324° sweep — visually impressive for "most are matched"
const greenAngle = donutProgress * 324;
// Bar chart: bars grow from 0 height, staggered 2 frames apart
// Alert banner: slides down from top with spring
```

---

### Scene 6 — Customer Portal (14s–17s)

> **Reference screenshot:** Customer portal — personal dashboard for יצחק מרדכי בלומנטל

| Property | Value |
|----------|-------|
| **Timing** | Frames 420–509 (14s–17s) |
| **Background** | Light `#F3F3F3` |

**Visual Description:**

This scene highlights that **every customer gets their own personal dashboard** — the portal view.

1. **Frame 0–10:** The Nifraim logo + brand name appears centered at top (matching portal header: orange stacked-layers icon + "Nifraim" in dark text).

2. **Frame 5–20:** Customer greeting animates in: `שלום, יצחק מרדכי בלומנטל` (Hello, Yitzhak Mordechai Blumenthal), Heebo 700, `28px`. Below: `ת.ז: 56004914` + `דצמבר 2025` green badge.

3. **Frame 12–35:** Four KPI cards slide in from right (RTL), staggered:

   | KPI | Value | Icon Color |
   |-----|-------|------------|
   | `מוצרים` (Products) | `31` | `#F57C00` (orange hexagon) |
   | `פרמיה חודשית` (Monthly Premium) | `₪701` | `#7F56D9` (violet $) |
   | `צבירה כוללת` (Total Accumulation) | `₪9,731,021` | `#2E844A` (green chart) |
   | `חברות ביטוח` (Insurance Companies) | `5` | `#F57C00` (orange building) |

4. **Frame 25–50:** Two side-by-side panels materialize:
   - **Left:** `המוצרים שלך` (Your Products, `31`) — stacked company cards:
     - `מור` — 11 products, `₪3.9M` accumulation, `11 פעיל` (green)
     - `הפניקס אקסלנס` — 16 products, `₪3.5M`, `7 פעיל` / `9 לא פעיל` (red)
     - `הראל` — 2 products, `₪2.2M`, `1 פעיל`
     - `כלל` — 1 product, `₪141K`, `1 פעיל`
   - **Right:** `התפלגות לפי חברה` (Distribution by Company) — donut chart:
     - `מור` 40% (orange), `הפניקס אקסלנס` 36% (violet), `הראל` 22% (green), `כלל` 1% (pink)
     - Center: `סה"כ צבירה ₪9.7M`

5. **Frame 45–89:** Text overlay fades in at bottom: `לכל לקוח — דשבורד אישי` (Every customer — a personal dashboard), Heebo 700, `24px`, `#F57C00`.

**Animation:**

```js
// KPI cards: staggered spring from right (RTL entrance)
// Product cards: staggered fadeInUp, 6-frame delay each
// Portal donut: segments grow like other donuts
// Company donut: orange 40% = 144°, violet 36% = 129.6°, green 22% = 79.2°
```

---

### Scene 7 — Impact Metrics + CTA (17s–20s)

| Property | Value |
|----------|-------|
| **Timing** | Frames 510–599 (17s–20s) |
| **Background** | Brand gradient: `linear-gradient(135deg, #E65100 0%, #F57C00 40%, #FF9800 70%, #FFB74D 100%)` |

**Visual Description:**

**Phase 1 — Metrics (frames 0–45):**

Four metric cards fly in over the gradient background, white text:

| Card | Number | Hebrew Label | Accent |
|------|--------|-------------|--------|
| 1 | `95%` | `חיסכון בזמן` (Time savings) | White number, large |
| 2 | `7+` | `פורמטים נתמכים` (Formats supported) | White number |
| 3 | `1,000+` | `קבצים עובדו` (Files processed) | White number |
| 4 | `50+` | `חברות ביטוח` (Insurance companies) | White number |

Cards: semi-transparent white background (`rgba(255,255,255,0.15)`), `border-radius: 16px`, `backdrop-filter: blur(10px)`. Numbers count up rapidly.

**Phase 2 — CTA (frames 30–89):**

1. **Frame 30–45:** Metric cards scale down and fade. Logo + "Nifraim" scales in at center, white.
2. **Frame 40–55:** Hero subtitle: `העלו קבצים, השוו נתונים, גלו פערים — תוך שניות`, white, Heebo 400, `22px`.
3. **Frame 45–65:** CTA button slides up — white bg, `border-radius: 12px`, text `התחילו עכשיו` in `#E65100`, Heebo 700. Gentle pulse animation.
4. **Frame 55–89:** URL `nifraim.co.il` below button, white, `opacity: 0.8`.

**Animation:**

```js
// Metrics: spring in from corners, count up numbers
// CTA: logo spring scale, button spring translateY, pulse = 1 + sin(frame * 0.2) * 0.015
const logoScale = spring({ fps: 30, frame: frame - 30, config: { damping: 14 } });
const btnY = spring({ fps: 30, frame: frame - 45, config: { damping: 12 } });
```

---

## 5. Animation Toolkit Reference

### Spring Presets

```js
// Snappy UI elements (icons, checkmarks, small cards)
const SNAPPY = { fps: 30, damping: 12, mass: 0.5 };

// Smooth large elements (charts, file cards, hero text)
const SMOOTH = { fps: 30, damping: 20, mass: 1 };

// Bouncy (file drop, button entrance)
const BOUNCY = { fps: 30, damping: 10, mass: 0.8 };
```

### Common Patterns

```js
// Fade in
const opacity = interpolate(frame, [startFrame, startFrame + 20], [0, 1], {
  extrapolateRight: 'clamp',
});

// Slide up
const translateY = interpolate(frame, [startFrame, startFrame + 25], [40, 0], {
  extrapolateRight: 'clamp',
});

// Count-up number
const count = Math.round(
  interpolate(frame, [startFrame, startFrame + 30], [0, targetNumber], {
    extrapolateRight: 'clamp',
  })
);

// RTL numbers (prevents Hebrew text reordering digits)
<span style={{ direction: 'ltr', unicodeBidi: 'embed' }}>{count}</span>
```

### Scene Transitions

Use overlapping `Sequence` components with 5-frame crossfade:

```js
// In each scene component, add entry/exit fades
const entryOpacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: 'clamp' });
const exitOpacity = interpolate(frame, [85, 89], [1, 0], { extrapolateRight: 'clamp' });
const opacity = Math.min(entryOpacity, exitOpacity);
```

---

## 6. Full Hebrew Text Reference

All Hebrew strings used across scenes, consolidated for easy copy-paste:

**Scene 1 — Brand Intro:**
| Hebrew Text | Translation | Style |
|------------|-------------|-------|
| `ניהול עמלות. חכם.` | Commission Management. Smart. | Heebo 600, 28px, `#FFB74D` |

**Scene 2 — The Problem:**
| Hebrew Text | Translation | Style |
|------------|-------------|-------|
| `?מנהלים עמלות בידיים` | Managing commissions manually? | Heebo 700, 42px, white |

**Scene 3 — Upload & Insights (KPI labels from actual app):**
| Hebrew Text | Translation | Style |
|------------|-------------|-------|
| `מוצרים` | Products | KPI label |
| `לקוחות` | Customers | KPI label |
| `סה"כ פרמיה` | Total Premium | KPI label |
| `סה"כ צבירה` | Total Accumulation | KPI label |
| `חברות` | Companies | KPI label |
| `מוצרים פעילים` | Active Products | KPI label |
| `התפלגות לפי סוג מוצר` | Distribution by Product Type | Chart title |
| `התפלגות לפי חברה` | Distribution by Company | Chart title |
| `לקוחות לפי פרמיה` | Customers by Premium | Chart title |
| `פרמיה` / `צבירה` | Premium / Accumulation | Toggle labels |

**Scene 4 — File Comparison (from actual comparison screen):**
| Hebrew Text | Translation | Style |
|------------|-------------|-------|
| `תוצאות השוואה` | Comparison Results | Heebo 700, title |
| `חדשים` | New | Green pill |
| `הוסרו` | Removed | Red pill |
| `שונו` | Changed | Orange pill |
| `ללא שינוי` | Unchanged | Gray pill |
| `התפלגות שינויים` | Change Distribution | Donut title |
| `סה"כ לקוחות` | Total Customers | Donut center label |
| `חדשים לפי חברה` | New by Company | Mini donut title |
| `הוסרו לפי חברה` | Removed by Company | Mini donut title |

**Scene 5 — Commission Dashboard (from actual per-company view):**
| Hebrew Text | Translation | Style |
|------------|-------------|-------|
| `התפלגות לקוחות` | Customer Distribution | Donut title |
| `נמצא בנפרעים` | Found in Commissions | Donut legend |
| `רק בנפרעים` | Commission Only | Donut legend |
| `לא שולם` | Unpaid | Donut legend, KPI |
| `לקוחות בנפרעים` | Customers in Commissions | KPI label |
| `סה"כ חוב לא משולם` | Total Unpaid Debt | KPI label |
| `סה"כ עמלה` | Total Commission | KPI label |
| `סה"כ יתרה` | Total Balance | KPI label |
| `לקוחות לפי צבירה` | Customers by Accumulation | Bar chart title |
| `לקוחות ללא תשלום עמלה` | Customers Without Commission | Alert text |

**Scene 6 — Customer Portal (from actual portal view):**
| Hebrew Text | Translation | Style |
|------------|-------------|-------|
| `שלום, יצחק מרדכי בלומנטל` | Hello, Yitzhak Mordechai Blumenthal | Heebo 700, greeting |
| `מוצרים` | Products | KPI label |
| `פרמיה חודשית` | Monthly Premium | KPI label |
| `צבירה כוללת` | Total Accumulation | KPI label |
| `חברות ביטוח` | Insurance Companies | KPI label |
| `המוצרים שלך` | Your Products | Section title |
| `התפלגות לפי חברה` | Distribution by Company | Donut title |
| `לכל לקוח — דשבורד אישי` | Every Customer — Personal Dashboard | Heebo 700, `#F57C00` |
| `פעיל` / `לא פעיל` | Active / Inactive | Product status badges |

**Scene 7 — Metrics + CTA:**
| Hebrew Text | Translation | Style |
|------------|-------------|-------|
| `חיסכון בזמן` | Time Savings | Metric label, white |
| `פורמטים נתמכים` | Supported Formats | Metric label, white |
| `קבצים עובדו` | Files Processed | Metric label, white |
| `חברות ביטוח` | Insurance Companies | Metric label, white |
| `העלו קבצים, השוו נתונים, גלו פערים — תוך שניות` | Upload files, compare data, discover gaps — in seconds | Heebo 400, 22px, white |
| `התחילו עכשיו` | Start Now | Heebo 700, 20px, `#E65100` |

### Mock Excel Column Headers (Scene 2)

From `backend/app/utils/hebrew_mappings.py`:

| Hebrew | English | DB Field |
|--------|---------|----------|
| `שם לקוח` | Client Name | `full_name` |
| `מספר זהות` | ID Number | `id_number` |
| `פרמיה` | Premium | `total_premium` |
| `חברה מנהלת` | Managing Company | `company` |
| `סוג מוצר` | Product Type | `product_type` |
| `יתרת צבירה` | Accumulation Balance | `accumulation` |
| `עמלת סוכן` | Agent Commission | `agent_commission` |
| `סטטוס מוצר` | Product Status | `product_status` |

---

## 7. Audio & Music

| Aspect | Recommendation |
|--------|---------------|
| **Mood** | Modern, clean SaaS promo — upbeat but professional. Confident, not aggressive. |
| **Tempo** | ~120 BPM. Builds energy through scenes 2–5, resolves at CTA. |
| **Instruments** | Clean synth pads, subtle electronic percussion, piano accents. |
| **SFX — Scene 1** | Soft synth tone on logo reveal |
| **SFX — Scene 2** | Paper shuffle / slide sounds for Excel cards |
| **SFX — Scene 3** | Soft "drop" on file landing, gentle "ding" per checkmark |
| **SFX — Scene 4** | Subtle "whoosh" for connection lines drawing |
| **SFX — Scene 5** | Soft rising tone as numbers count up |
| **SFX — Scene 7** | Resolving chord, confident ending |
| **Sources** | Royalty-free: Artlist, Epidemic Sound, or AI-generated via Suno/Udio |

---

## 8. Rendering & Export

### Primary Render

```bash
npx remotion render NifraimCommercial out/nifraim-commercial.mp4 \
  --codec h264 \
  --crf 18 \
  --pixel-format yuv420p
```

### Social Media Crops

| Platform | Aspect | Resolution | Notes |
|----------|--------|------------|-------|
| YouTube / LinkedIn | 16:9 | 1920×1080 | Primary render |
| Instagram Feed | 1:1 | 1080×1080 | Crop center, adjust text positioning |
| Instagram Stories / Reels | 9:16 | 1080×1920 | Vertical layout, stack elements |

For alternate crops, create separate Compositions with adjusted `width`/`height` and repositioned elements.

---

## 9. File Structure (Suggested)

```
remotion-commercial/
├── src/
│   ├── Root.tsx                        # RemotionRoot with Composition
│   ├── NifraimCommercial.tsx           # Main composition (scene sequencing)
│   ├── scenes/
│   │   ├── BrandIntro.tsx              # Scene 1: Logo + tagline
│   │   ├── ProblemScene.tsx            # Scene 2: Messy Excel chaos
│   │   ├── UploadInsightsScene.tsx     # Scene 3: Upload + KPI strip + charts
│   │   ├── FileComparisonScene.tsx     # Scene 4: Old vs new production diff
│   │   ├── CommissionDashboardScene.tsx # Scene 5: Per-company commission view
│   │   ├── CustomerPortalScene.tsx     # Scene 6: Personal customer dashboard
│   │   └── MetricsCTAOutro.tsx         # Scene 7: Impact numbers + CTA
│   ├── components/
│   │   ├── NifraimLogo.tsx             # Reusable logo SVG (3 stacked layers)
│   │   ├── DonutChart.tsx              # Animated donut (used in scenes 4, 5, 6)
│   │   ├── KPICard.tsx                 # Metric card with icon
│   │   ├── KPIStrip.tsx                # Horizontal KPI strip (scenes 3, 6)
│   │   ├── BarChart.tsx                # Horizontal bar chart (scenes 3, 5)
│   │   ├── StatusPill.tsx              # Colored status pills (scene 4)
│   │   ├── CompanyCard.tsx             # Product company card (scene 6)
│   │   ├── ExcelCard.tsx               # Mock spreadsheet (scene 2)
│   │   └── CountUp.tsx                 # Animated number counter
│   └── constants/
│       ├── colors.ts                   # Full palette from this guide
│       ├── tokens.ts                   # Radii, shadows, fonts
│       └── mockData.ts                 # Real numbers from screenshots
├── public/
│   └── bg-music.mp3
├── package.json
└── remotion.config.ts
```
