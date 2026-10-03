"""Public legal pages (no auth). Served at the site root so they have stable,
shareable URLs — Google Play requires a publicly reachable privacy-policy URL for
the Nifraim app, and it must honestly disclose the SMS reading + forwarding.

Registered with NO prefix in main.py and BEFORE the SPA catch-all, so `/privacy`
resolves to this route rather than the Vue index.html.

`/privacy` is ONE canonical policy covering two products, in two parts:
  part א — the Nifraim web platform (what the agent uploads about their clients)
  part ב — the Android SMS forwarder app (SMS reading + OTP forwarding)

Keep it static HTML, not a Vue route: this exact URL is registered in the Play
Console (`android/play-store/LISTING.md`), and a JS-rendered SPA can read as an
empty page to Google's reviewers. Part ב's disclosures are what Play approved —
edit them only to make them MORE accurate, never to soften them.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_PRIVACY_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>מדיניות פרטיות — Nifraim</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700;800;900&display=swap">
  <style>
    /* the site's look (2026-10-03): white, graphite headings, cobalt accents, Heebo. No orange. */
    :root { --graphite: #2A2E35; --ink: #181818; --blue: #2F73C4; --blue-ink: #245C9E;
            --muted: #5B6470; --line: #E6E8EC; --wash: #EEF4FB; }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body { margin: 0; background: #FFFFFF; color: var(--graphite);
           font-family: 'Heebo', system-ui, Arial, sans-serif; line-height: 1.75; font-size: 16px; }
    .site-bar { position: sticky; top: 0; z-index: 10; display: flex; align-items: center;
                justify-content: space-between; gap: 12px; padding: 12px clamp(16px, 4vw, 40px);
                background: rgba(255, 255, 255, 0.82); backdrop-filter: blur(16px);
                border-bottom: 1px solid var(--line); }
    .brand { font-weight: 900; font-size: 20px; letter-spacing: -0.03em; color: var(--graphite);
             text-decoration: none; direction: ltr; }
    .brand span { color: var(--blue); }
    .tabs { display: flex; gap: 2px; padding: 4px; border-radius: 999px; background: rgba(24, 24, 24, 0.05); }
    .tabs a { direction: ltr; padding: 7px 15px; border-radius: 999px; font-size: 14px; font-weight: 600;
              color: var(--ink); text-decoration: none; white-space: nowrap; transition: color .3s ease; }
    .tabs a:hover { color: var(--tc); background: #FFFFFF; }
    @media (max-width: 760px) { .tabs { display: none; } }
    .back { font-size: 14px; font-weight: 700; color: var(--ink); text-decoration: none;
            padding: 8px 16px; border: 1px solid rgba(24, 24, 24, 0.16); border-radius: 10px; }
    .back:hover { background: rgba(24, 24, 24, 0.05); }
    main { max-width: 820px; margin: 0 auto; padding: 56px 20px 80px; }
    h1 { margin: 0 0 6px; font-weight: 900; font-size: clamp(34px, 5vw, 52px); line-height: 1.05;
         letter-spacing: -0.035em; color: var(--graphite); }
    h2 { margin: 34px 0 8px; font-weight: 800; font-size: 21px; letter-spacing: -0.01em; color: var(--graphite); }
    .updated { color: var(--muted); font-size: 14px; margin: 0 0 28px; }
    p, li { color: #3A4048; }
    ul { padding-inline-start: 22px; }
    li { margin-bottom: 6px; }
    li::marker { color: var(--blue); }
    strong { color: var(--graphite); }
    code { background: #F3F4F6; padding: 1px 6px; border-radius: 6px; direction: ltr; display: inline-block;
           font-size: 0.92em; }
    a { color: var(--blue-ink); }
    .toc { display: flex; flex-wrap: wrap; gap: 8px; font-size: 14px; margin: 18px 0 8px; }
    .toc a { text-decoration: none; font-weight: 700; color: var(--graphite); padding: 8px 14px;
             border-radius: 999px; background: #F3F4F6; }
    .toc a:hover { background: var(--wash); color: var(--blue-ink); }
    .part { margin-top: 40px; padding: 8px 28px 24px; border: 1px solid var(--line); border-radius: 22px;
            box-shadow: 0 10px 30px rgba(24, 24, 24, 0.05); scroll-margin-top: 80px; }
    .part-label { display: inline-block; font-size: 12px; font-weight: 800; letter-spacing: .04em;
                  color: var(--blue-ink); background: var(--wash); padding: 4px 12px; border-radius: 999px;
                  margin: 18px 0 6px; }
    .part h1 { margin-top: 4px; }
    .part h2:first-of-type { margin-top: 18px; }
    .lead { background: var(--wash); border-inline-start: 4px solid var(--blue);
            border-radius: 0 12px 12px 0; padding: 14px 18px; margin: 18px 0; color: var(--graphite); }
    .never { background: #FFFFFF; border: 1px solid #D6E3F3; border-radius: 14px;
             padding: 18px 22px 6px; margin: 18px 0; }
    .never li { margin-bottom: 8px; }
    .en { direction: ltr; text-align: left; border-top: 1px solid var(--line); margin-top: 48px; padding-top: 24px; }
    @media (max-width: 600px) { .part { padding: 4px 18px 18px; } main { padding-top: 36px; } }
  </style>
</head>
<body>
  <header class="site-bar">
    <a class="brand" href="/">Nifraim<span>.com</span></a>
    <nav class="tabs" aria-label="ניווט">
      <a href="/#agent" style="--tc:#0A6664">Nifra Agent</a>
      <a href="/#call" style="--tc:#A63A86">Nifra Calls</a>
      <a href="/#report" style="--tc:#2E2A8C">Nifra Report</a>
    </nav>
    <a class="back" href="/">חזרה לאתר</a>
  </header>
  <main>
  <h1>מדיניות פרטיות — Nifraim</h1>
  <p class="updated">עודכן לאחרונה: אוקטובר 2026</p>

  <p>
    מסמך זה מכסה שני מוצרים נפרדים תחת השם Nifraim, ומסביר לגבי כל אחד מהם איזה מידע
    נאסף, למה הוא משמש — ובעיקר, למה הוא <strong>לא</strong> משמש.
  </p>
  <p class="toc">
    <a href="#platform">חלק א׳ — מערכת Nifraim (האתר)</a>
    <a href="#app">חלק ב׳ — אפליקציית ה-SMS לאנדרואיד</a>
  </p>

  <!-- ══════════ PART A — the web platform ══════════ -->
  <div class="part" id="platform">
    <span class="part-label">חלק א׳</span>
    <h1 style="font-size:22px">מערכת Nifraim — האתר</h1>

    <p class="lead">
      המערכת קוראת קבצי עמלות ופרודוקציה של הסוכן — קבצים שמכילים מידע על לקוחותיו.
      המידע הזה איננו שלנו. הוא של הסוכן ושל לקוחותיו, ואנחנו מתייחסים אליו כפיקדון.
    </p>

    <h2>איזה מידע אנחנו אוספים</h2>
    <p><strong>על הסוכן — המשתמש שלנו:</strong></p>
    <ul>
      <li>כתובת דוא"ל ושם, שנמסרים בעת ההרשמה.</li>
      <li>סיסמה, הנשמרת אך ורק כגיבוב (hash) חד-כיווני — אין לנו דרך לשחזר אותה.</li>
      <li>פרטי התחברות לפורטלים של חברות הביטוח, אם הסוכן בחר להפעיל הורדה אוטומטית.</li>
      <li>נתוני שימוש טכניים בסיסיים הדרושים לתפעול המערכת ולאבטחתה.</li>
    </ul>
    <p><strong>על לקוחות הסוכן — המידע הרגיש:</strong> מגיע מקבצי אקסל שהסוכן מעלה,
       או שהמערכת מורידה עבורו מפורטלי חברות הביטוח באישורו המפורש. הוא כולל
       מספרי תעודת זהות ושמות לקוחות; מספרי פוליסה, קופה וקרן וסוגי מוצרים;
       פרמיות, צבירות ועמלות.</p>

    <h2>איך אנחנו <em>לא</em> משתמשים במידע</h2>
    <p>זהו החלק החשוב ביותר, ולכן הוא מנוסח כרשימת התחייבויות. המידע של לקוחות הסוכן:</p>
    <div class="never">
      <ul>
        <li><strong>אינו משמש למחקר</strong> — לא מחקר פנימי, לא אקדמי, ולא מסחרי.</li>
        <li><strong>אינו משמש לניתוחים סטטיסטיים</strong> ולא להפקת תובנות שוק, גם לא במצטבר או בצורה אנונימית.</li>
        <li><strong>אינו משמש לאימון מודלים</strong> של בינה מלאכותית, ולא לכוונון (fine-tuning) שלהם.</li>
        <li><strong>אינו מצטבר בין סוכנים</strong> — אין השוואות, דירוגים או ממוצעים חוצי-משתמשים.</li>
        <li><strong>אינו נמכר, מושכר או מוחלף</strong> עם צד שלישי כלשהו.</li>
        <li><strong>אינו משמש לשיווק</strong> — לא שלנו, ולא של אף אחד אחר.</li>
      </ul>
    </div>

    <h2>למה כן משתמשים במידע</h2>
    <p>למטרה שלשמה הועלה, ולה בלבד: להפעיל את המערכת עבור הסוכן שהעלה אותו —
       התאמת פרודוקציה מול נפרעים וזיהוי פערים, חישוב עמלות צפויות מול עמלות שהתקבלו,
       הצגת לוחות מחוונים ודוחות, הצגת מידע ללקוח דרך פורטל הלקוחות כשהסוכן בחר לשתפו,
       ומענה לשאלות הסוכן באמצעות העוזר החכם המובנה במערכת.</p>

    <h2>הרשאות ואבטחה</h2>
    <p>הבידוד בין סוכנים אינו הבטחה בלבד — הוא נאכף בקוד:</p>
    <ul>
      <li><strong>הפרדה לפי משתמש.</strong> כל שאילתה למסד הנתונים מסוננת לפי מזהה הסוכן.
          סוכן אינו יכול לראות רשומה של סוכן אחר, גם לא בטעות.</li>
      <li><strong>סיסמאות.</strong> נשמרות כגיבוב bcrypt; איש בצוות אינו יכול לקרוא אותן.</li>
      <li><strong>הזדהות.</strong> הגישה מאובטחת באמצעות אסימוני JWT קצרי-תוקף.</li>
      <li><strong>תעבורה מוצפנת.</strong> כל התקשורת בין הדפדפן לשרת מתבצעת ב-HTTPS.</li>
      <li><strong>פורטל הלקוחות.</strong> כל קישור מוגן בסיסמה ייעודית, פג תוקף אוטומטית,
          ניתן לביטול מיידי על ידי הסוכן, וננעל לרבע שעה לאחר 5 ניסיונות כניסה כושלים.</li>
    </ul>

    <h2>Nifra Agent — העוזר החכם</h2>
    <p>Nifra Agent עונה על שאלות הסוכן על התיק שלו ומציע לו פעולות. כדי לענות, המערכת שולפת
       מתוך הנתונים של הסוכן בלבד את מה שנדרש לאותה שאלה — למשל לקוחות, פוליסות, עמלות,
       מיילים פתוחים וסיכומי שיחות — ושולחת אותו ל-Anthropic (Claude) לצורך ניסוח התשובה.</p>
    <ul>
      <li><strong>רק הנתונים של הסוכן.</strong> כל שליפה מוגבלת בקוד לחשבון הסוכן המחובר;
          העוזר אינו יכול לגשת לנתונים של סוכן אחר.</li>
      <li><strong>מציע — לא מבצע.</strong> שליחת מייל, תזכורת או בקשה לגורם חיצוני מתבצעות
          רק אחרי שהסוכן לחץ לאשר אותן. חריג אחד: כשהסוכן מבקש מהעוזר להקליט שיחה, ההקלטה
          מתחילה מיד (לאחר אישור ההסכמה המתואר בסעיף Nifra Calls).</li>
      <li><strong>מה נשמר.</strong> נוסח השאלה (עד 500 תווים) לצורך שיפור הניתוב, "זיכרונות"
          שהסוכן ביקש מהעוזר לזכור, ונתוני שימוש טכניים (כמות טוקנים). התשובות עצמן ושיחות
          הצ'אט אינן נשמרות בשרת. כל אלה נמחקים עם מחיקת החשבון.</li>
      <li><strong>נתונים ציבוריים.</strong> העוזר נעזר גם בנתוני קופות וקרנות פתוחים ממאגרי
          המידע הממשלתיים (data.gov.il), שאינם כוללים מידע אישי.</li>
    </ul>

    <h2>Nifra Calls — הקלטה, תמלול וסיכום שיחות</h2>
    <p class="lead">
      הסוכן יכול להקליט שיחה עם לקוח ולקבל תמליל וסיכום. לפני ההקלטה הראשונה המערכת מחייבת
      את הסוכן לאשר ש<strong>הלקוח יודע שהשיחה מוקלטת</strong>. האחריות ליידע את הצד השני
      בשיחה ולקבל את הסכמתו, כנדרש בחוק, מוטלת על הסוכן.
    </p>
    <ul>
      <li><strong>השמע לא יוצא מהשרתים שלנו.</strong> קובץ השמע עובר מהדפדפן לשרתים שלנו בלבד,
          והתמלול נעשה בשרת שלנו באמצעות מודל קוד-פתוח לזיהוי דיבור בעברית. ההקלטה אינה
          נשלחת לאף צד שלישי.</li>
      <li><strong>סיכום.</strong> טקסט התמליל — לא השמע — נשלח ל-Anthropic (Claude) כדי לנסח
          סיכום, משימות להמשך וטיוטת מכתב סיכום ללקוח. המכתב נשלח רק כשהסוכן לוחץ לשלוח.</li>
      <li><strong>שמירה ומחיקה.</strong> קובץ השמע נמחק אוטומטית 7 ימים לאחר ההקלטה. התמליל
          והסיכום נשמרים בחשבון הסוכן עד שהוא מוחק את השיחה, או עד מחיקת החשבון.</li>
    </ul>

    <h2>Mail Agent — קריאת מיילים וניסוח תשובות</h2>
    <p>Mail Agent קורא מיילים שמגיעים לסוכן מגורמים שהוא בחר (למשל חברות ביטוח), מסכם אותם
       ומנסח טיוטת תשובה. החיבור לתיבת הדואר נעשה על ידי הסוכן בלבד:</p>
    <ul>
      <li><strong>Microsoft (Outlook / Microsoft 365)</strong> — הרשאת קריאה בלבד (Mail.Read).
          המערכת אינה יכולה לשלוח, למחוק או לשנות דבר בתיבה.</li>
      <li><strong>Gmail</strong> — באמצעות "סיסמת אפליקציה" שהסוכן יוצר בחשבון Google שלו.
          הסיסמה נשמרת אצלנו מוצפנת, משמשת לקריאה (בלי לסמן מיילים כנקראו) ולשליחה רק כשהסוכן
          לוחץ לשלוח. הסוכן יכול לבטל אותה בכל עת בחשבון Google שלו.</li>
      <li><strong>הפניה (forwarding)</strong> — הסוכן מפנה אלינו מיילים מסוימים; אין לנו גישה
          לתיבה עצמה ואיננו שומרים פרטי גישה.</li>
    </ul>
    <ul>
      <li><strong>רק השולחים שהסוכן בחר.</strong> המערכת שומרת ומעבדת רק מיילים משולחים שהסוכן
          הוסיף לרשימה. בתיבות Microsoft השרת סורק את המיילים האחרונים כדי לסנן, ומיילים
          משולחים אחרים נזרקים מיד ואינם נשמרים.</li>
      <li><strong>סגנון כתיבה.</strong> רק אם הסוכן לוחץ "למד את הסגנון שלי", המערכת קוראת עד
          12 תשובות ששלח בעבר לאותם שולחים, ושומרת פרופיל סגנון ועד 3 דוגמאות — מוצפנות.</li>
      <li><strong>בינה מלאכותית.</strong> השולח, הנושא ותוכן המייל נשלחים ל-Anthropic (Claude)
          כדי לסווג ולסכם אותו. לניסוח טיוטה נשלחים גם פרופיל הסגנון והנתונים הרלוונטיים
          מהתיק של הסוכן (למשל המוצרים של הלקוח שהמייל עוסק בו).</li>
      <li><strong>שום דבר לא נשלח מעצמו.</strong> תשובה נשלחת רק כשהסוכן לוחץ "שלח". בקשות
          להסכמי עמלות נשלחות מתיבת הסוכן רק כשהוא יוזם אותן.</li>
      <li><strong>צרופות.</strong> נשמרים רק שם, סוג וגודל. קובץ נקלט לתיק כשהסוכן לוחץ לקלוט אותו;
          חריגים: קובצי הסכם (PDF) שחברת ביטוח שולחת בתשובה לבקשה שהסוכן שלח, וקובצי
          פרודוקציה של חברות ששולחות פרודוקציה במייל, נקלטים אוטומטית לתיק של אותו סוכן.</li>
      <li><strong>שמירה ומחיקה.</strong> נשמרים השולח, הנושא, הסיכום, הפרטים שזוהו (כגון מספר
          פוליסה וסכומים) והטיוטות. גוף המייל נשמר מוצפן ונמחק אוטומטית לאחר 90 יום. ניתוק
          תיבת הדואר מוחק את פרטי הגישה השמורים אצלנו — מומלץ גם לבטל את ההרשאה או את סיסמת
          האפליקציה בחשבון Microsoft / Google. שאר הנתונים נמחקים עם מחיקת החשבון או לבקשה.</li>
      <li><strong>צוות Nifraim</strong> אינו רואה את תוכן המיילים במסכי הניהול — רק אם תיבה
          מחוברת וכמה מיילים התקבלו.</li>
    </ul>

    <h2>ספקי צד שלישי</h2>
    <p>אנו נעזרים במספר מצומצם של ספקים. כל אחד פועל <strong>לפי הוראותינו בלבד</strong>,
       כמעבד מידע — ולא כגורם הרשאי לעשות במידע שימוש משלו:</p>
    <ul>
      <li><strong>Railway</strong> — אירוח השרתים ומסד הנתונים.</li>
      <li><strong>Resend</strong> — שליחת הודעות דוא"ל מהמערכת.</li>
      <li><strong>Anthropic (Claude)</strong> — מודל השפה שמפעיל את Nifra Agent, את סיכומי
          השיחות (טקסט התמליל בלבד), את הסינון והניסוח של Mail Agent ואת הצ'אט בפורטל
          הלקוחות. בכל פעם נשלחים אליו רק הנתונים הנדרשים לאותה משימה, בהתאם לתנאי ה-API
          שלו הקובעים כי אינם משמשים לאימון מודלים.</li>
      <li><strong>פורטלי חברות הביטוח</strong> — המערכת מתחברת אליהם בשם הסוכן ובאישורו,
          באמצעות פרטי ההתחברות שהוא מסר, אך ורק כדי להוריד את הדוחות שלו.</li>
    </ul>

    <h2>שיתוף עם לקוחות הסוכן</h2>
    <p>הסוכן יכול לייצר קישור אישי לפורטל עבור לקוח. הלקוח רואה בו את הרשומות שלו בלבד —
       הן מסוננות גם לפי הסוכן שיצר את הקישור וגם לפי תעודת הזהות של אותו לקוח.
       לקוח אינו יכול לראות לקוחות אחרים ואינו יכול לגשת למערכת הסוכן.</p>
    <p>בפורטל יכול הלקוח לשאול שאלות על התיק שלו בצ'אט חכם (Anthropic Claude). לצ'אט נשלחים
       רק נתוני התיק של אותו לקוח, בלי סכומים שהסוכן בחר להסתיר. הסוכן יכול לכבות את הצ'אט
       בכל קישור, והשיחה אינה נשמרת בשרת.</p>

    <h2>שמירה ומחיקה</h2>
    <p>המידע נשמר כל עוד חשבון הסוכן פעיל, מפני שהמערכת זקוקה להיסטוריה כדי להשוות בין
       חודשי דיווח. הסוכן יכול למחוק קבצים שהעלה ושיחות שהקליט בכל עת מתוך המערכת.
       קובצי שמע של הקלטות נמחקים אוטומטית 7 ימים לאחר ההקלטה.
       גוף המיילים ש-Mail Agent קרא נמחק אוטומטית לאחר 90 יום. למחיקת חשבון
       והנתונים שבו במלואם — פנו אלינו לכתובת שבתחתית העמוד.</p>

    <h2>הזכויות שלך</h2>
    <p>בהתאם לחוק הגנת הפרטיות, התשמ"א–1981, אתם זכאים לעיין במידע השמור עליכם,
       לבקש את תיקונו אם אינו מדויק, לבקש את מחיקתו, ולקבל עותק של הנתונים שלכם.
       כל פנייה כזו תיענה בתוך זמן סביר, ללא תשלום.</p>
  </div>

  <!-- ══════════ PART B — the Android app (Play-facing; do not soften) ══════════ -->
  <div class="part" id="app">
    <span class="part-label">חלק ב׳</span>
    <h1 style="font-size:22px">אפליקציית Nifraim לאנדרואיד</h1>

  <p>
    אפליקציית <strong>Nifraim</strong> מיועדת לסוכני ביטוח המשתמשים במערכת Nifraim.
    תפקידה היחיד הוא להעביר אוטומטית קודי אימות חד-פעמיים (OTP) שמגיעים ב-SMS
    מחברות הביטוח, כדי שתהליך ההורדה האוטומטי מהפורטלים יוכל להמשיך ללא הזנה ידנית.
  </p>

  <h2>אילו נתונים אנו קוראים</h2>
  <ul>
    <li>תוכן הודעות SMS <strong>נכנסות</strong> בלבד, ושם/מספר השולח — לצורך זיהוי קוד אימות.</li>
    <li>איננו קוראים את היסטוריית ההודעות, אנשי קשר, מיקום, או כל מידע אישי אחר.</li>
  </ul>

  <h2>סינון על המכשיר — מה נשאר אצלך</h2>
  <p>
    כל הודעה נבדקת על המכשיר עצמו מול תבניות חברות הביטוח לפי הכלל
    <strong>חסימה ← העברה ← ברירת מחדל בטוחה</strong>:
  </p>
  <ul>
    <li>הודעה התואמת תבנית <strong>חסימה</strong> (למשל קוד מהבנק) — <strong>נמחקת ולא נשלחת</strong>.</li>
    <li>הודעה התואמת תבנית חברת ביטוח, או הודעה שמכילה קוד בן 4–8 ספרות — מועברת.</li>
    <li>הודעה אישית ללא קוד — לעולם אינה עוזבת את המכשיר.</li>
  </ul>

  <h2>מה נשלח, ולאן</h2>
  <ul>
    <li>רק הודעות נושאות-קוד נשלחות אל כתובת ה-Webhook האישית של הסוכן בשרת Nifraim, דרך HTTPS מוצפן.</li>
    <li>הנתונים משמשים אך ורק לחילוץ קוד האימות עבור תהליך ההורדה האוטומטי של אותו סוכן.</li>
    <li>איננו מוכרים, משכירים או משתפים נתונים אלה עם צד שלישי כלשהו.</li>
  </ul>

  <h2>שמירת נתונים</h2>
  <p>
    קוד האימות נצרך מיידית על ידי תהליך ההורדה ואינו נשמר מעבר לזמן הנדרש להשלמתו.
  </p>

  <h2>הרשאות</h2>
  <ul>
    <li><code>RECEIVE_SMS</code> — לקרוא קודי אימות נכנסים (הליבה התפקודית של האפליקציה).</li>
    <li><code>INTERNET</code> — לשלוח את הקוד לכתובת ה-Webhook.</li>
    <li><code>POST_NOTIFICATIONS</code> / <code>REQUEST_IGNORE_BATTERY_OPTIMIZATIONS</code> — להמשיך לפעול ברקע.</li>
  </ul>

  </div><!-- /part ב -->

  <h2 style="margin-top:44px">יצירת קשר</h2>
  <p>
    לשאלות בנושא פרטיות, או לכל בקשה מסעיף "הזכויות שלך" — בשני החלקים:
    <a href="mailto:admin@nifraim.co.il">admin@nifraim.co.il</a>
  </p>

  <div class="en">
    <h2 style="border:0;padding:0">Privacy Policy — Nifraim app</h2>
    <p>
      The <strong>Nifraim</strong> app is an internal tool for insurance agents using the
      Nifraim platform. Its sole function is to forward one-time verification codes (OTP)
      that arrive by SMS from insurance companies, so the agent's automated portal
      download can continue without manual entry.
    </p>
    <ul>
      <li><strong>What we read:</strong> the content and sender of <em>incoming</em> SMS only,
          to detect a verification code. We do not read message history, contacts, or location.</li>
      <li><strong>On-device filtering</strong> (block → allow → safe-default): messages matching a
          BLOCK template (e.g. a bank code) are dropped and never sent; personal SMS without a code
          never leave the device.</li>
      <li><strong>What is sent:</strong> only code-bearing SMS, over encrypted HTTPS, to the agent's
          personal webhook on the Nifraim server, used solely to extract the OTP. We never sell,
          rent, or share this data with any third party.</li>
      <li><strong>Retention:</strong> the code is consumed immediately and not retained beyond the
          download it completes.</li>
      <li><strong>Contact:</strong> <a href="mailto:admin@nifraim.co.il">admin@nifraim.co.il</a></li>
    </ul>
  </div>
  </main>
</body>
</html>"""


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return _PRIVACY_HTML
