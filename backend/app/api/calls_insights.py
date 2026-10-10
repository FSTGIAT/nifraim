"""Nifra Insights — what the agent's calls add up to, and the promises to remind them of.

GET  /reminders        the 15-minute heads-ups + the morning brief + date proposals
POST /reminders/claim  first caller wins a reminder key (dedupe across tabs/devices)
POST /speak            the reminder sentences as MP3 — Azure "Hila" (services/tts.py)
GET  /board            products-first board + analyst panel (services/calls/insights_board.py)

Calls only, every query scoped to the caller and to privacy.visible(). Channel-agnostic:
the browser speaks it today; the Android app reads the same payload next version.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.call_recording import CallRecording
from app.models.calls_insights import CallsInsightsCache, ReminderClaim
from app.models.user import User
from app.services.calls import insights_board as B
from app.services.calls import reminders as R
from app.services import tts
from app.services.calls.privacy import visible

router = APIRouter()


async def done_calls(db: AsyncSession, user: User, limit: int = 1000) -> list[CallRecording]:
    return (await db.execute(
        select(CallRecording).where(CallRecording.user_id == user.id, CallRecording.status == "done", visible())
        .order_by(CallRecording.created_at.desc()).limit(limit)
    )).scalars().all()


@router.get("/reminders")
async def reminders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=3)
    claimed = set((await db.execute(select(ReminderClaim.key).where(
        ReminderClaim.user_id == user.id, ReminderClaim.claimed_at >= since))).scalars().all())
    return R.build(await done_calls(db, user), claimed=claimed, agent_name=user.full_name)


class ClaimIn(BaseModel):
    key: str


@router.post("/reminders/claim")
async def claim(body: ClaimIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    key = (body.key or "").strip()
    if not key or len(key) > 120 or not key.startswith(("task:", "brief:")):
        raise HTTPException(400, "מפתח לא תקין")
    row = (await db.execute(insert(ReminderClaim).values(user_id=user.id, key=key, claimed_at=datetime.utcnow())
                            .on_conflict_do_nothing(index_elements=["user_id", "key"])
                            .returning(ReminderClaim.id))).first()
    await db.commit()
    return {"claimed": row is not None}


class SpeakIn(BaseModel):
    text: str


@router.post("/speak")
async def speak(body: SpeakIn, user: User = Depends(get_current_user)):
    """The reminder sentences as MP3 in Hila's voice (Azure). 503 → the client uses the browser's voice."""
    try:
        audio = await tts.synthesize(body.text)
    except tts.TtsUnavailable:
        raise HTTPException(503, "voice unavailable")
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/board")
async def board(days: int = 0, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Products-first board + analyst panel. Themes/narrative come from the cached Claude pass;
    a change in the calls starts a new pass in the background (themes_status=computing)."""
    rows = await done_calls(db, user)
    fp = B.fingerprint(rows)
    cache = await db.get(CallsInsightsCache, user.id)
    status = "ready"
    if not rows:
        status = "empty"
    elif cache is None or cache.fingerprint != fp:
        status = B.schedule_refresh(user.id, fp)
    themes = cache.themes if cache else None
    narrative = [ln for ln in (cache.narrative or "").split("\n") if ln.strip()] if cache else []
    out = B.build(rows, themes, narrative, days=max(0, int(days or 0)))
    out.update(fingerprint=fp, themes_status=status, days=days,
               computed_at=cache.computed_at.isoformat() + "Z" if cache and cache.computed_at else None)
    return out
