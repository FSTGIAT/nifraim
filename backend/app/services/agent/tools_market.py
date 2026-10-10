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
        (r"\b05\b", "50"), (r"\b06\b", "60"), (r"(?<![א-ת])ל?גילאי", "לבני"), (r"(?<!\d)עד\s*50(?!\d)", "לבני 50 ומטה"), (r"(?<!\d)50\s*-\s*60(?!\d)", "לבני 50 עד 60"), (r"אג\"?ח", "אגח"), (r"סחיר", "סחיר")]   # visual-Hebrew files reverse 60 → "06"
KEY = {"עוקב", "sp500", "מניות", "כללי", "אגח", "כספי", "הלכה", "הלכתי", "שריעה", "סחיר", "מדדי", "מדד", "לבני", "50", "60",
       "ומטה", "ומעלה", "קיימות", "פאסיבי", "אקטיבי", "חול", "ישראל", "צמוד", "יעד", "2030", "2040", "פלוס", "משולב"}


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
    scored = []
    for f in cands:
        fk = tokens(f.fund_name)
        if fk:
            scored.append((len(tk & fk) / len(tk | fk), f))
    if not scored:
        return None, ""
    score = max(j for j, _ in scored)
    if score < 0.75:
        return None, ""
    # a tie is broken by the fund, never by list order: "הפניקס גמל מניות" tied with "הפניקס מרכזית לפיצויים
    # עד 15% מניות" and the severance fund won (2026-10-10). Open funds first, then the name sharing the most
    # words with the track + company (מקיפה / כללית / גמל), then size.
    words = set(norm(f"{track} {company or ''}").split())
    tied = [f for j, f in scored if j == score]
    best = max(tied, key=lambda f: (is_open(f), len(words & set(norm(f.fund_name).split())), getattr(f, "total_assets", None) or 0))
    return best, "tokens"


_LABEL_NOISE = re.compile(r"\s*(?:קרן השתלמות|קרנות השתלמות|השתלמות|קופת גמל להשקעה|קופת גמל|גמל להשקעה|חיסכון לכל ילד|"
                         r"פנסיה מקיפה|פנסיה|מקיפה|מסלול|קרן|בע\"מ|-)\s*")


def fund_label(name: str | None) -> str:
    """Chart label: company + track, without the category words every bar shares — the bar
    chart shows ~9 letters ("כלל השתלמות מניות" → "כלל מניות"); the full name is in the data."""
    s = re.sub(r"\s+", " ", _LABEL_NOISE.sub(" ", name or "")).strip()
    return s or (name or "")


def brand(name: str | None) -> str:
    """Market display name of a managing company. company_stem only knows the insurers we pair
    commissions for; an unknown one fell back to a suffix-strip — "אינפיניטי השתלמות, גמל ופנסיה
    בע"מ" showed as "אינפיניטי השתלמות,". Unknown → its first word. Display only: company_stem
    itself feeds rate matching and production merging, so it isn't touched here."""
    from app.utils.company_norm import _match_stem
    hit = _match_stem(name)
    return hit[1] if hit else ((name or "").replace(",", " ").split() or ["—"])[0]


def same_peer(a, b) -> bool:
    """Same risk level = same classification + track (delta._peer). Pension and savings-policy rows
    carry no specialization, so equal specialization (None == None) made EVERY policy a peer: a
    "הפניקס BlackRock כללי" policy was measured against "איילון עוקב מדדים - גמיש" and showed a
    ₪532K/yr "gap" on ₪2.8M (2026-10-10). The track's key words decide instead."""
    from app.services.fund_market.delta import _peer
    return _peer(a) == _peer(b)


def is_open(f) -> bool:
    """Can a new customer join this fund? Sector/employer-only funds (e.g. רום — local-authority
    employees) and veteran pension funds (קרנות כלליות, closed) are never a switch target or a
    "best fund" — they're only matched when the customer is already in them."""
    # מרכזית לפיצויים = employer-only severance funds ("מנורה מבטחים משתתפת בפנסיה תקציבית" was the #2
    # "best גמל at moderate risk", 2026-10-10)
    # IRA / בניהול אישי: self-managed, published yield 0.0 — never a peer or a target (track_score.self_managed)
    from app.services.fund_market.track_score import self_managed
    return (getattr(f, "target_population", None) in (None, "", "כלל האוכלוסיה")) \
        and getattr(f, "classification", None) not in ("קרנות כלליות", "מרכזית לפיצויים") and not self_managed(f)


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
    return {"fund_id": f.fund_id, "fund": f.fund_name, "company": brand(f.managing_corporation or f.fund_name),
            "track": " · ".join(x for x in (f.specialization, f.sub_specialization) if x),
            "avg_yield_3y": f.avg_yield_3y, "avg_yield_5y": f.avg_yield_5y, "ytd": f.ytd_yield, "month": f.monthly_yield,
            "mgmt_fee": f.mgmt_fee, "deposit_fee": f.deposit_fee, "sharpe": f.sharpe, "std_dev": f.std_dev,
            "size_m": f.total_assets, "net_inflow_m": f.net_monthly_deposits}


async def compare_category(ctx, cat: str, track: str = "", sort_by: str = "yield_3y", n: int = 10, min_size_m: float = 100,
                           company: str = "") -> dict:
    period = await latest_period(ctx.db)
    if not period:
        return {"error": "אין עדיין נתוני שוק — הסנכרון מגמל-נט לא רץ."}
    key = ("market", cat, track, sort_by, n, min_size_m, period, company)
    hit = cache.get("market", 0, key)
    if hit is not None:
        ctx_rid = ctx.keep(hit["_keep"][0], **hit["_keep"][1])
        return {**{k: v for k, v in hit.items() if k != "_keep"}, "result_id": ctx_rid}
    rows = await _category_rows(ctx.db, cat, period)
    if track:
        tk = tokens(track) or {track}
        rows = [f for f in rows if (tk & tokens(f"{f.fund_name} {f.specialization} {f.sub_specialization}")) or track in (f.specialization or "") or track in (f.fund_name or "")]
    if company:   # "תשווה בין מור למיטב" — that company's tracks, not just the market's top 10
        stem = company_stem(company) or company
        rows = [f for f in rows if brand(f.managing_corporation or f.fund_name) == stem or stem in (f.fund_name or "")]
    restricted = sum(1 for f in rows if not is_open(f))
    rows = [f for f in rows if is_open(f) and (f.total_assets or 0) >= (min_size_m or 0)]
    from app.services.fund_market.track_score import yields_12m
    y12 = await yields_12m(ctx.db, CATEGORIES[cat][0], period)
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
        "sorted_by": SORT_HE[col], "track_filter": track or None, "company_filter": company or None,
        "median": {"avg_yield_3y": _med([f.avg_yield_3y for f in rows]), "avg_yield_5y": _med([f.avg_yield_5y for f in rows]),
                   "ytd": _med([f.ytd_yield for f in rows]), "mgmt_fee": _med([f.mgmt_fee for f in rows])},
        "top": [{**_fund_row(f), "yield_12m": y12.get(f.fund_id)} for f in top],
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
           "n": {"type": "integer", "description": "כמה קופות (ברירת מחדל 10)"},
           "company": {"type": "string", "description": "רק מסלולים של חברה אחת (מור, מיטב, הפניקס…) — להשוואה בין חברות קרא פעם לכל חברה"}},
          category="market", status_he=f"משווה {CATEGORIES[cat][2]}")
    async def _f(ctx, track: str = "", sort_by: str = "yield_3y", n: int = 10, company: str = ""):
        return await compare_category(ctx, cat, track, sort_by, n, company=company)
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


def _compound(monthly: list) -> float | None:
    vals = [v for v in monthly if v is not None]
    if len(vals) < 12:
        return None
    g = 1.0
    for v in vals[:12]:
        g *= 1 + v / 100
    return round((g - 1) * 100, 2)


_FIT_KEYS = ("company", "category", "official_fund", "fund_id", "track", "match", "accumulation", "accounts", "rank_in_peers", "peers",
             "avg_yield_3y", "peer_median_avg_yield_3y", "yield_12m_pct", "mgmt_fee", "peer_median_fee",
             "annual_gap_vs_best_ils", "fee_gap_ils_per_year", "best_peer", "by_holdings")


def _slim_fit(r: dict) -> dict:
    """Only what an answer uses — a prefetch reaches the model cut at 4,000 chars (2026-10-10: a
    customer's pension sat past the cut and Nifra said it had no pension comparison)."""
    out = {k: r[k] for k in _FIT_KEYS if r.get(k) is not None}
    if out.get("official_fund"):
        out.pop("track", None)
        out.pop("match", None)
    if isinstance(out.get("best_peer"), dict):
        out["best_peer"] = {k: out["best_peer"].get(k) for k in ("fund", "avg_yield_3y")}
    # the direction in words — the model wrote "דמי ניהול נמוכים (0.19% מול 0.14% חציון)" (2026-10-10)
    f, m = out.get("mgmt_fee"), out.get("peer_median_fee")
    if f is not None and m is not None:
        out["fee_vs_peers"] = "גבוה מהחציון" if f > m + 0.005 else "נמוך מהחציון" if f < m - 0.005 else "כמו החציון"
    y, ym = out.get("avg_yield_3y"), out.get("peer_median_avg_yield_3y")
    if y is not None and ym is not None:
        out["yield_vs_peers"] = "מעל החציון" if y > ym + 0.05 else "מתחת לחציון" if y < ym - 0.05 else "כמו החציון"
    return out


async def holdings_ranks(db, cat: str, period: int, rows: list) -> dict[int, dict]:
    """fund_id → risk level + rank inside (category, risk level) — services/fund_market/track_score.
    Global market data → cached for every agent, keyed by the data month."""
    from app.services.fund_market.track_score import rank_groups, yields_12m
    key = ("holdings_ranks", cat, period)
    hit = cache.get("market", 0, key)
    if hit is None:
        y12 = await yields_12m(db, CATEGORIES[cat][0], period)
        hit = {"y12": y12, "ranks": rank_groups(rows, y12, is_open)}
        cache.put("market", 0, key, hit, ttl=6 * 3600)
    return {fid: {**info, "y12": hit["y12"].get(fid)} for fid, info in hit["ranks"].items()}


def holdings_view(f, info: dict | None, accumulation: float, y12: float | None) -> dict:
    """The agent-facing holdings block for one product: risk level, rank, action (+₪ when real)."""
    from app.services.fund_market.track_score import verdict
    if not info:
        return {"action": "אין נתוני חשיפה למסלול — אין דירוג לפי אחזקות"}
    out = {"risk_level": f"{info['level']} {info['label']}", "stock_pct": info.get("stock_pct"),
           "abroad_pct": info.get("abroad_pct"), "fx_pct": info.get("fx_pct")}
    if info.get("rank"):
        out["rank"] = f"#{info['rank']} מתוך {info['of']}"
        if info["leader"]["fund_id"] != f.fund_id:
            out["leader"] = {k: info["leader"].get(k) for k in ("fund", "avg_yield_3y", "yield_12m")}
    return {**out, **verdict(f, info, accumulation, y12)}


def _label_same_name(r: dict) -> dict:
    """Every same-name figure says so in its key — "אחרון בקבוצת הסיכון שלו" was written over a same-name 14/14
    and a "#1 בקבוצתה" over a track that is #9/26 at its risk level (2026-10-10)."""
    r = dict(r)
    rank, peers = r.pop("rank_in_peers", None), r.pop("peers", None)
    if rank:
        r["same_name_rank"] = f"#{rank} מתוך {peers} (מול מסלולים באותו שם)"
    if "annual_gap_vs_best_ils" in r:
        r["same_name_gap_ils"] = r.pop("annual_gap_vs_best_ils")
    if "best_peer" in r:
        r["same_name_best"] = r.pop("best_peer")
    if isinstance(r.get("by_holdings"), dict):
        r["risk_level_view"] = r.pop("by_holdings")
    return r


def _merge_same_track(items: list[dict]) -> list[dict]:
    """Several accounts in one official track → one line (accumulation and ₪ gaps summed)."""
    out: dict = {}
    for it in items:
        k = it.get("fund_id") or ("—", it.get("category"), it.get("track"))
        if k not in out:
            out[k] = {**it, "accounts": 1}
            out[k].pop("policy", None)
            continue
        o = out[k]
        o["accounts"] += 1
        for f in ("accumulation", "annual_gap_vs_best_ils", "fee_gap_ils_per_year"):
            if it.get(f) is not None:
                o[f] = (o.get(f) or 0) + it[f]
    return sorted(out.values(), key=lambda r: -(r.get("accumulation") or 0))


async def fund_fit(ctx, idn: str) -> dict:
    period = await latest_period(ctx.db)
    prods = await _customer_products(ctx, idn)
    if not period or not prods:
        return {"id_number": idn, "products": [], "note": "אין ללקוח מוצרי חיסכון בפרודוקציה, או שאין נתוני שוק."}
    rows_by_cat: dict[str, list] = {}
    hold_by_cat: dict[str, dict] = {}
    fund_by_id: dict[int, object] = {}
    res = []
    for p in prods:
        cat = category_for_product(p["product_type"], p["product"])
        if not cat or not p["accumulation"]:
            continue
        if cat not in rows_by_cat:
            rows_by_cat[cat] = await _category_rows(ctx.db, cat, period)
            hold_by_cat[cat] = await holdings_ranks(ctx.db, cat, period, rows_by_cat[cat])
        cands = rows_by_cat[cat]
        f, how = match_fund(p["track"], p["company"], cands)
        item = {"company": company_stem(p["company"]) or p["company"], "category": CATEGORIES[cat][2], "track": p["track"],
                "accumulation": round(p["accumulation"]), "policy": p["policy"]}
        if not f:
            item["match"] = "לא זוהה מסלול רשמי — אין השוואה"
            res.append(item)
            continue
        fund_by_id[f.fund_id] = (f, hold_by_cat[cat].get(f.fund_id))
        same_risk = [x for x in cands if same_peer(x, f)
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
            # one number, not a 12-row list per product (a 14-product customer was 14,500 chars and the
            # model never saw the pension at the end — 2026-10-10)
            "yield_12m_pct": _compound([y for _, y in hist]),
        })
        res.append(item)
    merged = _merge_same_track(res)
    for r in merged:   # the holdings view, on the merged accumulation (all accounts in the track)
        f_info = fund_by_id.get(r.get("fund_id"))
        if f_info:
            f, info = f_info
            r["by_holdings"] = holdings_view(f, info, r["accumulation"], r.get("yield_12m_pct"))
    res = [_slim_fit(r) for r in merged]
    actions = [{"track": r.get("official_fund"), "risk_level": r["by_holdings"].get("risk_level"), "rank": r["by_holdings"].get("rank"),
                "action": r["by_holdings"].get("action"),
                **({"annual_gain_ils": r["by_holdings"]["annual_gain_ils"]} if r["by_holdings"].get("annual_gain_ils") else {}),
                **({"leader": r["by_holdings"]["leader"]["fund"]} if r["by_holdings"].get("leader") else {})}
               for r in res if r.get("by_holdings")]
    for r in res:   # the product line keeps only where it stands; the action lives in the summary
        if r.get("by_holdings"):
            r["by_holdings"] = {k: r["by_holdings"][k] for k in ("risk_level", "rank") if r["by_holdings"].get(k)}
    y, m = divmod(period, 100)
    gaps = sorted((r for r in res if r.get("annual_gap_vs_best_ils")), key=lambda r: -r["annual_gap_vs_best_ils"])
    out = {"id_number": idn, "name": prods[0]["name"], "data_month": f"{m:02d}/{y}",
           # first, so a prefetch cut at 4,000 chars still carries it — the model once skipped an ₪11,103
           # pension gap and reported only ₪1,600 of השתלמות gaps (2026-10-10)
           # recommended actions FIRST (risk level by holdings); the same-name gaps are the second view —
           # with them first the model ignored the holdings view entirely (2026-10-10)
           "recommended_actions_by_risk_level": actions,
           "second_view_same_name": {"what": "השוואה משנית: מול מסלולים באותו שם בלבד (same_name_rank / same_name_gap_ils בכל מוצר)",
                                     "total_annual_gap_ils": sum(r["annual_gap_vs_best_ils"] for r in gaps)},
           "products": [_label_same_name(r) for r in res],
            "how_to_read": "ההמלצה = recommended_actions_by_risk_level. annual_gain_ils = צבירה × (תשואה שנתית ממוצעת 3ש של המוביל ברמת הסיכון − של המסלול). "
                           "אומדן מתשואות עבר, לא הבטחה.",
            "disclaimer": DISCLAIMER}
    if not res:   # products exist but none can be compared — say why instead of an empty list
        out["note"] = ("ללקוח יש בפרודוקציה " + str(len(prods)) + " מוצרים, אבל לאף אחד אין גם צבירה וגם סוג מוצר חיסכון שאפשר להשוות לשוק "
                       "(למשל צבירה ₪0). אין מה להשוות — אל תמציא השוואה.")
        out["products_seen"] = [{k: p[k] for k in ("company", "product_type", "track", "accumulation")} for p in prods[:6]]
    return out


@tool("get_customer_fund_fit", "עוקב אחרי הכסף של לקוח: לכל מוצר חיסכון (גמל, השתלמות, פנסיה, פוליסה) — המסלול הרשמי שלו, דירוג מול מסלולים באותה רמת סיכון, דמי ניהול מול השוק (₪ בשנה), המסלול הטוב ביותר ופער שנתי משוער ב-₪, ו-12 חודשי תשואה.",
      {"id_number": {"type": "string"}}, ["id_number"], category="market", status_he="משווה את הקופות של הלקוח לשוק")
async def get_customer_fund_fit(ctx, id_number: str):
    idn = "".join(ch for ch in str(id_number) if ch.isdigit()).lstrip("0") or "0"
    out = await fund_fit(ctx, idn)
    rows = [{"label": f"{p['company']} {p['category']}", "value": p.get("same_name_gap_ils") or 0} for p in out.get("products", []) if p.get("official_fund")]
    if rows:
        out["result_id"] = ctx.keep(rows, label="מוצר", value="פער שנתי משוער מול הטוב ביותר", title="כמה הלקוח מפסיד בשנה מול המסלול המוביל")
    return out


@tool("fund_opportunities", "הלקוחות שהכסף שלהם במסלולים שמפגרים אחרי השוק באותה רמת סיכון — מדורג לפי פער שנתי משוער ב-₪. להצעת שיחת שימור/ניוד ללקוחות.",
      {"category": {"type": "string", "enum": ["", *CATEGORIES]}, "min_gap_ils": {"type": "integer", "description": "פער מינימלי בשנה (ברירת מחדל 1000)"},
       "n": {"type": "integer"}},
      category="market", status_he="מחפש לקוחות במסלולים חלשים")
async def fund_opportunities(ctx, category: str = "", min_gap_ils: int = 1000, n: int = 10):
    data = await book_opportunities(ctx)
    if not data:
        return {"customers": [], "reason": "בפרודוקציה הפעילה אין מוצרי חיסכון (גמל/השתלמות/פנסיה/פוליסה) עם מסלול וצבירה שאפשר להשוות לשוק — "
                "או שכל המסלולים כבר המובילים ברמת הסיכון שלהם. ההשוואה מבוססת על המסלולים בקבצי הפרודוקציה, לא על המסלקה."}
    rows = []
    for d in data:
        items = [p_ for p_ in d["products"] if p_.get("annual_gain_ils") and (not category or p_["category"] == category)]
        gap = sum(p_["annual_gain_ils"] for p_ in items)
        if items and gap >= (min_gap_ils or 0):
            rows.append({**d, "gap": gap, "items": items})
    rows.sort(key=lambda d: -d["gap"])
    top = rows[: max(1, min(int(n or 10), 30))]
    out = [{"name": d["name"], "id_number": d["id_number"], "accumulation": d["accumulation"], "annual_gap_ils": round(d["gap"]),
            "products": [{"category": i["category"], "track": i["fund"], "rank": i["rank"], "best": i["leader"], "gap": i["annual_gain_ils"]}
                         for i in d["items"][:4]]} for d in top]
    rid = ctx.keep([{"label": d["name"], "value": d["annual_gap_ils"], "id_number": d["id_number"]} for d in out],
                   label="לקוח", value="פער שנתי משוער", title="לקוחות במסלולים שמפגרים אחרי השוק")
    # totals FIRST — "מה הפער הכולל של כל הלקוחות" got "hundreds of thousands" when they came after the list
    return {"total_customers": len(rows), "total_annual_gap_ils": round(sum(d["gap"] for d in rows)), "customers": out,
            "how_to_read": "רק מוצרים שההמלצה עליהם 'לבחון מעבר' (בחצי התחתון של רמת הסיכון, והמוביל טוב יותר ב-3 שנים). "
                           "פער = צבירה × (תשואה שנתית ממוצעת 3ש של המוביל ברמת הסיכון − המסלול של הלקוח). אומדן — "
                           "אותו חישוב כמו בכרטיס הלקוח (get_customer_fund_fit).",
            "disclaimer": DISCLAIMER, "result_id": rid}


async def book_opportunities(ctx) -> list[dict]:
    """Every customer's savings products against the market at their RISK LEVEL — the same holdings_view /
    verdict as get_customer_fund_fit, for the whole book in one pass (Nifra Market's hero, fund_opportunities).
    fund_opportunities used the best SAME-NAME peer while saying "same risk level": kiko's book read ₪3.86M
    while each customer card read a different figure (2026-10-10). One calculation now.
    → [{id_number, name, accumulation, annual_gain_ils, watch_gain_ils, products:[{category, fund, fund_id,
       accumulation, risk_level, rank, leader, action, annual_gain_ils}]}]"""
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord

    async def compute():
        period = await latest_period(ctx.db)
        ids = await _get_production_upload_ids(ctx.db, ctx.user.id)
        if not period or not ids:
            return []
        recs = (await ctx.db.execute(select(ClientRecord).where(
            ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id.in_(ids),
            ClientRecord.accumulation > 0))).scalars().all()
        rows_by_cat: dict[str, list] = {}
        ranks_by_cat: dict[str, dict] = {}
        match_cache: dict[tuple, object] = {}
        held: dict[tuple, dict] = {}          # (customer, category, fund_id) -> merged accumulation
        names: dict[str, str] = {}
        for r in recs:
            cat = category_for_product(r.product_type, r.product)
            if not cat:
                continue
            if cat not in rows_by_cat:
                rows_by_cat[cat] = await _category_rows(ctx.db, cat, period)
                ranks_by_cat[cat] = await holdings_ranks(ctx.db, cat, period, rows_by_cat[cat])
            splits = r.track_split if isinstance(r.track_split, list) and r.track_split else None
            parts = [(x.get("track"), float(x.get("amount") or 0)) for x in splits] if splits else [(r.track, float(r.accumulation or 0))]
            idn = str(r.id_number or "").lstrip("0")
            if not idn:
                continue
            names.setdefault(idn, " ".join(x for x in (r.first_name, r.last_name) if x) or idn)
            for trk, amt in parts:
                k = (cat, trk, r.receiving_company)
                if k not in match_cache:
                    match_cache[k] = match_fund(trk, r.receiving_company, rows_by_cat[cat])[0]
                f = match_cache[k]
                if f is None or amt <= 0:
                    continue
                h = held.setdefault((idn, cat, f.fund_id), {"f": f, "acc": 0.0})
                h["acc"] += amt
        per: dict[str, dict] = {}
        for (idn, cat, fid), h in held.items():
            f, info = h["f"], ranks_by_cat[cat].get(fid)
            v = holdings_view(f, info, h["acc"], (info or {}).get("y12"))
            c = per.setdefault(idn, {"id_number": idn, "name": names.get(idn, idn), "accumulation": 0.0,
                                     "annual_gain_ils": 0, "watch_gain_ils": 0, "products": []})
            c["accumulation"] += h["acc"]
            c["annual_gain_ils"] += v.get("annual_gain_ils") or 0
            c["watch_gain_ils"] += v.get("annual_gain_vs_leader_ils") or 0
            c["products"].append({"category": cat, "fund": f.fund_name, "fund_id": fid, "accumulation": round(h["acc"]),
                                  "risk_level": v.get("risk_level"), "rank": v.get("rank"),
                                  "leader": (v.get("leader") or {}).get("fund"), "action": v.get("action"),
                                  "track_3y": f.avg_yield_3y, "leader_3y": (v.get("leader") or {}).get("avg_yield_3y"),
                                  "annual_gain_ils": v.get("annual_gain_ils")})
        for c in per.values():
            c["accumulation"] = round(c["accumulation"])
            c["products"].sort(key=lambda p_: -(p_.get("annual_gain_ils") or 0))
        return sorted(per.values(), key=lambda c: -c["annual_gain_ils"])

    return await cache_get_or(ctx, ("book_opps",), compute)


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
        co = brand(f.managing_corporation or f.fund_name)
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
async def market_changes(ctx, category: str, period: int | None = None):
    """`period` (YYYYMM, not in the tool schema — Nifra Market's month picker): that month vs the one before."""
    from app.services.fund_market.delta import market_delta
    if category not in CATEGORIES:
        return {"error": "קטגוריה לא מוכרת."}
    source, classes, label = CATEGORIES[category]
    period = period or await latest_period(ctx.db)
    key = ("market_changes", category, period)
    hit = cache.get("market", 0, key)
    if hit is None:
        hit = await market_delta(ctx.db, source, classes, period=period, open_only=is_open)
        # don't pin "allocation unavailable" for hours while pensyanet is still importing that month
        if (hit.get("allocation_shifts") or {}).get("available") is not False:
            cache.put("market", 0, key, hit, ttl=6 * 3600)
    if not hit.get("found"):
        return hit
    flows = hit.get("top_inflows") or []
    rid = ctx.keep([{"label": fund_label(r["fund"])[:40], "value": r["net_inflow_m"]} for r in flows[:10]], label="קופה",
                   value="צבירה נטו בחודש (מ' ₪)", unit="", title=f"{label} — הכי הרבה כסף נכנס ({hit['month']})") if flows else None
    # Compact, most useful first: a prefetched tool reaches the model cut at 4,000 chars — the full
    # payload was 14,000 and the exposure shifts (at char 10,091) never arrived (2026-10-10).
    N = 6
    slim = lambda rows, keys: [{k: r[k] for k in keys if r.get(k) is not None} for r in (rows or [])[:N]]
    out = {"category": label, "month": hit["month"], "compared_with": hit["compared_with"], "summary": hit["summary"]}
    sh = hit.get("allocation_shifts")
    if sh and sh.get("available"):
        out["exposure_shifts_pp"] = {k: slim(v, ("fund", "before_pct", "now_pct", "change_pp")) for k, v in sh.items() if k != "available"}
    elif sh:
        out["exposure_shifts_pp"] = sh
    out |= {
        "fee_changes": slim(hit.get("fee_changes"), ("fund", "fee", "old", "new")),
        "rank_climbers": slim(hit.get("rank_climbers"), ("fund", "rank_before", "rank_now", "group_size")),
        "rank_fallers": slim(hit.get("rank_fallers"), ("fund", "rank_before", "rank_now", "group_size")),
        "top_inflows": slim(hit.get("top_inflows"), ("fund", "net_inflow_m")),
        "top_outflows": slim(hit.get("top_outflows"), ("fund", "net_inflow_m")),
        "new_funds": slim(hit.get("new_funds"), ("fund", "assets_m")),
        "not_reported": slim(hit.get("not_reported"), ("fund", "last_reported")),
        "rule": f"כל רשימה כאן מקוצרת ל-{N} שורות — לספירות (כמה קרנות חדשות, כמה שינויי דמי ניהול) השתמש רק ב-summary. "
                + (hit.get("rule") or ""),
        "result_id": rid, "disclaimer": DISCLAIMER, "source": "גמל-נט/פנסיה-נט/ביטוח-נט (רשות שוק ההון)",
    }
    return out


@tool("fund_allocation", "פילוח הנכסים של מסלול פנסיה (פנסיה-נט): 10 קבוצות ראשיות (אג\"ח ממשלתיות, מיועדות, מניות, הלוואות…), רמת סיכון, "
      "סחיר/לא סחיר, ארץ/חו\"ל, חשיפה למניות/חו\"ל/מט\"ח — החודש האחרון והשינוי מהחודש שלפניו; וגם האיזון האקטוארי של הקרן. "
      "fund = שם המסלול או מספר הקופה.",
      {"fund": {"type": "string"}}, ["fund"], category="market", status_he="בודק את פילוח הנכסים")
async def fund_allocation(ctx, fund: str):
    from app.models.fund_market import PensyanetData as P
    from app.services.fund_market.delta import track_allocation
    period = (await ctx.db.execute(select(func.max(F.report_period)).where(F.source == "pension"))).scalar_one_or_none()
    rows = (await ctx.db.execute(select(F).where(F.source == "pension", F.report_period == period))).scalars().all()
    # the same lookup as track_rank (question words stripped, whole words, brand(), "עד 50") — its own
    # word match opened answers with "לא מצאתי" for "מנורה מבטחים פנסיה כללי" (2026-10-10)
    q = (fund or "").strip()
    f = _find_fund(q, rows)
    if not f:
        cands = [x for x in rows if set(_clean_track_q(q).split()) & set((x.fund_name or "").split())]
        return {"found": False, "candidates": [{"fund_id": x.fund_id, "fund": x.fund_name} for x in cands[:10]] or None,
                "note": "לא נמצא מסלול פנסיה בשם הזה. נסה שם מלא כפי שמופיע בפנסיה-נט, או מספר קופה."}
    hits = [f]
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



@tool("customers_in_market_moves", "הלקוחות שלי שהכסף שלהם במסלולים שירדו (או עלו) בדירוג התשואה החודש לעומת החודש הקודם, בתוך קבוצת השווים — "
      "לפי המוצרים בפרודוקציה (גמל, השתלמות, פנסיה, פוליסות). direction: down (ירדו, ברירת מחדל) / up (עלו). category ריק = כל הקטגוריות.",
      {"direction": {"type": "string", "enum": ["down", "up"]}, "category": {"type": "string", "enum": ["", *CATEGORIES]},
       "n": {"type": "integer"}},
      category="market", status_he="מחפש לקוחות במסלולים שזזו בדירוג")
async def customers_in_market_moves(ctx, direction: str = "down", category: str = "", n: int = 15):
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord
    from app.services.fund_market.delta import MIN_GROUP, MIN_RANK_MOVE, rank_moves

    period = await latest_period(ctx.db)
    ids = await _get_production_upload_ids(ctx.db, ctx.user.id)
    if not period or not ids:
        return {"customers": [], "note": "אין פרודוקציה פעילה או נתוני שוק."}
    recs = (await ctx.db.execute(select(ClientRecord).where(
        ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id.in_(ids),
        ClientRecord.accumulation > 0, ClientRecord.track.isnot(None)))).scalars().all()
    moves_by_cat, rows_by_cat, fit = {}, {}, {}
    per_cust: dict[str, dict] = defaultdict(lambda: {"acc": 0.0, "items": []})
    matched = unmatched = 0
    for r in recs:
        cat = category_for_product(r.product_type, r.product)
        if not cat or (category and cat != category):
            continue
        if cat not in rows_by_cat:
            src, classes, _ = CATEGORIES[cat]
            rows_by_cat[cat] = await _category_rows(ctx.db, cat, period)
            moves_by_cat[cat] = await rank_moves(ctx.db, src, classes)
        k = (cat, r.track, r.receiving_company)
        if k not in fit:
            fm = match_fund(r.track, r.receiving_company, rows_by_cat[cat])[0]
            best = None
            if fm and fm.avg_yield_3y is not None:   # the best open track at the same risk level (fund_opportunities' rule)
                best = max((x for x in rows_by_cat[cat] if same_peer(x, fm) and (x.total_assets or 0) >= 100
                            and x.avg_yield_3y is not None and is_open(x)), key=lambda x: x.avg_yield_3y, default=None)
            fit[k] = (fm, best)
        f, best = fit[k]
        if not f:
            unmatched += 1
            continue
        matched += 1
        mv = moves_by_cat[cat]["moves"].get(f.fund_id)
        if not mv or mv[2] < MIN_GROUP:
            continue
        before, now, size = mv
        d = before - now                                   # + = climbed
        if (direction == "down" and d > -MIN_RANK_MOVE) or (direction == "up" and d < MIN_RANK_MOVE):
            continue
        idn = str(r.id_number).lstrip("0")
        c = per_cust[idn]
        c["name"] = " ".join(x for x in (r.first_name, r.last_name) if x) or idn
        c["acc"] += float(r.accumulation)
        gap = (float(r.accumulation) * (best.avg_yield_3y - f.avg_yield_3y) / 100
               if best and best.fund_id != f.fund_id and f.avg_yield_3y is not None else 0.0)
        c["gap"] = c.get("gap", 0.0) + gap
        same = next((it for it in c["items"] if it["fund_id"] == f.fund_id), None)   # two accounts, one track → one line
        if same:
            same["accumulation"] += round(float(r.accumulation)); same["accounts"] += 1
            if same["annual_gap_vs_best_ils"] is not None:
                same["annual_gap_vs_best_ils"] += round(gap)
        else:
            c["items"].append({"category": CATEGORIES[cat][2], "track": f.fund_name, "fund_id": f.fund_id, "rank_before": before,
                               "rank_now": now, "group_size": size, "ytd_now": f.ytd_yield, "avg_yield_3y": f.avg_yield_3y,
                               "best_same_risk": ({"fund": best.fund_name, "avg_yield_3y": best.avg_yield_3y}
                                                  if best and best.fund_id != f.fund_id else None),
                               "annual_gap_vs_best_ils": round(gap) if f.avg_yield_3y is not None else None,
                               **({} if f.avg_yield_3y is not None else {"note": "אין למסלול 3 שנות תשואה — אין פער לחשב"}),
                               "accumulation": round(float(r.accumulation)), "accounts": 1})
    rows = sorted(({"id_number": k, "name": v["name"], "accumulation": round(v["acc"]), "annual_gap_vs_best_ils": round(v.get("gap", 0)),
                    "products": v["items"][:4]}
                   for k, v in per_cust.items()), key=lambda d: -d["accumulation"])
    top = rows[: max(1, min(int(n or 15), 40))]
    rid = ctx.keep([{"label": d["name"], "value": d["accumulation"], "id_number": d["id_number"]} for d in top],
                   label="לקוח", value="צבירה במסלולים שזזו (₪)", unit="₪",
                   title="לקוחות במסלולים שירדו בדירוג" if direction == "down" else "לקוחות במסלולים שעלו בדירוג") if top else None
    any_cat = next(iter(moves_by_cat.values()), {})
    return {"direction": "ירדו בדירוג" if direction == "down" else "עלו בדירוג", "month": any_cat.get("month"),
            "compared_with": any_cat.get("compared_with"), "customers_found": len(rows), "customers": top,
            "products_matched_to_a_fund": matched, "products_not_matched": unmatched, "result_id": rid,
            "rule": f"דירוג = מקום בתשואה מתחילת השנה בתוך קבוצת השווים (לפחות {MIN_GROUP} קופות), תזוזה של {MIN_RANK_MOVE} מקומות לפחות. "
                    "רק מוצרים שהמסלול שלהם זוהה בוודאות מול הנתונים הרשמיים (products_not_matched לא נבדקו). "
                    "ירידה בדירוג בחודש אחד אינה סיבה לניוד — הצג כנקודה לבדיקה. annual_gap_vs_best_ils = צבירה × (תשואה שנתית ממוצעת 3ש "
                    "של המסלול הטוב באותה רמת סיכון − של המסלול הנוכחי) — אומדן, כבר מחושב כאן; אל תאמר שאין פער כשהוא מופיע.",
            "disclaimer": DISCLAIMER}



@tool("best_tracks_by_risk", "המסלולים המובילים בקטגוריה לפי רמת סיכון שנקבעת מהאחזקות בפועל (חשיפה למניות): 1 נמוך · 2 מתון · 3 בינוני · 4 מוגבר · 5 גבוה; "
      "index=true = מסלולי מדד/חו\"ל (חשיפה לחו\"ל 85%+) כקבוצה נפרדת. דירוג לפי ציון אחד: תשואה 12 חודשים, 3 ו-5 שנים, שארפ, ודמי ניהול כשיקול משני. "
      "רק מסלולים פתוחים לציבור, מעל ₪100 מיליון, עם 3 שנות היסטוריה.",
      {"category": {"type": "string", "enum": list(CATEGORIES)}, "level": {"type": "integer", "minimum": 1, "maximum": 5},
       "index": {"type": "boolean"}, "n": {"type": "integer"}},
      ["category", "level"], category="market", status_he="מדרג מסלולים לפי רמת סיכון")
async def best_tracks_by_risk(ctx, category: str, level: int, index: bool = False, n: int = 8):
    from app.services.fund_market.track_score import INDEX_STYLE, LEVELS
    period = await latest_period(ctx.db)
    if not period or category not in CATEGORIES:
        return {"error": "אין נתוני שוק."}
    rows = await _category_rows(ctx.db, category, period)
    ranks = await holdings_ranks(ctx.db, category, period, rows)
    style = INDEX_STYLE if index else ""
    by_id = {f.fund_id: f for f in rows}
    group = sorted(((by_id[fid], r) for fid, r in ranks.items() if r.get("rank") and r["level"] == level and r["style"] == style),
                   key=lambda t: t[1]["rank"])
    note = None
    if not group and not index:
        # every pension track above 75% stocks is an index/abroad track — "the leader at high risk" is
        # one of those, not "there are none" (2026-10-10)
        style = INDEX_STYLE
        group = sorted(((by_id[fid], r) for fid, r in ranks.items() if r.get("rank") and r["level"] == level and r["style"] == style),
                       key=lambda t: t[1]["rank"])
        if group:
            note = "ברמת סיכון זו כל המסלולים המדורגים הם מסלולי מדד/חו\"ל — אלה המובילים ביניהם."
    if not group:
        # pension level 5: 43 tracks, none rankable (all younger than 3 years) — say so, not "אין נתונים"
        at = [by_id[fid] for fid, r in ranks.items() if r["level"] == level and fid in by_id]
        if at:
            young = sum(1 for f in at if f.avg_yield_3y is None)
            small = sum(1 for f in at if f.avg_yield_3y is not None and (f.total_assets or 0) < 100)
            note = (f"ברמת סיכון זו יש {len(at)} מסלולים, אף אחד לא מדורג: {young} צעירים מ-3 שנים, {small} קטנים מ-₪100M, "
                    "השאר סגורים לציבור או בקבוצה של פחות מ-5. אפשר להציג את רמה 4 (מוגבר).")
    top = group[: max(1, min(int(n or 8), 20))]
    y, m = divmod(period, 100)
    label = next(he for _, lv, he in LEVELS if lv == level) + (f" · {style}" if style else "")
    rid = ctx.keep([{"label": fund_label(f.fund_name)[:40], "value": f.avg_yield_3y} for f, _ in top], label="מסלול",
                   value="תשואה שנתית ממוצעת 3ש", unit="%", title=f"{CATEGORIES[category][2]} — רמת סיכון {label}") if top else None
    return {"category": CATEGORIES[category][2], "risk_level": f"{level} {label}", "data_month": f"{m:02d}/{y}",
            "tracks_in_level": len(group), **({"note": note} if note else {}),
            "top": [{"rank": r["rank"], "fund_id": f.fund_id, "fund": f.fund_name, "company": brand(f.managing_corporation or f.fund_name),
                     "stock_pct": r.get("stock_pct"), "abroad_pct": r.get("abroad_pct"), "yield_12m": r.get("y12"),
                     "avg_yield_3y": f.avg_yield_3y, "avg_yield_5y": f.avg_yield_5y, "sharpe": f.sharpe, "mgmt_fee": f.mgmt_fee,
                     "size_m": f.total_assets} for f, r in top],
            "result_id": rid, "disclaimer": DISCLAIMER,
            "rule": "רמת סיכון = לפי חשיפה למניות בפועל, לא לפי שם המסלול. תשואות עבר; דמי הניהול כאן הם ממוצע הקופה, לא של הלקוח."}


@tool("compare_companies", "השוואה בין שתי חברות באותה קטגוריה: מסלול מול מסלול מאותו סוג (מניות מול מניות, לבני 50 מול לבני 50…), "
      "תשואה 3 ו-5 שנים, 12 חודשים, דמי ניהול וגודל, ומי מנצחת בכמה זוגות. category = pension/gemel/hishtalmut/gemel_invest.",
      {"category": {"type": "string", "enum": [c for c in CATEGORIES if c != "savings_policy"]},
       "company_a": {"type": "string"}, "company_b": {"type": "string"}},
      ["category", "company_a", "company_b"], category="market", status_he="משווה בין החברות")
async def compare_companies(ctx, category: str, company_a: str, company_b: str):
    """Pairs, not two lists: "תשווה בין כלל לאלטשולר בפנסיה" opened with "כלל מובילה" over a higher
    Altshuler median, and Mor's "לבני 50 ומטה" was set against Meitav's "עוקב מדדי מניות" (2026-10-10).
    Per company and track type the LARGEST open track stands for it (the main fund, not a side one)."""
    from app.services.fund_market.delta import _peer
    period = await latest_period(ctx.db)
    if not period or category not in CATEGORIES:
        return {"error": "אין נתוני שוק."}
    rows = [f for f in await _category_rows(ctx.db, category, period) if is_open(f) and (f.total_assets or 0) >= 100]
    a, b = brand(company_a), brand(company_b)
    main: dict[str, dict] = {a: {}, b: {}}
    for f in rows:
        co = brand(f.managing_corporation or f.fund_name)
        if co in main:
            k = _peer(f)
            if k not in main[co] or (f.total_assets or 0) > (main[co][k].total_assets or 0):
                main[co][k] = f
    if not main[a] or not main[b]:
        return {"found": False, "note": f"אין מסלולים פתוחים של {a if not main[a] else b} בקטגוריה הזו."}
    y12 = (await holdings_ranks(ctx.db, category, period, rows))
    pairs, wins = [], {a: 0, b: 0, "תיקו": 0}
    for k in main[a].keys() & main[b].keys():
        fa, fb = main[a][k], main[b][k]
        if fa.avg_yield_3y is None or fb.avg_yield_3y is None:
            continue
        d = round(fa.avg_yield_3y - fb.avg_yield_3y, 2)
        w = a if d > 0.05 else b if d < -0.05 else "תיקו"
        wins[w] += 1
        pairs.append({"track_type": fund_label(fa.fund_name), "winner_3y": w, "gap_3y_pp": abs(d),
                      a: {"fund": fa.fund_name, "avg_yield_3y": fa.avg_yield_3y, "avg_yield_5y": fa.avg_yield_5y,
                          "yield_12m": (y12.get(fa.fund_id) or {}).get("y12"), "mgmt_fee": fa.mgmt_fee, "size_m": fa.total_assets},
                      b: {"fund": fb.fund_name, "avg_yield_3y": fb.avg_yield_3y, "avg_yield_5y": fb.avg_yield_5y,
                          "yield_12m": (y12.get(fb.fund_id) or {}).get("y12"), "mgmt_fee": fb.mgmt_fee, "size_m": fb.total_assets}})
    pairs.sort(key=lambda p_: -((p_[a]["size_m"] or 0) + (p_[b]["size_m"] or 0)))
    y, m = divmod(period, 100)
    lead = a if wins[a] > wins[b] else b if wins[b] > wins[a] else None
    return {"category": CATEGORIES[category][2], "data_month": f"{m:02d}/{y}", "companies": [a, b],
            "verdict": (f"{lead} טובה יותר ב-{max(wins[a], wins[b])} מתוך {len(pairs)} זוגות מסלולים מאותו סוג (תשואה 3ש)"
                        if lead else f"תיקו: {wins[a]} מול {wins[b]} מתוך {len(pairs)} זוגות"),
            "wins_3y": wins, "pairs": pairs[:12],
            "only_in": {a: [fund_label(f.fund_name) for k, f in main[a].items() if k not in main[b]][:8],
                        b: [fund_label(f.fund_name) for k, f in main[b].items() if k not in main[a]][:8]},
            "rule": "השווה רק בתוך זוג (אותו סוג מסלול). פתח ב-verdict. אל תשווה חציונים של כל החברה — הם תלויים בתמהיל המסלולים. "
                    "תשואות עבר אינן מבטיחות תשואות עתידיות.", "disclaimer": DISCLAIMER}


@tool("track_rank", "באיזה מקום מסלול מסוים: (1) מול מסלולים באותו שם/מאפיין (לבני 50, מניות…) לפי תשואה שנתית ממוצעת 3 שנים, "
      "(2) מול כל המסלולים באותה רמת סיכון לפי האחזקות בפועל, בציון משולב (12 חודשים, 3 ו-5 שנים, שארפ, דמי ניהול). fund = שם המסלול או מספר קופה.",
      {"fund": {"type": "string"}}, ["fund"], category="market", status_he="בודק את דירוג המסלול")
async def track_rank(ctx, fund: str):
    period = await latest_period(ctx.db)
    q = (fund or "").strip()
    # exact / whole-word over every category first; the loose company+track-words match only inside the
    # category the question names — "הפניקס גמל מניות" resolved to Phoenix השתלמות מניות (2026-10-10)
    rows_by = {cat: await _category_rows(ctx.db, cat, period) for cat in CATEGORIES}
    named = category_for_product(q, q)
    found = None
    for loose in (False, True):
        for cat in ([named] if (loose and named) else [] if loose else list(CATEGORIES)):
            f = _find_fund(q, rows_by[cat], loose=loose)
            if f:
                found = (cat, f, rows_by[cat])
                break
        if found:
            break
    if not found:
        # the company's REAL tracks in the category asked — Nifra invented "מגדל השתלמות כללי לבני 50 ומטה"
        # as a name to try; השתלמות has no age tracks at all (2026-10-10)
        from app.services.agent.router import _company
        co = _company(q)
        pool = rows_by.get(named) or [r for rs in rows_by.values() for r in rs]
        tracks = sorted({x.fund_name for x in pool if is_open(x) and (not co or brand(x.managing_corporation or x.fund_name) == brand(co))})
        age = bool(re.search(r"לבני|לגילאי|ומטה|ומעלה|\b50\b|\b60\b", q))
        has_age = any(re.search(r"לבני|לגילאי|ומטה|ומעלה", t) for t in tracks)
        return {"found": False, "note": "לא נמצא מסלול בשם הזה. אל תמציא שם — הצע רק מהרשימה existing_tracks.",
                **({"no_age_tracks": "אין מסלולי גיל (לבני 50 וכו') בקטגוריה הזו אצל החברה הזו."} if age and tracks and not has_age else {}),
                "existing_tracks": tracks[:20] or None}
    cat, f, rows = found
    same = [x for x in rows if same_peer(x, f) and (x.total_assets or 0) >= 100 and x.avg_yield_3y is not None
            and (is_open(x) or x.fund_id == f.fund_id)]
    by3 = sorted(same, key=lambda x: -x.avg_yield_3y)
    hold = (await holdings_ranks(ctx.db, cat, period, rows)).get(f.fund_id) or {}
    y, m = divmod(period, 100)
    return {"found": True, "fund": f.fund_name, "fund_id": f.fund_id, "category": CATEGORIES[cat][2], "data_month": f"{m:02d}/{y}",
            # the track's OWN figures and the LEADER's, each labelled — with only the track's own 3y return in a
            # field next to the leader's name, Nifra wrote "מובילה מור עם 14.7%" (14.7% = Phoenix's) (2026-10-10)
            "this_track": {"avg_yield_3y": f.avg_yield_3y, "yield_12m": (hold or {}).get("y12"), "ytd_yield": f.ytd_yield,
                           "month_yield": f.monthly_yield, "avg_yield_5y": f.avg_yield_5y, "sharpe": f.sharpe,
                           "mgmt_fee": f.mgmt_fee, "deposit_fee": f.deposit_fee, "size_m": f.total_assets},
            "same_name_rank": {"rank": by3.index(f) + 1 if f in by3 else None, "of": len(by3),
                               "leader": by3[0].fund_name if by3 else None,
                               "leader_avg_yield_3y": by3[0].avg_yield_3y if by3 else None,
                               "median_avg_yield_3y": _med([x.avg_yield_3y for x in by3])},
            "risk_level_rank": {"risk_level": f"{hold['level']} {hold['label']}" if hold else None, "rank": hold.get("rank"),
                                "of": hold.get("of"), "leader": (hold.get("leader") or {}).get("fund"),
                                "leader_avg_yield_3y": (hold.get("leader") or {}).get("avg_yield_3y")},
            "note": "שני דירוגים שונים: מול מסלולים באותו שם (תשואה 3ש) ומול רמת הסיכון לפי האחזקות (ציון משולב). ציין את שניהם.",
            "disclaimer": DISCLAIMER}


_QWORDS = re.compile(r"(?:^|\s)(?:מה|מהו|מהי|הדירוג|דירוג|של|באיזה|איזה|מקום|במקום|ברמת|רמת|הסיכון|סיכון|שלו|שלה|טוב|טובה|"
                     r"איך|שווה|מדורג|מדורגת|הפילוח|פילוח|החשיפה|חשיפה|למניות|לחו\"ל|יש|ב|ה|—|-|התשואה|תשואה|ל-12|12|חודשים|החודשים|האחרונים|"
                     r"מתחילת|השנה|דמי|הניהול|ניהול|השארפ|שארפ|החודשית|חודשית|ל-3|ל-5|3|5|שנים|השנים|שלוש|חמש|השתנה|השתנו|בפילוח|מהחודש|החודש|שעבר|הקודם|לעומת)(?=\s|$)")


def _clean_track_q(q: str) -> str:
    """The track name out of a question — "מה הדירוג של מגדל השתלמות מניות?" → "מגדל השתלמות מניות" (the whole
    question went into the name match and three real tracks came back "not found", 2026-10-10)."""
    t = re.sub(r"[?!.,]", " ", q or "")
    for _ in range(3):
        t = _QWORDS.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def _find_fund(q: str, rows: list, *, loose: bool = True):
    """One track by id, exact name, whole words, or (loose) company + track words."""
    q = _clean_track_q(q) or q
    if q.isdigit():
        return next((f for f in rows if f.fund_id == int(q)), None)
    norm = lambda x: re.sub(r"\s+", " ", (x or "").replace('"', "").replace("-", " ")).strip()
    hits = [f for f in rows if norm(f.fund_name) == norm(q)]
    if not hits:
        words = [w for w in norm(q).split() if w]
        hits = [f for f in rows if set(words) <= set(norm(f.fund_name).split())]
    if not hits and loose and tokens(q):
        from app.services.agent.router import _company
        co = _company(q)
        stem = company_stem(co) if co else None
        want = tokens(q)
        kinds = [k for k in ("מקיפה", "כללית", "משלימה") if k in q]
        stem = brand(co) if co else None   # brand(): company_stem turns Infinity into "אינפיניטי השתלמות,"
        hits = [f for f in rows if (not stem or brand(f.managing_corporation or f.fund_name) == stem)
                and want <= tokens(f.fund_name) and all(k in (f.fund_name or "") for k in kinds)]
        exact = [f for f in hits if tokens(f.fund_name) == want]   # "מניות" beats "עוקב מדדי מניות"
        hits = exact or hits
    hits.sort(key=lambda f: -(f.total_assets or 0))
    return hits[0] if hits and len(hits) <= 6 else None
