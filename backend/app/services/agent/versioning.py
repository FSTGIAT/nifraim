"""users.ai_data_version — bump it whenever an agent's data changes.

Called from upload ingest, the cycle batch end, מסלקה ingest, mail intake and
rate edits. Never raises: a failed bump must not fail an ingest (the TTL still
expires the cache)."""
from __future__ import annotations

import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


async def bump(db: AsyncSession, user_id, reason: str = "", *, commit: bool = False) -> None:
    try:
        await db.execute(update(User).where(User.id == user_id)
                         .values(ai_data_version=User.ai_data_version + 1))
        if commit:
            await db.commit()
        from app.services.agent import cache
        cache.drop_user(user_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("ai_data_version bump failed (%s): %s", reason, e)


async def current(db: AsyncSession, user_id) -> int:
    return int((await db.execute(select(User.ai_data_version).where(User.id == user_id))).scalar_one_or_none() or 0)


# ─── automatic invalidation ─────────────────────────────────────────────────
# Any ORM write to a table the AI reads bumps that user's ai_data_version in the
# SAME transaction. One hook instead of a call in every ingest path — it also
# covers the local worker (it runs this code against the prod DB) and admin fixes.
_WATCHED = ("FileUpload", "CommissionComparison", "Debt", "CommissionRate", "PensionHolding", "PensionInquiry",
            "MailItem", "CollectionCase", "CompanyContact", "ProductionSummary", "ClientRecord", "AiDocument",
            "MaslakaAgentLink", "AgreementRequest", "InsurancePolicy", "PolicyDocument", "HarbRequest")
_registered = False


def register_listeners() -> None:
    """Collect user ids on flush (real changes only); bump AFTER COMMIT in a separate
    short transaction. Never inside the ingest's own transaction: an UPDATE users there
    would hold that row lock for the whole ingest and could deadlock two ingests of the
    same agent. Rolled-back work bumps nothing."""
    global _registered
    if _registered:
        return
    _registered = True
    import asyncio
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    @event.listens_for(Session, "after_flush")
    def _collect(session, flush_context):  # noqa: ANN001
        ids = session.info.setdefault("ai_bump", set())
        for obj in session.new:
            if type(obj).__name__ in _WATCHED and getattr(obj, "user_id", None):
                ids.add(obj.user_id)
        for obj in session.deleted:
            if type(obj).__name__ in _WATCHED and getattr(obj, "user_id", None):
                ids.add(obj.user_id)
        for obj in session.dirty:   # dirty includes no-op sets — only count real changes
            if type(obj).__name__ in _WATCHED and getattr(obj, "user_id", None) \
                    and session.is_modified(obj, include_collections=False):
                ids.add(obj.user_id)

    @event.listens_for(Session, "after_commit")
    def _after_commit(session):  # noqa: ANN001
        ids = session.info.pop("ai_bump", None)
        if not ids:
            return
        try:
            asyncio.get_running_loop().create_task(bump_now(*ids, reason="orm"))
        except RuntimeError:   # no loop (sync script) — the TTL still expires the cache
            pass

    @event.listens_for(Session, "after_rollback")
    def _after_rollback(session):  # noqa: ANN001
        session.info.pop("ai_bump", None)


async def bump_now(*user_ids, reason: str = "") -> None:
    """Bump in its own short transaction (also called explicitly after background
    recomputes that write with core update()/delete(), which the ORM hook can't see)."""
    ids = [u for u in user_ids if u]
    if not ids:
        return
    try:
        from app.database import async_session
        async with async_session() as db:
            await db.execute(update(User).where(User.id.in_(ids)).values(ai_data_version=User.ai_data_version + 1))
            await db.commit()
        from app.services.agent import cache
        for u in ids:
            cache.drop_user(u)
    except Exception as e:  # noqa: BLE001
        logger.warning("ai_data_version bump_now failed (%s): %s", reason, e)
