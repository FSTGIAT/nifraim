"""Generate the AI data dictionary (Markdown, categorized) from the SQLAlchemy models.

    cd backend && PYTHONPATH=. python scripts/build_data_dictionary.py [--fill-rates]

Output: app/services/agent/dictionary/{index,<category>}.md — shipped with the app;
index.md goes into Nifra Agent's cached system prompt, category pages are read on
demand through open_page("dict/<category>.md").

--fill-rates queries the configured DB for the % of non-null values per column
(percentages only, no data). A column that is ~always empty is marked so the model
never "analyzes" nulls (e.g. pension_holdings.track on the 15th path).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401

OUT = Path(__file__).resolve().parent.parent / "app" / "services" / "agent" / "dictionary"

# category -> (Hebrew title, one-line meaning, tables)
CATEGORIES = {
    "production": ("פרודוקציה ותיק", "מה יש לכל לקוח בכל חברה — מוצר, צבירה, פרמיה, מסלול", ["client_records", "file_uploads", "production_summaries", "recruits"]),
    "commissions": ("עמלות ונפרעים", "מה שולם בפועל מול מה שצפוי, חובות וגבייה", ["commission_comparisons", "debts", "collection_cases", "volume_bonus_payments"]),
    "agreements": ("הסכמים ושיעורי עמלה", "שיעורי עמלה מההסכמים, מסמכי הסכם ובקשות הסכם", ["commission_rates", "volume_commission_rates", "ai_documents", "agreement_requests", "company_contacts", "paying_companies"]),
    "maslaka": ("מסלקה פנסיונית", "בקשות למסלקה ותשובות — החזקות לקוח, פרודוקציה ב-15 לחודש", ["pension_inquiries", "pension_holdings", "maslaka_agent_links"]),
    "mail": ("מייל", "מיילים מחברות ולקוחות, טיוטות, שולחים במעקב", ["mail_items", "mail_watch_senders", "mail_agent_profiles"]),
    "automation": ("הורדה אוטומטית ומחזור", "ריצות פורטלים, מחזור חודשי ב-21", ["portal_runs", "portal_run_batches", "cycle_notifications"]),
    "customers_portal": ("פורטל לקוח", "קישורים ותמונות מצב שהסוכן שיתף עם לקוחות", ["customer_portal_links", "portal_snapshots"]),
    "market": ("נתוני שוק", "תשואות, דמי ניהול וזרימות רשמיים לכל קופה לפי חודש (גמל-נט/פנסיה-נט/ביטוח-נט)", ["fund_market_monthly", "fund_tracks", "yield_recommendations"]),
    "ai": ("זיכרון ה-AI", "מה ה-AI למד על הסוכן ואילו שאלות הוא שואל", ["ai_memories", "ai_intent_log"]),
}

# column notes the model must know — units, meaning, traps (table.column -> Hebrew note)
NOTES = {
    "client_records.id_number": "ת.ז לקוח בלי אפסים מובילים",
    "client_records.receiving_company": "החברה המנהלת (שם משפטי; לנרמל לפי שורש: הפניקס/מגדל/…)",
    "client_records.accumulation": "צבירה ₪. accumulation_source='nifraim' = הושלם מהנפרעים כשהפרודוקציה הייתה ₪0",
    "client_records.total_premium": "פרמיה ₪ (חודשית בביטוח)",
    "client_records.track": "מסלול השקעה (שם כפי שהחברה כותבת)",
    "client_records.track_split": "פיצול צבירה בין מסלולים: [{track, amount}]",
    "client_records.commission_paid": "עמלה ששולמה בפועל ₪ (שורות נפרעים)",
    "client_records.product_status": "סטטוס מוצר מהחברה (פעיל/מבוטל/מוקפא…)",
    "file_uploads.period_month": "החודש שהקובץ מדווח עליו (לא תאריך ההעלאה); נפרעים מגיעים ~30 יום באיחור",
    "file_uploads.is_production": "True = קובץ הפרודוקציה הפעיל של החברה",
    "commission_rates.rate": "שיעור כשבר (0.0025 = 0.25%). נפרעים = עמלת ספר + שיעור תגמול; לא להמציא רכיב חסר",
    "debts.expected_amount": "עמלה צפויה שלא שולמה ₪ (status=open)",
    "pension_holdings.accumulation": "צבירה ₪ מהמסלקה",
    "pension_holdings.track": "ריק במסלול ה-15 לחודש — לא לנתח",
    "pension_holdings.management_fee_deposit": "ריק במסלול ה-15 לחודש — לא לנתח",
    "pension_holdings.expected_pension": "ריק במסלול ה-15 לחודש — לא לנתח",
    "pension_inquiries.interface_code": "events_v007:<קוד> — 9100 טרום ייעוץ כל הגופים, 9101 גוף אחד, 9102 איתור קופות רדומות, 2000/2100 פרודוקציה",
    "fund_market_monthly.report_period": "YYYYMM של הדיווח (פיגור של 1–2 חודשים)",
    "fund_market_monthly.mgmt_fee": "דמי ניהול מצבירה באחוזים (0.53 = 0.53%)",
    "fund_market_monthly.avg_yield_3y": "תשואה שנתית ממוצעת 3 שנים באחוזים",
    "fund_market_monthly.net_monthly_deposits": "צבירה נטו בחודש, מיליוני ₪",
    "fund_market_monthly.total_assets": "גודל הקופה, מיליוני ₪",
}

CAVEATS = """# אזהרות נתונים (קרא לפני ניתוח)
- שיעור עמלה נשמר כשבר: 0.0025 = 0.25%.
- נפרעים מדווחים ~30 יום באיחור: קובץ שהגיע במאי הוא בדרך כלל של אפריל (period_month).
- "0 מותאמים" בנתוני מסלקה של חברה = ממתין למסלקה, לא תקלה. ביצוע גבייה 100% במצב הזה הוא ירוק כוזב.
- בהחזקות מהמסלקה מה-15 לחודש מתמלאים רק: חברה, מוצר, סוג מוצר, פוליסה, צבירה, פרמיה. מסלול, דמי ניהול, קצבה צפויה וכיסויים — ריקים. לא לנתח אותם.
- הכשרה: הפרודוקציה מגיעה במייל ואין בה פרמיה ולא מספר פוליסה — None, לא אפס.
- הפניקס (טרמינל): הצבירה בשקלים שלמים, ואין שמות לקוחות בקובץ.
- ת.ז תמיד בלי אפסים מובילים.
- סכומים מוצגים רק כשהם > 0. לא להציג מקפים לערכים ריקים.
- נתוני שוק (גמל-נט/פנסיה-נט/ביטוח-נט) הם תשואות עבר — תמיד לציין את חודש הנתונים ושאינן מבטיחות תשואה עתידית.
"""


async def fill_rates() -> dict[str, dict[str, float]]:
    from sqlalchemy import text
    from app.database import async_session
    out: dict[str, dict[str, float]] = {}
    async with async_session() as db:
        for t in Base.metadata.sorted_tables:
            cols = [c.name for c in t.columns]
            try:
                n = (await db.execute(text(f'select count(*) from "{t.name}"'))).scalar_one()
                if not n:
                    continue
                parts = ", ".join(f'count("{c}")' for c in cols)
                row = (await db.execute(text(f'select {parts} from "{t.name}"'))).one()
                out[t.name] = {c: round(100 * v / n) for c, v in zip(cols, row)}
            except Exception:  # noqa: BLE001
                await db.rollback()
    return out


def col_type(c) -> str:
    try:
        return str(c.type).split("(")[0].lower()
    except Exception:  # noqa: BLE001
        return "?"


def build(rates: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tables = {t.name: t for t in Base.metadata.sorted_tables}
    idx = ["# מילון הנתונים — קטגוריות", "",
           "כל הטבלאות מסוננות לפי הסוכן (user_id) מלבד נתוני שוק. לפירוט עמודות: open_page('dict/<קטגוריה>.md').", ""]
    for key, (title, meaning, names) in CATEGORIES.items():
        present = [n for n in names if n in tables]
        idx.append(f"- **{title}** (`dict/{key}.md`) — {meaning}. טבלאות: {', '.join(present)}")
        page = [f"# {title}", meaning, ""]
        for n in present:
            t = tables[n]
            page += [f"## {n}", "", "| עמודה | סוג | מילוי | הערה |", "|---|---|---|---|"]
            for c in t.columns:
                if c.name in ("id",) or c.name.endswith("_encrypted"):
                    continue
                fr = rates.get(n, {}).get(c.name)
                fill = "—" if fr is None else (f"{fr}%" + (" ⚠ כמעט ריק" if fr < 5 else ""))
                page.append(f"| {c.name} | {col_type(c)} | {fill} | {NOTES.get(f'{n}.{c.name}', '')} |")
            page.append("")
        (OUT / f"{key}.md").write_text("\n".join(page), encoding="utf-8")
    idx += ["", "- **אזהרות** (`dict/caveats.md`) — מה לא לנתח ואיך לקרוא יחידות"]
    (OUT / "caveats.md").write_text(CAVEATS, encoding="utf-8")
    (OUT / "index.md").write_text("\n".join(idx), encoding="utf-8")
    print(f"wrote {len(CATEGORIES) + 2} pages to {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fill-rates", action="store_true")
    a = ap.parse_args()
    build(asyncio.run(fill_rates()) if a.fill_rates else {})
