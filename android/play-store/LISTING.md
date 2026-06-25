# Nifraim — Google Play listing cheat-sheet (Closed Testing)

Copy/paste these into the Play Console. Primary language: **Hebrew (he-IL)**.
Package: `com.nifraim.smsforwarder` · Track: **Closed testing**.

---

## App details
- **App name:** Nifraim
- **Default language:** Hebrew (he-IL)
- **App or game:** App
- **Free or paid:** Free
- **Privacy policy URL:** https://nifraim-production.up.railway.app/privacy

## Short description (≤80 chars, Hebrew)
```
העברת קוד אימות (OTP) אוטומטית מ-SMS לסוכני Nifraim — הגדרה חד-פעמית.
```

## Full description (Hebrew)
```
Nifraim היא אפליקציית עזר פנימית לסוכני ביטוח המשתמשים במערכת Nifraim.

תפקידה היחיד: כאשר חברת ביטוח שולחת קוד אימות חד-פעמי (OTP) ב-SMS במהלך הורדת
דוחות אוטומטית מהפורטלים, האפליקציה מזהה את הקוד ומעבירה אותו באופן מאובטח לכתובת
ה-Webhook האישית של הסוכן — כך שתהליך ההורדה ממשיך לבד, ללא הקלדה ידנית.

איך זה עובד:
• מתקינים פעם אחת דרך הקישור האישי במערכת Nifraim — כתובת ה-Webhook מוגדרת אוטומטית.
• מאשרים הרשאת SMS ומכבים אופטימיזציית סוללה.
• זהו. האפליקציה פועלת ברקע בשקט.

פרטיות תחילה — הסינון מתבצע על המכשיר:
• הודעות אישיות ללא קוד לעולם אינן עוזבות את המכשיר.
• ניתן להגדיר תבניות "חסימה" (למשל קודים מהבנק) שלא יישלחו.
• רק הודעות נושאות-קוד מחברות הביטוח מועברות, דרך HTTPS מוצפן.

אפליקציה זו מיועדת לשימוש פנימי של סוכני Nifraim בלבד.
```

## Categorization
- **Category:** Business (or Productivity)
- **Tags:** —
- **Contact email:** admin@nifraim.co.il

---

## Graphics (in android/play-store/)
- **App icon:** `icon.png` (512×512, 32-bit PNG)
- **Feature graphic:** `feature.png` (1024×500)
- **Phone screenshots:** `screenshot-1.png`, `screenshot-2.png` (≥2 required, 1080×1920)

---

## Data safety form
- **Does your app collect or share user data?** Yes (collects, does not share).
- **Data type collected:** *SMS messages* (under "Messages").
  - **Collected:** Yes · **Shared:** No
  - **Processed ephemerally?** Yes — the OTP is consumed immediately, not stored long-term.
  - **Required or optional:** Required (core function).
  - **Purpose:** App functionality.
- **Is data encrypted in transit?** Yes (HTTPS).
- **Can users request data deletion?** The app stores no personal data server-side beyond
  the transient OTP; agents can revoke their webhook token in the Nifraim web UI.

## Content rating questionnaire
- Utility/Productivity app; no objectionable content. Answer "No" to all violence/
  sexual/gambling/etc. prompts → results in **Everyone / PEGI 3**.

---

## RECEIVE_SMS — restricted permission justification (paste in Permissions declaration)
```
Nifraim is a private, internal tool for our insurance agents. Its core and only
function is to read the one-time verification code (OTP) that an insurance company
sends by SMS during an automated report download, and forward only that code to the
agent's own secure webhook so the automated download can proceed unattended.

The app reads only INCOMING SMS, filters on-device (personal messages without a code,
and messages matching a block template such as bank codes, are dropped and never
leave the device), and transmits only code-bearing messages over HTTPS to the agent's
own server. We do not read SMS history, do not access contacts, and do not sell or
share any data. Distribution is restricted to our agents via a closed testing track.
RECEIVE_SMS is essential because the OTP arrives by SMS and must be captured in real
time to continue the automation; no alternative API delivers these third-party OTPs.
```

> Note: if Google requests a **demo video**, record a short screen capture showing:
> the app's single screen → an OTP SMS arriving → the "last forwarded" timestamp
> updating → the Nifraim portal run continuing automatically.

---

## Reminder
- Upload **`app-release.aab`** (from `app/build/outputs/bundle/release/`), NOT the APK.
- Accept **Play App Signing** when prompted (Google holds the real signing key; we
  signed with the upload key `nifraim`).
- The **upload keystore** is `android/upload-keystore.jks` — back it up + its password
  (in `android/keystore.properties`, gitignored).
