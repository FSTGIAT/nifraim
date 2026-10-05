"""Data tools — thin wrappers over the SAME functions the dashboards call.

One source per number: received / expected / unpaid come from
api.comparison.company_summary + company_unpaid (debts + persisted comparison),
trends from api.production.get_commission_trend / get_expected_commission_trend,
the book from api.production.get_production_breakdown / get_production_clients.
Nothing here recomputes money with new SQL.
"""
from __future__ import annotations

import re
from collections import defaultdict

from sqlalchemy import select

from app.services.agent import cache
from app.services.agent.registry import tool

_TTL = 1800


async def _cached(ctx, key: tuple, fn):
    hit = cache.get(ctx.user.id, ctx.data_version, key)
    if hit is None:
        hit = await fn()
        cache.put(ctx.user.id, ctx.data_version, key, hit, ttl=_TTL)
    return hit


def _r(v) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


async def company_summary(ctx) -> dict:
    from app.api import comparison
    return await _cached(ctx, ("company_summary",), lambda: comparison.company_summary(db=ctx.db, user=ctx.user))


async def commission_trend(ctx) -> list:
    from app.api import production
    return await _cached(ctx, ("trend",), lambda: production.get_commission_trend(db=ctx.db, user=ctx.user))


async def expected_trend(ctx) -> dict:
    from app.api import production
    return await _cached(ctx, ("expected_trend",), lambda: production.get_expected_commission_trend(db=ctx.db, user=ctx.user))


async def breakdown(ctx) -> dict:
    from app.api import production
    return await _cached(ctx, ("breakdown",), lambda: production.get_production_breakdown(db=ctx.db, user=ctx.user))


def _match_company(name: str, wanted: str) -> bool:
    from app.utils.company_norm import normalize_company
    if not wanted:
        return True
    a = normalize_company(name) or name or ""
    b = normalize_company(wanted) or wanted
    return b in a or a in b


@tool("get_overview", "תמונת מצב של כל התיק: עמלות שהתקבלו מול צפויות, פער (לא שולם), לקוחות, פרמיה וצבירה, וחודש הנפרעים האחרון. התחל כאן לשאלה כללית.",
      category="overview", status_he="מסכם את התיק")
async def get_overview(ctx):
    s = await company_summary(ctx)
    t = await commission_trend(ctx)
    b = await breakdown(ctx)
    tot = s.get("totals") or {}
    comps = b.get("companies") or []
    last = t[-1] if t else {}
    prev = t[-2] if len(t) > 1 else {}
    rows = [{"label": c["company"], "value": _r(c.get("received"))} for c in s.get("companies", []) if c.get("received")]
    rid = ctx.keep(rows, label="חברה", value="עמלה שהתקבלה", title="עמלות שהתקבלו לפי חברה")
    return {
        "received_total": _r(tot.get("received")), "expected_total": _r(tot.get("expected")),
        "gap_unpaid_total": _r(tot.get("gap")), "unpaid_customers": tot.get("unpaid"),
        "customers_in_production": tot.get("produced"), "matched_customers": tot.get("matched"),
        "premium_total": _r(sum(c.get("premium") or 0 for c in comps)),
        "accumulation_total": _r(sum(c.get("accumulation") or 0 for c in comps)),
        "last_commission_month": last.get("period_label"), "last_month_received": _r(last.get("total_commission")),
        "prev_month_received": _r(prev.get("total_commission")) if prev else None,
        "companies": [c["company"] for c in s.get("companies", [])],
        "result_id": rid,
    }


@tool("get_unpaid", "עמלות שלא שולמו. בלי company: פער ומספר לקוחות לא משולמים לכל חברה. עם company: רשימת הלקוחות שלא שולמו בחברה, המוצרים והצפי לכל אחד.",
      {"company": {"type": "string", "description": "שם חברה (מגדל, הפניקס...) או ריק לכל החברות"},
       "limit": {"type": "integer", "description": "כמה לקוחות להחזיר (ברירת מחדל 15)"}},
      category="commissions", status_he="בודק עמלות שלא שולמו")
async def get_unpaid(ctx, company: str = "", limit: int = 15):
    s = await company_summary(ctx)
    if not company:
        rows = sorted(({"label": c["company"], "value": _r(c.get("gap")), "unpaid_customers": c.get("unpaid"),
                        "received": _r(c.get("received")), "expected": _r(c.get("expected"))}
                       for c in s.get("companies", []) if (c.get("gap") or 0) > 0), key=lambda r: -r["value"])
        rid = ctx.keep(rows, label="חברה", value="פער (לא שולם)", title="עמלות שלא שולמו לפי חברה")
        return {"total_gap": _r((s.get("totals") or {}).get("gap")), "unpaid_customers": (s.get("totals") or {}).get("unpaid"),
                "by_company": rows, "result_id": rid}
    from app.api import comparison
    match = next((c["company"] for c in s.get("companies", []) if _match_company(c["company"], company)), company)
    d = await _cached(ctx, ("company_unpaid", match), lambda: comparison.company_unpaid(company=match, db=ctx.db, user=ctx.user))
    custs = sorted(d.get("customers") or [], key=lambda c: -float(c.get("expected") or 0))
    rows = [{"label": c.get("name") or c.get("id_number"), "value": _r(c.get("expected")), "id_number": c.get("id_number"),
             "products": [p.get("product") for p in c.get("products", [])][:4]} for c in custs[: max(1, min(limit, 50))]]
    rid = ctx.keep(rows, label="לקוח", value="צפי עמלה", title=f"לא שולם — {match}")
    # the company's own received / expected / gap — "כמה התקבל מהראל", "כמה זה באחוזים מהצפי שם"
    co = next((c for c in s.get("companies", []) if c["company"] == match), {})
    exp_all, got = float(co.get("expected") or 0), float(co.get("received") or 0)
    return {"company": match, "customers_count": len(custs), "total_expected": _r(d.get("total_expected")),
            "company_received": _r(got), "company_expected": _r(exp_all),
            "unpaid_pct_of_expected": round(100 * (exp_all - got) / exp_all) if exp_all >= 1 else None,
            "note": None if float(d.get("total_expected") or 0) >= 1 else
                    f"ב{match} אין חוב פתוח: הלקוחות ברשימה הם בצפי ₪0 (לא צפויה עמלה).",
            "customers": rows, "result_id": rid}


@tool("get_commission_trend", "עמלות שהתקבלו בפועל לפי חודש (נפרעים), כולל פירוק לפי חברה, ולצידן הצפי לפי חודש. לשאלות 'כמה קיבלתי החודש', 'מגמה', 'השוואה לחודש קודם'.",
      {"company": {"type": "string", "description": "חברה אחת או ריק לסך הכל"}},
      category="commissions", status_he="מושך את מגמת העמלות")
async def get_commission_trend(ctx, company: str = ""):
    t = await commission_trend(ctx)
    pts = []
    for p in t:
        if company:
            v = sum(float(x or 0) for k, x in (p.get("by_company") or {}).items() if _match_company(k, company))
        else:
            v = float(p.get("total_commission") or 0)
        pts.append({"label": p.get("period_label"), "value": _r(v)})
    e = await expected_trend(ctx)
    exp = {p.get("period_label"): _r(p.get("total_expected")) for p in (e.get("points") or [])}
    rid = ctx.keep(pts, label="חודש", value="עמלה שהתקבלה", title=f"עמלות לפי חודש{' — ' + company if company else ''}")
    last, prev = (pts[-1] if pts else None), (pts[-2] if len(pts) > 1 else None)
    s = await company_summary(ctx)
    return {"months": pts, "expected_by_month": exp if not company else None,
            "last": last, "prev": prev,
            "change": _r(last["value"] - prev["value"]) if last and prev else None,
            # measured: the model put expected_by_month[last] against `last` and reported a ₪69,926 gap (real: ₪24,136)
            "note": ("months = רק קבצי נפרעים עם חודש מזוהה (קובץ בלי חודש לא נספר כאן — לכן חברה יכולה להיראות ₪0). "
                     "expected_by_month כולל גם חברות שעוד לא שלחו דוח — אין להשוות אותו לסכום שהתקבל. "
                     "המספרים שכן ניתן להשוות (לכל חברה בתקופה האחרונה שלה): "
                     f"צפי {_r((s.get('totals') or {}).get('expected'))}, התקבל {_r((s.get('totals') or {}).get('received'))}, "
                     f"פער (לא שולם) {_r((s.get('totals') or {}).get('gap'))} — ופירוט לחברה: get_unpaid(company)."),
            "result_id": rid}


@tool("get_portfolio", "התיק בפרודוקציה לפי חברה ומוצר: פרמיה, צבירה, מספר לקוחות ומוצרים, וצפי עמלה.",
      {"company": {"type": "string", "description": "חברה אחת או ריק לכולן"},
       "metric": {"type": "string", "enum": ["accumulation", "premium", "clients"], "description": "לפי מה לדרג (ברירת מחדל צבירה)"}},
      category="production", status_he="סוקר את התיק")
async def get_portfolio(ctx, company: str = "", metric: str = "accumulation"):
    b = await breakdown(ctx)
    comps = [c for c in (b.get("companies") or []) if _match_company(c["company"], company)]
    rows = sorted(({"label": c["company"], "value": _r(c.get(metric)), "premium": _r(c.get("premium")),
                    "accumulation": _r(c.get("accumulation")), "clients": c.get("clients"), "products": c.get("count"),
                    "expected_commission": _r(c.get("commission")),
                    "by_product": [{"product": p["product"], "premium": _r(p.get("premium")), "accumulation": _r(p.get("accumulation")),
                                    "clients": p.get("clients")} for kind in ("insurance", "financial")
                                   for p in (c.get("products") or {}).get(kind, [])][:8]}
                   for c in comps), key=lambda r: -r["value"])
    unit = "" if metric == "clients" else "₪"
    rid = ctx.keep([{"label": r["label"], "value": r["value"]} for r in rows], label="חברה",
                   value={"accumulation": "צבירה", "premium": "פרמיה", "clients": "לקוחות"}[metric], unit=unit,
                   title="התיק לפי חברה")
    return {"companies": rows, "result_id": rid}


@tool("top_customers", "הלקוחות הגדולים בתיק (מכל קבצי הפרודוקציה הפעילים): לפי צבירה, פרמיה, או products = מספר המוצרים (פוליסות/חשבונות שונים) ללקוח.",
      {"metric": {"type": "string", "enum": ["accumulation", "premium", "products"]}, "n": {"type": "integer", "description": "כמה (ברירת מחדל 10)"}},
      category="production", status_he="מדרג את הלקוחות")
async def top_customers(ctx, metric: str = "accumulation", n: int = 10):
    n = max(1, min(int(n or 10), 30))
    if metric == "products":
        return await _top_by_products(ctx, n)
    from app.api import production
    rows = await _cached(ctx, ("clients", metric), lambda: production.get_production_clients(sort=metric, search=None, db=ctx.db, user=ctx.user))
    key = "accumulation" if metric == "accumulation" else "premium"
    top = []
    for r in rows[:n]:
        d = r if isinstance(r, dict) else r.__dict__
        name = d.get("name") or " ".join(x for x in (d.get("first_name"), d.get("last_name")) if x) or d.get("id_number")
        top.append({"label": name, "value": _r(d.get(key) or d.get(f"total_{key}")), "id_number": d.get("id_number"),
                    "companies": d.get("companies") or d.get("company")})
    rid = ctx.keep(top, label="לקוח", value="צבירה" if key == "accumulation" else "פרמיה", title="הלקוחות הגדולים")
    # what each top customer HOLDS — "אילו מוצרים יש ללקוחות המובילים" → render_chart(type=table)
    holdings = await _holdings_of(ctx, [t["id_number"] for t in top if t.get("id_number")])
    for t in top:
        h = holdings.get(str(t.get("id_number") or "").lstrip("0"), {})
        t["products"] = h.get("products", [])
        t["companies_list"] = h.get("companies", [])
    trid = ctx.keep([], label="לקוח", value="", title="הלקוחות המובילים והמוצרים שלהם", table={
        "columns": ["לקוח", "פרמיה" if key == "premium" else "צבירה", "חברות", "מוצרים"],
        "rows": [[t["label"], t["value"] or None, ", ".join(t["companies_list"]), ", ".join(t["products"])] for t in top]})
    # the VISUAL: customers × product categories (filled = holds it, ring = a gap → cross-sell)
    freq: dict[str, int] = {}
    for t in top:
        for cat in holdings.get(str(t.get("id_number") or "").lstrip("0"), {}).get("cats", {}):
            freq[cat] = freq.get(cat, 0) + 1
    cols = [c for c, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])) if c != "אחר"][:7]
    matrix = {"columns": cols, "rows": [{
        "label": t["label"], "value": t["value"], "companies": t["companies_list"],
        "cells": {c: holdings.get(str(t.get("id_number") or "").lstrip("0"), {}).get("cats", {}).get(c, 0) for c in cols},
    } for t in top]}
    mrid = ctx.keep([], label="לקוח", value="פרמיה" if key == "premium" else "צבירה", title="הלקוחות המובילים — מה יש לכל אחד",
                    chart="matrix", table=None)
    ctx.results[mrid]["matrix"] = matrix
    return {"metric": metric, "customers": top, "result_id": rid, "products_table_result_id": trid,
            "products_matrix_result_id": mrid}


# product name → a category an agent thinks in (the matrix columns)
_CATS = [("בריאות", ("בריאות", "ר.ת", "רפואי", "ניתוח", "השתלות")), ("סיעוד", ("סיעוד",)),
         ("מחלות קשות", ("מחלות", "קשות")), ("תאונות", ("תאונ", "נכות", "שברים")),
         ("השתלמות", ("השתלמות",)), ("פנסיה", ("פנסי",)), ("גמל להשקעה", ("להשקעה",)), ("גמל", ("גמל",)),
         ("חיסכון", ("פוליס", "חיסכון", "חסכון")), ("סיכונים", ("סיכונ", "ריסק", "משכנתא")), ("חיים", ("חיים",))]


def product_category(label: str | None) -> str:
    t = label or ""
    for cat, keys in _CATS:
        if any(k in t for k in keys):
            return cat
    return "אחר"


async def _holdings_of(ctx, ids: list) -> dict:
    """id → {companies: [...], products: [...]} from the active production (distinct, short)."""
    from sqlalchemy import func
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord
    from app.utils.company_norm import company_stem
    want = {str(i).lstrip("0") for i in ids if i}
    if not want:
        return {}
    upl = await _get_production_upload_ids(ctx.db, ctx.user.id)
    if not upl:
        return {}
    rows = (await ctx.db.execute(select(func.ltrim(ClientRecord.id_number, "0"), ClientRecord.receiving_company,
                                        ClientRecord.product_type, ClientRecord.product)
            .where(ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id.in_(upl),
                   func.ltrim(ClientRecord.id_number, "0").in_(want)))).all()
    out: dict[str, dict] = {}
    for idn, co, pt, prod in rows:
        h = out.setdefault(idn, {"companies": [], "products": []})
        c = company_stem(co) or co
        if c and c not in h["companies"]:
            h["companies"].append(c)
        label = (pt or prod or "").strip()
        if label and label not in h["products"] and len(h["products"]) < 6:
            h["products"].append(label)
        cat = product_category(f"{pt or ''} {prod or ''}")
        h.setdefault("cats", {})
        h["cats"][cat] = h["cats"].get(cat, 0) + 1
    return out


async def _top_by_products(ctx, n: int) -> dict:
    """Distinct products per customer = distinct policy/account numbers (one policy's
    coverage lines — הראל lists up to 8 riders per policy — are ONE product)."""
    from sqlalchemy import func
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord

    async def compute():
        ids = await _get_production_upload_ids(ctx.db, ctx.user.id)
        if not ids:
            return []
        from sqlalchemy import literal_column
        prod_key = func.coalesce(ClientRecord.fund_policy_number, ClientRecord.product)
        idn = func.ltrim(ClientRecord.id_number, literal_column("'0'"))   # ONE expression: select == group by
        n_products = func.count(func.distinct(prod_key))
        q = (select(idn, func.min(ClientRecord.first_name), func.min(ClientRecord.last_name),
                    n_products, func.count(func.distinct(ClientRecord.receiving_company)))
             .where(ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id.in_(ids), ClientRecord.id_number.isnot(None))
             .group_by(idn).order_by(n_products.desc()).limit(30))
        return [{"label": " ".join(x for x in (fn, ln) if x) or idn, "value": int(cnt), "id_number": idn, "companies": int(cos)}
                for idn, fn, ln, cnt, cos in (await ctx.db.execute(q)).all()]
    rows = (await _cached(ctx, ("top_products",), compute))[:n]
    rid = ctx.keep(rows, label="לקוח", value="מוצרים", unit="", title="לקוחות עם הכי הרבה מוצרים")
    return {"metric": "products", "customers": rows, "result_id": rid,
            "note": "מוצר = פוליסה/חשבון שונה; כיסויים של אותה פוליסה נספרים כמוצר אחד."}


@tool("find_customer", "חיפוש לקוח לפי שם, חלק משם או ת.ז. כשנמצאו 1–2 לקוחות — מחזיר מיד את הכרטיס המלא שלהם (אין צורך ב-get_customer).",
      {"query": {"type": "string"}}, ["query"], category="customer", status_he="מחפש את הלקוח")
async def find_customer(ctx, query: str):
    from app.services import data_map
    m = await ctx.map()
    q = (query or "").strip()
    if q.isdigit():
        return await get_customer(ctx, q)
    page = data_map.page_search(m, q)
    ids = list(dict.fromkeys(re.findall(r"customers/(\d+)\.md", page)))
    # many with this name, but exactly ONE you spoke with in a call → that's who is meant
    # ("מה הצעד הבא מול חיים?" — 6 people named חיים, one call with חיים אלימלך)
    spoke = re.findall(r"customers/(\d+)\.md\)[^\n]*דיברת איתו", page)
    if len(ids) > 2 and len(set(spoke)) == 1:
        others = len(ids) - 1
        card = await get_customer(ctx, spoke[0])
        return (f"הכוונה כמעט בוודאות ללקוח שדיברת איתו בשיחה (יש עוד {others} בשם הזה) — ענה עליו, "
                f"ואמור בחצי משפט שבחרת בו כי דיברתם:\n\n{card}")[:9000]
    if 1 <= len(ids) <= 2:
        cards = [await get_customer(ctx, i) for i in ids]
        head = "נמצאו 2 לקוחות בשם הזה — שני הכרטיסים:" if len(ids) == 2 else ""
        return "\n\n".join(x for x in [head, *cards] if x)[:9000]
    return page[:4000]


@tool("get_customer", "כרטיס לקוח מלא לפי ת.ז: כל המוצרים בכל החברות, צבירה ופרמיה, מה שולם ומה לא, תמונת תיק (כפל/חסר), ומה הגיע מהמסלקה.",
      {"id_number": {"type": "string"}}, ["id_number"], category="customer", status_he="פותח את כרטיס הלקוח")
async def get_customer(ctx, id_number: str):
    from app.services import data_map
    idn = "".join(ch for ch in str(id_number) if ch.isdigit()).lstrip("0") or "0"
    m = await ctx.map()
    await data_map.add_production_customers(ctx.db, m, [idn])
    page = data_map.render(m, f"customers/{idn}.md")[:5000]
    c = next((x for x in m.customers if str(x.get("id_number")).lstrip("0") == idn), None) or m.extra.get(idn)
    if c:
        prods = c.get("production_products") or []
        rows = [[p.get("company") or "", p.get("product") or p.get("product_type") or "", p.get("policy_number") or "",
                 p.get("status") or "", _r(p.get("accumulation")) or None, _r(p.get("premium")) or None,
                 _r(p.get("expected_commission")) or None] for p in prods[:40]]
        if rows:
            nm = " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) or idn
            rid = ctx.keep([], label="מוצר", value="", title=f"המוצרים של {nm}",
                           table={"columns": ["חברה", "מוצר", "פוליסה", "סטטוס", "צבירה", "פרמיה", "צפי עמלה"], "rows": rows})
            page += f"\n\n(טבלת המוצרים: result_id={rid} — render_chart(type=table) כשמבקשים טבלה)"
    try:
        from app.services.agent.tools_maslaka import holdings_lines
        page += "\n" + "\n".join(await holdings_lines(ctx, idn))
    except Exception:  # noqa: BLE001 — מסלקה is optional context
        pass
    return page


@tool("get_rate", "שיעור העמלה מההסכם לחברה (ולמוצר אם צוין): ספר, תגמול, טווח שנים, תוקף. אם אין הסכם — אומר שאין.",
      {"company": {"type": "string"}, "product": {"type": "string", "description": "מוצר (גמל, השתלמות, פנסיה, בריאות...) או ריק"}},
      ["company"], category="agreements", status_he="בודק את ההסכם")
async def get_rate(ctx, company: str, product: str = ""):
    from app.models.commission_rate import CommissionRate
    rates = (await ctx.db.execute(select(CommissionRate).where(CommissionRate.user_id == ctx.user.id))).scalars().all()
    hits = [r for r in rates if _match_company(r.company_name, company) and (not product or product in (r.product or "") or (r.product or "") in product)]
    if not hits:
        return {"company": company, "product": product or None, "found": False,
                "note": "אין שיעור בהסכם לחברה/מוצר הזה. אפשר לבקש את ההסכם מהחברה (מדף ההסכמים)."}
    return {"company": company, "found": True, "rates": [
        {"company": r.company_name, "product": r.product or "כללי", "rate_pct": round(float(r.rate) * 100, 3),
         "kind": r.rate_kind, "scope": r.rate_scope, "paid_to": r.paid_to,
         "from": r.effective_from, "to": r.effective_to} for r in hits[:25]],
        "note": "rate_pct באחוזים (השיעור נשמר כשבר)."}


@tool("list_agreements", "אילו הסכמי עמלות יש לסוכן, לכל חברה כמה שיעורים, ואילו חברות בתיק בלי הסכם.",
      category="agreements", status_he="סוקר את ההסכמים")
async def list_agreements(ctx):
    from app.services import data_map
    return data_map.page_agreements(await ctx.map())


@tool("get_insights", "תובנות לפעולה מתוך הנתונים: tasks = מה פתוח היום, retention = סכנת נטישה/פיגור, crosssell = כפל/חסר/איחוד, reconcile = פערים בין הסכם לנפרעים.",
      {"kind": {"type": "string", "enum": ["tasks", "retention", "crosssell", "reconcile"]}}, ["kind"],
      category="opportunities", status_he="מחפש הזדמנויות")
async def get_insights(ctx, kind: str):
    from app.services import data_map
    return data_map.render(await ctx.map(), f"{kind}.md")[:6000]


@tool("open_page", "פתיחת דף במפת הנתונים (Markdown): index.md, companies.md, companies/<key>.md, customers/<ת.ז>.md, search/<שם>.md, unpaid.md, mail.md, agreements.md, top.md, policy/<מספר>.md — או dict/<קטגוריה>.md במילון הנתונים.",
      {"path": {"type": "string"}}, ["path"], category="navigation", status_he="קורא בנתונים")
async def open_page(ctx, path: str):
    p = (path or "index.md").strip().lstrip("./")
    if p.startswith("dict/"):
        from app.services.agent.prompt import dictionary_page
        return dictionary_page(p[len("dict/"):])
    from app.services import data_map
    return data_map.render(await ctx.map(), p)[:6000]


@tool("list_mail", "מיילים פתוחים מחברות ומלקוחות (מה-Mail Agent): מי, סיכום, האם יש טיוטה.",
      category="mail", status_he="בודק את המיילים")
async def list_mail(ctx):
    from app.services import data_map
    return data_map.page_mail(await ctx.map())[:5000]


@tool("get_production_changes", "מה השתנה בפרודוקציה מול הקובץ הקודם של אותה חברה: לקוחות חדשים ולקוחות שיצאו (עזבו/בוטלו), לכל חברה.",
      category="production", status_he="משווה לחודש הקודם")
async def get_production_changes(ctx):
    from app.models.record import ClientRecord
    from app.models.upload import FileUpload

    async def compute():
        ups = (await ctx.db.execute(select(FileUpload).where(
            FileUpload.user_id == ctx.user.id, FileUpload.file_category == "production")
            .order_by(FileUpload.uploaded_at.desc()))).scalars().all()
        by_co: dict[str, list] = defaultdict(list)
        for u in ups:
            if u.company_source and u.company_source != "מאוחד":
                by_co[u.company_source].append(u)
        out = []
        for co, lst in by_co.items():
            cur = next((u for u in lst if u.is_production), None)
            prev = next((u for u in lst if cur and u.id != cur.id and (u.period_month or u.uploaded_at) != (cur.period_month or cur.uploaded_at)), None)
            if not cur or not prev:
                continue

            async def people(uid):
                rows = (await ctx.db.execute(select(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name)
                        .where(ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id == uid, ClientRecord.id_number.isnot(None)))).all()
                return {str(r[0]).lstrip("0"): " ".join(x for x in (r[1], r[2]) if x) for r in rows}
            a, b = await people(cur.id), await people(prev.id)
            new, gone = set(a) - set(b), set(b) - set(a)
            out.append({"company": co, "current_period": str(cur.period_month or cur.uploaded_at.date()),
                        "previous_period": str(prev.period_month or prev.uploaded_at.date()),
                        "new": len(new), "left": len(gone),
                        "new_names": [a[i] or i for i in list(new)[:8]], "left_names": [b[i] or i for i in list(gone)[:8]]})
        return out
    data = await _cached(ctx, ("prod_changes",), compute)
    if not data:
        return {"companies": [], "note": "אין קובץ פרודוקציה קודם להשוואה באף חברה."}
    rid = ctx.keep([{"label": d["company"], "value": d["left"]} for d in data], label="חברה", value="לקוחות שיצאו", unit="",
                   title="לקוחות שיצאו לפי חברה")
    return {"companies": data, "result_id": rid}


@tool("get_agreement_doc", "קריאת מסמך הסכם/דף עמלות שהסוכן העלה (PDF שחולץ): סיכום, חברות, תוכן מלא. לשאלות 'מה כתוב בהסכם', תנאים, בונוסים, היקפים. בלי query — רשימת המסמכים.",
      {"query": {"type": "string", "description": "שם חברה או מילה משם הקובץ"}}, category="agreements", status_he="קורא את מסמך ההסכם")
async def get_agreement_doc(ctx, query: str = ""):
    from app.models.ai_document import AiDocument
    docs = (await ctx.db.execute(select(AiDocument).where(AiDocument.user_id == ctx.user.id, AiDocument.status == "ready")
                                 .order_by(AiDocument.uploaded_at.desc()))).scalars().all()
    if not docs:
        return "הסוכן עוד לא העלה מסמכי הסכם (מדף ההסכמים)."
    q = (query or "").strip()
    hits = [d for d in docs if not q or q in (d.filename or "") or any(q in str(c) or str(c) in q for c in (d.companies_mentioned or []))]
    if not q or not hits:
        head = "" if not q else f"לא נמצא מסמך עבור «{q}». "
        return head + "המסמכים: " + "; ".join(f"{d.filename} ({', '.join(map(str, d.companies_mentioned or [])) or d.doc_type or ''})" for d in docs[:20])
    d = hits[0]
    body = d.extracted_text or ""
    if not body and isinstance(d.structured_data, dict):
        body = str(d.structured_data.get("full_content") or "")
    return (f"# {d.filename}\nסוג: {d.doc_type or ''} · חברות: {', '.join(map(str, d.companies_mentioned or []))}\n\n"
            f"## סיכום\n{d.summary or ''}\n\n## תוכן\n{body[:10000]}"
            + (f"\n\n(יש עוד {len(hits) - 1} מסמכים תואמים)" if len(hits) > 1 else ""))
