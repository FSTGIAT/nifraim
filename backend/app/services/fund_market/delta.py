"""Month-over-month changes in the official fund data (fund_market_monthly, + pensyanet_data for
pension asset allocation). GLOBAL market data — no user.

Rules (the same lesson as the מסלקה delta, 2026-10-10):
  * a change is measured only on funds present in BOTH months;
  * a fund missing from the newest month is "לא דווח החודש", never "נסגר" — Menora's target-date
    tracks stopped reporting after 06/2026 without any closure notice in the data;
  * a fund is "חדש" only when its id never appeared before (a returning id is not new).
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund_market import FundMarketMonthly as F, PensyanetData as P

MIN_GROUP = 5          # rank moves only inside a peer group at least this big
MIN_RANK_MOVE = 3
EXPOSURE_ITEMS = {4751: "חשיפה למניות", 4752: "חשיפה לחו\"ל", 4761: "חשיפה למט\"ח"}
DESIGNATED = 4712      # אג"ח מיועדות (10 main groups)


async def periods(db: AsyncSession, source: str) -> list[int]:
    return list((await db.execute(select(F.report_period).where(F.source == source).distinct()
                                  .order_by(F.report_period.desc()).limit(24))).scalars())


def _ym(p: int) -> str:
    y, m = divmod(p, 100)
    return f"{m:02d}/{y}"


def _peer(f) -> tuple:
    """Same classification + track. Pension rows carry no specialization, so the track's key words
    (מניות / לבני 50 ומטה / עוקב מדדים…) decide — else all 150 new-fund tracks were one group."""
    from app.services.agent.tools_market import tokens
    return (f.classification or "", f.specialization or "", f.sub_specialization or "",
            frozenset(tokens(f.fund_name)) if not f.specialization else frozenset())


def _ranks(rows: list, attr: str) -> dict[int, tuple[int, int]]:
    """fund_id -> (rank, group size) by `attr` descending inside its peer group."""
    groups = defaultdict(list)
    for f in rows:
        if getattr(f, attr) is not None:
            groups[_peer(f)].append(f)
    out = {}
    for g in groups.values():
        g.sort(key=lambda f: getattr(f, attr), reverse=True)
        for i, f in enumerate(g, 1):
            out[f.fund_id] = (i, len(g))
    return out


def _row(f) -> dict:
    return {"fund_id": f.fund_id, "fund": f.fund_name, "company": f.managing_corporation,
            "classification": f.classification, "track": " · ".join(x for x in (f.specialization, f.sub_specialization) if x) or None}


async def market_delta(db: AsyncSession, source: str, classes: tuple[str, ...] = (), *, period: int | None = None,
                       open_only=None, n: int = 10) -> dict:
    """The newest month (or `period`) against the month before it, for one source (and optional
    classifications). `open_only(f) -> bool` narrows the movers lists to funds the public can join."""
    ps = await periods(db, source)
    cur_p = period if period in ps else (ps[0] if ps else None)
    prev_p = next((p for p in ps if cur_p and p < cur_p), None)
    if not cur_p or not prev_p:
        return {"found": False, "note": "אין שני חודשים של נתונים להשוואה."}

    async def month(p):
        q = select(F).where(F.source == source, F.report_period == p)
        if classes:
            q = q.where(F.classification.in_(classes))
        return {f.fund_id: f for f in (await db.execute(q)).scalars()}

    cur, prev = await month(cur_p), await month(prev_p)
    both = cur.keys() & prev.keys()
    ever_before = set((await db.execute(select(F.fund_id).where(F.source == source, F.report_period < cur_p).distinct())).scalars())
    new_ids = [i for i in cur.keys() - prev.keys() if i not in ever_before]
    back_ids = [i for i in cur.keys() - prev.keys() if i in ever_before]
    gone_ids = prev.keys() - cur.keys()
    keep = (lambda f: open_only(f)) if open_only else (lambda f: True)

    fee_changes = []
    for i in both:
        a, b = prev[i], cur[i]
        for attr, label in (("mgmt_fee", "דמי ניהול מצבירה"), ("deposit_fee", "דמי ניהול מהפקדה")):
            x, y = getattr(a, attr), getattr(b, attr)
            if x is not None and y is not None and abs(y - x) >= 0.005:
                fee_changes.append({**_row(b), "fee": label, "old": x, "new": y, "change": round(y - x, 3)})
    fee_changes.sort(key=lambda r: abs(r["change"]), reverse=True)

    r_now, r_prev = _ranks([cur[i] for i in both], "ytd_yield"), _ranks([prev[i] for i in both], "ytd_yield")
    movers = []
    for i in both:
        if i in r_now and i in r_prev and r_now[i][1] >= MIN_GROUP and keep(cur[i]):
            d = r_prev[i][0] - r_now[i][0]          # + = climbed
            if abs(d) >= MIN_RANK_MOVE:
                movers.append({**_row(cur[i]), "rank_now": r_now[i][0], "rank_before": r_prev[i][0],
                               "group_size": r_now[i][1], "ytd_now": cur[i].ytd_yield, "month_yield": cur[i].monthly_yield})
    movers.sort(key=lambda r: r["rank_before"] - r["rank_now"], reverse=True)

    flows = [{**_row(cur[i]), "net_inflow_m": cur[i].net_monthly_deposits, "assets_m": cur[i].total_assets,
              "assets_change_m": round((cur[i].total_assets or 0) - (prev[i].total_assets or 0), 1)}
             for i in both if cur[i].net_monthly_deposits is not None and keep(cur[i])]
    flows.sort(key=lambda r: r["net_inflow_m"], reverse=True)

    def total(rows, attr):
        return round(sum(getattr(f, attr) or 0 for f in rows), 1)

    out = {
        "found": True, "month": _ym(cur_p), "compared_with": _ym(prev_p),
        "summary": {
            "funds_compared": len(both), "new_funds": len(new_ids), "returned_funds": len(back_ids),
            "not_reported_this_month": len(gone_ids), "fee_changes": len(fee_changes),
            "assets_m_now": total([cur[i] for i in both], "total_assets"),
            "assets_m_before": total([prev[i] for i in both], "total_assets"),
            "net_inflow_m_this_month": total([cur[i] for i in both], "net_monthly_deposits") if flows else None,
        },
        "fee_changes": fee_changes[:n],
        "rank_climbers": movers[:n], "rank_fallers": list(reversed(movers[-n:])) if movers else [],
        "top_inflows": flows[:n], "top_outflows": list(reversed(flows[-n:])) if flows else [],
        "new_funds": [_row(cur[i]) | {"assets_m": cur[i].total_assets} for i in new_ids][:n],
        "not_reported": [_row(prev[i]) | {"last_reported": _ym(prev_p), "assets_m_then": prev[i].total_assets}
                         for i in sorted(gone_ids, key=lambda i: -(prev[i].total_assets or 0))][:n],
        "rule": "שינוי נמדד רק על קופות שדווחו בשני החודשים. קופה שלא דווחה החודש — 'לא דווח החודש', לא 'נסגרה'. "
                "דירוג = מקום בתשואה מתחילת השנה בתוך קבוצת השווים (אותו סיווג ומסלול). שינוי בנכסים כולל תשואה, "
                "צבירה נטו = הפקדות + העברות פנימה − משיכות. נכסים וזרימות במיליוני ₪, תשואות ודמי ניהול באחוזים.",
    }
    if source == "pension":
        out["allocation_shifts"] = await allocation_shifts(db, cur_p, prev_p, ids=[i for i in both if keep(cur[i])], n=n)
    return out


async def rank_moves(db: AsyncSession, source: str, classes: tuple[str, ...] = ()) -> dict:
    """{period, compared_with, moves: {fund_id: (rank_before, rank_now, group_size)}} for every fund
    in both months, ranked by YTD yield inside its peer group (the same rule as market_delta)."""
    ps = await periods(db, source)
    if len(ps) < 2:
        return {"moves": {}}

    async def month(p):
        q = select(F).where(F.source == source, F.report_period == p)
        if classes:
            q = q.where(F.classification.in_(classes))
        return {f.fund_id: f for f in (await db.execute(q)).scalars()}

    cur, prev = await month(ps[0]), await month(ps[1])
    both = cur.keys() & prev.keys()
    r_now, r_prev = _ranks([cur[i] for i in both], "ytd_yield"), _ranks([prev[i] for i in both], "ytd_yield")
    return {"month": _ym(ps[0]), "compared_with": _ym(ps[1]),
            "moves": {i: (r_prev[i][0], r_now[i][0], r_now[i][1]) for i in both if i in r_now and i in r_prev}}


async def _alloc(db: AsyncSession, period: int, ids: list[int] | None = None) -> dict[int, dict[int, float]]:
    q = select(P.entity_id, P.item_id, P.pct).where(P.report == "assets_main", P.level == "track", P.period == period)
    if ids is not None:
        q = q.where(P.entity_id.in_(ids))
    out: dict[int, dict[int, float]] = defaultdict(dict)
    for ent, item, pct in (await db.execute(q)).all():
        if pct is not None:
            out[ent][item] = pct
    return out


async def allocation_shifts(db: AsyncSession, cur_p: int, prev_p: int, ids: list[int] | None = None, n: int = 10) -> dict:
    """Pension tracks whose stock / abroad / FX exposure moved most (percentage points) between
    the two months — pensyanet asset reports. Empty when a month wasn't imported."""
    a, b = await _alloc(db, prev_p, ids), await _alloc(db, cur_p, ids)
    if not a or not b:
        return {"available": False, "note": "פילוח הנכסים מפנסיה-נט לא יובא לשני החודשים."}
    names = dict((await db.execute(select(F.fund_id, F.fund_name).where(F.source == "pension", F.report_period == cur_p))).all())
    out = {"available": True}
    for item, label in EXPOSURE_ITEMS.items():
        moves = [{"fund_id": i, "fund": names.get(i), "before_pct": a[i][item], "now_pct": b[i][item],
                  "change_pp": round(b[i][item] - a[i][item], 2)}
                 for i in a.keys() & b.keys() if item in a[i] and item in b[i]]
        moves.sort(key=lambda r: abs(r["change_pp"]), reverse=True)
        out[label] = moves[:n]
    return out


async def track_allocation(db: AsyncSession, fund_id: int) -> dict:
    """One pension track's asset allocation, newest month, with the change from the month before."""
    ps = list((await db.execute(select(P.period).where(P.report == "assets_main", P.level == "track", P.entity_id == fund_id)
                                .distinct().order_by(P.period.desc()).limit(2))).scalars())
    if not ps:
        return {"found": False}
    rows = (await db.execute(select(P).where(P.report == "assets_main", P.level == "track", P.entity_id == fund_id,
                                             P.period.in_(ps)))).scalars().all()
    by: dict[tuple, dict] = {}
    for r in rows:
        k = (r.grp, r.item_id)
        d = by.setdefault(k, {"group": r.grp, "item": r.item_name})
        d["now_pct" if r.period == ps[0] else "before_pct"] = r.pct
        if r.period == ps[0]:
            d["amount_k"] = r.amount
    groups: dict[str, list] = defaultdict(list)
    for (grp, _), d in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if d.get("now_pct") is None:
            continue
        if d.get("before_pct") is not None:
            d["change_pp"] = round(d["now_pct"] - d["before_pct"], 2)
        groups[grp].append({k: v for k, v in d.items() if k != "group"})
    return {"found": True, "fund_id": fund_id, "fund": rows[0].entity_name, "month": _ym(ps[0]),
            "compared_with": _ym(ps[1]) if len(ps) > 1 else None, "groups": groups,
            "units": "אחוז מנכסי המסלול; amount_k באלפי ₪", "source": "פנסיה-נט (רשות שוק ההון)"}
