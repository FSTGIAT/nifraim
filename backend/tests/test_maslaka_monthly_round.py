"""The monthly round — a fresh 2100 to EVERY body on the 24th, failures re-sent on
the 25th/26th, nothing on any other day, nothing doubled.

    source backend/venv/bin/activate && python backend/tests/test_maslaka_monthly_round.py

Runs against the local dev DB (test@test.com). Snapshots and restores the user's
link; deletes every inquiry it creates.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


async def main() -> None:
    from sqlalchemy import delete, select, update
    from app.config import settings
    from app.database import async_session
    from app.models.maslaka_agent_link import MaslakaAgentLink
    from app.models.pension_audit import PensionAuditLog
    from app.models.pension_inquiry import PensionInquiry
    from app.models.user import User
    from app.services.maslaka import orchestration
    from app.services.maslaka.code_tables import PROVIDER_CODE_TO_COMPANY

    assert "localhost" in settings.DATABASE_URL, "local dev DB only"
    n_bodies = len(PROVIDER_CODE_TO_COMPANY)
    # 06:30 Israel = 03:30 UTC (IDT) on the given October day.
    def at(day: int) -> datetime:
        return datetime(2026, 10, day, 3, 30)

    async with async_session() as db:
        user = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()
        link = (await db.execute(select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == user.id))).scalar_one_or_none()
        created_link = link is None
        if created_link:
            link = MaslakaAgentLink(user_id=user.id, status="not_started")
            db.add(link)
        snap = (link.status, link.agent_id_number, link.agent_name, link.auto_production, link.auto_production_at)
        link.status, link.agent_id_number, link.agent_name = "approved", "040336281", "סוכן בדיקה"
        link.auto_production, link.auto_production_at = True, None
        await db.commit()
        before = set((await db.execute(select(PensionInquiry.id).where(
            PensionInquiry.user_id == user.id))).scalars().all())

    async def stamp(day: int):
        """Rows are created with the real clock; date them to the simulated day."""
        async with async_session() as db:
            ids = [r.id for r in await new_rows() if r.created_at.day not in (24, 25, 26)]
            if ids:
                await db.execute(update(PensionInquiry).where(PensionInquiry.id.in_(ids)).values(created_at=at(day)))
                await db.commit()

    async def new_rows():
        async with async_session() as db:
            rows = (await db.execute(select(PensionInquiry).where(
                PensionInquiry.user_id == user.id,
                PensionInquiry.interface_code == "events_v007:2100"))).scalars().all()
            return [r for r in rows if r.id not in before]

    try:
        print("\nThe 24th — every body, even ones with an older live subscription:")
        async with async_session() as db:
            n = await orchestration.monthly_production_round(db, user.id, now=at(24))
            await db.commit()
        await stamp(24)
        rows = await new_rows()
        check(f"queued one 2100 per body ({n_bodies})", n == n_bodies and len(rows) == n_bodies, f"{n}/{len(rows)}")
        check("each to a different body", len({r.target_yatzran_id for r in rows}) == n_bodies)
        check("all pending, for the Gateway to send", all(r.status == "pending" for r in rows))

        print("\nThe 25th — nothing failed, nothing re-sent:")
        async with async_session() as db:
            n = await orchestration.monthly_production_round(db, user.id, now=at(25))
            await db.commit()
        await stamp(25)
        check("no duplicates", n == 0 and len(await new_rows()) == n_bodies, str(n))

        print("\nThe 26th — two were rejected, only those two go again:")
        failed = [rows[0].id, rows[1].id]
        async with async_session() as db:
            await db.execute(update(PensionInquiry).where(PensionInquiry.id.in_(failed)).values(status="failed"))
            await db.commit()
            n = await orchestration.monthly_production_round(db, user.id, now=at(26))
            await db.commit()
        check("re-sent exactly the 2 failed bodies", n == 2, str(n))

        print("\nThe 27th — the _all job does nothing outside the 24th–26th:")
        async with async_session() as db:
            n = await orchestration.monthly_production_round_all(db, now=at(27))
        check("no requests on the 27th", n == 0, str(n))

        print("\nAn agent who turned automatic production off gets nothing:")
        async with async_session() as db:
            l = await db.get(MaslakaAgentLink, link.id)
            l.auto_production, l.auto_production_at = False, datetime(2026, 10, 1)
            await db.commit()
            n = await orchestration.monthly_production_round(db, user.id, now=at(24))
        check("opted-out agent skipped", n == 0, str(n))
    finally:
        async with async_session() as db:
            mine = [r.id for r in await new_rows()]
            if mine:
                await db.execute(delete(PensionAuditLog).where(PensionAuditLog.inquiry_id.in_(mine)))
                await db.execute(delete(PensionInquiry).where(PensionInquiry.id.in_(mine)))
            l = await db.get(MaslakaAgentLink, link.id)
            if created_link:
                await db.delete(l)
            else:
                (l.status, l.agent_id_number, l.agent_name, l.auto_production, l.auto_production_at) = snap
            await db.commit()

    print("\nALL PASS" if not FAILURES else f"\n{len(FAILURES)} FAILED: {FAILURES}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    asyncio.run(main())
