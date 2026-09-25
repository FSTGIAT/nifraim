"""Automatic monthly production — consent + approval open the subscriptions, nothing else does.

    source backend/venv/bin/activate && python backend/tests/test_maslaka_auto_production.py

Runs against the local dev DB (test@test.com). Snapshots and restores the user's
link; deletes every inquiry it creates.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


async def main() -> None:
    from sqlalchemy import delete, select
    from app.config import settings
    from app.database import async_session
    from app.models.maslaka_agent_link import MaslakaAgentLink
    from app.models.pension_audit import PensionAuditLog
    from app.models.pension_inquiry import PensionInquiry
    from app.models.user import User
    from app.services.maslaka import association, orchestration

    assert "localhost" in settings.DATABASE_URL, "local dev DB only"
    async with async_session() as db:
        user = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()
        link = (await db.execute(select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == user.id))).scalar_one_or_none()
        created_link = link is None
        if created_link:
            link = MaslakaAgentLink(user_id=user.id, status="not_started")
            db.add(link)
        snap = (link.status, link.agent_id_number, link.agent_name, link.auto_production, link.auto_production_at)
        link.status, link.agent_id_number, link.agent_name = "submitted", "040336281", "סוכן בדיקה"
        link.auto_production = False
        await db.commit()
        bodies = await orchestration.agent_bodies(db, user.id)
    expected = [b for b in bodies if b["clients"] > 0 and not b["monthly"]]
    print(f"  (test user has customers at {len(expected)} bodies)")

    async def monthly_ids():
        async with async_session() as db:
            return (await db.execute(select(PensionInquiry.id).where(
                PensionInquiry.user_id == user.id,
                PensionInquiry.interface_code == "events_v007:2100"))).scalars().all()

    before = set(await monthly_ids())
    try:
        print("\nNo consent → approval opens nothing:")
        async with async_session() as db:
            l = await db.get(MaslakaAgentLink, link.id)
            await association.mark_approved(db, l)
        check("approved without consent: 0 subscriptions", set(await monthly_ids()) == before)

        print("\nConsent + approved → one monthly subscription per body with customers:")
        async with async_session() as db:
            l = await db.get(MaslakaAgentLink, link.id)
            l.status, l.auto_production = "submitted", True
            await db.commit()
            await association.mark_approved(db, l)
        new = set(await monthly_ids()) - before
        check("subscriptions opened on approval", len(new) == len(expected), f"{len(new)} / {len(expected)}")
        async with async_session() as db:
            rows = (await db.execute(select(PensionInquiry).where(PensionInquiry.id.in_(new)))).scalars().all()
        check("all pending (the Gateway sends them)", all(r.status == "pending" for r in rows))
        check("subject is the agent", all(r.customer_id_number == "40336281" for r in rows))
        check("each names its body", {r.target_yatzran_id for r in rows} == {b["id"] for b in expected})

        print("\nIdempotent — the daily sweep adds nothing twice:")
        async with async_session() as db:
            n = await orchestration.ensure_all_monthly_subscriptions(db)
        check("second run opens 0", n == 0, str(n))
    finally:
        async with async_session() as db:
            ids = list(set(await monthly_ids()) - before)
            if ids:
                await db.execute(delete(PensionAuditLog).where(PensionAuditLog.inquiry_id.in_(ids)))
                await db.execute(delete(PensionInquiry).where(PensionInquiry.id.in_(ids)))
            if created_link:
                await db.execute(delete(MaslakaAgentLink).where(MaslakaAgentLink.id == link.id))
            else:
                l = await db.get(MaslakaAgentLink, link.id)
                l.status, l.agent_id_number, l.agent_name, l.auto_production, l.auto_production_at = snap
            await db.commit()

    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES)))
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    asyncio.run(main())
