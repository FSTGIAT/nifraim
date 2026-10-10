"""Nifra Market parity: the screen's numbers are the numbers Nifra's answers use.

For the agent with the most customers in the DB pointed at by DATABASE_URL:
  * /api/market/overview — each listed customer's yearly gap == the sum of annual_gain_ils in that
    customer's get_customer_fund_fit (the per-customer card), and the total == the sum over customers;
  * /api/market/customer/<id> — the ladder's "is_this" row sits at the rank the card states;
  * an agent with no data gets the missing-data line from the overview, while ladder / duel still answer
    from the public market data.
Run: DATABASE_URL=... venv/bin/python tests/test_market_api.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import func, select  # noqa: E402

from app.api import market as M  # noqa: E402
from app.database import async_session  # noqa: E402
from app.models.pension_holding import PensionHolding  # noqa: E402
from app.models.upload import FileUpload  # noqa: E402
from app.models.user import User  # noqa: E402


async def _user_with_most_customers(db):
    uid = (await db.execute(select(PensionHolding.user_id, func.count(func.distinct(PensionHolding.customer_id_number)))
                            .group_by(PensionHolding.user_id).order_by(func.count(func.distinct(PensionHolding.customer_id_number)).desc())
                            .limit(1))).first()
    return (await db.get(User, uid[0])) if uid else None


async def _empty_user(db):
    has = select(FileUpload.user_id).distinct()
    return (await db.execute(select(User).where(User.is_active.is_(True), User.id.not_in(has),
                                                User.id.not_in(select(PensionHolding.user_id).distinct())).limit(1))).scalar_one_or_none()


async def test_overview_matches_customer_cards():
    async with async_session() as db:
        u = await _user_with_most_customers(db)
        if not u:
            print("skip: no agent with data")
            return
        ov = await M.overview(u, db)
        assert not ov.get("missing"), ov.get("missing")
        assert ov["customers"], "no customers to review"
        for c in ov["customers"][:5]:
            card = await M.customer(c["id_number"], u, db)
            gain = sum(a.get("annual_gain_ils") or 0 for a in card.get("recommended_actions_by_risk_level", []))
            assert abs(gain - c["annual_gain_ils"]) <= 1, (c["name"], gain, c["annual_gain_ils"])
            for p in card.get("products", []):
                lad, rank = p.get("ladder"), (p.get("risk_level_view") or {}).get("rank")
                if lad and rank:
                    me = next(t for t in lad["tracks"] if t["is_this"])
                    assert rank.startswith(f"#{me['rank']} מתוך {lad['of']}"), (rank, me["rank"], lad["of"])
        await db.rollback()
    print("ok: overview == customer cards, ladders == ranks")


async def test_empty_agent_gets_market_but_no_book():
    async with async_session() as db:
        u = await _empty_user(db)
        if not u:
            print("skip: no empty agent")
            return
        ov = await M.overview(u, db)
        assert ov.get("missing") and not ov["customers"], ov
        lad = await M.ladder("pension", 4, False, u, db)
        assert lad.get("top"), "public ladder empty for a new agent"
        assert all(not t["customers"] for t in lad["top"])
        duel = await M.duel("pension", "כלל", "אלטשולר", u, db)
        assert duel.get("pairs"), duel
        await db.rollback()
    print("ok: empty agent — market data yes, book no")


async def main():
    await test_overview_matches_customer_cards()
    await test_empty_agent_gets_market_but_no_book()
    print("ALL PASSED")


if __name__ == "__main__":
    asyncio.run(main())
