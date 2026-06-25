"""Public legal pages (no auth). Served at the site root so they have stable,
shareable URLs — Google Play requires a publicly reachable privacy-policy URL for
the Nifraim app, and it must honestly disclose the SMS reading + forwarding.

Registered with NO prefix in main.py and BEFORE the SPA catch-all, so `/privacy`
resolves to this route rather than the Vue index.html.
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
  </style>
</head>
<body>
  <h1>מדיניות פרטיות — אפליקציית Nifraim</h1>
  <p class="updated">עודכן לאחרונה: יוני 2026</p>

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

  <h2>יצירת קשר</h2>
  <p>לשאלות בנושא פרטיות: <a href="mailto:admin@nifraim.co.il">admin@nifraim.co.il</a></p>

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
