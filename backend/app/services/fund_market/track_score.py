"""Risk level by holdings + rank within product × risk level — GLOBAL market data, no user.

Peers by NAME ("לבני 50 ומטה", "מניות") tell an agent how a track does against tracks with the
same label. Peers by HOLDINGS tell what the customer is really exposed to: an "S&P 500" track is
113% abroad and 99% foreign currency, a "משולב סחיר" track can hold as many stocks as a "מניות"
one. Both views go to the agent (tools_market.fund_fit).

  * risk level 1–5 from the track's stock exposure (% of assets): <15 נמוך · <35 מתון · <55 בינוני
    · <75 מוגבר · else גבוה. Index/abroad tracks (abroad ≥ 85%) form their own group at a level.
  * rank = position inside (category, level, style) by one score: 12-month return (compounded from
    the monthly yields) 25%, 3-year average 35%, 5-year average 25%, Sharpe 15%, management fee −10%,
    each as a z-score in the group; weights are spread over the fields a track HAS.
  * ranked only: open to the public, ≥ ₪100M, with 3 years of history, not a self-managed IRA account — else a young track with one
    great year leads the table (measured: "כלל תמר מניות סחיר", +31% in 12 months, no 3-year data).
Measured on kiko's 34300624 (2026-10-10): Mor pension לבני 50 ומטה is #1 of 8 by name and #14 of 34
by holdings — both true, the agent sees both.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund_market import FundMarketMonthly as F

LEVELS = [(15, 1, "נמוך"), (35, 2, "מתון"), (55, 3, "בינוני"), (75, 4, "מוגבר"), (10_000, 5, "גבוה")]
INDEX_STYLE = "חו\"ל/מדד"
ANNUITY_STYLE = "מקבלי קצבה"
WEIGHTS = (("y12", 0.25), ("avg_yield_3y", 0.35), ("avg_yield_5y", 0.25), ("sharpe", 0.15), ("mgmt_fee", -0.10))
MIN_ASSETS_M = 100
MIN_GROUP = 5


def pct(f, attr: str) -> float | None:
    v, a = getattr(f, attr), f.total_assets
    return round(100 * v / a, 1) if v is not None and a else None


def risk_level(f) -> dict | None:
    """{level 1–5, label, style, stock/abroad/fx %} from the track's exposures, or None."""
    s = pct(f, "stock_exposure")
    if s is None:
        return None
    abroad = pct(f, "foreign_exposure")
    # annuitant tracks ("למקבלי קצבה") are for people already drawing a pension — never a saver's switch
    # target ("ישראלה, 60+: leader = מיטב הלכה למקבלי קצבה", 2026-10-10); index/abroad tracks likewise apart
    style = ANNUITY_STYLE if "קצבה" in (f.fund_name or "") else INDEX_STYLE if (abroad or 0) >= 85 else ""
    for lim, n, he in LEVELS:
        if s < lim:
            return {"level": n, "label": he + (f" · {style}" if style else ""), "style": style,
                    "stock_pct": s, "abroad_pct": abroad, "fx_pct": pct(f, "fx_exposure")}
    return None


def self_managed(f) -> bool:
    """IRA / בניהול אישי accounts: the saver picks the holdings, the published yield is 0.0 — two of them
    padded השתלמות level 4 to 5 tracks and lifted a 5.31%-a-year track to #3 (2026-10-10)."""
    n = f.fund_name or ""
    return "IRA" in n.upper() or "בניהול אישי" in n


def _compound(monthly: list) -> float | None:
    if len(monthly) < 12 or any(v is None for v in monthly[:12]):
        return None
    g = 1.0
    for v in monthly[:12]:
        g *= 1 + v / 100
    return round((g - 1) * 100, 2)


async def yields_12m(db: AsyncSession, source: str, period: int) -> dict[int, float | None]:
    """fund_id → compounded return of the 12 months ending at `period`."""
    y, m = divmod(period, 100)
    start = (y - 1) * 100 + m + 1 if m < 12 else y * 100 + 1
    rows = (await db.execute(select(F.fund_id, F.report_period, F.monthly_yield).where(
        F.source == source, F.report_period >= start, F.report_period <= period))).all()
    by: dict[int, dict[int, float]] = defaultdict(dict)
    for fid, p, v in rows:
        by[fid][p] = v
    return {fid: _compound([d[p] for p in sorted(d, reverse=True)]) for fid, d in by.items()}


def _z(vals: list, v) -> float:
    xs = [x for x in vals if x is not None]
    if v is None or len(xs) < 3:
        return 0.0
    return (v - statistics.mean(xs)) / (statistics.pstdev(xs) or 1)


def rank_groups(rows: list, y12: dict[int, float | None], is_open) -> dict[int, dict]:
    """fund_id → {risk…, rank, of, leader, score} for every rankable track in `rows` (one category,
    one period). Tracks that are not rankable still get their risk level (rank None)."""
    out: dict[int, dict] = {}
    groups: dict[tuple, list] = defaultdict(list)
    for f in rows:
        r = risk_level(f)
        if not r:
            continue
        out[f.fund_id] = {**r, "rank": None, "of": None}
        if is_open(f) and (f.total_assets or 0) >= MIN_ASSETS_M and f.avg_yield_3y is not None and not self_managed(f):
            groups[(r["level"], r["style"])].append(f)
    for members in groups.values():
        if len(members) < MIN_GROUP:   # "#1 מתוך 2" is not a ranking — those tracks keep their risk level only
            continue
        vals = {k: [(y12.get(x.fund_id) if k == "y12" else getattr(x, k)) for x in members] for k, _ in WEIGHTS}

        def score(x):
            parts = [(w, vals[k], y12.get(x.fund_id) if k == "y12" else getattr(x, k)) for k, w in WEIGHTS]
            have = [(w, vs, v) for w, vs, v in parts if v is not None]
            tot = sum(abs(w) for w, _, _ in have) or 1
            return sum(w * _z(vs, v) for w, vs, v in have) / tot

        ranked = sorted(members, key=score, reverse=True)
        lead = ranked[0]
        for i, x in enumerate(ranked, 1):
            out[x.fund_id].update(rank=i, of=len(ranked), score=round(score(x), 2),
                                  leader={"fund_id": lead.fund_id, "fund": lead.fund_name, "avg_yield_3y": lead.avg_yield_3y,
                                          "yield_12m": y12.get(lead.fund_id), "sharpe": lead.sharpe, "mgmt_fee": lead.mgmt_fee})
    return out


def verdict(f, info: dict, accumulation: float, y12: float | None) -> dict:
    """The action for one product, from its holdings rank. A ₪ figure only when the group leader
    is really better over 3 years (a leader can win on 12 months or stability instead)."""
    if not info or info.get("rank") is None:
        return {"action": "אין דירוג לפי אחזקות (מסלול צעיר מ-3 שנים, קטן, סגור לציבור, או פחות מ-5 מסלולים דומים)"}
    rank, of, lead = info["rank"], info["of"], info["leader"]
    gain = None
    if lead["fund_id"] != f.fund_id and lead.get("avg_yield_3y") is not None and f.avg_yield_3y is not None \
            and lead["avg_yield_3y"] > f.avg_yield_3y:
        gain = round(accumulation * (lead["avg_yield_3y"] - f.avg_yield_3y) / 100)
    if rank <= max(2, of // 5):
        return {"action": "להשאיר — בין המובילים ברמת הסיכון שלו"}
    if rank > of / 2:
        if gain:
            return {"action": f"לבחון מעבר ל-{lead['fund']} (#1 ברמת הסיכון)", "annual_gain_ils": gain}
        return {"action": "נמוך בדירוג, אבל המוביל לא טוב ממנו ב-3 שנים (יתרונו ב-12 חודשים או ביציבות) — לבדוק, לא לנייד אוטומטית"}
    return {"action": "במרכז הטבלה — לעקוב", **({"annual_gain_vs_leader_ils": gain} if gain else {})}
