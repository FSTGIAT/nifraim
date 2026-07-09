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
  <style>
    body { font-family: 'Heebo', system-ui, Arial, sans-serif; max-width: 760px;
           margin: 0 auto; padding: 32px 20px 64px; color: #1A1A2E; line-height: 1.7; }
    h1 { color: #F57C00; font-size: 26px; margin-bottom: 4px; }
    h2 { font-size: 19px; margin-top: 30px; border-bottom: 2px solid #F57C00;
         padding-bottom: 4px; display: inline-block; }
    .updated { color: #706E6B; font-size: 13px; margin-bottom: 24px; }
    ul { padding-inline-start: 22px; }
    code { background: #F3F3F3; padding: 1px 5px; border-radius: 3px; direction: ltr;
           display: inline-block; }
    .en { direction: ltr; text-align: left; border-top: 1px solid #E5E5E5;
          margin-top: 48px; padding-top: 24px; }
    a { color: #F57C00; }
    .part { margin-top: 44px; padding-top: 8px; border-top: 3px solid #F57C00; }
    .part-label { display: inline-block; font-size: 12px; font-weight: 700;
                  letter-spacing: .04em; color: #F57C00; margin: 12px 0 2px; }
    .part h2:first-of-type { margin-top: 18px; }
    .lead { background: #FFF6EE; border-inline-start: 4px solid #F57C00;
            border-radius: 0 8px 8px 0; padding: 14px 18px; margin: 18px 0; }
    .never { background: #FFF; border: 1px solid #F7C89A; border-radius: 10px;
             padding: 18px 22px 6px; margin: 18px 0; }
    .never li { margin-bottom: 8px; }
    .toc { font-size: 14px; color: #706E6B; margin-bottom: 8px; }
    .toc a { text-decoration: none; }
  </style>
</head>
<body>
  <h1>מדיניות פרטיות — Nifraim</h1>
  <p class="updated">עודכן לאחרונה: יולי 2026</p>

  <p>
    מסמך זה מכסה שני מוצרים נפרדים תחת השם Nifraim, ומסביר לגבי כל אחד מהם איזה מידע
    נאסף, למה הוא משמש — ובעיקר, למה הוא <strong>לא</strong> משמש.
  </p>
  <p class="toc">
    <a href="#platform">חלק א׳ — מערכת Nifraim (האתר)</a> &nbsp;·&nbsp;
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

    <h2>ספקי צד שלישי</h2>
    <p>אנו נעזרים במספר מצומצם של ספקים. כל אחד פועל <strong>לפי הוראותינו בלבד</strong>,
       כמעבד מידע — ולא כגורם הרשאי לעשות במידע שימוש משלו:</p>
    <ul>
      <li><strong>Railway</strong> — אירוח השרתים ומסד הנתונים.</li>
      <li><strong>Resend</strong> — שליחת הודעות דוא"ל מהמערכת.</li>
      <li><strong>Anthropic (Claude)</strong> — מפעיל את העוזר החכם. כששואלים אותו שאלה,
          הנתונים הרלוונטיים לאותה שאלה נשלחים אליו כדי לייצר תשובה, בהתאם לתנאי ה-API
          שלו הקובעים כי אינם משמשים לאימון מודלים.</li>
      <li><strong>פורטלי חברות הביטוח</strong> — המערכת מתחברת אליהם בשם הסוכן ובאישורו,
          באמצעות פרטי ההתחברות שהוא מסר, אך ורק כדי להוריד את הדוחות שלו.</li>
    </ul>

    <h2>שיתוף עם לקוחות הסוכן</h2>
    <p>הסוכן יכול לייצר קישור אישי לפורטל עבור לקוח. הלקוח רואה בו את הרשומות שלו בלבד —
       הן מסוננות גם לפי הסוכן שיצר את הקישור וגם לפי תעודת הזהות של אותו לקוח.
       לקוח אינו יכול לראות לקוחות אחרים ואינו יכול לגשת למערכת הסוכן.</p>

    <h2>שמירה ומחיקה</h2>
    <p>המידע נשמר כל עוד חשבון הסוכן פעיל, מפני שהמערכת זקוקה להיסטוריה כדי להשוות בין
       חודשי דיווח. הסוכן יכול למחוק קבצים שהעלה בכל עת מתוך המערכת. למחיקת חשבון
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
</body>
</html>"""


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return _PRIVACY_HTML
