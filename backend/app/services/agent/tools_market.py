"""Fund-market skills — the six categories of the official גמל-נט / פנסיה-נט / ביטוח-נט
data (services/fund_market). One compare skill per category, a per-customer
"fund fit" that follows the customer's own money, market flows, and the ranked
opportunities list.

Matching a customer's product to an official fund NEVER guesses across insurers:
candidates are narrowed to the same managing company (company_stem) and the same
category (from product_type), then compared on the track's key tokens (age band,
מניות/כללי/S&P500…). No confident match → "לא זוהה מסלול" (never a neighbour's fund).
"""
from __future__ import annotations

import re
import statistics
from collections import defaultdict

from sqlalchemy import func, select

from app.models.fund_market import FundMarketMonthly as F
from app.services.agent import cache
from app.services.agent.registry import tool
from app.utils.company_norm import company_stem

DISCLAIMER = "תשואות עבר אינן מבטיחות תשואות עתידיות."

# skill -> (source, classifications, Hebrew label)
CATEGORIES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "hishtalmut": ("gemel", ("קרנות השתלמות",), "קרנות השתלמות"),
    "gemel": ("gemel", ("תגמולים ואישית לפיצויים", "מרכזית לפיצויים"), "קופות גמל ואישית לפיצויים"),
    "gemel_invest": ("gemel", ("קופת גמל להשקעה",), "קופות גמל להשקעה"),
    "child_savings": ("gemel", ("קופת גמל להשקעה - חסכון לילד",), "חיסכון לכל ילד"),
    "pension": ("pension", ("קרנות חדשות", "קרנות כלליות"), "קרנות פנסיה"),
    "savings_policy": ("insurance", (), "פוליסות חיסכון"),
}
SORTS = {"yield_3y": F.avg_yield_3y, "yield_5y": F.avg_yield_5y, "ytd": F.ytd_yield, "month": F.monthly_yield,
         "fee": F.mgmt_fee, "sharpe": F.sharpe, "size": F.total_assets, "inflow": F.net_monthly_deposits}
SORT_HE = {"yield_3y": "תשואה שנתית ממוצעת 3 שנים", "yield_5y": "תשואה שנתית ממוצעת 5 שנים", "ytd": "תשואה מתחילת השנה",
           "month": "תשואה חודשית", "fee": "דמי ניהול מצבירה", "sharpe": "שארפ", "size": "גודל (מ' ₪)", "inflow": "צבירה נטו בחודש (מ' ₪)"}


def category_for_product(product_type: str | None, product: str | None = None) -> str | None:
    t = f"{product_type or ''} {product or ''}"
    if "השתלמות" in t:
        return "hishtalmut"
    if "לילד" in t or "חסכון לכל ילד" in t or "חיסכון לכל ילד" in t:
        return "child_savings"
    if "להשקעה" in t:
        return "gemel_invest"
    if "פנסיה" in t or "מקיפה" in t:
        return "pension"
    if "פוליס" in t or "חיסכון" in t or "חסכון" in t:
        return "savings_policy"
    if "גמל" in t or "תגמולים" in t or "פיצויים" in t:
        return "gemel"
    return None


_SYN = [(r"מחקה", "עוקב"), (r"s\s*&\s*p\s*-?\s*500|500\s*s\s*&\s*p", "sp500"), (r"\bשקלי\b", "כספי"),
        (r"\b05\b", "50"), (r"אג\"?ח", "אגח"), (r"סחיר", "סחיר")]
KEY = {"עוקב", "sp500", "מניות", "כללי", "אגח", "כספי", "הלכה", "הלכתי", "שריעה", "סחיר", "מדדי", "מדד", "לבני", "50", "60",
       "ומטה", "ומעלה", "עד", "קיימות", "פאסיבי", "אקטיבי", "חול", "ישראל", "צמוד", "יעד", "2030", "2040", "פלוס", "משולב"}


def tokens(name: str | None) -> set[str]:
    s = (name or "").lower().replace("'", "").replace("-", " ").replace("_", " ")
    for a, b in _SYN:
        s = re.sub(a, b, s)
    return {w for w in re.split(r"[\s,()/]+", s) if w in KEY}


def match_fund(track: str | None, company: str | None, funds: list) -> tuple[object | None, str]:
    """(fund row, how) — 'exact' | 'tokens' | '' (no confident match)."""
    if not track:
        return None, ""
    stem = company_stem(company) or company_stem(track)
    cands = [f for f in funds if stem and company_stem(f.managing_corporation or f.fund_name) == stem]
    if not cands:
        return None, ""
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"^\d+\s*|\d{3,4}(?=[א-ת])", "", (s or "").replace('"', ""))).strip().lower()
    t = norm(track)
    for f in cands:
        if norm(f.fund_name) == t:
            return f, "exact"
    tk = tokens(track)
    if not tk:
        return None, ""
    best, score = None, 0.0
    for f in cands:
        fk = tokens(f.fund_name)
        if not fk:
            continue
        j = len(tk & fk) / len(tk | fk)
        if j > score:
            best, score = f, j
    return (best, "tokens") if best and score >= 0.75 else (None, "")


_LABEL_NOISE = re.compile(r"\s*(?:קרן השתלמות|קרנות השתלמות|השתלמות|קופת גמל להשקעה|קופת גמל|גמל להשקעה|חיסכון לכל ילד|"
                         r"פנסיה מקיפה|פנסיה|מקיפה|מסלול|קרן|בע\"מ|-)\s*")


def fund_label(name: str | None) -> str:
    """Chart label: company + track, without the category words every bar shares — the bar
    chart shows ~9 letters ("כלל השתלמות מניות" → "כלל מניות"); the full name is in the data."""
    s = re.sub(r"\s+", " ", _LABEL_NOISE.sub(" ", name or "")).strip()
    return s or (name or "")


def is_open(f) -> bool:
    """Can a new customer join this fund? Sector/employer-only funds (e.g. רום — local-authority
    employees) and veteran pension funds (קרנות כלליות, closed) are never a switch target or a
    "best fund" — they're only matched when the customer is already in them."""
    return (f.target_population in (None, "", "כלל האוכלוסיה")) and f.classification != "קרנות כלליות"


async def latest_period(db) -> int | None:
    return (await db.execute(select(func.max(F.report_period)))).scalar_one_or_none()


async def _category_rows(db, cat: str, period: int) -> list:
    source, classes, _ = CATEGORIES[cat]
    q = select(F).where(F.source == source, F.report_period == period)
    if classes:
        q = q.where(F.classification.in_(classes))
    return list((await db.execute(q)).scalars().all())


def _med(vals):
    vals = [v for v in vals if v is not None]
    return round(statistics.median(vals), 2) if vals else None


def _fund_row(f) -> dict:
    return {"fund_id": f.fund_id, "fund": f.fund_name, "company": company_stem(f.managing_corporation) or f.managing_corporation,
            "track": " · ".join(x for x in (f.specialization, f.sub_specialization) if x),
            "avg_yield_3y": f.avg_yield_3y, "avg_yield_5y": f.avg_yield_5y, "ytd": f.ytd_yield, "month": f.monthly_yield,
            "mgmt_fee": f.mgmt_fee, "deposit_fee": f.deposit_fee, "sharpe": f.sharpe, "std_dev": f.std_dev,
            "size_m": f.total_assets, "net_inflow_m": f.net_monthly_deposits}


async def compare_category(ctx, cat: str, track: str = "", sort_by: str = "yield_3y", n: int = 10, min_size_m: float = 100) -> dict:
    period = await latest_period(ctx.db)
    if not period:
        return {"error": "אין עדיין נתוני שוק — הסנכרון מגמל-נט לא רץ."}
    key = ("market", cat, track, sort_by, n, min_size_m, period)
    hit = cache.get("market", 0, key)
    if hit is not None:
        ctx_rid = ctx.keep(hit["_keep"][0], **hit["_keep"][1])
        return {**{k: v for k, v in hit.items() if k != "_keep"}, "result_id": ctx_rid}
    rows = await _category_rows(ctx.db, cat, period)
    if track:
        tk = tokens(track) or {track}
        rows = [f for f in rows if (tk & tokens(f"{f.fund_name} {f.specialization} {f.sub_specialization}")) or track in (f.specialization or "") or track in (f.fund_name or "")]
    restricted = sum(1 for f in rows if not is_open(f))
    rows = [f for f in rows if is_open(f) and (f.total_assets or 0) >= (min_size_m or 0)]
    col = sort_by if sort_by in SORTS else "yield_3y"
    attr = {"yield_3y": "avg_yield_3y", "yield_5y": "avg_yield_5y", "ytd": "ytd_yield", "month": "monthly_yield", "fee": "mgmt_fee",
            "sharpe": "sharpe", "size": "total_assets", "inflow": "net_monthly_deposits"}[col]
    asc = col == "fee"
    ranked = sorted([f for f in rows if getattr(f, attr) is not None], key=lambda f: getattr(f, attr), reverse=not asc)
    top = ranked[: max(1, min(int(n or 10), 25))]
    y, m = divmod(period, 100)
    out = {
        "category": CATEGORIES[cat][2], "data_month": f"{m:02d}/{y}", "funds_compared": len(rows),
        "excluded_restricted": restricted,
        "note": "רק קופות פתוחות לכלל הציבור (בלי קופות סקטוריאליות/מפעליות וקרנות ותיקות סגורות)",
        "sorted_by": SORT_HE[col], "track_filter": track or None,
        "median": {"avg_yield_3y": _med([f.avg_yield_3y for f in rows]), "avg_yield_5y": _med([f.avg_yield_5y for f in rows]),
                   "ytd": _med([f.ytd_yield for f in rows]), "mgmt_fee": _med([f.mgmt_fee for f in rows])},
        "top": [_fund_row(f) for f in top],
        "units": "תשואות ודמי ניהול באחוזים; גודל וזרימות במיליוני ₪", "source": "גמל-נט/פנסיה-נט/ביטוח-נט (רשות שוק ההון, data.gov.il)",
        "disclaimer": DISCLAIMER,
    }
    keep_args = ([{"label": fund_label(f.fund_name)[:40], "value": round(getattr(f, attr), 2)} for f in top],
                 {"label": "קופה", "value": SORT_HE[col], "unit": "%" if col not in ("size", "inflow") else "", "title": f"{CATEGORIES[cat][2]} — {SORT_HE[col]}"})
    out["result_id"] = ctx.keep(keep_args[0], **keep_args[1])
    cache.put("market", 0, key, {**out, "_keep": keep_args}, ttl=6 * 3600)
    return out


def _compare_tool(cat: str, desc: str):
    @tool(f"compare_{cat}", desc + " נתונים רשמיים חודשיים לפי קופה: תשואה (חודש, מתחילת שנה, 3/5 שנים), דמי ניהול, שארפ, גודל וזרימות.",
          {"track": {"type": "string", "description": "סינון מסלול: מניות, כללי, S&P500, אג\"ח, לבני 50 עד 60, הלכה… או ריק"},
           "sort_by": {"type": "string", "enum": list(SORTS)},
           "n": {"type": "integer", "description": "כמה קופות (ברירת מחדל 10)"}},
          category="market", status_he=f"משווה {CATEGORIES[cat][2]}")
    async def _f(ctx, track: str = "", sort_by: str = "yield_3y", n: int = 10):
        return await compare_category(ctx, cat, track, sort_by, n)
    return _f


compare_hishtalmut = _compare_tool("hishtalmut", "השוואת קרנות השתלמות.")
compare_gemel = _compare_tool("gemel", "השוואת קופות גמל לתגמולים ואישיות לפיצויים (כולל מסלולי גיל).")
compare_gemel_invest = _compare_tool("gemel_invest", "השוואת קופות גמל להשקעה.")
compare_child_savings = _compare_tool("child_savings", "השוואת מסלולי חיסכון לכל ילד.")
compare_pension = _compare_tool("pension", "השוואת קרנות פנסיה (מקיפות/חדשות וכלליות).")
compare_savings_policy = _compare_tool("savings_policy", "השוואת פוליסות חיסכון (ביטוח-נט).")


async def _customer_products(ctx, idn: str) -> list[dict]:
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord
    ids = await _get_production_upload_ids(ctx.db, ctx.user.id)
    if not ids:
        return []
    recs = (await ctx.db.execute(select(ClientRecord).where(
        ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id.in_(ids),
        func.ltrim(ClientRecord.id_number, "0") == idn))).scalars().all()
    out = []
    for r in recs:
        splits = r.track_split if isinstance(r.track_split, list) and r.track_split else None
        parts = [(s.get("track"), float(s.get("amount") or 0)) for s in splits] if splits else [(r.track, float(r.accumulation or 0))]
        for trk, amt in parts:
            out.append({"company": r.receiving_company, "product_type": r.product_type, "product": r.product,
                        "track": trk, "accumulation": amt, "policy": r.fund_policy_number,
                        "name": " ".join(x for x in (r.first_name, r.last_name) if x)})
    return out


async def fund_fit(ctx, idn: str) -> dict:
    period = await latest_period(ctx.db)
    prods = await _customer_products(ctx, idn)
    if not period or not prods:
        return {"id_number": idn, "products": [], "note": "אין ללקוח מוצרי חיסכון בפרודוקציה, או שאין נתוני שוק."}
    rows_by_cat: dict[str, list] = {}
    res = []
    for p in prods:
        cat = category_for_product(p["product_type"], p["product"])
        if not cat or not p["accumulation"]:
            continue
        if cat not in rows_by_cat:
            rows_by_cat[cat] = await _category_rows(ctx.db, cat, period)
        cands = rows_by_cat[cat]
        f, how = match_fund(p["track"], p["company"], cands)
        item = {"company": company_stem(p["company"]) or p["company"], "category": CATEGORIES[cat][2], "track": p["track"],
                "accumulation": round(p["accumulation"]), "policy": p["policy"]}
        if not f:
            item["match"] = "לא זוהה מסלול רשמי — אין השוואה"
            res.append(item)
            continue
        same_risk = [x for x in cands if x.specialization == f.specialization and (x.sub_specialization == f.sub_specialization)
                     and (x.total_assets or 0) >= 100 and x.avg_yield_3y is not None and (is_open(x) or x.fund_id == f.fund_id)]
        best = max((x for x in same_risk if is_open(x)), key=lambda x: x.avg_yield_3y, default=None)
        med_fee = _med([x.mgmt_fee for x in same_risk])
        hist = (await ctx.db.execute(select(F.report_period, F.monthly_yield).where(
            F.source == f.source, F.fund_id == f.fund_id).order_by(F.report_period.desc()).limit(12))).all()
        item.update({
            "match": "מדויק" if how == "exact" else "לפי מאפייני המסלול",
            "official_fund": f.fund_name, "fund_id": f.fund_id,
            "avg_yield_3y": f.avg_yield_3y, "peer_median_avg_yield_3y": _med([x.avg_yield_3y for x in same_risk]),
            "rank_in_peers": (sorted(same_risk, key=lambda x: -x.avg_yield_3y).index(f) + 1) if f in same_risk else None,
            "peers": len(same_risk), "mgmt_fee": f.mgmt_fee, "peer_median_fee": med_fee,
            "fee_gap_ils_per_year": round(p["accumulation"] * ((f.mgmt_fee or 0) - (med_fee or 0)) / 100) if med_fee is not None and f.mgmt_fee is not None else None,
            "best_peer": {"fund": best.fund_name, "company": company_stem(best.managing_corporation), "avg_yield_3y": best.avg_yield_3y,
                          "mgmt_fee": best.mgmt_fee} if best and best.fund_id != f.fund_id else None,
            "annual_gap_vs_best_ils": round(p["accumulation"] * (best.avg_yield_3y - f.avg_yield_3y) / 100)
            if best and f.avg_yield_3y is not None and best.fund_id != f.fund_id else 0,
            "last_12_months_yield": [{"month": f"{pp % 100:02d}/{pp // 100}", "yield": y} for pp, y in reversed(hist)],
        })
        res.append(item)
    y, m = divmod(period, 100)
    return {"id_number": idn, "name": prods[0]["name"], "data_month": f"{m:02d}/{y}", "products": res,
            "how_to_read": "annual_gap_vs_best_ils = צבירה × (תשואה שנתית ממוצעת 3ש של המסלול הטוב באותה רמת סיכון − של המסלול הנוכחי). אומדן, לא הבטחה.",
            "disclaimer": DISCLAIMER}


@tool("get_customer_fund_fit", "עוקב אחרי הכסף של לקוח: לכל מוצר חיסכון (גמל, השתלמות, פנסיה, פוליסה) — המסלול הרשמי שלו, דירוג מול מסלולים באותה רמת סיכון, דמי ניהול מול השוק (₪ בשנה), המסלול הטוב ביותר ופער שנתי משוער ב-₪, ו-12 חודשי תשואה.",
      {"id_number": {"type": "string"}}, ["id_number"], category="market", status_he="משווה את הקופות של הלקוח לשוק")
async def get_customer_fund_fit(ctx, id_number: str):
    idn = "".join(ch for ch in str(id_number) if ch.isdigit()).lstrip("0") or "0"
    out = await fund_fit(ctx, idn)
    rows = [{"label": f"{p['company']} {p['category']}", "value": p.get("annual_gap_vs_best_ils") or 0} for p in out.get("products", []) if p.get("official_fund")]
    if rows:
        out["result_id"] = ctx.keep(rows, label="מוצר", value="פער שנתי משוער מול הטוב ביותר", title="כמה הלקוח מפסיד בשנה מול המסלול המוביל")
    return out


@tool("fund_opportunities", "הלקוחות שהכסף שלהם במסלולים שמפגרים אחרי השוק באותה רמת סיכון — מדורג לפי פער שנתי משוער ב-₪. להצעת שיחת שימור/ניוד ללקוחות.",
      {"category": {"type": "string", "enum": ["", *CATEGORIES]}, "min_gap_ils": {"type": "integer", "description": "פער מינימלי בשנה (ברירת מחדל 1000)"},
       "n": {"type": "integer"}},
      category="market", status_he="מחפש לקוחות במסלולים חלשים")
async def fund_opportunities(ctx, category: str = "", min_gap_ils: int = 1000, n: int = 10):
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord

    async def compute():
        period = await latest_period(ctx.db)
        ids = await _get_production_upload_ids(ctx.db, ctx.user.id)
        if not period or not ids:
            return []
        recs = (await ctx.db.execute(select(ClientRecord).where(
            ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id.in_(ids),
            ClientRecord.accumulation > 0, ClientRecord.track.isnot(None)))).scalars().all()
        rows_by_cat: dict[str, list] = {}
        fit_cache: dict[tuple, tuple] = {}
        per_cust: dict[str, dict] = defaultdict(lambda: {"gap": 0.0, "acc": 0.0, "items": []})
        for r in recs:
            cat = category_for_product(r.product_type, r.product)
            if not cat:
                continue
            if cat not in rows_by_cat:
                rows_by_cat[cat] = await _category_rows(ctx.db, cat, period)
            k = (cat, r.track, r.receiving_company)
            if k not in fit_cache:
                cands = rows_by_cat[cat]
                f, _ = match_fund(r.track, r.receiving_company, cands)
                best = None
                if f and f.avg_yield_3y is not None:
                    peers = [x for x in cands if x.specialization == f.specialization and x.sub_specialization == f.sub_specialization
                             and (x.total_assets or 0) >= 100 and x.avg_yield_3y is not None and is_open(x)]
                    best = max(peers, key=lambda x: x.avg_yield_3y, default=None)
                fit_cache[k] = (cat, f, best)
            cat, f, best = fit_cache[k]
            if not f or not best or best.fund_id == f.fund_id:
                continue
            gap = float(r.accumulation) * (best.avg_yield_3y - f.avg_yield_3y) / 100
            idn = str(r.id_number).lstrip("0")
            c = per_cust[idn]
            c["name"] = " ".join(x for x in (r.first_name, r.last_name) if x) or idn
            c["gap"] += gap
            c["acc"] += float(r.accumulation)
            c["items"].append({"category": cat, "track": f.fund_name, "best": best.fund_name, "gap": round(gap)})
        return [{"id_number": k, **v} for k, v in per_cust.items()]

    data = await cache_get_or(ctx, ("fund_opps",), compute)
    if not data:
        return {"customers": [], "reason": "בפרודוקציה הפעילה אין מוצרי חיסכון (גמל/השתלמות/פנסיה/פוליסה) עם מסלול וצבירה שאפשר להשוות לשוק — "
                "או שכל המסלולים כבר המובילים ברמת הסיכון שלהם. ההשוואה מבוססת על המסלולים בקבצי הפרודוקציה, לא על המסלקה."}
    rows = [d for d in data if d["gap"] >= (min_gap_ils or 0)
            and (not category or any(i["category"] == category for i in d["items"]))]
    rows.sort(key=lambda d: -d["gap"])
    top = rows[: max(1, min(int(n or 10), 30))]
    out = [{"name": d["name"], "id_number": d["id_number"], "accumulation": round(d["acc"]), "annual_gap_ils": round(d["gap"]),
            "products": d["items"][:4]} for d in top]
    rid = ctx.keep([{"label": d["name"], "value": d["annual_gap_ils"], "id_number": d["id_number"]} for d in out],
                   label="לקוח", value="פער שנתי משוער", title="לקוחות במסלולים שמפגרים אחרי השוק")
    return {"customers": out, "total_customers": len(rows), "total_annual_gap_ils": round(sum(d["gap"] for d in rows)),
            "how_to_read": "פער = צבירה × (תשואה שנתית ממוצעת 3ש של המסלול המוביל באותה רמת סיכון − המסלול של הלקוח). אומדן.",
            "disclaimer": DISCLAIMER, "result_id": rid}


async def cache_get_or(ctx, key, fn, ttl=1800):
    hit = cache.get(ctx.user.id, ctx.data_version, key)
    if hit is None:
        hit = await fn()
        cache.put(ctx.user.id, ctx.data_version, key, hit, ttl=ttl)
    return hit


@tool("market_flows", "לאן זורם הכסף בשוק בקטגוריה: אילו חברות/קופות קיבלו הכי הרבה צבירה נטו (הפקדות+העברות פנימה פחות משיכות) בחודש האחרון ובשלושה חודשים.",
      {"category": {"type": "string", "enum": list(CATEGORIES)}}, ["category"], category="market", status_he="בודק לאן זורם הכסף")
async def market_flows(ctx, category: str):
    period = await latest_period(ctx.db)
    if not period or category not in CATEGORIES:
        return {"error": "אין נתוני שוק."}
    source, classes, label = CATEGORIES[category]
    periods = (await ctx.db.execute(select(F.report_period).where(F.source == source).distinct()
                                    .order_by(F.report_period.desc()).limit(3))).scalars().all()
    q = select(F).where(F.source == source, F.report_period.in_(periods))
    if classes:
        q = q.where(F.classification.in_(classes))
    rows = (await ctx.db.execute(q)).scalars().all()
    by_co_last, by_co_3 = defaultdict(float), defaultdict(float)
    for f in rows:
        co = company_stem(f.managing_corporation or f.fund_name) or f.managing_corporation or "—"
        v = f.net_monthly_deposits or 0
        by_co_3[co] += v
        if f.report_period == period:
            by_co_last[co] += v
    ranked = sorted(by_co_3.items(), key=lambda kv: -kv[1])
    rid = ctx.keep([{"label": k, "value": round(v, 1)} for k, v in ranked[:10]], label="חברה", value="צבירה נטו 3 חודשים (מ' ₪)", unit="",
                   title=f"{label} — לאן זורם הכסף (3 חודשים)")
    y, m = divmod(period, 100)
    return {"category": label, "data_month": f"{m:02d}/{y}", "units": "מיליוני ₪",
            "net_inflow_3_months": [{"company": k, "net_m": round(v, 1)} for k, v in ranked],
            "net_inflow_last_month": [{"company": k, "net_m": round(v, 1)} for k, v in sorted(by_co_last.items(), key=lambda kv: -kv[1])],
            "result_id": rid}


@tool("market_changes", "מה השתנה בשוק בחודש האחרון לעומת החודש שלפניו, בקטגוריה: שינויי דמי ניהול, קופות שעלו/ירדו בדירוג התשואה בתוך קבוצת השווים, "
      "הכי הרבה כניסות/יציאות כסף, קופות חדשות וקופות שלא דווחו החודש; בפנסיה גם שינויי חשיפה למניות/חו\"ל/מט\"ח (פנסיה-נט).",
      {"category": {"type": "string", "enum": list(CATEGORIES)}}, ["category"], category="market", status_he="בודק מה השתנה בשוק")
async def market_changes(ctx, category: str):
    from app.services.fund_market.delta import market_delta
    if category not in CATEGORIES:
        return {"error": "קטגוריה לא מוכרת."}
    source, classes, label = CATEGORIES[category]
    period = await latest_period(ctx.db)
    key = ("market_changes", category, period)
    hit = cache.get("market", 0, key)
    if hit is None:
        hit = await market_delta(ctx.db, source, classes, open_only=is_open)
        # don't pin "allocation unavailable" for hours while pensyanet is still importing that month
        if (hit.get("allocation_shifts") or {}).get("available") is not False:
            cache.put("market", 0, key, hit, ttl=6 * 3600)
    if not hit.get("found"):
        return hit
    flows = hit.get("top_inflows") or []
    rid = ctx.keep([{"label": fund_label(r["fund"])[:40], "value": r["net_inflow_m"]} for r in flows[:10]], label="קופה",
                   value="צבירה נטו בחודש (מ' ₪)", unit="", title=f"{label} — הכי הרבה כסף נכנס ({hit['month']})") if flows else None
    return {"category": label, **hit, "result_id": rid, "disclaimer": DISCLAIMER,
            "source": "גמל-נט/פנסיה-נט/ביטוח-נט (רשות שוק ההון)"}


@tool("fund_allocation", "פילוח הנכסים של מסלול פנסיה (פנסיה-נט): 10 קבוצות ראשיות (אג\"ח ממשלתיות, מיועדות, מניות, הלוואות…), רמת סיכון, "
      "סחיר/לא סחיר, ארץ/חו\"ל, חשיפה למניות/חו\"ל/מט\"ח — החודש האחרון והשינוי מהחודש שלפניו; וגם האיזון האקטוארי של הקרן. "
      "fund = שם המסלול או מספר הקופה.",
      {"fund": {"type": "string"}}, ["fund"], category="market", status_he="בודק את פילוח הנכסים")
async def fund_allocation(ctx, fund: str):
    from app.models.fund_market import PensyanetData as P
    from app.services.fund_market.delta import track_allocation
    period = (await ctx.db.execute(select(func.max(F.report_period)).where(F.source == "pension"))).scalar_one_or_none()
    rows = (await ctx.db.execute(select(F).where(F.source == "pension", F.report_period == period))).scalars().all()
    q = (fund or "").strip()
    if q.isdigit():
        hits = [f for f in rows if f.fund_id == int(q)]
    else:
        words = [w for w in re.split(r"\s+", q.replace('"', "")) if w]
        hits = [f for f in rows if all(w in (f.fund_name or "").replace('"', "") for w in words)]
        if not hits and tokens(q):   # "מור מניות" → company + track words
            stem = company_stem(q)
            hits = [f for f in rows if (not stem or company_stem(f.managing_corporation or f.fund_name) == stem)
                    and tokens(q) <= tokens(f.fund_name)]
    if not hits:
        return {"found": False, "note": "לא נמצא מסלול פנסיה בשם הזה. נסה שם מלא כפי שמופיע בפנסיה-נט, או מספר קופה."}
    if len(hits) > 1:
        hits.sort(key=lambda f: -(f.total_assets or 0))
        if len(hits) > 6:
            return {"found": False, "candidates": [{"fund_id": f.fund_id, "fund": f.fund_name} for f in hits[:12]],
                    "note": "יותר מדי מסלולים מתאימים — בחר אחד."}
    f = hits[0]
    alloc = await track_allocation(ctx.db, f.fund_id)
    if not alloc.get("found"):
        return {"found": False, "fund": f.fund_name, "note": "פילוח הנכסים מפנסיה-נט עוד לא יובא למסלול הזה."}
    # the track's parent fund (pensyanet 'tracks' rows carry ID_KRN) → its actuarial balance. The site
    # stopped publishing fund-level yields (financial/demographic) in 01/2017 — those fields are blank.
    parent = (await ctx.db.execute(select(P.data).where(P.report == "tracks", P.entity_id == f.fund_id)
                                   .order_by(P.period.desc()).limit(1))).scalar_one_or_none()
    actuarial = None
    if parent and parent.get("ID_KRN"):
        y = (await ctx.db.execute(select(P).where(P.report == "yields", P.level == "fund", P.entity_id == int(parent["ID_KRN"]),
                                                  P.data.has_key("ODEF_GIRAON_ACTUARI_RIVONI"))
                                  .order_by(P.period.desc()).limit(1))).scalar_one_or_none()
        if y:
            actuarial = {"fund": y.entity_name, "month": f"{y.period % 100:02d}/{y.period // 100}",
                         "quarterly_pct": y.data.get("ODEF_GIRAON_ACTUARI_RIVONI"),
                         "fund_assets_m": y.data.get("YIT_NCHASIM_BFOAL")}
    main = alloc["groups"].get("חלוקת נכסים ל-10 קבוצות ראשיות") or []
    rid = ctx.keep([{"label": g["item"], "value": g["now_pct"]} for g in main if g.get("now_pct")], label="סוג נכס",
                   value="% מהנכסים", unit="%", title=f"{f.fund_name} — פילוח נכסים ({alloc['month']})") if main else None
    others = [{"fund_id": h.fund_id, "fund": h.fund_name} for h in hits[1:6]]
    return {**alloc, "actuarial_balance": actuarial, "result_id": rid, "other_matches": others or None,
            "note": "חשיפה למניות יכולה להיות גבוהה מאחזקת המניות הישירה (נגזרים/תעודות סל). איזון אקטוארי = התאמת הזכויות לפי ניסיון התמותה/נכות של הקרן (+ = גירעון/עודף לפי הסימן כפי שמפורסם). "
                    "תשואה פיננסית/דמוגרפית ברמת הקרן לא מפורסמת מאז 01/2017 — אל תמציא אותה.",
            "disclaimer": DISCLAIMER}
