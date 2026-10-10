"""Nifra Market — the fund rankings as a screen (frontend components/market/*).

Every number comes from the SAME functions Nifra's answers use (services/agent/tools_market.py): risk-level
rankings (track_score), the per-customer verdict (holdings_view), same-name ranks, compare_companies,
market_changes. No new math here — only shaping for charts. Market data (גמל-נט / פנסיה-נט) is public and
works for every agent from day one; the customer views read the agent's own book and say what's missing.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user
from app.database import get_db
from app.models.user import User

router = APIRouter()

CATS = ("pension", "gemel", "hishtalmut", "gemel_invest")


async def _ctx(db: AsyncSession, user: User):
    from app.services.agent.context import ToolContext
    from app.services.agent.versioning import current as current_version
    return ToolContext(db=db, user=user, data_version=await current_version(db, user.id))


def _cat(category: str) -> str:
    if category not in CATS:
        raise HTTPException(400, "קטגוריה לא מוכרת")
    return category


async def _customer_funds(ctx) -> dict[int, list[dict]]:
    """fund_id -> the agent's customers holding it (from the same book view as the hero)."""
    from app.services.agent.tools_market import book_opportunities
    out: dict[int, list[dict]] = {}
    for c in await book_opportunities(ctx):
        for p in c["products"]:
            out.setdefault(p["fund_id"], []).append({"id_number": c["id_number"], "name": c["name"],
                                                    "accumulation": p["accumulation"], "action": p["action"],
                                                    "annual_gain_ils": p.get("annual_gain_ils")})
    return out


async def _risk_group(ctx, category: str, fund_id: int) -> dict | None:
    """The whole risk-level group a fund is ranked in, in rank order — the drill's ladder."""
    from app.services.agent.tools_market import _category_rows, brand, holdings_ranks, latest_period
    period = await latest_period(ctx.db)
    rows = await _category_rows(ctx.db, category, period)
    ranks = await holdings_ranks(ctx.db, category, period, rows)
    me = ranks.get(fund_id)
    if not me or not me.get("rank"):
        return None
    by = {f.fund_id: f for f in rows}
    group = sorted(((fid, r) for fid, r in ranks.items() if r.get("rank") and r["level"] == me["level"]
                    and r["style"] == me["style"] and fid in by), key=lambda t: t[1]["rank"])
    return {"risk_level": f"{me['level']} {me['label']}", "of": me["of"],
            "tracks": [{"rank": r["rank"], "fund_id": fid, "fund": by[fid].fund_name,
                        "company": brand(by[fid].managing_corporation or by[fid].fund_name),
                        "avg_yield_3y": by[fid].avg_yield_3y, "yield_12m": r.get("y12"), "mgmt_fee": by[fid].mgmt_fee,
                        "size_m": by[fid].total_assets, "is_this": fid == fund_id} for fid, r in group]}


@router.get("/overview")
async def overview(user: User = Depends(get_paid_user), db: AsyncSession = Depends(get_db)):
    """The hero: the book's yearly gap vs the risk-level leaders + the customers with the biggest gaps."""
    from app.services.agent.router import missing_data_line
    from app.services.agent.tools_market import book_opportunities, latest_period
    ctx = await _ctx(db, user)
    period = await latest_period(db)
    y, m = divmod(period or 0, 100)
    out = {"data_month": f"{m:02d}/{y}" if period else None, "book": await ctx.book_state()}
    missing = await missing_data_line(ctx, "top")
    if missing:
        return {**out, "missing": missing, "customers": [], "total_annual_gain_ils": 0}
    book = await book_opportunities(ctx)
    act = [c for c in book if c["annual_gain_ils"]]
    ranked = sum(1 for c in book for p in c["products"] if p.get("rank"))
    return {**out, "total_annual_gain_ils": round(sum(c["annual_gain_ils"] for c in act)),
            "customers_to_review": len(act), "customers_compared": len(book), "products_ranked": ranked,
            "customers": [{k: c[k] for k in ("id_number", "name", "accumulation", "annual_gain_ils")}
                          | {"top": next((p for p in c["products"] if p.get("annual_gain_ils")), None)} for c in act[:12]],
            "rule": "רק מוצרים שההמלצה עליהם 'לבחון מעבר' (בחצי התחתון של רמת הסיכון, והמוביל טוב יותר ב-3 שנים). "
                    "פער = צבירה × (תשואה ממוצעת 3ש של המוביל − של המסלול). תשואות עבר אינן מבטיחות תשואות עתידיות."}


@router.get("/customer/{id_number}")
async def customer(id_number: str, user: User = Depends(get_paid_user), db: AsyncSession = Depends(get_db)):
    """One customer's products: the risk-level ladder each is ranked in + the same-name view (fund_fit)."""
    from app.services.agent.tools_market import CATEGORIES, fund_fit
    ctx = await _ctx(db, user)
    idn = "".join(ch for ch in id_number if ch.isdigit()).lstrip("0") or "0"
    fit = await fund_fit(ctx, idn)
    by_label = {v[2]: k for k, v in CATEGORIES.items()}
    for p in fit.get("products", []):
        cat = by_label.get(p.get("category"))
        if cat and p.get("fund_id"):
            p["ladder"] = await _risk_group(ctx, cat, p["fund_id"])
    return fit


@router.get("/ladder")
async def ladder(category: str = Query(...), level: int = Query(..., ge=1, le=5), index: bool = False,
                 user: User = Depends(get_paid_user), db: AsyncSession = Depends(get_db)):
    """The leaders at one risk level (best_tracks_by_risk) + how many of the agent's customers hold each."""
    from app.services.agent.tools_market import best_tracks_by_risk
    ctx = await _ctx(db, user)
    out = await best_tracks_by_risk(ctx, _cat(category), level, index=index, n=15)
    held = await _customer_funds(ctx) if (await ctx.book_state())["production"] else {}
    for t in out.get("top", []):
        t["customers"] = held.get(t.get("fund_id"), [])[:20]
    return out


@router.get("/moves")
async def moves(category: str = Query(...), user: User = Depends(get_paid_user), db: AsyncSession = Depends(get_db)):
    """This month vs last: rank climbers / fallers and flows (market_changes) + the agent's customers in fallers."""
    from app.services.agent.tools_market import customers_in_market_moves, market_changes
    ctx = await _ctx(db, user)
    mc = await market_changes(ctx, _cat(category))
    out = {k: mc.get(k) for k in ("category", "month", "compared_with", "summary", "rank_climbers", "rank_fallers",
                                  "top_inflows", "top_outflows", "disclaimer")}
    if (await ctx.book_state())["production"]:
        down = await customers_in_market_moves(ctx, direction="down", category=category, n=10)
        out["my_customers_in_fallers"] = down.get("customers", [])
    return out


@router.get("/duel")
async def duel(category: str = Query(...), a: str = Query(...), b: str = Query(...),
               user: User = Depends(get_paid_user), db: AsyncSession = Depends(get_db)):
    """Two companies, track type against track type (compare_companies)."""
    from app.services.agent.tools_market import compare_companies
    ctx = await _ctx(db, user)
    return await compare_companies(ctx, _cat(category), a, b)
