/**
 * Error codes → what the agent actually reads.
 *
 * The backend never sends a message, only a stable code. Provider errors
 * ("AADSTS65001", "AUTHENTICATIONFAILED", "invalid_grant") are meaningless to an
 * insurance agent, and imaplib's error strings can echo the failed LOGIN line
 * with the password in it. Mapping happens here, once.
 *
 * Every entry: say what happened, then give exactly one thing to do. Never blame
 * the agent, and never use the words OAuth / IMAP / MX / token / webhook.
 */

export const MAILBOX_ERRORS = {
  admin_consent_required: {
    title: 'צריך אישור חד-פעמי של מנהל המערכת',
    body: 'בארגון שלך, חיבור של תוכנה חיצונית לתיבת המייל מחייב אישור של מנהל המערכת. שלח לו את הקישור, ואחרי שיאשר — לחץ שוב על "התחברות עם Microsoft".',
    action: 'העתקת קישור למנהל',
    escape: 'אין לך מנהל מערכת? אפשר במקום זה להעביר אלינו את המייל אוטומטית.',
    tone: 'warn',
  },
  consent_revoked: {
    title: 'החיבור למייל הופסק',
    body: 'זה קורה למשל אחרי שינוי סיסמה. לחיצה אחת ונחבר מחדש.',
    action: 'חבר מחדש',
    tone: 'warn',
  },
  bad_app_password: {
    title: 'הסיסמה לא התקבלה',
    body: 'ודא שהעתקת את סיסמת האפליקציה בת 16 התווים שיצרת בהגדרות Google, ולא את הסיסמה הרגילה של Gmail.',
    tone: 'danger',
  },
  mailbox_unreachable: {
    title: 'לא הצלחנו להתחבר לתיבה כרגע',
    body: 'ננסה שוב אוטומטית בעוד כמה דקות. אין צורך לעשות דבר.',
    tone: 'warn',
  },
  attachment_unreadable: {
    title: 'הגיע קובץ מהכשרה, אבל לא הצלחנו לקרוא אותו',
    body: 'שמרנו את הקובץ והצוות שלנו בודק. אין צורך לעשות כלום.',
    tone: 'warn',
  },
  not_configured: {
    title: 'החיבור עדיין לא הושלם',
    body: 'הזן את כתובת המייל שאליה הכשרה שולחת את הקובץ, והמשך לפי ההוראות.',
    tone: 'muted',
  },
  forward_rule_silent: {
    title: 'נראה שהגדרת ההעברה לא פעילה',
    body: 'לא קיבלנו אף הודעה מאז שהחיבור נוצר. בוא נבדוק את כלל ההעברה יחד.',
    tone: 'warn',
  },
}

/**
 * The normal state for most of the month. Deliberately NOT an error: Hachshara
 * sends once a month, so a warning colour here would teach agents to distrust a
 * feature that is working perfectly.
 */
export const CONNECTED_NO_MAIL_YET = {
  title: 'החיבור פעיל',
  body: 'עדיין לא הגיע קובץ מהכשרה — הם שולחים אותו פעם בחודש. נעדכן אותך ברגע שיגיע.',
  tone: 'muted',
}

export function errorCopy(code) {
  if (!code) return null
  return MAILBOX_ERRORS[code] || MAILBOX_ERRORS.mailbox_unreachable
}

/** "נקלט לאחרונה: 4 במאי 2026" — or the pre-first-arrival state. */
export function lastReceivedLabel(iso) {
  if (!iso) return 'טרם התקבל קובץ'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'טרם התקבל קובץ'
  return `נקלט לאחרונה: ${d.toLocaleDateString('he-IL', { day: 'numeric', month: 'long', year: 'numeric' })}`
}
