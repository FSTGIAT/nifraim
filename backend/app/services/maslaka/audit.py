"""Audit-log helper.

Single rule: never raise into the caller. An audit failure must not abort
the business operation — the precedent across this codebase is the portal
snapshot path (`backend/app/services/portal_service.py`'s `_create_snapshot_bg`
swallows + logs exceptions for the same reason). If we can't write the
audit row we log a warning and move on.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pension_audit import PensionAuditLog

logger = logging.getLogger(__name__)


async def log_event(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    event_type: str,
    inquiry_id: uuid.UUID | None = None,
    customer_id_number: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    actor: str = "agent",
    detail: str | None = None,
    autoflush: bool = True,
) -> None:
    """Append one row to pension_audit_logs. Never raises.

    `autoflush=True` flushes the row to the DB before returning so callers
    that don't commit immediately (background jobs that batch writes) still
    persist the audit row. Pass `autoflush=False` if you're already inside
    a transaction that will be committed by the caller — saves a round-trip.
    """
    try:
        row = PensionAuditLog(
            user_id=user_id,
            inquiry_id=inquiry_id,
            customer_id_number=customer_id_number,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor=actor,
            detail=detail,
        )
        db.add(row)
        if autoflush:
            await db.flush()
    except Exception as e:
        logger.error(
            "maslaka.audit: failed to record event_type=%s user_id=%s inquiry_id=%s: %s",
            event_type, user_id, inquiry_id, e,
        )
