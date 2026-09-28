"""Monthly cycle (מחזור) — the single source for every cycle-aware UI surface:
the Production tab lock, the manual-upload window, the automation tab's
"next cycle" card, and the cycle notification modal. See services/cycle_service.py.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.cycle_notification import CycleNotification
from app.models.user import User
from app.services import cycle_service

router = APIRouter()


@router.get("/status")
async def cycle_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    state = await cycle_service.user_cycle_state(db, user)
    state.manual_run_allowed = cycle_service.manual_run_allowed(user, state)
    return cycle_service.state_dict(state)


@router.get("/notifications")
async def unseen_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(CycleNotification)
        .where(CycleNotification.user_id == user.id, CycleNotification.seen_at.is_(None))
        .order_by(CycleNotification.created_at.asc())
    )).scalars().all()
    out = []
    for n in rows:
        title, body = cycle_service.notification_copy(n.kind, n.period)
        out.append({
            "id": str(n.id),
            "kind": n.kind,
            "period": n.period.isoformat(),
            "period_label": cycle_service.month_label(n.period),
            "title": title,
            "body": body,
            "created_at": n.created_at.isoformat(),
        })
    return out


@router.post("/notifications/{notification_id}/seen")
async def mark_seen(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Notification not found")
    n = (await db.execute(
        select(CycleNotification).where(CycleNotification.id == nid, CycleNotification.user_id == user.id)
    )).scalar_one_or_none()
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if n.seen_at is None:
        n.seen_at = datetime.utcnow()
        await db.commit()
    return {"ok": True}


async def manual_production_window(db: AsyncSession, user: User):
    """Gate for every manual PRODUCTION upload. Returns the period (first-of-
    month date) the upload must be filed under, or None for admins (support
    uploads are not bound to the cycle). Raises 403 with X-Cycle-Gate
    (locked | maslaka | waiting) so the UI can explain why."""
    if user.is_admin:
        return None
    state = await cycle_service.user_cycle_state(db, user)
    if state.locked:
        reason, msg = "locked", "לשונית הפרודוקציה תיפתח במחזור הראשון שלך"
    elif state.production_source == "maslaka":
        reason, msg = "maslaka", "הפרודוקציה החודשית מגיעה אוטומטית מהמסלקה — אין צורך להעלות ידנית"
    elif state.prelaunch:
        return None
    elif not state.manual_upload_open:
        reason, msg = "waiting", "העלאת הפרודוקציה תיפתח בסיום ההורדה האוטומטית של המחזור"
    else:
        from datetime import date as _date
        return _date.fromisoformat(state.current_period)
    raise HTTPException(status_code=403, detail=msg, headers={"X-Cycle-Gate": reason})
