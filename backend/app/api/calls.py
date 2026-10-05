"""שיחות — recorded agent↔customer conversations.

POST /api/calls streams the browser recording to calls-gateway (private network) and
returns at once; the transcript + summary arrive asynchronously (events_consumer) and the
UI polls GET /api/calls/{id}. Every query is scoped to the caller's user_id.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import httpx
from pydantic import BaseModel
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.call_recording import CallRecording
from app.models.user import User
from app.services.calls import contract as C
from app.services.calls.events_consumer import NO_SPEECH_ERROR
from app.services.calls.categories import label as category_label
from app.services.calls.ingest import ingest_call, upload_chunks

router = APIRouter()

def _out(c: CallRecording, full: bool = True) -> dict:
    d = {
        "id": str(c.id), "status": c.status, "error": c.error, "duration_s": c.duration_s,
        "created_at": c.created_at.isoformat() + "Z" if c.created_at else None,
        "done_at": c.done_at.isoformat() + "Z" if c.done_at else None,
        "title": c.title, "summary": c.summary, "insights": c.insights,
        "no_speech": c.error == NO_SPEECH_ERROR,
        "source": c.source or "widget", "phone_number": c.phone_number, "direction": c.direction,
        "started_at": c.started_at.isoformat() + "Z" if c.started_at else None,
        "id_number": c.id_number,
        "category": c.category, "category_label": category_label(c.category) if c.category else None,
    }
    if full:
        d.update(transcript_text=c.transcript_text, segments=c.segments or [])
    return d


async def _own(db: AsyncSession, user: User, call_id: str) -> CallRecording:
    try:
        cid = uuid.UUID(call_id)
    except ValueError:
        raise HTTPException(404, "not found")
    call = (await db.execute(select(CallRecording).where(
        CallRecording.id == cid, CallRecording.user_id == user.id))).scalar_one_or_none()
    if call is None:
        raise HTTPException(404, "not found")
    return call


@router.get("/status")
async def calls_status(user: User = Depends(get_current_user)):
    return {"enabled": bool(settings.CALLS_ENABLED and settings.CALLS_GATEWAY_URL and settings.REDIS_URL)}


@router.post("")
async def upload_call(
    audio: UploadFile = File(...),
    duration_s: float | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    call = await ingest_call(db, user, upload_chunks(audio), audio.content_type or "", duration_s)
    return _out(call)


@router.get("")
async def list_calls(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(CallRecording).where(CallRecording.user_id == user.id)
        .order_by(CallRecording.created_at.desc()).limit(200))).scalars().all()
    return [_out(c, full=False) for c in rows]


@router.get("/{call_id}")
async def get_call(call_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return _out(await _own(db, user, call_id))


class FollowupIn(BaseModel):
    to_email: str
    to_name: str | None = None
    subject: str
    body: str


@router.post("/{call_id}/followup/send")
async def send_followup(call_id: str, data: FollowupIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """The agent approved (maybe edited) the customer follow-up — send it from THEIR mailbox."""
    from app.services import agent_actions
    from app.services.mail_intake import MailIntakeError
    from app.services.mail_intake.send import NoSendableMailbox
    call = await _own(db, user, call_id)
    try:
        await agent_actions.send(db, user, "email", data.model_dump())
    except agent_actions.ActionError as e:
        raise HTTPException(400, str(e))
    except NoSendableMailbox:
        raise HTTPException(400, "not_connected")
    except MailIntakeError as e:
        raise HTTPException(502, str(e))
    ins = dict(call.insights or {})
    ins["followup"] = {**(ins.get("followup") or {}), "status": "sent", "to_email": data.to_email,
                       "sent_at": datetime.utcnow().isoformat() + "Z"}
    call.insights = ins
    await db.commit()
    return {"ok": True, "to_email": data.to_email}


@router.post("/{call_id}/followup/dismiss")
async def dismiss_followup(call_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    call = await _own(db, user, call_id)
    ins = dict(call.insights or {})
    ins["followup"] = {**(ins.get("followup") or {}), "status": "dismissed"}
    call.insights = ins
    await db.commit()
    return {"ok": True}


class TaskIn(BaseModel):
    done: bool = True


@router.post("/{call_id}/tasks/{index}")
async def set_task_done(call_id: str, index: int, body: TaskIn, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    """Tick a call's task — on the server, so Nifra Agent knows what is still open."""
    call = await _own(db, user, call_id)
    call.insights = set_task(call.insights, index, body.done)
    await db.commit()
    return {"ok": True, "action_items": call.insights.get("action_items")}


def set_task(insights: dict | None, index: int, done: bool) -> dict:
    ins = dict(insights or {})
    items = [dict(a) for a in ins.get("action_items") or []]
    if not 0 <= index < len(items):
        raise HTTPException(404, "אין משימה כזו")
    items[index]["done"] = done
    items[index]["done_at"] = datetime.utcnow().isoformat() + "Z" if done else None
    ins["action_items"] = items
    return ins


@router.delete("/{call_id}")
async def delete_call(call_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    call = await _own(db, user, call_id)
    if settings.CALLS_GATEWAY_URL:
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                await http.delete(f"{settings.CALLS_GATEWAY_URL.rstrip('/')}/files/{call.id}",
                                  headers={C.SECRET_HEADER: settings.CALLS_SECRET})
        except Exception:
            pass  # audio ages out by retention anyway; the agent's delete must not fail on it
    await db.delete(call)
    await db.commit()
    return {"ok": True}
