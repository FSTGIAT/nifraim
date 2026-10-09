"""מסלקה (pension clearinghouse) tools: status, a customer's holdings, and a
PROPOSED request (9100/9101/9102) — the agent's click sends it through the same
gates as the מסלקה tab (MASLAKA_ENABLED + approved שיוך), never the model."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.services.agent.registry import tool

IL = ZoneInfo("Asia/Jerusalem")
CODE_HE = {
    "9100": "מידע טרום ייעוץ — כל הגופים", "9101": "מידע טרום ייעוץ — גוף אחד",
    "9102": "איתור קופות שהפסיקו לקבל הפקדות", "9200": "החזקות חד-פעמי", "9201": "החזקות שוטף",
    "2000": "דוח פרודוקציה חד-פעמי", "2100": "דוח פרודוקציה חודשי", "1700": "מתן ייפוי כוח", "1900": "ביטול ייפוי כוח",
}
STATUS_HE = {"pending": "ממתין לשליחה", "submitted": "נשלח", "acknowledged": "התקבל במסלקה",
             "partial": "התקבל חלקית", "completed": "הושלם", "failed": "נדחה", "expired": "פג תוקף"}


async def holdings_lines(ctx, idn: str) -> list[str]:
    from app.services.maslaka.orchestration import get_enriched_picture
    pic = await get_enriched_picture(ctx.db, user_id=ctx.user.id, id_number=idn)
    if not pic:
        return []
    out = ["", "## מהמסלקה"]
    for p in (pic.get("products") or [])[:15]:
        bits = [p.get("company") or p.get("receiving_company"), p.get("product") or p.get("product_type"),
                f"צבירה ₪{round(float(p.get('accumulation') or 0)):,}" if p.get("accumulation") else None]
        out.append("- " + " · ".join(str(b) for b in bits if b))
    return out


@tool("maslaka_status", "מצב המסלקה של הסוכן: האם השיוך אושר, בקשות פתוחות ומתי צפויה תשובה, כמה לקוחות עם נתוני מסלקה, ומתי מגיעה הפרודוקציה (15 לחודש).",
      category="maslaka", status_he="בודק את המסלקה")
async def maslaka_status(ctx):
    from app.models.maslaka_agent_link import MaslakaAgentLink
    from app.models.pension_holding import PensionHolding
    from app.models.pension_inquiry import PensionInquiry
    from app.services.maslaka.orchestration import expected_answer_by
    from sqlalchemy import func

    link = (await ctx.db.execute(select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == ctx.user.id))).scalars().first()
    inqs = (await ctx.db.execute(select(PensionInquiry).where(PensionInquiry.user_id == ctx.user.id)
                                 .order_by(PensionInquiry.created_at.desc()).limit(300))).scalars().all()
    by = Counter((STATUS_HE.get(i.status, i.status), CODE_HE.get((i.interface_code or "").rpartition(":")[2], i.interface_code)) for i in inqs)
    open_rows = []
    for i in inqs:
        due, _ = expected_answer_by(i)
        if due and len(open_rows) < 10:
            open_rows.append({"customer": i.customer_name or i.customer_id_number,
                              "request": CODE_HE.get((i.interface_code or "").rpartition(":")[2], i.interface_code),
                              "status": STATUS_HE.get(i.status, i.status),
                              "answer_expected": due.astimezone(IL).strftime("%d/%m %H:%M")})
    customers = (await ctx.db.execute(select(func.count(func.distinct(PensionHolding.customer_id_number)))
                                      .where(PensionHolding.user_id == ctx.user.id))).scalar_one()
    now = datetime.now(IL)
    nxt15 = now.replace(day=15) if now.day <= 15 else (now.replace(year=now.year + (now.month == 12), month=now.month % 12 + 1, day=15))
    return {
        "association": {"status": getattr(link, "status", "not_started"),
                        "approved_at": getattr(link, "approved_at", None), "auto_production": getattr(link, "auto_production", None)},
        "requests_by_status": [{"status": s, "request": c, "count": n} for (s, c), n in by.most_common(12)],
        "open_requests": open_rows,
        "customers_with_maslaka_data": customers,
        "next_production_date": nxt15.strftime("%d/%m/%Y"),
        "rule": "דוח פרודוקציה מהמסלקה מגיע ב-15 לחודש למי ששיוכו אושר; 9100 עונה תוך שעות. 0 מותאמים = ממתין למסלקה, לא תקלה.",
    }


@tool("customer_holdings", "כל המוצרים של לקוח כפי שהגיעו מהמסלקה (חברה, מוצר, צבירה, פרמיה). ריק = עוד לא נשלחה/נענתה בקשת 9100 ללקוח.",
      {"id_number": {"type": "string"}}, ["id_number"], category="maslaka", status_he="מושך נתוני מסלקה")
async def customer_holdings(ctx, id_number: str):
    from app.services.maslaka.orchestration import get_enriched_picture
    idn = "".join(ch for ch in str(id_number) if ch.isdigit()).lstrip("0") or "0"
    pic = await get_enriched_picture(ctx.db, user_id=ctx.user.id, id_number=idn)
    if not pic:
        return {"id_number": idn, "found": False,
                "note": "אין נתוני מסלקה ללקוח. אפשר להציע בקשת 9100 (propose_maslaka_request)."}
    prods = pic.get("products") or []
    rid = ctx.keep([{"label": p.get("company") or "—", "value": round(float(p.get("accumulation") or 0), 2)} for p in prods],
                   label="חברה", value="צבירה", title="צבירה לפי חברה — מסלקה")
    return {"id_number": idn, "found": True, "kpis": pic.get("kpis"), "products": prods[:25], "result_id": rid}


@tool("maslaka_delta", "מה השתנה בקובץ הפרודוקציה מהמסלקה לעומת החודש הקודם (או לעומת קובץ הפרודוקציה של הסוכן, אם זה הקובץ הראשון): מוצרים חדשים, מוצרים שהוסרו, וצבירות שהשתנו — לפי חברה, עם הלקוחות הבולטים. as_of = תאריך הנכונות של הקובץ (YYYY-MM-DD), ריק = האחרון.",
      {"as_of": {"type": "string"}}, [], category="maslaka", status_he="משווה את קובץ המסלקה")
async def maslaka_delta(ctx, as_of: str = ""):
    from datetime import date
    from app.services.maslaka.delta import monthly_delta
    try:
        d = date.fromisoformat(as_of) if as_of else None
    except ValueError:
        d = None
    res = await monthly_delta(ctx.db, ctx.user.id, d)
    if not res.get("summary"):
        return {"found": False, "note": "עוד לא הגיע קובץ פרודוקציה מהמסלקה."}
    base = res["base"] or {}
    vs = ("קובץ המסלקה של " + base.get("as_of", "")) if base.get("kind") == "maslaka" else \
         ("קובץ הפרודוקציה " + (base.get("filename") or "") + (f" ({base['as_of'][:7]})" if base.get("as_of") else ""))
    rid = ctx.keep([{"label": c["company"], "value": c["new"] + c["removed"] + c["changed"]} for c in res["by_company"]],
                   label="חברה", value="שינויים", unit="", title="שינויים לפי חברה — מסלקה")
    slim = lambda items: [{k: i.get(k) for k in ("name", "id_number", "company", "product", "old_accumulation",
                                                  "new_accumulation", "accumulation_diff")} for i in items[:10]]
    return {"found": True, "as_of": res["as_of"], "compared_with": vs, "summary": res["summary"],
            "by_company": res["by_company"], "top_new": slim(res["new"]), "top_removed": slim(res["removed"]),
            "top_changed": slim(res["changed"]), "result_id": rid,
            "rule": "חדש = מוצר שלא היה בצד השני; הוסר = מוצר שהיה ולא הגיע; השתנה = צבירה שזזה ב-₪100 וגם ב-1% לפחות. חברה שלא ענתה בשני הצדדים לא נספרת."}


# Only 9100 — exactly what the מסלקה tab sends (/api/maslaka/inquiry: ID + name, no extra
# consent fields). 9101 needs a target body and 9102 was never sent live; add them here
# only after the tab supports them and the מסלקה accepted one.
@tool("propose_maslaka_request", "הכנת בקשת 9100 למסלקה ללקוח — כל המוצרים של הלקוח מכל הגופים (מידע טרום ייעוץ, תשובה תוך שעות). לא נשלחת עד שהסוכן מאשר. בקשות אחרות (9101/9102) עדיין לא נתמכות — אמור זאת אם מבקשים.",
      {"code": {"type": "string", "enum": ["9100"]}, "id_number": {"type": "string"},
       "customer_name": {"type": "string"}},
      ["code", "id_number"], category="maslaka", status_he="מכין בקשה למסלקה", action=True)
async def propose_maslaka_request(ctx, code: str, id_number: str, customer_name: str = ""):
    """Prepares a 9100 ONLY for an agent the מסלקה can accept it from — the same gates the approve
    route enforces (api/maslaka.require_maslaka_enabled + require_association_approved), checked
    BEFORE the card is drawn: an unregistered agent used to approve and only then get a 403.
    The agent's click is still what sends it (/office-agent/act re-checks every gate)."""
    from app.config import settings
    from app.models.maslaka_agent_link import APPROVED, SUBMITTED, MaslakaAgentLink
    from app.models.pension_inquiry import PensionInquiry

    if code != "9100":
        return "רק בקשת 9100 (כל המוצרים של הלקוח) נתמכת כרגע. אמור זאת לסוכן."
    idn = "".join(ch for ch in str(id_number) if ch.isdigit()).lstrip("0")
    if not 5 <= len(idn) <= 9:
        return "ת.ז לא תקינה — בקש מהסוכן ת.ז מלאה של הלקוח. לא הוכנה בקשה."
    if not settings.MASLAKA_ENABLED:
        return ("לא הוכנה בקשה: החיבור למסלקה עוד לא פעיל בסביבה הזו (בצד של Nifraim, לא אצל הסוכן). "
                "אמור לסוכן במשפט אחד שזה יופעל בקרוב.")
    link = (await ctx.db.execute(select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == ctx.user.id))).scalars().first()
    status = getattr(link, "status", "not_started")
    if status != APPROVED:
        why = {SUBMITTED: "טופס השיוך נשלח ומחכה לאישור המסלקה — אחרי האישור אפשר לשלוח בקשות.",
               "rejected": "השיוך נדחה במסלקה — צריך לתקן ולהגיש שוב את טופס השיוך בלשונית המסלקה."}.get(
            status, "הסוכן עוד לא השלים את השיוך לבית התוכנה במסלקה — טופס השיוך נמצא בלשונית המסלקה.")
        return f"לא הוכנה בקשה — השיוך למסלקה לא מאושר. {why} אל תכין בקשה; הסבר לסוכן במשפט אחד מה חסר."
    # one open 9100 per customer — a second one is noise at a regulator
    open_req = (await ctx.db.execute(select(PensionInquiry).where(
        PensionInquiry.user_id == ctx.user.id, PensionInquiry.customer_id_number == idn,
        PensionInquiry.status.in_(("pending", "submitted", "acknowledged", "partial")),
        PensionInquiry.created_at >= datetime.utcnow() - timedelta(days=3),
    ).order_by(PensionInquiry.created_at.desc()).limit(1))).scalar_one_or_none()
    if open_req:
        from app.services.maslaka.orchestration import expected_answer_by
        due, _ = expected_answer_by(open_req)
        return ("לא הוכנה בקשה חדשה — כבר יש בקשת 9100 פתוחה ללקוח הזה"
                + (f", התשובה צפויה עד {due.astimezone(IL).strftime('%d/%m %H:%M')}" if due else "") + ". אמור זאת לסוכן.")
    ctx.proposals.append({"kind": "maslaka", "code": code, "code_he": CODE_HE.get(code, code),
                          "customer_id_number": idn, "customer_name": (customer_name or "")[:120]})
    return "הבקשה הוכנה והוצגה לסוכן לאישור (השיוך מאושר). כתוב משפט אחד: מה הבקשה ומתי צפויה תשובה (9100: תוך שעות)."
