"""The API's side of the calls plane: consume calls:events (group "api") and write the DB.

  transcribing → row.status = transcribing
  transcribed  → load the transcript (Redis key, else the gateway's done/<id>.json),
                 store it, status = summarizing → Claude summary → status = done
  failed       → status = failed + the Hebrew error

Runs as one asyncio task inside the API process, under a supervisor that restarts it
after any error (a Redis blip must never silently stop the plane — same idea as
maslaka_worker.py). user_id always comes from the DB row, never from the event.
A sweep fails calls stuck in a non-terminal state for STUCK_AFTER, so every call ends
done|failed.
"""
from __future__ import annotations

import asyncio
import re
import json
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta

import httpx
from sqlalchemy import update

from app.config import settings
from app.database import async_session
from app.models.call_recording import CALL_TERMINAL, CallRecording
from app.services.calls import contract as C
from app.services.calls.redis_client import get_redis

logger = logging.getLogger(__name__)

CONSUMER = f"{socket.gethostname()}-{os.getpid()}"
NO_SPEECH_ERROR = "לא זוהה דיבור בהקלטה"
# Whisper "hears" noise as filler ("אהההה", "תודה רבה" — a known hallucination on silence).
_FILLER = {"תודה", "רבה", "אה", "אהה", "אממ", "הממ", "כן", "לא", "אוקיי", "טוב"}


def has_speech(text: str | None) -> bool:
    """At least 3 distinct real words — otherwise Claude would summarise noise."""
    import re
    words = {w for w in re.findall(r"[\u0590-\u05FFA-Za-z]{2,}", text or "")
             if w not in _FILLER and not re.fullmatch(r"(.)\1+", w) and not re.fullmatch(r"א+ה+", w)}
    return len(words) >= 3
STUCK_AFTER = timedelta(hours=3)
_task: asyncio.Task | None = None


async def _load_transcript(r, call_id: str) -> dict | None:
    raw = await r.get(C.TRANSCRIPT_KEY.format(call_id=call_id))
    if raw:
        return json.loads(raw)
    if settings.CALLS_GATEWAY_URL:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.get(f"{settings.CALLS_GATEWAY_URL.rstrip('/')}/transcripts/{call_id}",
                                  headers={C.SECRET_HEADER: settings.CALLS_SECRET})
            if resp.status_code == 200:
                return resp.json()
    return None


async def _on_transcribed(r, call_id: str) -> None:
    from app.services.calls.summarize import summarize_call
    from app.services.mail_agent.llm import LlmUnavailable

    tx = await _load_transcript(r, call_id)
    async with async_session() as db:
        call = await db.get(CallRecording, uuid.UUID(call_id))
        if call is None or call.status in CALL_TERMINAL:
            await r.delete(C.TRANSCRIPT_KEY.format(call_id=call_id))   # orphan / deleted call
            return
        if tx is None:
            call.status, call.error = "failed", "התמלול לא נמצא"
            await db.commit()
            return
        call.segments = tx.get("segments") or []
        call.transcript_text = tx.get("text") or ""
        call.duration_s = tx.get("duration_s") or call.duration_s
        call.stt_model = (tx.get("model") or "")[:80]
        call.transcribed_at = datetime.utcnow()
        call.status = "summarizing"
        await db.commit()

        if not has_speech(call.transcript_text):
            call.status, call.done_at = "done", datetime.utcnow()
            call.error = NO_SPEECH_ERROR
            await db.commit()
        else:
            try:
                out, model = await summarize_call(call.segments, call.duration_s)
                call.title = (out.get("title") or "")[:120] or None
                call.summary = out.get("summary") or None
                insights = {k: out.get(k) for k in (
                    "tldr", "key_points", "action_items", "customer_needs", "products_mentioned",
                    "objections", "sentiment", "follow_up")}
                insights.update(await _followup(db, call, out))
                call.insights = insights
                call.llm_model = model
            except LlmUnavailable:
                logger.exception("calls: summary unavailable for %s", call_id)
                call.error = "הסיכום לא זמין כרגע — התמלול נשמר"
            call.status, call.done_at = "done", datetime.utcnow()
            await db.commit()
    # stored in Postgres now — the Redis copy can go (the gateway's done/<id>.json ages out)
    await r.delete(C.TRANSCRIPT_KEY.format(call_id=call_id))


async def _match_customer(db, user, name: str, id_number: str) -> dict:
    """Who the call was with, from what was SAID (name / ת.ז) matched against the
    agent's production files. Never guessed: no match → matched=False, the agent types it."""
    from app.models.user import User
    from app.services.office_agent import contacts
    u = await db.get(User, user)
    want = {"name": name.strip(), "id_number": id_number.strip(), "email": "", "matched": False}
    for q in ([id_number.lstrip("0")] if id_number.strip().isdigit() else []) + ([name.strip()] if name.strip() else []):
        hits = [c for c in await contacts(db, u, q[:60], limit=5) if c["kind"] == "customer"]
        if len(hits) == 1 or (hits and q.isdigit()):
            h = hits[0]
            return {"name": h["name"], "id_number": h["id_number"], "email": h["email"] or "", "matched": True}
    return want


async def _followup(db, call: CallRecording, out: dict) -> dict:
    """The customer-facing summary Nifra Agent offers to send (only on the agent's click)."""
    body = (out.get("followup_body") or "").strip()
    if not body:
        return {}
    # the model signs off anyway sometimes — drop its closing so ours is the only one
    lines = body.splitlines()
    while lines and (not lines[-1].strip() or re.match(r"^\s*(בברכה|בברכת|תודה רבה|שלך|שלכם)\b.*$", lines[-1]) or len(lines[-1].split()) <= 2 and lines[-2:-1] and re.match(r"^\s*(בברכה|בברכת)", lines[-2])):
        lines.pop()
    body = "\n".join(lines).strip()
    from app.models.user import User
    u = await db.get(User, call.user_id)
    sign = (u.full_name or "").strip() if u else ""
    customer = await _match_customer(db, call.user_id, out.get("customer_name") or "", out.get("customer_id_number") or "")
    return {
        "customer": customer,
        "followup": {
            "status": "ready",
            "subject": (out.get("followup_subject") or out.get("title") or "סיכום השיחה שלנו").strip()[:200],
            "body": body + (f"\n\nבברכה,\n{sign}" if sign else ""),
        },
    }


async def _set_status(call_id: str, status: str, error: str | None = None) -> None:
    async with async_session() as db:
        stmt = (update(CallRecording)
                .where(CallRecording.id == uuid.UUID(call_id), CallRecording.status.notin_(CALL_TERMINAL))
                .values(status=status, **({"error": error[:300]} if error else {})))
        await db.execute(stmt)
        await db.commit()


async def _handle(r, msg_id: str, f: dict) -> None:
    call_id = f.get("call_id", "")
    if C.is_valid_call_id(call_id):
        status = f.get("status")
        if status == C.EV_TRANSCRIBING:
            await _set_status(call_id, "transcribing")
        elif status == C.EV_FAILED:
            await _set_status(call_id, "failed", f.get("error") or "התמלול נכשל")
        elif status == C.EV_TRANSCRIBED:
            await _on_transcribed(r, call_id)
    await r.xack(C.EVENTS_STREAM, C.API_GROUP, msg_id)


async def _fail_stuck() -> None:
    cutoff = datetime.utcnow() - STUCK_AFTER
    async with async_session() as db:
        await db.execute(
            update(CallRecording)
            .where(CallRecording.status.notin_(CALL_TERMINAL), CallRecording.created_at < cutoff)
            .values(status="failed", error="העיבוד לא הסתיים בזמן"))
        await db.commit()


async def _run() -> None:
    r = get_redis()
    try:
        await r.xgroup_create(C.EVENTS_STREAM, C.API_GROUP, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise
    # events a previous API process read but never acked (redeploy mid-summary)
    _, orphans, *_ = await r.xautoclaim(C.EVENTS_STREAM, C.API_GROUP, CONSUMER, min_idle_time=60_000,
                                        start_id="0-0", count=50)
    for msg_id, f in orphans:
        if f:
            await _handle(r, msg_id, f)
    sweep = 0
    while True:
        resp = await r.xreadgroup(C.API_GROUP, CONSUMER, {C.EVENTS_STREAM: ">"}, count=10, block=5000)
        for _stream, msgs in resp or []:
            for msg_id, f in msgs:
                await _handle(r, msg_id, f)
        sweep += 1
        if sweep % 120 == 0:   # ~every 10 min when idle
            await _fail_stuck()


async def _supervise() -> None:
    backoff = 5
    while True:
        try:
            logger.info("calls: events consumer up as %s", CONSUMER)
            await _run()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("calls: events consumer crashed — restarting in %ss", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


def start_calls_consumer() -> None:
    global _task
    if settings.CALLS_ENABLED and settings.REDIS_URL and _task is None:
        _task = asyncio.create_task(_supervise())


async def stop_calls_consumer() -> None:
    global _task
    if _task:
        _task.cancel()
        _task = None
