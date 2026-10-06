"""לא להעלות — numbers whose calls never leave the agent's phone, plus the personal calls that were hidden."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user as get_current_user
from app.database import get_db
from app.models.blocked_phone import BlockedPhone
from app.models.call_recording import CallRecording
from app.models.user import User
from app.services.calls.ingest import phone_display, phone_key
from app.services.calls.privacy import PERSONAL, hide_call, hide_calls_with, unhide_call

router = APIRouter()


class BlockIn(BaseModel):
    phone: str
    label: str | None = None


def _out(b: BlockedPhone) -> dict:
    return {"id": str(b.id), "phone": phone_display(b.phone_key) or "0" + b.phone_key, "label": b.label or "",
            "created_at": b.created_at.isoformat() + "Z" if b.created_at else None}


@router.get("")
async def list_blocked(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(BlockedPhone).where(BlockedPhone.user_id == user.id)
                             .order_by(BlockedPhone.created_at.desc()))).scalars().all()
    hidden = (await db.execute(select(CallRecording).where(CallRecording.user_id == user.id, CallRecording.category == PERSONAL)
                               .order_by(CallRecording.created_at.desc()).limit(100))).scalars().all()
    return {"numbers": [_out(b) for b in rows],
            "hidden_calls": [{"id": str(c.id), "title": c.title or "שיחה אישית", "phone": c.phone_number or "",
                              "at": (c.started_at or c.created_at).isoformat() + "Z" if (c.started_at or c.created_at) else None,
                              "reason": (c.insights or {}).get("personal") or "summary"} for c in hidden]}


async def block(db, user, phone: str, label: str | None) -> tuple[BlockedPhone, int]:
    key = phone_key(phone)
    if not key:
        raise HTTPException(400, "מספר טלפון לא תקין")
    b = (await db.execute(select(BlockedPhone).where(BlockedPhone.user_id == user.id, BlockedPhone.phone_key == key))).scalar_one_or_none()
    if b is None:
        b = BlockedPhone(user_id=user.id, phone_key=key, label=(label or "").strip()[:80] or None)
        db.add(b)
    elif label:
        b.label = label.strip()[:80]
    hidden = await hide_calls_with(db, user.id, key)
    await db.commit()
    await db.refresh(b)
    return b, hidden


@router.post("")
async def add_blocked(data: BlockIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    b, hidden = await block(db, user, data.phone, data.label)
    return {**_out(b), "hidden_calls": hidden}


@router.delete("/{bid}")
async def remove_blocked(bid: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        b = await db.get(BlockedPhone, uuid.UUID(bid))
    except ValueError:
        b = None
    if not b or b.user_id != user.id:
        raise HTTPException(404, "לא נמצא")
    await db.delete(b)
    await db.commit()
    return {"ok": True}


async def _own_call(db, user, call_id: str) -> CallRecording:
    try:
        c = await db.get(CallRecording, uuid.UUID(call_id))
    except ValueError:
        c = None
    if not c or c.user_id != user.id:
        raise HTTPException(404, "לא נמצא")
    return c


class PersonalIn(BaseModel):
    block_number: bool = False


@router.post("/calls/{call_id}/personal")
async def mark_personal(call_id: str, data: PersonalIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """The agent marks a call as personal (from the call card) — and maybe never uploads that number again."""
    c = await _own_call(db, user, call_id)
    await hide_call(db, c, reason="agent")
    blocked = False
    if data.block_number and c.phone_number:
        await block(db, user, c.phone_number, (c.insights or {}).get("customer", {}).get("name") if isinstance((c.insights or {}).get("customer"), dict) else None)
        blocked = True
    await db.commit()
    return {"ok": True, "blocked": blocked}


@router.post("/calls/{call_id}/restore")
async def restore_call(call_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    c = await _own_call(db, user, call_id)
    await unhide_call(db, c)
    await db.commit()
    return {"ok": True}
