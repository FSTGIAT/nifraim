"""שיחות — recorded agent↔customer conversations.

POST /api/calls streams the browser recording to calls-gateway (private network) and
returns at once; the transcript + summary arrive asynchronously (events_consumer) and the
UI polls GET /api/calls/{id}. Every query is scoped to the caller's user_id.
"""
from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.call_recording import CallRecording
from app.models.user import User
from app.services.calls import contract as C
from app.services.calls.events_consumer import NO_SPEECH_ERROR

router = APIRouter()

_EXT = {
    "audio/webm": ".webm", "video/webm": ".webm", "audio/ogg": ".ogg",
    "audio/mp4": ".m4a", "audio/x-m4a": ".m4a", "audio/aac": ".m4a",
    "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/mpeg": ".mp3",
}


def _out(c: CallRecording, full: bool = True) -> dict:
    d = {
        "id": str(c.id), "status": c.status, "error": c.error, "duration_s": c.duration_s,
        "created_at": c.created_at.isoformat() + "Z" if c.created_at else None,
        "done_at": c.done_at.isoformat() + "Z" if c.done_at else None,
        "title": c.title, "summary": c.summary, "insights": c.insights,
        "no_speech": c.error == NO_SPEECH_ERROR,
    }
    if full:
        d.update(transcript_text=c.transcript_text, segments=c.segments or [])
    return d


def _gateway() -> str:
    if not (settings.CALLS_ENABLED and settings.CALLS_GATEWAY_URL):
        raise HTTPException(503, "שירות השיחות עדיין לא הופעל")
    return settings.CALLS_GATEWAY_URL.rstrip("/")


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
    gateway = _gateway()
    mime = (audio.content_type or "").split(";")[0].strip().lower()
    ext = _EXT.get(mime)
    if not ext:
        raise HTTPException(415, "פורמט הקלטה לא נתמך")

    call = CallRecording(user_id=user.id, status="uploaded", mime_type=mime,
                         duration_s=duration_s if duration_s and duration_s > 0 else None)
    db.add(call)
    await db.commit()
    await db.refresh(call)

    size = 0

    async def body():
        nonlocal size
        while chunk := await audio.read(1024 * 1024):
            size += len(chunk)
            if size > settings.CALLS_MAX_BYTES:
                raise HTTPException(413, "ההקלטה ארוכה מדי")
            yield chunk

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10)) as http:
            resp = await http.post(f"{gateway}/ingest/{call.id}", params={"ext": ext}, content=body(),
                                   headers={C.SECRET_HEADER: settings.CALLS_SECRET,
                                            "Content-Type": "application/octet-stream"})
            resp.raise_for_status()
    except HTTPException as e:
        call.status, call.error = "failed", str(e.detail)
        await db.commit()
        raise
    except Exception:
        call.status, call.error = "failed", "שרת ההקלטות לא זמין — נסו שוב בעוד רגע"
        await db.commit()
        raise HTTPException(502, call.error)

    call.status, call.audio_bytes = "queued", size
    await db.commit()
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
