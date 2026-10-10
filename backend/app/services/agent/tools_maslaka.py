"""מסלקה (pension clearinghouse) tools: status, a customer's holdings, and a
PROPOSED request (9100/9101/9102) — the agent's click sends it through the same
gates as the מסלקה tab (MASLAKA_ENABLED + approved שיוך), never the model."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.services.agent.registry import tool

IL = ZoneInfo("Asia/Jerusalem")
_CO_NOISE = re.compile(r'\s*(חברה לביטוח|פנסיה וגמל|גמל ופנסיה|פנסיה מקיפה|בע"מ|בעמ)\s*')


def short_co(name: str | None) -> str:
    """The tab's shortCo (MaslakaDeltaDrill.vue): 'הפניקס פנסיה וגמל בע"מ' → 'הפניקס'."""
    return re.sub(r"\s+", " ", _CO_NOISE.sub(" ", name or "")).strip() or (name or "")
CODE_HE = {
    "9100": "מידע טרום ייעוץ — כל הגופים", "9101": "מידע טרום ייעוץ — גוף אחד",
    "9102": "איתור קופות שהפסיקו לקבל הפקדות", "9200": "החזקות חד-פעמי", "9201": "החזקות שוטף",
    "2000": "דוח פרודוקציה חד-פעמי", "2100": "דוח פרודוקציה חודשי", "1700": "מתן ייפוי כוח", "1900": "ביטול ייפוי כוח",
}
# "acknowledged" was "התקבל במסלקה" — the model read it as "the REPORT arrived" and
# listed the bodies still waiting as the ones that answered (2026-10-10). It only
# means the מסלקה accepted our REQUEST; data comes later ("partial"/"completed").
STATUS_HE = {"pending": "ממתין לשליחה", "submitted": "נשלח", "acknowledged": "הבקשה התקבלה במסלקה — ממתין לנתונים",
             "partial": "הגיעו נתונים (חלקית)", "completed": "הגיעו נתונים", "failed": "נדחה", "expired": "פג תוקף"}


async def holdings_lines(ctx, idn: str) -> list[str]:
    from app.services.maslaka.orchestration import get_enriched_picture
    pic = await get_enriched_picture(ctx.db, user_id=ctx.user.id, id_number=idn)
    if not pic:
        return []
    # Each line says whether the product is in the agent's production file, so the
    # model never has to guess it from company names (2026-10-09 it told the agent
    # Mor products were "missing from production" when all 7 were matched).
    out = ["", "## מהמסלקה (בפרודוקציה = נמצא גם בקובץ הפרודוקציה של הסוכן)"]
    for p in (pic.get("products") or [])[:15]:
        bits = [p.get("company") or p.get("receiving_company"), p.get("product") or p.get("product_type"),
                f"צבירה ₪{round(float(p.get('accumulation') or 0)):,}" if p.get("accumulation") else None,
                p.get("account_status"),
                "בפרודוקציה" if p.get("match_status") == "matched" else "לא בפרודוקציה"]
        out.append("- " + " · ".join(str(b) for b in bits if b))
    return out


async def latest_file(ctx) -> dict | None:
    """The newest מסלקה production file: which bodies ANSWERED (and with how much)
    and which are still waiting. Built from file_coverage — the same source as the
    מסלקה tab's "<month> מול הפרודוקציה שלך" panel, so Nifra and the tab name the
    same companies."""
    from sqlalchemy import func
    from app.models.pension_holding import PensionHolding
    from app.models.pension_inquiry import PensionInquiry
    from app.services.maslaka.delta import PRODUCTION_CODES, file_coverage

    cov = await file_coverage(ctx.db, ctx.user.id)
    if not cov.get("as_of"):
        return None
    from datetime import date
    as_of = date.fromisoformat(cov["as_of"])
    arrived = (await ctx.db.execute(
        select(func.min(PensionHolding.created_at))
        .join(PensionInquiry, PensionInquiry.id == PensionHolding.inquiry_id)
        .where(PensionHolding.user_id == ctx.user.id, PensionHolding.status_date == as_of,
               PensionInquiry.interface_code.in_(PRODUCTION_CODES))
    )).scalar_one_or_none()
    return {
        "valid_as_of": cov["as_of"],
        "arrived_at": arrived.astimezone(IL).strftime("%d/%m/%Y") if arrived else None,
        "companies_answered": [
            {"company": c["company"], "customers": c["in_customers"] + c["out_customers"],
             "customers_with_a_product_not_in_your_production": c["out_customers"],
             "products": c["in"] + c["out"],
             "products_in_your_production": c["in"], "products_not_in_your_production": c["out"]}
            for c in cov["by_company"]],
        "companies_waiting": [
            {"company": w["company"], "answer_expected": w.get("due"), "not_sent_yet": w.get("queued")}
            for w in cov.get("waiting") or []],
    }


@tool("maslaka_status", "מצב המסלקה של הסוכן: האם השיוך אושר, קובץ הפרודוקציה האחרון מהמסלקה — מתי הגיע, מאילו חברות הגיעו נתונים ואילו עדיין ממתינות — בקשות פתוחות ומתי צפויה תשובה, ומתי הקובץ הבא.",
      category="maslaka", status_he="בודק את המסלקה")
async def maslaka_status(ctx):
    from app.models.maslaka_agent_link import MaslakaAgentLink
    from app.models.pension_holding import PensionHolding
    from app.models.pension_inquiry import PensionInquiry
    from sqlalchemy import func

    link = (await ctx.db.execute(select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == ctx.user.id))).scalars().first()
    inqs = (await ctx.db.execute(select(PensionInquiry).where(PensionInquiry.user_id == ctx.user.id)
                                 .order_by(PensionInquiry.created_at.desc()).limit(300))).scalars().all()
    by = Counter((STATUS_HE.get(i.status, i.status), CODE_HE.get((i.interface_code or "").rpartition(":")[2], i.interface_code)) for i in inqs)
    from app.services.maslaka.delta import answer_due, next_file_due
    nxt = await next_file_due(ctx.db, ctx.user)
    open_rows = []
    for i in inqs:
        due, _ = answer_due(i, nxt)
        if due:
            open_rows.append({"customer": i.customer_name or i.customer_id_number,
                              "request": CODE_HE.get((i.interface_code or "").rpartition(":")[2], i.interface_code),
                              "status": STATUS_HE.get(i.status, i.status),
                              "answer_expected": due.astimezone(IL).strftime("%d/%m %H:%M"), "_due": due})
    open_rows.sort(key=lambda r: r["_due"])
    open_count = len(open_rows)
    open_rows = [{k: v for k, v in r.items() if k != "_due"} for r in open_rows[:10]]
    customers = (await ctx.db.execute(select(func.count(func.distinct(PensionHolding.customer_id_number)))
                                      .where(PensionHolding.user_id == ctx.user.id))).scalar_one()
    nxt15 = nxt   # one rule with the מסלקה tab's files list
    return {
        "latest_production_file": await latest_file(ctx),
        "association": {"status": getattr(link, "status", "not_started"),
                        "approved_at": getattr(link, "approved_at", None), "auto_production": getattr(link, "auto_production", None)},
        "requests_by_status": [{"status": s, "request": c, "count": n} for (s, c), n in by.most_common(12)],
        "open_requests": open_rows,
        "open_requests_count": open_count,
        "customers_with_maslaka_data": customers,
        "next_production_date": nxt15.strftime("%d/%m/%Y"),
        "rule": "דוח פרודוקציה מהמסלקה מגיע ב-15 לחודש למי ששיוכו אושר; 9100 עונה תוך שעות. 0 מותאמים = ממתין למסלקה, לא תקלה. "
                "מאילו חברות הגיעו נתונים = רק latest_production_file.companies_answered; companies_waiting עוד לא שלחו. "
                "בקשה 'התקבלה במסלקה' = הבקשה נקלטה, לא שהגיעו נתונים. מתי הגיע הקובץ = arrived_at, לא הכלל של ה-15.",
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
    rid = ctx.keep([{"label": short_co(c["company"]), "value": c["new"] + c["removed"] + c["changed"]} for c in res["by_company"]],
                   label="חברה", value="שינויים", unit="", title="שינויים לפי חברה — מסלקה")
    slim = lambda items: [{k: i.get(k) for k in ("name", "id_number", "company", "product", "old_accumulation",
                                                  "new_accumulation", "accumulation_diff")} for i in items[:10]]

    def split(bucket):   # "15 (מור 8, אלטשולר שחם 3, …)" — written here so the model never re-adds it wrong
        parts = sorted(((short_co(c["company"]), c[bucket]) for c in res["by_company"] if c[bucket]), key=lambda x: -x[1])
        return f"{sum(n for _, n in parts)} (" + ", ".join(f"{co} {n}" for co, n in parts) + ")" if parts else "0"

    cust = lambda items: len({i["id_number"] for i in items})
    from_production = base.get("kind") != "maslaka"
    return {"found": True, "as_of": res["as_of"], "compared_with": vs, "summary": res["summary"],
            # customers WITH a new / missing / changed product — not "new customers" (the model wrote
            # "21 לקוחות חדשים" for 21 customers who each got a new product, 2026-10-10)
            "customers": {"with_a_new_product": cust(res["new"]), "with_a_product_not_in_this_file": cust(res["removed"]),
                          "with_an_accumulation_change": cust(res["changed"]),
                          "with_any_change": cust(res["new"] + res["removed"] + res["changed"])},
            "products_by_company": {"new": split("new"), "removed": split("removed"), "changed": split("changed")},
            "by_company": res["by_company"], "top_new": slim(res["new"]), "top_removed": slim(res["removed"]),
            "top_changed": slim(res["changed"]), "result_id": rid,
            "rule": "חדש = מוצר שלא היה בצד השני; הוסר = מוצר שהיה ולא הגיע בקובץ הזה; השתנה = צבירה שזזה ב-₪100 וגם ב-1% לפחות. חברה שלא ענתה בשני הצדדים לא נספרת. "
                    "'הוסר' לא אומר שהלקוח עזב: ייתכן שהמוצר נסגר, הועבר לגוף או לסוכן אחר, או פשוט לא נכלל בקובץ. "
                    "אל תכתוב 'עזב'/'עזבו' — כתוב 'לא הופיע בקובץ המסלקה' והצע לבדוק. "
                    "פירוט לפי חברה — רק כפי שכתוב ב-products_by_company. נשאלת על לקוחות — ענה במספרי customers. "
                    "ענה ישר במספרים, בלי משפט פתיחה על מה צריך לבדוק."
                    + (" ההשוואה היא מול קובץ הפרודוקציה, לא מול קובץ מסלקה קודם: שינויי הצבירה כוללים תשואות של כל התקופה ביניהם — אמור זאת, ואל תציג אותם כפעולות של הלקוחות."
                       if from_production else "")}


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


@tool("customer_changes", "מה השתנה אצל לקוח לאורך זמן: מוצרים חדשים / שלא הופיעו / שהצבירה שלהם זזה — קובץ המסלקה האחרון מול הקודם (או מול קובץ הפרודוקציה), "
      "עם הצבירה אז ועכשיו; ולכל מסלול שלו — תשואת החודש, מתחילת השנה ו-12 חודשים, ותזוזת הדירוג החודש מול מסלולים דומים.",
      {"id_number": {"type": "string"}}, ["id_number"], category="maslaka", status_he="בודק מה השתנה אצל הלקוח")
async def customer_changes(ctx, id_number: str):
    from app.services.agent.tools_market import (CATEGORIES, _category_rows, _customer_products, category_for_product,
                                                 latest_period, match_fund)
    from app.services.fund_market.delta import rank_moves
    from app.services.fund_market.track_score import yields_12m
    from app.services.maslaka.delta import monthly_delta

    idn = "".join(ch for ch in str(id_number) if ch.isdigit()).lstrip("0") or "0"
    res = await monthly_delta(ctx.db, ctx.user.id)
    base = res.get("base") or {}
    pick = lambda items: [{k: i.get(k) for k in ("company", "product", "policy", "old_accumulation", "new_accumulation", "accumulation_diff")
                           if i.get(k) is not None} for i in items if str(i.get("id_number")).lstrip("0") == idn]
    products = {"new": pick(res.get("new") or []), "not_in_this_file": pick(res.get("removed") or []),
                "accumulation_changed": pick(res.get("changed") or [])}
    unchanged_note = None
    if res.get("as_of") and not any(products.values()):
        unchanged_note = "אין שינוי מעל הסף (₪100 וגם 1%) באף מוצר של הלקוח בקובץ הזה."

    tracks = []
    period = await latest_period(ctx.db)
    rows_by_cat, moves_by_cat, y12_by_src, seen = {}, {}, {}, set()
    for p in await _customer_products(ctx, idn):
        cat = category_for_product(p["product_type"], p["product"])
        if not cat or not period:
            continue
        if cat not in rows_by_cat:
            src, classes, _ = CATEGORIES[cat]
            rows_by_cat[cat] = await _category_rows(ctx.db, cat, period)
            moves_by_cat[cat] = await rank_moves(ctx.db, src, classes)
            if src not in y12_by_src:
                y12_by_src[src] = await yields_12m(ctx.db, src, period)
        f = match_fund(p["track"], p["company"], rows_by_cat[cat])[0]
        if not f or f.fund_id in seen:
            continue
        seen.add(f.fund_id)
        mv = moves_by_cat[cat]["moves"].get(f.fund_id)
        tracks.append({"track": f.fund_name, "category": CATEGORIES[cat][2], "month_yield": f.monthly_yield, "ytd_yield": f.ytd_yield,
                       "yield_12m": y12_by_src[f.source].get(f.fund_id),
                       **({"rank_before": mv[0], "rank_now": mv[1], "group_size": mv[2]} if mv else {})})
    y, m = divmod(period or 0, 100)
    return {"id_number": idn,
            "maslaka_file": res.get("as_of"),
            "compared_with": ("קובץ המסלקה של " + (base.get("as_of") or "")) if base.get("kind") == "maslaka"
            else ("קובץ הפרודוקציה " + (base.get("as_of") or "")[:7] if base.get("as_of") else None),
            "products": products, "note": unchanged_note,
            "tracks_this_month": tracks, "market_month": f"{m:02d}/{y}" if period else None,
            "history_available": "הצבירה לאורך זמן: רק שתי נקודות — קובץ הפרודוקציה וקובץ המסלקה האחרון (המסלקה החודשית התחילה ב-09/2026). "
                                 "תשואות המסלולים — חודשיות מ-2023.",
            "rule": "שינוי צבירה כולל תשואות של כל התקופה שבין שני הקבצים, לא רק הפקדות. 'לא הופיע' ≠ עזב."}
