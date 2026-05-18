import asyncio
import base64
import json
import logging
import os
import uuid
from typing import AsyncGenerator

import anthropic
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.paying_company import PayingCompany
from app.models.recruit import Recruit
from app.models.commission_rate import CommissionRate
from app.models.volume_commission_rate import VolumeCommissionRate
from app.models.production_summary import ProductionSummary
from app.models.ai_document import AiDocument
from app.models.fund_track import FundTrack
from app.models.fund_track_fund import FundTrackFund
from app.services.comparison_service import compute_comparison, _normalize_id

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a specialized insurance reconciliation analyst assistant for the Nifraim platform.
המשתמש שמדבר איתך הוא סוכן הביטוח בעל התיק. כל הנתונים למטה שייכים לו ולתיק הלקוחות שלו.
כשהוא שואל "שלי" הוא מתכוון לנתונים שלו כסוכן — סה"כ הפרמיה, הלקוחות, העמלות וכו'.
You have access ONLY to the user's data shown below. You MUST:
- Answer ONLY questions about this data. Refuse anything else politely.
- Always respond in Hebrew.
- Be concise and professional.
- Use numbers and specific data points from the context.
- If asked about something not in the data, say you don't have that information.
- When presenting lists, comparisons, or financial data — ALWAYS use markdown tables with | columns |.
- Format currency values with ₪ symbol and comma separators (e.g. ₪1,234).
- Use **bold** for important numbers and key insights.
- Keep tables concise — max 10 rows, summarize the rest.
- You may have access to multi-month production history. You can identify trends, growth/decline patterns, and notable changes over time.
- The personal file (קובץ אישי) may include sign dates (תאריך חתימה) for each client. Use the "גיוסים לפי חודש" block to answer questions like "כמה גייסתי במרץ/אפריל" — count per month and by company. If a client in the personal file has a sign date after the active production file's month, they won't appear in production yet — that's expected, not an error.

=== הנחיות קריטיות לנתוני עמלות (אל תפר!) ===
1. **אסור לחשב סכומי עמלה לבד** על ידי הכפלה של שיעור עמלה בפרמיה או בצבירה.
   דוגמה אסורה: "מנורה: פרמיה 172,000 × 95% = עמלה 163,000" — זה שקר.
   **חריג**: אם בקונטקסט מופיעים שדות `עמלה צפויה`, `expected_commission`, `סכום עמלה חזוי` —
   אלה ערכים שכבר חושבו עבורך ע"י המערכת לפי שיעורי ההסכם. אתה רשאי (וצריך!) לדווח אותם
   כשהמשתמש שואל על עמלות שלא שולמו / שצריכות להתקבל. **חובה לציין** שאלה ערכים חזויים
   ("צפויים לפי ההסכם"), לא ערכים מאומתים מנפרעים.
2. **כשמדווחים על "סכום לא שולם"** — הקפד להבחין:
   • **פרמיה לא משולמת** = הסכום שהלקוח שילם לחברה אבל לסוכן לא הגיעה עמלה (פרמיה ברוטו, גדול).
   • **עמלה צפויה לא שולמה** = הסכום שהסוכן היה אמור לקבל לפי שיעור ההסכם (= פרמיה × אחוז, קטן בהרבה).
   המשתמש כמעט תמיד מתכוון לשנייה. אם בקונטקסט יש את שני הערכים — דווח את ה"עמלה צפויה" כסכום
   הראשי וצרף את ה"פרמיה" כהקשר ("מתוך פרמיה של X₪").
3. **דווח רק על סכומי עמלה ש-(א) בפועל מקבצי נפרעים, או (ב) חושבו ע"י המערכת**.
   אם בלוק "=== קבצי נפרעים שהועלו ===" לא מפרט חברה מסוימת — **אין לך נתוני עמלה בפועל**.
   אל תנחש. אל תמציא.
4. **שיעורי עמלה (table של אחוזים) ≠ עמלה בפועל**. שיעורים מופיעים ב"שיעורי עמלה" ומשמשים
   להבהרת תנאי ההסכם ולחישוב עמלה חזויה (שהמערכת עושה עבורך, לא אתה).
5. כששואלים "תראה לי את העמלות שהתקבלו" — הצג **רק** סכומים מקבצי נפרעים שהועלו, וציין מפורשות אילו חברות חסרות קובץ נפרעים.

=== בלוק "עובדות לקוח" — מקור אמת מוחלט ===
כאשר המשתמש שואל על לקוח ספציפי (לפי ת.ז או שם), ובלוק "=== עובדות לקוח ===" מופיע
ב-view_context או בהקשר:
- **חובה לצטט מהבלוק הזה ישירות**. אסור לסתור אותו.
- אם הבלוק אומר "פרודוקציה=כן · נפרעים=כן" — הלקוח מופיע בשני הקבצים. אל תגיד "רק בנפרעים".
- אם הבלוק אומר "השתנו · Δפרמיה +1,000" — הלקוח שינה את הפרמיה ב-+1,000₪. דווח את הערך בדיוק.
- אם הלקוח אינו ברשימה (לא בטופ 30), השתמש בנתונים האחרים, אבל אל תמציא ערכים על לקוחות שלא ברשימה.

=== בלוק "מונים" — בדיקת סכימה ===
כשמופיעה שורת "בדיקת סכימה: A+B+C=N ✓" — A+B+C **חייבים** להסתכם ל-N. אל תדווח חלוקה
שאינה תואמת. אם המשתמש שואל "כמה לקוחות בשניהם" — צטט בדיוק את הערך מהשורה הזו, ולא חישוב משלך.

=== סוגי עמלות במסמכי ביטוח (חשוב — אל תערבב ביניהם!) ===
מסמכי הסכמי עמלה בישראל מכילים בדרך כלל **שלושה–ארבעה סוגי שיעורי עמלה שונים** באותו מסמך,
ובדרך כלל בטבלאות נפרדות:

A. **עמלת היקף / היקפים** — תשלום חד־פעמי בעת הצטרפות לקוח חדש (אחוזים גבוהים: 30%–60% מהפרמיה השנתית, או סכום שקלי קבוע).
B. **עמלת נפרעים / שימור / טיפול** — עמלה שוטפת על פרמיה שמגיעה בפועל (אחוזים נמוכים: 3%–9% בחיים/בריאות, 0.2%–0.6% בקופ"ג).
C. **עמלת ספר / עמלת ספר מקסימלית** — שיעור שנקבע ע"י החברה כתקרה לפיה מחושבת עמלת הסוכן (לעיתים 15%).
D. **החזרי עמלה / ניכויי ביטולים** — אחוז שיוחזר במקרה של ביטול מוקדם, מדורג לפי שנת ביטול.

**חוקי שימוש:**
- אם השאלה שואלת "אחוז **נפרעים** שאני מקבל בכל מוצר" → השב **רק** משורות עמלת הנפרעים (B).
  אל תכלול שורות מטבלת עמלת ההיקף (A) או טבלת עמלת הספר (C).
- אם השאלה שואלת "עמלת היקף" → השב מ-(A) בלבד.
- אם השאלה שואלת "החזר על ביטול" → השב מ-(D) בלבד.
- כשהמסמך מאוחד טבלאות של ביטוח כללי + חיים + בריאות + פנסיה — הקפד להתאים את המוצר לקטגוריה.
  למשל "תרופות", "השתלות", "ניתוחים בחו"ל" שייכים לטבלת בריאות, לא לטבלת רכוש/כללי.
- בכל תשובה על שיעורי עמלה ממסמך — **ציין במפורש מאיזה סוג עמלה השיעור** (נפרעים / היקף / ספר / החזר).

=== תצוגה חזותית (viz) — אופציונלי ===
כשהתשובה שלך כוללת פירוט מספרי שווה הצגה (למשל 5+ פריטים עם ערכים, או ערך-גיבור חד-משמעי,
או אחוז מכריע), **בסוף התשובה בלבד** (אחרי הטקסט הרגיל) הוסף בלוק JSON בדיוק בפורמט הזה:

<<VIZ:{{"type":"...","title":"...",...}}>>

הבלוק יהפוך לאנימציה שמופיעה ליד הצ'אט — אל תזכיר אותו בטקסט הגלוי. אל תעטוף אותו ב-markdown.
סוגים נתמכים:

1) type=bar — רשימה של פריט→ערך (עד 10 שורות). השתמש כשיש ≥5 פריטים עם ערך מספרי משמעותי.
   דוגמה:
   <<VIZ:{{"type":"bar","title":"הירידה לפי לקוח ב-מיטב","unit":"₪","direction":"down","data":[{{"label":"יחזקאל קר","value":-3379182,"id":"50052083"}},{{"label":"דני לוי","value":-420000}}],"highlight_label":"יחזקאל קר","insight":"לקוח אחד = 75% מהירידה"}}>>

2) type=kpi — מספר-גיבור יחיד עם תת-כותרת. השתמש כשהסיפור הוא "סכום אחד גדול" (סה\"כ / רווח).
   דוגמה:
   <<VIZ:{{"type":"kpi","title":"סך העמלות שהתקבלו","value":204671,"unit":"₪","subtitle":"408 עלייה · 1 ירידה","direction":"up"}}>>

3) type=donut — התפלגות פרופורציונית (עד 8 פרוסות). השתמש כשהיחסים הם הסיפור.
   דוגמה:
   <<VIZ:{{"type":"donut","title":"פרמיה לפי חברה","unit":"₪","data":[{{"label":"הראל","value":83407}},{{"label":"מגדל","value":41200}}],"highlight_label":"הראל"}}>>

4) type=fund-track — תצוגה מפוארת של מסלול קופת גמל/השתלמות מבלוק "נתוני שוק".
   השתמש כשהמשתמש שואל על ביצועי מסלול ספציפי ("מה התשואה של מניות", "מי הקרן הכי טובה ב-50-60",
   "תראה לי קופת גמל להשקעה — מניות"). זוהי תצוגת ה-wow המלאה: ממוצעי 4 תקופות + טופ 10 קרנות
   + הדגשה זהובה על הראשונה + שורת תובנה.

   המזהים החוקיים (track_id) — חובה להעביר אחד מהם בדיוק (ללא המצאה):
   gemel-under50, gemel-50to60, gemel-over60, gemel-stocks,
   hish-klali, hish-stocks,
   polisa-klali, polisa-stocks,
   gle-klali, gle-stocks.

   הפורמט מינימלי במכוון — הלקוח שואב את שאר הנתונים מ-API:
   <<VIZ:{{"type":"fund-track","track_id":"gemel-stocks","insight":"כלל תמר מובילה עם +31.7% בשנה האחרונה"}}>>

   - track_id חובה. אם אין מסלול תואם, אל תפלוט viz מהסוג הזה.
   - title רשות (אם מושמט הלקוח משתמש בשם מהמסד).
   - insight רשות — משפט קצר אחד שמסכם את הסיפור (מי המנצח, גודל הפער, מגמה).

הנחיות קשיחות:
- **אל תפלוט viz** כאשר התשובה היא שאלת "כמה/מה/האם" פשוטה, אישור, סירוב, או טקסט קצר בלא פירוט מספרי.
- **ערכים חייבים להגיע מהקשר בלבד** (מה שמופיע בבלוקים למעלה). אל תמציא מספרים.
- השתמש ב-direction: "down" לירידות, "up" לעליות, אחרת השמט (ברירת המחדל: ניטרלי כתום).
- שמור על 10 נקודות bar לכל היותר, 8 פרוסות donut.

**FINAL CHECKLIST לפני שליחה** — אם השאלה היא "מי הכי X / top N / רשימת מובילים / השוואה בין חברות"
ויש לך ≥5 שורות עם ערך מספרי בתשובה, **חובה** לסיים ב-`<<VIZ:…>>`. אחרת אתה מפר את חוזה הממשק
והדיאגרמה לא תיפתח. זה לא אופציונלי במקרים האלה — זה חלק מהתשובה.

**ריבוי-viz לתשובות סינתזה** — כשהתשובה מסכמת כמה זוויות נתונים שונות (לדוגמה: "איך אני יכול
להשתפר", "תן לי סקירה כללית", "מה הזדמנויות שלי"), ולכל זווית יש סיפור נומרי חזק משלה,
**מותר להוסיף עד 3 בלוקי `<<VIZ:…>>` ברצף** בסוף התשובה — אחד אחרי השני, ללא טקסט ביניהם.
ה-UI יציג אותם כקרוסלה ניתנת לדפדוף. כל בלוק חייב לעמוד בפני עצמו (כותרת + insight ברורים).
דוגמה: סקירה ביצועים שמסיימת ב-`<<VIZ:{{...bar תשואות...}}>><<VIZ:{{...donut פילוח פרמיה...}}>>`.
אל תפלוט יותר מ-3. אל תפלוט viz חלש רק כדי למלא מכסה — איכות לפני כמות.

=== נתוני המשתמש ===
{context}
==="""


def _record_to_dict(r):
    return {c.key: getattr(r, c.key) for c in r.__table__.columns if c.key not in ("id", "user_id", "upload_id")}


async def _get_production_context(db: AsyncSession, user_id: uuid.UUID) -> tuple[str | None, FileUpload | None]:
    """Get production file analytics as context string."""
    # Find active production upload
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,
        )
    )
    prod_upload = result.scalar_one_or_none()
    if not prod_upload:
        return None, None

    uid = prod_upload.id

    # Totals
    totals = await db.execute(
        select(
            func.count().label("cnt"),
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("total_premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("total_accumulation"),
        ).where(ClientRecord.upload_id == uid)
    )
    t = totals.one()

    # Product type breakdown
    product_q = await db.execute(
        select(
            ClientRecord.product_type,
            func.count().label("count"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.product_type.isnot(None))
        .group_by(ClientRecord.product_type)
        .order_by(desc(func.count()))
    )
    products = [
        f"{r[0]}({r[1]} מוצרים, פרמיה: {float(r[2]):,.0f}₪)"
        for r in product_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Top 10 clients by premium
    top_premium_q = await db.execute(
        select(
            ClientRecord.id_number,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("total_prem"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.total_premium), 0)))
        .limit(10)
    )
    top_premium = [
        f"{r.first_name or ''} {r.last_name or ''}".strip() + f"({float(r.total_prem):,.0f}₪)"
        for r in top_premium_q.all() if float(r.total_prem) > 0
    ]

    # Top 10 clients by accumulation
    top_accum_q = await db.execute(
        select(
            ClientRecord.id_number,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("total_accum"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
        .limit(10)
    )
    top_accum = [
        f"{r.first_name or ''} {r.last_name or ''}".strip() + f"({float(r.total_accum):,.0f}₪)"
        for r in top_accum_q.all() if float(r.total_accum) > 0
    ]

    parts = [
        "=== קובץ פרודוקציה ===",
        f"שם קובץ: {prod_upload.filename}",
        f"סה\"כ רשומות (מוצרים): {t.cnt}",
        f"לקוחות ייחודיים: {t.unique_clients}",
        f"סה\"כ פרמיה: {float(t.total_premium):,.0f}₪",
        f"סה\"כ צבירה: {float(t.total_accumulation):,.0f}₪",
    ]
    # Company breakdown with unique client counts
    company_enriched_q = await db.execute(
        select(
            ClientRecord.receiving_company,
            func.count().label("count"),
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
    )
    companies_enriched = [
        f"{r[0]}({r[2]} לקוחות, {r[1]} מוצרים, פרמיה: {float(r[3]):,.0f}₪, צבירה: {float(r[4]):,.0f}₪)"
        for r in company_enriched_q.all() if r[0] and r[0] not in ("nan", "None")
    ]
    if companies_enriched:
        parts.append(f"חברות: {', '.join(companies_enriched)}")
    if products:
        parts.append(f"סוגי מוצרים: {', '.join(products)}")
    if top_premium:
        parts.append(f"לקוחות מובילים (פרמיה): {', '.join(top_premium)}")
    if top_accum:
        parts.append(f"לקוחות מובילים (צבירה): {', '.join(top_accum)}")

    return "\n".join(parts), prod_upload


async def _get_comparison_context(db: AsyncSession, user_id: uuid.UUID, prod_upload: FileUpload) -> str | None:
    """Recompute comparison from latest commission uploads and format as context.

    Matches the dashboard logic exactly:
    - Deduplicate commission uploads by filename (use latest)
    - "נמצא בשניהם" = matched customers
    - "לא שולם" = only_production customers with accumulation > 0 (for gemel)
    - "רק בנפרעים" = only_commission customers
    - Total shown = matched + unpaid + only_commission (excludes only_prod with no accumulation)
    """
    # Find commission uploads, deduplicate by filename (keep latest).
    # CRITICAL: filter to production's period_month — agents care about
    # "this month's commissions vs production", not the cumulative total
    # across every commission file ever uploaded. Files whose period_month
    # doesn't match (or is NULL — undetectable) are excluded; their count
    # is surfaced separately so the AI can mention it.
    comm_uploads_result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user_id,
            FileUpload.file_category == "commission",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    all_comm_uploads = comm_uploads_result.scalars().all()
    if not all_comm_uploads:
        return None

    prod_period = getattr(prod_upload, "period_month", None)
    excluded_no_period: list[str] = []
    excluded_wrong_period: list[tuple[str, str]] = []
    if prod_period is not None:
        period_matched: list = []
        for u in all_comm_uploads:
            if u.period_month is None:
                excluded_no_period.append(u.filename)
            elif u.period_month == prod_period:
                period_matched.append(u)
            else:
                excluded_wrong_period.append((u.filename, u.period_month.isoformat()))
        all_comm_uploads = period_matched

    # Deduplicate so each commission *company* appears once, using its latest
    # upload. Falling back to filename when company_source is blank preserves
    # behavior for older rows. No hard count cap — MAX_CONTEXT_CHARS in
    # build_user_context() is the real safety net, and the previous cap of 5
    # silently dropped most companies from the AI's numeric context (visible
    # in the AI Library but invisible to chat answers).
    seen_keys = set()
    comm_uploads = []
    for u in all_comm_uploads:
        key = (u.company_source or u.filename or "").strip().lower()
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        comm_uploads.append(u)

    # Load production records
    prod_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.user_id == user_id,
        )
    )
    prod_records = prod_result.scalars().all()
    if not prod_records:
        return None

    prod_dicts = [_record_to_dict(r) for r in prod_records]

    # Load paying companies
    paying_result = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user_id)
    )
    paying_names = [p.company_name for p in paying_result.scalars().all()]

    # Load commission rates so we can compute the EXPECTED commission for
    # unpaid items. Without this, the AI sees only premium/accumulation and
    # reports those as "unpaid amounts", which the user reads as commission
    # (orders of magnitude wrong).
    rates_result = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user_id)
    )
    user_rates = rates_result.scalars().all()

    from datetime import date as _date_today
    _TODAY = _date_today.today()

    def _rate_for(company_name: str, category: str) -> float:
        """Find the most relevant commission rate for a company.

        Selection priority (after company match):
          1. Rate whose validity window covers today, kind=total or single.
          2. Same as (1), kind=book.
          3. Any matching rate, kind=total/single, then book.
          4. Median of remaining matches.

        `reward` and `addition` kinds are NEVER returned alone — they are
        partial components, summing them with `book` is the consumer's job
        (or just don't, since we already insert `total` separately).
        Returns 0 when no rate is on file."""
        if not company_name:
            return 0.0
        target = company_name.strip().lstrip("ה").lower()
        candidates = [
            r for r in user_rates
            if r.company_name and (
                target in r.company_name.lstrip("ה").lower()
                or r.company_name.lstrip("ה").lower() in target
            )
        ]
        if not candidates:
            return 0.0

        def _kind(r) -> str:
            return (getattr(r, "rate_kind", None) or "single").lower()

        def _covers_today(r) -> bool:
            ef, et = getattr(r, "effective_from", None), getattr(r, "effective_to", None)
            if ef and ef > _TODAY:
                return False
            if et and et < _TODAY:
                return False
            return True

        # Pass 1 — current validity, total/single
        for r in candidates:
            if _covers_today(r) and _kind(r) in ("total", "single"):
                return float(r.rate)
        # Pass 2 — current validity, book
        for r in candidates:
            if _covers_today(r) and _kind(r) == "book":
                return float(r.rate)
        # Pass 3 — any validity, total/single, prefer product=NULL default
        prio = [r for r in candidates if _kind(r) in ("total", "single")]
        if prio:
            defaults = [r for r in prio if not r.product]
            return float((defaults[0] if defaults else prio[0]).rate)
        # Pass 4 — book
        books = [r for r in candidates if _kind(r) == "book"]
        if books:
            return float(books[0].rate)
        # Fallback — median, BUT exclude reward/addition (they're partial)
        usable = [float(r.rate) for r in candidates if _kind(r) not in ("reward", "addition")]
        if not usable:
            return 0.0
        usable.sort()
        return usable[len(usable) // 2]

    def _expected_commission(product: dict, rate_frac: float, is_gemel: bool) -> float:
        """Compute the commission the agent should receive for ONE product
        for ONE month, given an agreement rate stored as a fraction
        (0.0032 = 0.32%). Gemel uses the monthly fraction of an annual rate
        on accumulation; insurance uses the rate directly on premium."""
        if rate_frac <= 0:
            return 0.0
        if is_gemel:
            accum = float(product.get("accumulation") or product.get("balance") or 0)
            return accum * rate_frac / 12.0
        premium = float(product.get("premium") or product.get("total_premium") or 0)
        return premium * rate_frac

    comparison_parts = []
    # Period header — tells the AI exactly which month it's reporting on
    # (and surfaces excluded files so it can prompt the user to re-upload).
    if prod_period is not None:
        comparison_parts.append(
            f"=== תקופת השוואה: {prod_period.isoformat()} (חודש הקובץ הנוכחי של הפרודוקציה) ==="
        )
        comparison_parts.append(
            f"קבצי נפרעים תואמי תקופה: {len(comm_uploads)}"
        )
        if excluded_wrong_period:
            sample = ", ".join(f"{fn} ({p})" for fn, p in excluded_wrong_period[:4])
            comparison_parts.append(
                f"קבצי נפרעים מתקופות אחרות שנמצאו במערכת ולא נכללו: {len(excluded_wrong_period)} ({sample}…)"
            )
        if excluded_no_period:
            sample = ", ".join(excluded_no_period[:4])
            comparison_parts.append(
                f"קבצי נפרעים ללא תקופה מזוהה שלא נכללו: {len(excluded_no_period)} ({sample}…). הצע למשתמש להעלות אותם שוב."
            )
        comparison_parts.append("")
    # Cross-company aggregation — the per-company blocks below are organized
    # per commission file, but users frequently ask "across all companies,
    # who's the biggest unpaid". Without a pre-aggregated block the AI either
    # mentally merges (sometimes correctly) or refuses with a "no global
    # view" answer. We compute the merge here once.
    global_unpaid_by_company: dict[str, dict] = {}
    global_unpaid_clients: list[dict] = []  # flat list with co + expected_comm

    for comm_upload in comm_uploads:
        comm_result = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id == comm_upload.id,
                ClientRecord.user_id == user_id,
            )
        )
        comm_records = comm_result.scalars().all()
        if not comm_records:
            continue

        comm_dicts = [_record_to_dict(r) for r in comm_records]
        comparison = compute_comparison(prod_dicts, comm_dicts, paying_names)

        cat = comparison.get("commission_category", "")
        cat_label = comparison.get("commission_category_label", "")
        source = comm_upload.company_source or comm_upload.filename
        is_gemel = cat == "gemel_hishtalmut"

        # Commission company sources for filtering only_production (matches frontend relevantCustomers)
        comm_company = comm_upload.company_source or ""

        def _matches_commission_company(product_company):
            # Use the deterministic normalizer instead of a substring fuzzy
            # match — `"הראל גמל"` and `"הראל חברה לביטוח בע״מ"` both reduce
            # to "הראל", so the customer's products attribute correctly to
            # the commission file. Fixes the silent-drop classification bug
            # that misclassified אבלין פיפרברג.
            from app.utils.company_norm import same_company
            return same_company(comm_company, product_company)

        # Classify customers exactly like the dashboard
        matched = [c for c in comparison["customers"] if c["match_status"] == "matched"]
        only_comm = [c for c in comparison["customers"] if c["match_status"] == "only_commission"]

        # Filter only_production to relevant commission company (like frontend relevantCustomers)
        relevant_only_prod = []
        for c in comparison["customers"]:
            if c["match_status"] != "only_production":
                continue
            relevant_products = [
                p for p in c.get("production_products", [])
                if _matches_commission_company(p.get("company")) or _matches_commission_company(p.get("company_full"))
            ]
            if relevant_products:
                c_copy = dict(c)
                c_copy["production_products"] = relevant_products
                relevant_only_prod.append(c_copy)

        # "לא שולם" = relevant only_production, filtered by accumulation for gemel
        if is_gemel:
            unpaid = [c for c in relevant_only_prod
                      if any((p.get("accumulation") or 0) > 0 for p in c.get("production_products", []))]
        else:
            unpaid = relevant_only_prod

        # Dashboard total = matched + unpaid + only_commission
        dashboard_total = len(matched) + len(unpaid) + len(only_comm)
        commission_customers = matched + only_comm

        # Commission totals (from matched + only_commission customers)
        total_commission = sum(c.get("total_commission") or 0 for c in commission_customers)

        # Total balance from all commission products (matched + unmatched)
        total_balance = 0
        for c in commission_customers:
            for p in c.get("product_matches", {}).get("matched", []):
                total_balance += p.get("balance") or 0
            for p in c.get("product_matches", {}).get("unmatched_commission", []):
                total_balance += p.get("balance") or 0

        # Unpaid amounts — TWO different numbers, both important:
        #   - unpaid_premium: gross premium (or accumulation for gemel) the
        #     client paid the insurance company. This is the BIG number.
        #   - unpaid_expected_commission: what the agent should have received
        #     based on the agreement rate. This is the SMALL number and the
        #     one the user actually means when asking "what wasn't paid to me".
        rate_frac_for_cat = _rate_for(source, "gemel" if is_gemel else "insurance")
        unpaid_premium = 0.0
        unpaid_expected_commission = 0.0
        for c in unpaid:
            for p in c.get("production_products", []):
                # Cast through float() — production_products values may be
                # Decimal (from SQLAlchemy Numeric columns), and Decimal+float
                # raises TypeError. Old code used int 0 init which silently
                # promoted; we use float 0.0 so we must coerce explicitly.
                premium_or_accum = float(p.get("premium") or 0) or float(p.get("accumulation") or 0)
                unpaid_premium += premium_or_accum
                unpaid_expected_commission += _expected_commission(p, rate_frac_for_cat, is_gemel)

        # Per-company commission breakdown (matched + only_commission)
        comm_by_company = {}
        for c in commission_customers:
            for p in c.get("product_matches", {}).get("matched", []):
                co = p.get("company") or "לא ידוע"
                comm_by_company.setdefault(co, {"count": 0, "commission": 0})
                comm_by_company[co]["count"] += 1
                comm_by_company[co]["commission"] += p.get("commission") or 0
            for p in c.get("product_matches", {}).get("unmatched_commission", []):
                co = p.get("company") or "לא ידוע"
                comm_by_company.setdefault(co, {"count": 0, "commission": 0})
                comm_by_company[co]["count"] += 1
                comm_by_company[co]["commission"] += p.get("commission") or 0

        # Per-company unpaid breakdown — tracks both premium and the expected
        # commission (premium × agreement rate, or accum × rate / 12 for gemel).
        unpaid_by_company = {}
        for c in unpaid:
            for p in c.get("production_products", []):
                co = p.get("company") or p.get("company_full") or "לא ידוע"
                bucket = unpaid_by_company.setdefault(
                    co, {"customers": [], "premium": 0.0, "expected_commission": 0.0, "rate_frac": 0.0}
                )
                bucket["rate_frac"] = _rate_for(co, "gemel" if is_gemel else "insurance")
                name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('id_number', '')
                premium_val = float(p.get("premium") or 0)
                exp_comm = _expected_commission(p, bucket["rate_frac"], is_gemel)
                if name not in [n for n, _, _ in bucket["customers"]]:
                    bucket["customers"].append((name, premium_val, exp_comm))
                bucket["premium"] += premium_val
                bucket["expected_commission"] += exp_comm

                # Also accumulate into the cross-company view.
                gbucket = global_unpaid_by_company.setdefault(
                    co, {"customers_count": 0, "premium": 0.0, "expected_commission": 0.0}
                )
                gbucket["premium"] += premium_val
                gbucket["expected_commission"] += exp_comm
                global_unpaid_clients.append({
                    "name": name,
                    "company": co,
                    "premium": premium_val,
                    "expected_commission": exp_comm,
                    "id_number": c.get("id_number"),
                })

        part = [
            f"\n--- השוואת נפרעים: {source} ({cat_label}) ---",
            f"קובץ נפרעים: {comm_upload.filename}",
            f"סה\"כ לקוחות בהשוואה: {dashboard_total}",
            f"נמצא בשניהם (משולם): {len(matched)} ({_pct(len(matched), dashboard_total)}%)",
            f"לא שולם (בפרודוקציה אבל לא בנפרעים — חייבים לסוכן): {len(unpaid)} ({_pct(len(unpaid), dashboard_total)}%)",
            f"רק בנפרעים (בנפרעים אבל לא בפרודוקציה — לא חייבים לסוכן): {len(only_comm)} ({_pct(len(only_comm), dashboard_total)}%)",
            f"הערה חשובה: כש'חייבים לי' = לקוחות 'לא שולם' בלבד. 'רק בנפרעים' הם לקוחות שהחברה משלמת עליהם עמלה אבל לא מופיעים בפרודוקציה.",
            f"סה\"כ עמלה שהתקבלה: {total_commission:,.0f}₪",
            f"סה\"כ יתרה: {total_balance:,.0f}₪",
        ]

        # Commission by company
        if comm_by_company:
            co_lines = ", ".join(
                f"{co}({v['count']} מוצרים, עמלה: {v['commission']:,.0f}₪)"
                for co, v in sorted(comm_by_company.items(), key=lambda x: x[1]["commission"], reverse=True)
            )
            part.append(f"עמלות שהתקבלו לפי חברה: {co_lines}")

        if unpaid:
            part.append(
                f"סה\"כ פרמיה לא משולמת (סכום ברוטו שלקוחות שילמו לחברה): {unpaid_premium:,.0f}₪"
            )
            if unpaid_expected_commission > 0:
                part.append(
                    f"סה\"כ עמלה צפויה לא שולמה לסוכן (פרמיה × שיעור הסכם, חישוב המערכת): "
                    f"{unpaid_expected_commission:,.2f}₪"
                )
            else:
                part.append(
                    "הערה: אין שיעור הסכם בטבלה לחברה זו — לכן לא ניתן לחשב עמלה צפויה. "
                    "דווח רק את הפרמיה ובקש מהמשתמש להוסיף שיעור."
                )
            # Per-company breakdown: name(premium → expected commission)
            if unpaid_by_company:
                for co, data in sorted(unpaid_by_company.items(), key=lambda x: x[1]["expected_commission"], reverse=True):
                    names_with_amounts = ", ".join(
                        f"{name}(פרמיה {premium:,.0f}₪→עמלה צפויה {exp_comm:,.2f}₪)"
                        for name, premium, exp_comm in data["customers"][:5]
                    )
                    rate_pct = data["rate_frac"] * 100
                    rate_note = f"שיעור {rate_pct:.2f}%" if rate_pct > 0 else "אין שיעור בטבלה"
                    part.append(
                        f"לא משולמים מ{co} ({len(data['customers'])} לקוחות, "
                        f"פרמיה: {data['premium']:,.0f}₪, "
                        f"עמלה צפויה: {data['expected_commission']:,.2f}₪, "
                        f"{rate_note}): {names_with_amounts}"
                    )
            else:
                unpaid_names = [
                    f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('id_number', '')
                    for c in unpaid[:10]
                ]
                part.append(f"לקוחות לא משולמים: {', '.join(unpaid_names)}")

        comparison_parts.append("\n".join(part))

    if not comparison_parts:
        return None

    # Cross-company unpaid summary — emitted as the FIRST block so it's the
    # easiest thing the AI reaches for when the question spans companies.
    if global_unpaid_clients:
        # Dedupe by (id_number, company) — same client may have appeared
        # multiple times if they have multiple products in the same company.
        # Already accumulated into the dict above via .setdefault; the flat
        # list keeps every product-row so we can rank by individual amount.
        agg = {}
        for row in global_unpaid_clients:
            key = (row["id_number"] or row["name"], row["company"])
            a = agg.setdefault(key, {
                "name": row["name"], "company": row["company"],
                "premium": 0.0, "expected_commission": 0.0,
            })
            a["premium"] += row["premium"]
            a["expected_commission"] += row["expected_commission"]
        # Sort by expected commission (the number the user cares about) desc.
        top_clients = sorted(agg.values(), key=lambda x: x["expected_commission"], reverse=True)[:15]
        total_premium = sum(b["premium"] for b in global_unpaid_by_company.values())
        total_expected = sum(b["expected_commission"] for b in global_unpaid_by_company.values())

        cross_block = [
            "\n--- סיכום כללי לכלל החברות: לא משולמים ---",
            f"סה\"כ פרמיה לא משולמת מכלל החברות (ברוטו): {total_premium:,.0f}₪",
            f"סה\"כ עמלה צפויה לא שולמה לסוכן מכלל החברות: {total_expected:,.2f}₪",
            "פירוט לפי חברה (ממוין לפי עמלה צפויה):",
        ]
        for co, data in sorted(global_unpaid_by_company.items(), key=lambda x: x[1]["expected_commission"], reverse=True):
            cross_block.append(
                f"  {co}: פרמיה {data['premium']:,.0f}₪ → עמלה צפויה {data['expected_commission']:,.2f}₪"
            )
        cross_block.append("הלקוחות הלא משולמים הגדולים ביותר (top 15, מכלל החברות, ממוין לפי עמלה צפויה):")
        for client in top_clients:
            cross_block.append(
                f"  {client['name']} ({client['company']}): "
                f"פרמיה {client['premium']:,.0f}₪ → עמלה צפויה {client['expected_commission']:,.2f}₪"
            )
        cross_block.append(
            "הערה ל-AI: השתמש בבלוק הזה כשמשתמש שואל 'מי הכי לא משולם / הלקוחות הגדולים ביותר / "
            "מהן ההפסדים שלי מכלל החברות'. הנתונים כבר חושבו, אין צורך לאגד מחדש. "
            "**חובה** לסיים את התשובה ב-viz מסוג bar עם עד 10 הלקוחות הראשונים מהבלוק, "
            "value = עמלה צפויה. דוגמה: "
            "<<VIZ:{\"type\":\"bar\",\"title\":\"הלקוחות הלא משולמים הגדולים ביותר\","
            "\"unit\":\"₪\",\"direction\":\"down\","
            "\"data\":[{\"label\":\"<שם לקוח>\",\"value\":<עמלה צפויה>}]}>>"
        )
        comparison_parts.insert(0, "\n".join(cross_block))

    return "\n".join(comparison_parts)


async def _get_myfile_context(db: AsyncSession, user_id: uuid.UUID, prod_upload: FileUpload) -> str | None:
    """Get My File (recruits) comparison context against production."""
    # Load recruits
    recruits_result = await db.execute(
        select(Recruit).where(Recruit.user_id == user_id).order_by(Recruit.created_at.desc())
    )
    recruits = recruits_result.scalars().all()
    if not recruits:
        return None

    # Group recruits by normalized id (keep first per client)
    recruits_by_id = {}
    for r in recruits:
        key = _normalize_id(r.id_number)
        if key not in recruits_by_id:
            recruits_by_id[key] = r

    # Load production records grouped by normalized id
    prod_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.user_id == user_id,
        )
    )
    prod_records = prod_result.scalars().all()
    prod_by_id = {}
    for r in prod_records:
        if r.id_number:
            prod_by_id.setdefault(_normalize_id(r.id_number), []).append(r)

    found_count = 0
    found_clients = []
    not_found = []
    total_premium_found = 0.0
    total_recruit_amount = 0.0
    company_stats = {}
    # Monthly breakdown by sign_date (YYYY-MM -> {total, by_company})
    monthly_stats = {}

    HEBREW_MONTHS = {
        1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל", 5: "מאי", 6: "יוני",
        7: "יולי", 8: "אוגוסט", 9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
    }

    for norm_id, recruit in recruits_by_id.items():
        prod_recs = prod_by_id.get(norm_id, [])
        comp = recruit.company or "לא ידוע"
        if comp not in company_stats:
            company_stats[comp] = {"found": 0, "not_found": 0, "premium": 0.0}

        recruit_amount = float(recruit.amount or 0)
        total_recruit_amount += recruit_amount

        if prod_recs:
            found_count += 1
            premium = sum(float(r.total_premium or 0) for r in prod_recs)
            total_premium_found += premium
            company_stats[comp]["found"] += 1
            company_stats[comp]["premium"] += premium
            found_clients.append(recruit)
        else:
            not_found.append(recruit)
            company_stats[comp]["not_found"] += 1

        # Monthly bucket by sign_date
        if recruit.sign_date:
            ym = recruit.sign_date.strftime("%Y-%m")
            bucket = monthly_stats.setdefault(ym, {"total": 0, "by_company": {}})
            bucket["total"] += 1
            bucket["by_company"][comp] = bucket["by_company"].get(comp, 0) + 1

    total = len(recruits_by_id)
    not_found_count = total - found_count
    with_sign_date = sum(1 for r in recruits_by_id.values() if r.sign_date)
    without_sign_date = total - with_sign_date

    parts = [
        "\n--- קובץ אישי (My File) ---",
        f"סה\"כ לקוחות בקובץ אישי: {total}",
        f"סה\"כ סכום בקובץ אישי: {total_recruit_amount:,.0f}₪",
        f"נמצאו בפרודוקציה: {found_count} ({_pct(found_count, total)}%)",
        f"לא נמצאו בפרודוקציה: {not_found_count} ({_pct(not_found_count, total)}%)",
        f"סה\"כ פרמיה של לקוחות שנמצאו: {total_premium_found:,.0f}₪",
        f"לקוחות עם תאריך חתימה/הצטרפות: {with_sign_date} מתוך {total}",
    ]
    if without_sign_date:
        parts.append(
            f"⚠ {without_sign_date} לקוחות בקובץ האישי חסר להם תאריך חתימה — "
            "לא ייכללו בספירות החודשיות למטה. ייתכן שיש לעדכן את הקובץ או להעלות אותו שוב."
        )

    # Monthly breakdown with Hebrew month names — helps AI answer "how many in March?"
    if monthly_stats:
        parts.append("\nגיוסים לפי חודש (לפי תאריך חתימה):")
        for ym in sorted(monthly_stats.keys(), reverse=True):
            year, month_num = ym.split("-")
            month_name = HEBREW_MONTHS.get(int(month_num), month_num)
            bucket = monthly_stats[ym]
            by_co = ", ".join(
                f"{co}: {n}"
                for co, n in sorted(bucket["by_company"].items(), key=lambda x: x[1], reverse=True)
            )
            parts.append(f"  {month_name} {year} ({ym}): {bucket['total']} לקוחות — {by_co}")

    if company_stats:
        co_lines = ", ".join(
            f"{co}(נמצאו {v['found']}, לא נמצאו {v['not_found']}, פרמיה: {v['premium']:,.0f}₪)"
            for co, v in sorted(company_stats.items(), key=lambda x: x[1]["found"] + x[1]["not_found"], reverse=True)[:8]
        )
        parts.append(f"פירוט לפי חברה: {co_lines}")

    # Detail clients — sorted by sign_date desc so recent recruits come first,
    # which matters when the global context cap truncates the tail.
    def _format_recruit(r, include_status=False):
        name = f"{r.first_name} {r.last_name}".strip() or r.id_number
        amt = float(r.amount or 0)
        product = r.product or ""
        sign = r.sign_date.strftime("%Y-%m-%d") if r.sign_date else "—"
        detail = f"  {name} (ת.ז: {r.id_number}, חברה: {r.company or '—'}, תאריך חתימה: {sign}"
        if product:
            detail += f", מוצר: {product}"
        if amt > 0:
            detail += f", סכום: {amt:,.0f}₪"
        if include_status and r.customer_status:
            detail += f", סטטוס: {r.customer_status}"
        detail += ")"
        return detail

    def _sort_key(r):
        # Most recent sign_date first; rows without sign_date go last.
        return (r.sign_date is None, -(r.sign_date.toordinal() if r.sign_date else 0))

    if not_found:
        parts.append(f"\nלקוחות שלא נמצאו בפרודוקציה ({len(not_found)}) — ייתכן שגויסו אחרי תאריך קובץ הפרודוקציה:")
        for r in sorted(not_found, key=_sort_key):
            parts.append(_format_recruit(r, include_status=True))

    if found_clients:
        parts.append(f"\nלקוחות שנמצאו בפרודוקציה ({len(found_clients)}):")
        for r in sorted(found_clients, key=_sort_key):
            parts.append(_format_recruit(r))

    return "\n".join(parts)


async def _get_commission_rates_context(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Get commission rates and volume rates as context."""
    # Nifraim commission rates
    rates_result = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user_id)
    )
    rates = rates_result.scalars().all()

    # Volume commission rates
    vol_rates_result = await db.execute(
        select(VolumeCommissionRate).where(VolumeCommissionRate.user_id == user_id)
    )
    vol_rates = vol_rates_result.scalars().all()

    if not rates and not vol_rates:
        return None

    parts = [
        "\n=== שיעורי עמלה (אחוזים בלבד — לא סכומים!) ===",
        "להבהרת תנאי ההסכם עם כל חברה. אסור להכפיל אחוזים אלה בפרמיה/צבירה כדי לדווח סכום עמלה.",
    ]
    if rates:
        parts.append("שיעורי עמלת נפרעים (לפי חברה · מוצר · סוג):")
        # Group by (company, product) so the AI can see e.g.
        #   הפניקס · השתלות וטיפולים מיוחדים (book): 15.00%
        #   הפניקס · השתלות וטיפולים מיוחדים (reward): 7.20%
        # without conflating components into a single fake number.
        _KIND_LABEL = {
            "book": "ספר", "reward": "תגמול",
            "total": "סה״כ", "single": "single", "addition": "תוספת",
        }
        from collections import defaultdict
        grouped: dict[tuple[str, str], list] = defaultdict(list)
        for r in rates:
            grouped[(r.company_name or "", r.product or "(default)")].append(r)
        for (company, product), rows in grouped.items():
            for r in rows:
                kind = (getattr(r, "rate_kind", None) or "single").lower()
                kind_label = _KIND_LABEL.get(kind, kind)
                freq = f", תדירות: {r.payment_frequency}" if r.payment_frequency else ""
                eff = ""
                if r.effective_from or r.effective_to:
                    ef = r.effective_from.isoformat() if r.effective_from else "—"
                    et = r.effective_to.isoformat() if r.effective_to else "—"
                    eff = f" [תוקף {ef}→{et}]"
                parts.append(
                    f"  {company} · {product} ({kind_label}): "
                    f"{float(r.rate) * 100:.2f}%{freq}{eff}"
                )

    if vol_rates:
        parts.append("שיעורי עמלת היקפים:")
        for r in vol_rates:
            nifraim = f"נפרעים: {float(r.nifraim_rate) * 100:.2f}%" if r.nifraim_rate else ""
            volume = f"היקפים: {float(r.volume_rate_per_million):,.0f}₪/מיליון" if r.volume_rate_per_million else ""
            freq = f", תדירות: {r.payment_frequency}" if r.payment_frequency else ""
            rate_parts = [p for p in [nifraim, volume] if p]
            parts.append(f"  {r.company_name}: {', '.join(rate_parts)}{freq}")

    return "\n".join(parts)


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "0"
    return f"{part * 100 / total:.0f}"


STOP_WORDS = {'האם', 'מה', 'כמה', 'של', 'את', 'לי', 'על', 'יש', 'אם', 'או',
              'הוא', 'היא', 'זה', 'זו', 'לא', 'כן', 'איפה', 'למה', 'מי', 'איך',
              'שלי', 'שלו', 'שלה', 'לו', 'לה',
              'גם', 'עם', 'בין', 'כל', 'אני', 'הם', 'הן', 'אנחנו', 'אתה', 'את'}


async def _search_customers(db: AsyncSession, user_id: uuid.UUID, prod_upload_id, question: str) -> str | None:
    """Search for specific customers mentioned in the question, in both production and commission files."""
    import re

    # Extract potential ID numbers (5+ digits)
    id_patterns = re.findall(r'\d{5,}', question)

    # Extract Hebrew name words (filter stop words)
    words = re.findall(r'[\u0590-\u05FF]+', question)
    name_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]

    if not id_patterns and not name_words:
        return None

    # Get all upload IDs to search (production + commission)
    upload_ids_to_search = [(prod_upload_id, "פרודוקציה")]

    comm_uploads_result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user_id,
            FileUpload.file_category == "commission",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    seen_filenames = set()
    for u in comm_uploads_result.scalars().all():
        if u.filename not in seen_filenames:
            seen_filenames.add(u.filename)
            label = f"נפרעים ({u.company_source or u.filename})"
            upload_ids_to_search.append((u.id, label))
        if len(seen_filenames) >= 5:
            break

    all_lines = ["\n--- תוצאות חיפוש לקוחות ---"]

    for upload_id, source_label in upload_ids_to_search:
        results = []

        # Search by ID number
        for id_pat in id_patterns:
            q = await db.execute(
                select(ClientRecord).where(
                    ClientRecord.upload_id == upload_id,
                    ClientRecord.id_number.like(f"%{id_pat}%"),
                ).limit(10)
            )
            results.extend(q.scalars().all())

        # Search by name
        for word in name_words[:3]:
            q = await db.execute(
                select(ClientRecord).where(
                    ClientRecord.upload_id == upload_id,
                    (ClientRecord.first_name.ilike(f"%{word}%")) |
                    (ClientRecord.last_name.ilike(f"%{word}%")),
                ).limit(10)
            )
            results.extend(q.scalars().all())

        if not results:
            continue

        # Deduplicate by id
        seen = set()
        unique = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)

        all_lines.append(f"\n[{source_label}]")
        for r in unique[:10]:
            name = f"{r.first_name or ''} {r.last_name or ''}".strip()
            premium = float(r.total_premium or 0)
            accum = float(r.accumulation or 0)
            commission = float(r.commission_before_fee or 0) if hasattr(r, 'commission_before_fee') and r.commission_before_fee else 0
            line = (
                f"שם: {name}, ת.ז: {r.id_number}, חברה: {r.receiving_company or '—'}, "
                f"מוצר: {r.product_type or r.product or '—'}, "
                f"סטטוס: {r.product_status or '—'}, "
                f"פרמיה: {premium:,.0f}₪, צבירה: {accum:,.0f}₪"
            )
            if commission > 0:
                line += f", עמלה: {commission:,.0f}₪"
            all_lines.append(line)

    if len(all_lines) <= 1:
        return None

    return "\n".join(all_lines)


async def _get_historical_context(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Get multi-month production history from pre-computed summaries."""
    result = await db.execute(
        select(ProductionSummary)
        .where(ProductionSummary.user_id == user_id)
        .order_by(desc(ProductionSummary.upload_date))
        .limit(12)
    )
    summaries = result.scalars().all()
    if not summaries:
        return None

    parts = ["=== היסטוריית פרודוקציה ==="]
    parts.append("חודש | לקוחות | פרמיה | צבירה | שינוי פרמיה")
    parts.append("---|---|---|---|---")

    for s in summaries:
        premium_change = ""
        if s.changes_json:
            pct = s.changes_json.get("premium_diff_pct", 0)
            if pct > 0:
                premium_change = f"+{pct}%"
            elif pct < 0:
                premium_change = f"{pct}%"

        parts.append(
            f"{s.period_label} | {s.unique_clients:,} | "
            f"{float(s.total_premium):,.0f}₪ | {float(s.total_accumulation):,.0f}₪ | "
            f"{premium_change or '—'}"
        )

    # Add notable changes for the most recent month
    latest = summaries[0]
    if latest.changes_json:
        ch = latest.changes_json
        changes_parts = []
        if ch.get("new_clients", 0) > 0:
            changes_parts.append(f"+{ch['new_clients']} לקוחות חדשים")
        if ch.get("removed_clients", 0) > 0:
            changes_parts.append(f"-{ch['removed_clients']} עזבו")
        if ch.get("premium_diff", 0) != 0:
            diff = ch["premium_diff"]
            sign = "+" if diff > 0 else ""
            changes_parts.append(f"פרמיה {sign}{diff:,.0f}₪")
        if changes_parts:
            parts.append(f"\nשינויים בולטים ({latest.period_label}): {', '.join(changes_parts)}")

    return "\n".join(parts)


async def _get_customer_history(
    db: AsyncSession, user_id: uuid.UUID, question: str
) -> str | None:
    """Get per-customer historical data across production uploads when a specific customer is mentioned."""
    import re

    # Extract ID number from question
    id_match = re.search(r'\d{5,}', question)
    if not id_match:
        return None

    search_id = id_match.group(0).lstrip('0') or '0'

    # Query this customer across all production uploads
    result = await db.execute(
        select(
            FileUpload.filename,
            FileUpload.uploaded_at,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
            func.count().label("products"),
        )
        .join(FileUpload, ClientRecord.upload_id == FileUpload.id)
        .where(
            ClientRecord.id_number == search_id,
            FileUpload.user_id == user_id,
            FileUpload.file_category == "production",
        )
        .group_by(FileUpload.id, FileUpload.filename, FileUpload.uploaded_at)
        .order_by(desc(FileUpload.uploaded_at))
        .limit(12)
    )
    rows = result.all()
    if not rows:
        return None

    name = f"{rows[0].first_name or ''} {rows[0].last_name or ''}".strip()
    parts = [f"=== היסטוריית לקוח: {name} (ת.ז {search_id}) ==="]
    parts.append("תקופה | פרמיה | צבירה | מוצרים")
    parts.append("---|---|---|---")

    for r in rows:
        period = r.uploaded_at.strftime("%Y-%m")
        parts.append(
            f"{period} | {float(r.premium):,.0f}₪ | {float(r.accumulation):,.0f}₪ | {r.products}"
        )

    return "\n".join(parts)


def _detect_question_topics(question: str) -> set[str]:
    """Detect which data sources are relevant to the user's question."""
    q = question.lower()
    topics = set()

    # Always include production (base context)
    topics.add("production")

    # Commission / comparison keywords
    if any(w in q for w in ["נפרעים", "עמלה", "עמלות", "משולם", "לא שולם", "commission", "השוואה", "השוואת"]):
        topics.add("comparison")

    # My file / recruits keywords
    if any(w in q for w in ["קובץ אישי", "מגויס", "מגויסים", "גיוס", "תיק אישי", "ניהול תיק", "מעקב"]):
        topics.add("myfile")

    # Commission rates keywords
    if any(w in q for w in ["שיעור", "שיעורי", "אחוז", "rates", "תעריף", "היקפים"]):
        topics.add("rates")

    # History / trends keywords
    if any(w in q for w in ["מגמה", "מגמות", "היסטוריה", "שינוי", "שינויים", "חודש קודם",
                             "חודשים", "לאורך זמן", "השוואה בין חודשים", "גדל", "ירד",
                             "עלה", "ירידה", "עלייה", "צמיחה", "trend", "history"]):
        topics.add("history")

    # Customer search — if question has names or IDs
    import re
    if re.search(r'\d{5,}', question) or len([w for w in re.findall(r'[\u0590-\u05FF]+', question) if w not in STOP_WORDS and len(w) > 1]) > 0:
        topics.add("search")

    # If no specific topic detected, include everything
    if topics == {"production"}:
        topics = {"production", "comparison", "myfile", "rates", "history"}

    return topics


MAX_CONTEXT_CHARS = 120000  # ~30K tokens — must fit one comparison block per commission company; truncation here silently hid later companies from the AI


async def _get_commission_boundaries(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Authoritative list of which companies have uploaded commission (נפרעים) files.

    This block gives the AI a hard boundary — it must NEVER report commission
    amounts for a company not in this list.
    """
    result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user_id,
            FileUpload.file_category == "commission",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    uploads = result.scalars().all()

    header = "=== קבצי נפרעים שהועלו (גבול הנתונים) ==="
    if not uploads:
        return (
            f"{header}\n"
            "אין קבצי נפרעים במערכת. לא ניתן לדווח על סכומי עמלה בפועל לשום חברה.\n"
            "במענה על שאלות על עמלות — ציין זאת במפורש."
        )

    # Group by company_source (fallback: filename)
    by_company: dict[str, list[FileUpload]] = {}
    for u in uploads:
        key = u.company_source or u.filename or "חברה לא ידועה"
        by_company.setdefault(key, []).append(u)

    lines = [
        header,
        "רק לחברות ברשימה הזו יש סכומי עמלה בפועל בקבצים. "
        "לכל חברה אחרת — אין נתוני עמלה, אל תמציא סכומים:"
    ]
    for co, files in by_company.items():
        file_list = ", ".join(f"{f.filename} ({f.uploaded_at.strftime('%Y-%m-%d')})" for f in files)
        lines.append(f"- {co}: {file_list}")
    return "\n".join(lines)


_DOCS_BLOCK_BUDGET = 22000  # max chars contributed by uploaded documents

# Hebrew triggers that signal a document-oriented question. When the user
# asks anything like "summarize the document" / "what does the agreement say"
# / "what commission rates do I get at <company>", we treat the question as
# doc-oriented and expand to (or attach) the PDF.
_DOC_QUESTION_MARKERS = (
    "מסמך", "מהמסמך", "במסמך", "המסמך",
    "נספח", "חוזה", "הסכם", "הסכמ", "חוזר",
    "סכם", "סיכום", "תקציר",
    "מה כתוב", "מפרט", "כתוב במסמך", "כתוב בהסכם",
    "פרק", "סעיף", "טבלת",
    # Commission-related terms — when paired with a known uploaded company,
    # we want to attach that company's source PDF to the answer.
    "עמלה", "עמלות", "נפרעים", "היקף", "היקפים", "עמלת ספר",
    "החזר", "ביטול", "אחוז", "שיעור", "שיעורי",
)


def _company_aliases(company: str) -> list[str]:
    """Return short matchable variants of a company name.

    Example: "הראל חברה לביטוח בע״מ" → ["הראל חברה לביטוח בע״מ", "הראל"].
    Lets us match a user typing just "הראל" against the stored full name.
    """
    c = (company or "").strip()
    if not c:
        return []
    aliases = [c.lower()]
    # First whitespace-separated word, if it's not a generic stop word.
    head = c.split()[0] if c.split() else ""
    if head and len(head) >= 3 and head.lower() not in {"חברה", "ביטוח", "בית"}:
        aliases.append(head.lower())
    return aliases


def _doc_matches_question(doc: "AiDocument", question: str) -> bool:
    if not question or not doc:
        return False
    q = question.lower()
    if doc.filename and doc.filename in question:
        return True
    for c in (doc.companies_mentioned or []):
        for alias in _company_aliases(c):
            if alias and alias in q:
                return True
    return False


def _question_is_document_oriented(q: str, doc: "AiDocument") -> bool:
    if not q:
        return False
    if any(m in q for m in _DOC_QUESTION_MARKERS):
        return True
    return _doc_matches_question(doc, q)


def _question_mentions_any_doc_marker(q: str) -> bool:
    return bool(q) and any(m in q for m in _DOC_QUESTION_MARKERS)


_MAX_PDF_ATTACHMENTS = 2
_MAX_ATTACHED_BYTES = 25 * 1024 * 1024  # keep payload under Anthropic limits


async def _find_attachments_for_question(
    db: AsyncSession, user_id: uuid.UUID, question: str
) -> list["AiDocument"]:
    """Pick up to 2 AiDocuments to attach as `document` blocks in the chat
    call. We match on filename or company name in the question; if the
    question is doc-oriented but mentions no specific doc, we fall back to
    the most recent uploaded doc so questions like "סכם את המסמך" still get
    the source attached.
    """
    if not question:
        return []
    result = await db.execute(
        select(AiDocument)
        .where(AiDocument.user_id == user_id, AiDocument.status == "ready")
        .order_by(desc(AiDocument.uploaded_at))
        .limit(10)
    )
    docs = list(result.scalars().all())
    if not docs:
        return []

    matches: list[AiDocument] = []
    for d in docs:
        if _doc_matches_question(d, question):
            matches.append(d)

    # Fallback: doc-oriented question that doesn't name a specific company
    # (e.g. "סכם את המסמך") → attach the latest uploaded doc.
    if not matches and _question_mentions_any_doc_marker(question):
        matches.append(docs[0])

    out: list[AiDocument] = []
    total = 0
    for d in matches[:_MAX_PDF_ATTACHMENTS]:
        if not d.file_path or not os.path.exists(d.file_path):
            continue
        try:
            size = os.path.getsize(d.file_path)
        except OSError:
            continue
        if total + size > _MAX_ATTACHED_BYTES:
            break
        total += size
        out.append(d)
    return out


async def _get_documents_context(db: AsyncSession, user_id: uuid.UUID, question: str = "") -> str | None:
    """Inject summaries (or full content) of uploaded AI documents.

    Two tiers of inclusion:
    - Default: filename + companies + short summary (~250 chars/doc).
    - Document-oriented question (matches _DOC_QUESTION_MARKERS, or
      filename/company keyword): embed the full extracted text so the AI can
      truly answer "summarize this PDF" or "what does section X say".

    Capped at _DOCS_BLOCK_BUDGET chars total to keep the wider context block
    under the model's input budget.
    """
    result = await db.execute(
        select(AiDocument)
        .where(
            AiDocument.user_id == user_id,
            AiDocument.status == "ready",
        )
        .order_by(desc(AiDocument.uploaded_at))
        .limit(10)
    )
    docs = result.scalars().all()
    if not docs:
        return None

    q = question or ""
    lines = ["=== מסמכי AI שהועלו (ידע נצבר) ==="]
    total = len(lines[0])
    for d in docs:
        companies = d.companies_mentioned or []
        co_str = ", ".join(companies) if companies else "—"
        head = f"\n\n• **{d.filename}** ({d.doc_type or 'document'}) — חברות: {co_str}"
        body = f"\n  סיכום: {d.summary or '(אין סיכום)'}"
        chunk = head + body

        if _question_is_document_oriented(q, d):
            full = ((d.structured_data or {}).get("full_content") or "").strip()
            if full:
                remaining = _DOCS_BLOCK_BUDGET - total - len(chunk) - 200
                if remaining > 1000:
                    if len(full) > remaining:
                        full = full[:remaining] + "\n[… חלק מהמסמך קוצץ …]"
                    chunk += f"\n  תוכן המסמך:\n{full}"
            else:
                # Older docs may not have full_content yet — fall back to the
                # structured JSON so the AI still sees the rates.
                try:
                    payload = json.dumps(d.structured_data, ensure_ascii=False)
                except (TypeError, ValueError):
                    payload = ""
                if payload:
                    if len(payload) > 3000:
                        payload = payload[:3000] + "…"
                    chunk += f"\n  נתונים מובנים: {payload}"

        if total + len(chunk) > _DOCS_BLOCK_BUDGET:
            lines.append("\n[… מסמכים נוספים קוצצו לחיסכון בהקשר …]")
            break
        lines.append(chunk)
        total += len(chunk)

    return "".join(lines)


async def build_user_context(db: AsyncSession, user_id, question: str = "") -> str | None:
    prod_context, prod_upload = await _get_production_context(db, user_id)

    # Even without a production file we still want the AI to be helpful when
    # the user has only uploaded reference documents (commission agreements).
    docs_context = await _get_documents_context(db, user_id, question)

    if not prod_context and not docs_context:
        return None

    topics = _detect_question_topics(question) if question else {"production", "comparison", "myfile", "rates", "history"}

    # Always include the commission-files boundary block first — this tells the
    # AI exactly which companies have commission data and prevents fabrication.
    boundaries = await _get_commission_boundaries(db, user_id)
    context_parts = [boundaries]
    if prod_context:
        context_parts.append(prod_context)

    # Historical production trends
    if "history" in topics:
        hist_context = await _get_historical_context(db, user_id)
        if hist_context:
            context_parts.append(hist_context)

        # Per-customer history if a specific ID is mentioned
        if question:
            cust_hist = await _get_customer_history(db, user_id, question)
            if cust_hist:
                context_parts.append(cust_hist)

    if prod_upload:
        if "comparison" in topics:
            comp_context = await _get_comparison_context(db, user_id, prod_upload)
            if comp_context:
                context_parts.append(comp_context)

        if "myfile" in topics:
            myfile_context = await _get_myfile_context(db, user_id, prod_upload)
            if myfile_context:
                context_parts.append(myfile_context)

        # Search for specific customers if question contains names/IDs
        if question and "search" in topics:
            search_context = await _search_customers(db, user_id, prod_upload.id, question)
            if search_context:
                context_parts.append(search_context)

    # Commission rates (independent of production upload)
    if "rates" in topics:
        rates_context = await _get_commission_rates_context(db, user_id)
        if rates_context:
            context_parts.append(rates_context)

    # Uploaded AI documents — already loaded above so we can route around
    # "no production file" mode. Append at the end of the context block.
    if docs_context:
        context_parts.append(docs_context)

    full_context = "\n\n".join(context_parts)

    # Truncate if too long to avoid API overload
    if len(full_context) > MAX_CONTEXT_CHARS:
        full_context = full_context[:MAX_CONTEXT_CHARS] + "\n\n[... נתונים נוספים קוצצו למניעת עומס ...]"

    return full_context


async def _get_market_funds_context(db: AsyncSession) -> str | None:
    """Compact, global mygemel.net snapshot. Always injected — independent of
    the user's own uploads — so the assistant can answer questions like
    "מה התשואות החודש בקופות גמל?" even before any files are uploaded.
    Returns None if the table is empty (e.g. first deploy before scrape).
    """
    rows = (
        await db.execute(select(FundTrack).order_by(FundTrack.sort_order))
    ).scalars().all()
    rows = [r for r in rows if r.month_return is not None]
    if not rows:
        return None

    # Top 3 individual funds per track (the source orders by month-% desc).
    # Cap at 3 to keep the system prompt budget under control — full per-fund
    # data is available via /api/ai/knowledge if the user opens the AI library.
    detail_rows = (
        await db.execute(
            select(FundTrackFund)
            .where(FundTrackFund.rank <= 3)
            .order_by(FundTrackFund.track_id, FundTrackFund.rank)
        )
    ).scalars().all()
    top_by_track: dict[str, list[FundTrackFund]] = {}
    for f in detail_rows:
        top_by_track.setdefault(f.track_id, []).append(f)

    updated = max((r.scraped_at for r in rows if r.scraped_at), default=None)
    updated_str = updated.strftime("%Y-%m-%d") if updated else "לא ידוע"
    period = rows[0].period_label or ""

    lines = [
        "=== נתוני שוק — קופות גמל / השתלמות / חיסכון / גמ\"ל להשקעה ===",
        f"מקור: mygemel.net | מעודכן: {updated_str} | תקופת התייחסות: {period}",
        "ערכי התשואה (ממוצע מסלול + טופ 3 קופות) באחוזים, מסודרים מהטובה ביותר.",
    ]
    for r in rows:
        nums = []
        if r.month_return is not None: nums.append(f"חודשי {float(r.month_return):+.2f}%")
        if r.y1_return    is not None: nums.append(f"שנה {float(r.y1_return):+.2f}%")
        if r.y3_return    is not None: nums.append(f"3ש {float(r.y3_return):+.2f}%")
        if r.y5_return    is not None: nums.append(f"5ש {float(r.y5_return):+.2f}%")
        lines.append(f"- {r.label_he} (ממוצע): {' | '.join(nums)}")
        for f in top_by_track.get(r.id, []):
            if f.month_return is None:
                continue
            lines.append(
                f"    {f.rank}. {f.fund_name}: חודשי {float(f.month_return):+.2f}%"
                + (f" | שנה {float(f.y1_return):+.2f}%" if f.y1_return is not None else "")
            )
    lines.append("הנחיה: ציין את נתוני השוק האלה כשהמשתמש שואל על ביצועי קופות. אל תמציא מספרים — אם הקופה/המסלול אינם ברשימה אמור שאין לך נתון.")
    return "\n".join(lines)


async def stream_chat(
    user_id,
    question: str,
    history: list[dict],
    view_context: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream the AI answer over SSE. Opens its own DB session and releases it
    BEFORE the Claude stream begins — keeping pool connections short-lived.

    Previously the session was injected via `Depends(get_db)` and held for the
    entire stream (5–30s of Claude generation), which (combined with client
    disconnects mid-stream) leaked connections — see Railway log warnings:
    "garbage collector is trying to clean up non-checked-in connection ...".
    """
    from app.database import async_session

    # All DB work happens up-front inside one short-lived session. The Claude
    # streaming loop below runs with NO open DB session.
    async with async_session() as db:
        context = await build_user_context(db, user_id, question=question)
        market_context = await _get_market_funds_context(db)
        attachments = await _find_attachments_for_question(db, user_id, question)

    if context is None and market_context is None:
        yield f"data: {json.dumps({'text': 'אין נתונים במערכת. יש להעלות קבצים תחילה.'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    # `context` may be None when the user has no uploads but market data exists;
    # `SYSTEM_PROMPT.format(context=...)` accepts an empty string fine.
    system_prompt = SYSTEM_PROMPT.format(context=context or "(אין נתונים אישיים — ראה נתוני שוק להלן)")
    if market_context:
        system_prompt += "\n\n" + market_context
    if view_context:
        system_prompt += (
            f"\n\n=== המסך הנוכחי של המשתמש ===\n"
            f"{view_context}\n\n"
            "הנחיה חשובה: הבלוק למעלה הוא מקור האמת ל\"מה שהמשתמש רואה עכשיו\". "
            "אל תגיד שאין לך נתונים השוואתיים או היסטוריים — הבלוק הזה כולל בדיוק את ההשוואה בין שני קבצי הפרודוקציה שהמשתמש צופה בה, "
            "לרבות לקוחות שהשתנו, חדשים, הוסרו, לקוחות שעברו חברה (אותו ת.ז מופיע גם בהוסרו וגם בחדשים עם חברה שונה), "
            "ושינויי פרמיה/צבירה/עמלה לפי חברה. השתמש בנתונים האלו ישירות כדי לענות על כל שאלה הקשורה להשוואה, "
            "למעברי חברה, לעליות/ירידות לפי חברה או לקוח — ואל תמציא שאין לך את הנתון."
        )

    messages = []
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Attach the source PDF(s) when the question is about an uploaded doc —
    # this gives Claude direct access to the agreement instead of only the
    # pre-extracted summary, which is necessarily lossy. We attach BOTH the
    # raw PDF (for tables/layout via vision) AND the pdfplumber text layer
    # (deterministic text scan) — vision fallback handles scanned PDFs.
    # (Loaded above inside the short-lived DB session.)
    if attachments:
        user_blocks: list[dict] = []
        for d in attachments:
            try:
                with open(d.file_path, "rb") as f:
                    pdf_b64 = base64.standard_b64encode(f.read()).decode("ascii")
            except OSError as e:
                logger.warning(f"Could not read attached PDF {d.file_path}: {e}")
                continue
            user_blocks.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
                "title": d.filename,
            })
            text_layer = (d.extracted_text or "").strip()
            if text_layer:
                # Cap to keep input tokens reasonable; head of the doc
                # typically contains the most-asked tables.
                if len(text_layer) > 40000:
                    text_layer = text_layer[:40000] + "\n\n[... text layer truncated ...]"
                user_blocks.append({
                    "type": "text",
                    "text": (
                        f"### שכבת טקסט מ-{d.filename} (מקור אמת לטקסט/מספרים):\n\n"
                        f"{text_layer}"
                    ),
                })
        user_blocks.append({
            "type": "text",
            "text": (
                f"מצורפים {len(attachments)} מסמכים שהמשתמש העלה. ענה על השאלה תוך שימוש ישיר בתוכן המסמכים המצורפים.\n\n"
                "**כללי קריאה של מסמכי הסכמי עמלות בישראל — חשוב מאוד:**\n\n"
                "1. **שמות מוצרים**: צטט בדיוק כפי שהם מופיעים — אל תתרגם, אל תעגל מילים, אל תשנה.\n\n"
                "2. **עמלת ספר + תוספת = סה״כ**: בהסכמי הראל (וחברות דומות) שיעור הנפרעים הסופי הוא סכום של שני רכיבים שמופיעים בטבלאות נפרדות:\n"
                "   • **עמלת ספר** — שיעור בסיס לכל קטגוריה (למשל 11% לחיים/ריסק, 14% לבריאות). מופיעה לרוב ככותרת/הצהרה לפני הטבלה.\n"
                "   • **תוספת נפרעים** — שיעור נוסף לכל מוצר ספציפי (למשל 5% להכנסה למשפחה).\n"
                "   • **סה״כ נפרעים** = עמלת ספר + תוספת נפרעים. **חובה לחבר** ולהציג את כל שלושת המספרים.\n"
                "   דוגמה: חיים — ספר 11%, מגן 1 תוספת 8.2% ⇒ סה״כ 19.2%.\n"
                "   חפש בכל סעיף את עמלת הספר הרלוונטית **לפני** שאתה מציג רק את התוספת.\n\n"
                "3. **קטגוריות**: שמור על ההפרדה במסמך (חיים/ריסק | בריאות | פנסיה־גמל־השתלמות | רכוש־כללי). אל תמזג מוצר מקטגוריה אחת לאחרת.\n\n"
                "4. **טווחים אופייניים**: פנסיה/גמל/השתלמות — 0.2%–0.6%. חיים/בריאות — 4%–9% (לפני הוספת עמלת ספר). אם אתה מקבל מספר שיוצא מהטווח, ודא שזיהית את הקטגוריה הנכונה.\n\n"
                "5. **תנאי ביטול / החזרי עמלה (Clawback)**: ב**כל** הסכם עמלה ביטוחי בישראל יש מנגנון החזר במקרה של ביטול מוקדם, גם אם הוא לא מופיע בעמוד הראשון. חובה לחפש אותו לפני שאתה אומר 'לא נמצא':\n"
                "   • מילות חיפוש: 'ביטול', 'החזר', 'החזרי עמלה', 'ניכויי ביטולים', 'Clawback', 'פדיון', 'משיכה', 'ניוד', 'מחיקת תפוקה', 'הפסקת גבייה', 'ירידה בפרמיה'.\n"
                "   • מבנה אופייני: טבלה של אחוז החזרה לפי משך הזמן מהמכירה — למשל '12 חודשים ראשונים = 100% החזר', '13–24 חודשים = 50%', 'מעבר ל-24 חודשים = 0%'.\n"
                "   • בדרך כלל הסעיף מציין גם: ההחזר יחסי לחלק שבוטל, אפשרות קיזוז מעמלות עתידיות, וטריגרים נוספים (ביטול, פדיון, ניוד, ירידה מהותית בפרמיה).\n"
                "   • כשאתה משיב — הצג את הטבלה המלאה + הטריגרים + מנגנון הקיזוז.\n\n"
                "6. **שלמות**: אם הטבלה ארוכה, כלול את כל השורות — אל תקצר. לפני שאתה אומר 'אין במסמך' — חפש לעומק את הסעיף הרלוונטי וצטט מאיפה במסמך הסקת זאת.\n\n"
                f"שאלת המשתמש: {question}"
            ),
        })
        messages.append({"role": "user", "content": user_blocks})
    else:
        messages.append({"role": "user", "content": question})

    if not settings.ANTHROPIC_API_KEY:
        yield f"data: {json.dumps({'text': 'שגיאה: מפתח API של Anthropic לא הוגדר. יש להגדיר ANTHROPIC_API_KEY.'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Try Sonnet twice (with backoff), then Haiku as fallback
    attempts = [
        ("claude-sonnet-4-20250514", 0),
        ("claude-sonnet-4-20250514", 2),
        ("claude-haiku-4-5-20251001", 1),
    ]
    last_error = None

    # Sentinel-aware streaming: the AI may append `<<VIZ:{...}>>` at the very
    # end of its answer. Strip it from the visible text and emit a separate
    # `{"viz": {...}}` SSE event so the frontend can render a Remotion viz.
    VIZ_OPEN = "<<VIZ:"
    VIZ_CLOSE = ">>"
    HOLD = len(VIZ_OPEN) - 1  # = 5; hold back last 5 chars in case of partial marker

    # Accumulator for the numeric validator — collects ONLY the user-visible
    # text (viz JSON excluded). Fed into validate_answer() just before the
    # `done` event so warnings surface on the same message.
    visible_text_chunks: list[str] = []

    for model, delay in attempts:
        if delay:
            await asyncio.sleep(delay)
        try:
            viz_state = "text"
            tail = ""      # chars held back in `text` state
            viz_buf = ""   # contents accumulated in `buffering_viz` state
            async with client.messages.stream(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            ) as stream:
                viz_emitted_in_this_attempt = False
                async for chunk in stream.text_stream:
                    if viz_state == "text":
                        combined = tail + chunk
                        open_idx = combined.find(VIZ_OPEN)
                        if open_idx != -1:
                            before = combined[:open_idx]
                            if before:
                                visible_text_chunks.append(before)
                                yield f"data: {json.dumps({'text': before}, ensure_ascii=False)}\n\n"
                            viz_buf = combined[open_idx + len(VIZ_OPEN):]
                            tail = ""
                            viz_state = "buffering_viz"
                            close_idx = viz_buf.find(VIZ_CLOSE)
                            if close_idx != -1:
                                viz_raw = viz_buf[:close_idx]
                                try:
                                    viz = json.loads(viz_raw)
                                    yield f"data: {json.dumps({'viz': viz}, ensure_ascii=False)}\n\n"
                                    viz_emitted_in_this_attempt = True
                                    logger.warning(f"VIZ emitted: type={viz.get('type')} title={viz.get('title', '')[:50]}")
                                except json.JSONDecodeError:
                                    logger.warning(f"Bad viz JSON: {viz_raw[:120]}")
                                after = viz_buf[close_idx + len(VIZ_CLOSE):]
                                viz_state = "text"
                                viz_buf = ""
                                tail = after
                        else:
                            # Only hold chars back if the tail actually looks like
                            # a partial "<<VIZ:" prefix — otherwise stream immediately.
                            hold = 0
                            for i in range(min(len(VIZ_OPEN), len(combined)), 0, -1):
                                if combined.endswith(VIZ_OPEN[:i]):
                                    hold = i
                                    break
                            safe_end = len(combined) - hold
                            if safe_end > 0:
                                visible_text_chunks.append(combined[:safe_end])
                                yield f"data: {json.dumps({'text': combined[:safe_end]}, ensure_ascii=False)}\n\n"
                            tail = combined[safe_end:]
                    else:  # buffering_viz
                        viz_buf += chunk
                        close_idx = viz_buf.find(VIZ_CLOSE)
                        if close_idx != -1:
                            viz_raw = viz_buf[:close_idx]
                            try:
                                viz = json.loads(viz_raw)
                                yield f"data: {json.dumps({'viz': viz}, ensure_ascii=False)}\n\n"
                                viz_emitted_in_this_attempt = True
                                logger.warning(f"VIZ emitted: type={viz.get('type')} title={viz.get('title', '')[:50]}")
                            except json.JSONDecodeError:
                                logger.warning(f"Bad viz JSON: {viz_raw[:120]}")
                            after = viz_buf[close_idx + len(VIZ_CLOSE):]
                            viz_state = "text"
                            viz_buf = ""
                            tail = after
            # End-of-stream drain: the tail may contain one OR MORE remaining
            # `<<VIZ:…>>` blocks (the AI can emit 2-3 in a row for synthesis
            # answers). The chunk loop above only processes the first viz it
            # sees per chunk; if the final chunk packs multiple, they end up
            # in `tail` together. Walk through them here.
            while viz_state == "text" and tail:
                open_idx = tail.find(VIZ_OPEN)
                if open_idx == -1:
                    visible_text_chunks.append(tail)
                    yield f"data: {json.dumps({'text': tail}, ensure_ascii=False)}\n\n"
                    tail = ""
                    break
                if open_idx > 0:
                    visible_text_chunks.append(tail[:open_idx])
                    yield f"data: {json.dumps({'text': tail[:open_idx]}, ensure_ascii=False)}\n\n"
                rest = tail[open_idx + len(VIZ_OPEN):]
                close_idx = rest.find(VIZ_CLOSE)
                if close_idx == -1:
                    break  # mid-viz at EOF — drop silently
                viz_raw = rest[:close_idx]
                try:
                    viz = json.loads(viz_raw)
                    yield f"data: {json.dumps({'viz': viz}, ensure_ascii=False)}\n\n"
                    viz_emitted_in_this_attempt = True
                    logger.warning(f"VIZ emitted (drain): type={viz.get('type')} title={viz.get('title', '')[:50]}")
                except json.JSONDecodeError:
                    logger.warning(f"Bad viz JSON (drain): {viz_raw[:120]}")
                tail = rest[close_idx + len(VIZ_CLOSE):]
            # Diagnostic so we can tell apart "AI didn't emit viz" vs "parser ate it" in prod logs.
            if not viz_emitted_in_this_attempt:
                logger.warning(f"NO VIZ emitted for question[:80]={question[:80]!r}")
            last_error = None
            break  # success
        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'text': 'שגיאה: מפתח ה-API אינו תקין.'}, ensure_ascii=False)}\n\n"
            last_error = None
            break
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            last_error = e
            logger.warning(f"AI chat {model} failed: {type(e).__name__}: {e}")
            continue
        except Exception as e:
            last_error = e
            logger.error(f"AI chat error: {type(e).__name__}: {e}")
            break

    if last_error:
        logger.error(f"AI chat all attempts failed: {type(last_error).__name__}: {last_error}")
        yield f"data: {json.dumps({'text': 'שגיאה: לא ניתן לעבד את הבקשה כרגע. נסה שוב בעוד רגע.'}, ensure_ascii=False)}\n\n"

    # Numeric validator — flag currency amounts in the answer that don't
    # appear in the source context. Advisory: surfaces as a yellow chip on
    # the user's message. Skip on error responses (no point validating an
    # error message).
    if not last_error and visible_text_chunks:
        try:
            from app.services.ai_answer_validator import validate_answer
            answer_text = "".join(visible_text_chunks)
            # The source context the AI saw = view_context + the dynamic
            # context block. system_prompt holds both after the format().
            check_result = validate_answer(answer_text, system_prompt)
            if check_result.has_warnings():
                yield (
                    "data: "
                    + json.dumps({"warnings": check_result.warnings}, ensure_ascii=False)
                    + "\n\n"
                )
        except Exception as e:
            logger.warning("ai_answer_validator failed: %s", e)

    yield f"data: {json.dumps({'done': True})}\n\n"
