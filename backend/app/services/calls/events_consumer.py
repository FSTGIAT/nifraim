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
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import update

from app.config import settings
from app.database import async_session
from app.models.call_recording import CALL_TERMINAL, CallRecording
from app.services.calls import contract as C
from app.services.calls.categories import CATEGORIES
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


SUMMARY_UNAVAILABLE = "הסיכום לא זמין כרגע — התמלול נשמר"


async def summarize_into(db, call: CallRecording) -> bool:
    """Claude summary → title, summary, category, insights (tasks, roles, quotes, follow-up,
    customer). Shared by the live pipeline and the sweep. False = Claude unavailable (the
    call keeps its transcript and SUMMARY_UNAVAILABLE; the sweep retries it later)."""
    from app.models.user import User
    from app.services.calls.summarize import summarize_call
    from app.services.mail_agent.llm import LlmUnavailable
    try:
        u = await db.get(User, call.user_id)
        known = (await _match_customer(db, call.user_id, "", "", known_id=call.id_number)
                 if getattr(call, "id_number", None) else None)
        out, model = await summarize_call(
            call.segments, call.duration_s,
            agent_name=((u.full_name or "").strip() if u else "") or None,
            customer_name=(known or {}).get("name") if (known or {}).get("matched") else None,
            call_date=call_day(call),
        )
    except LlmUnavailable:
        logger.exception("calls: summary unavailable for %s", call.id)
        call.error = SUMMARY_UNAVAILABLE
        return False
    call.title = (out.get("title") or "")[:120] or None
    call.summary = out.get("summary") or None
    insights = {k: out.get(k) for k in (
        "tldr", "key_points", "action_items", "customer_needs", "products_mentioned",
        "objections", "sentiment", "follow_up", "customer_quotes",
        "topics", "companies_mentioned", "urgency")}
    insights["action_items"] = clean_tasks(insights.get("action_items"))
    for k in LIST_FIELDS:
        insights[k] = as_list(insights.get(k))
    call.category = out.get("category") if out.get("category") in CATEGORIES else "other"
    roles = _clean_roles(out.get("speaker_roles"), call.segments)
    if roles:
        insights["speaker_roles"] = roles
        insights["talk_ratio"] = talk_ratio(call.segments, roles)
    insights["customer_quotes"] = verified_quotes(insights.get("customer_quotes"), call.segments, roles)
    insights.update(await _followup(db, call, out))
    if "customer" not in insights and getattr(call, "id_number", None):
        insights["customer"] = await _match_customer(db, call.user_id, "", "", known_id=call.id_number)
    call.insights = insights
    call.llm_model = model
    if call.error == SUMMARY_UNAVAILABLE:
        call.error = None
    return True


async def index_safely(db, call: CallRecording) -> int:
    """Semantic-search passages for the call — never raises (the sweep retries what's missing)."""
    try:
        from app.services.calls.embeddings import index_call
        return await index_call(db, call)
    except Exception:  # noqa: BLE001
        logger.exception("calls: indexing %s for semantic search failed", call.id)
        await db.rollback()
        return 0


async def _on_transcribed(r, call_id: str) -> None:

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
        call.segments = one_voice_unlabelled(tx.get("segments") or [])
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
            await summarize_into(db, call)
            call.status, call.done_at = "done", datetime.utcnow()
            from app.services.calls.privacy import PERSONAL, hide_call, is_blocked
            if call.category == PERSONAL or await is_blocked(db, call.user_id, call.phone_number):
                # a personal call: hidden, no tasks / follow-up, audio deleted now — never indexed
                await hide_call(db, call, reason="summary" if call.category == PERSONAL else "blocked")
                await db.commit()
            else:
                await db.commit()
                await index_safely(db, call)
    # stored in Postgres now — the Redis copy can go (the gateway's done/<id>.json ages out)
    await r.delete(C.TRANSCRIPT_KEY.format(call_id=call_id))


def call_day(call):
    """The call's own date in Israel (a phone call: when it started; else when it was uploaded)."""
    from zoneinfo import ZoneInfo
    at = call.started_at or call.created_at
    if not at:
        return None
    return at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Asia/Jerusalem")).date()


LIST_FIELDS = ("key_points", "customer_needs", "products_mentioned", "objections", "customer_quotes",
               "topics", "companies_mentioned")


def as_list(v) -> list[str]:
    """A list field the model returned as ONE string ("<item>a</item><item>b</item>", or lines)
    becomes the list it meant — a string there blanked the whole call summary in the UI."""
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x or "").strip()]
    if not isinstance(v, str) or not v.strip():
        return []
    tagged = re.findall(r"<item>(.*?)</item>", v, flags=re.S)
    parts = tagged or re.split(r"\n+", v)
    return [p.strip(" -•\t") for p in parts if p.strip(" -•\t")]


def clean_tasks(items) -> list[dict]:
    """Tasks as stored: {text, owner, due, due_date: YYYY-MM-DD|"", due_time: HH:MM|"", done: bool}
    plus, once the agent acted: done_at, sched_date/sched_time (a date/time the agent CONFIRMED
    for the reminder). A date or time that isn't real is dropped (never guessed) — open_promises
    and the reminders rely on it. The sweep re-cleans every task, so a field missing here is lost."""
    out = []
    for a in items if isinstance(items, list) else []:
        if not isinstance(a, dict) or not (a.get("text") or "").strip():
            continue
        t = {"text": a["text"].strip(), "owner": a.get("owner") if a.get("owner") in ("agent", "customer") else "agent",
             "due": (a.get("due") or "").strip(), "due_date": _iso_day(a.get("due_date")),
             "due_time": _hhmm(a.get("due_time")), "done": bool(a.get("done"))}
        if a.get("done_at") and t["done"]:
            t["done_at"] = str(a["done_at"])[:40]
        sd = _iso_day(a.get("sched_date"))
        if sd:
            t["sched_date"], t["sched_time"] = sd, _hhmm(a.get("sched_time"))
        out.append(t)
    return out


def _iso_day(v) -> str:
    from datetime import date
    v = (v or "").strip() if isinstance(v, str) else ""
    try:
        return date.fromisoformat(v).isoformat() if v else ""
    except ValueError:
        return ""


def _hhmm(v) -> str:
    m = re.fullmatch(r"([01]?\d|2[0-3])[:.]([0-5]\d)", (v or "").strip()) if isinstance(v, str) else None
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def one_voice_unlabelled(segments: list[dict]) -> list[dict]:
    """A call always has two sides. If the diarizer heard only one voice (one mic, a quiet
    line), its labels say nothing — drop them so the summary infers roles from the words
    instead of calling everyone the agent."""
    if len({s.get("speaker") for s in segments if s.get("speaker")}) >= 2:
        return segments
    return [{k: v for k, v in s.items() if k != "speaker"} for s in segments]


def _norm(t: str) -> str:
    return re.sub(r"[^\w]+", " ", t or "").strip()


def verified_quotes(quotes, segments: list[dict], roles: dict) -> list[str]:
    """Keep a "customer quote" only if it really is in a line the customer said.
    Unlabelled transcripts have no proof of who said what → no customer quotes.
    The LLM proposes, the transcript decides."""
    if not isinstance(quotes, list) or not roles:
        return []
    customer = {k for k, v in (roles or {}).items() if v == "customer"}
    lines = [_norm(s.get("text", "")) for s in segments or []
             if not customer or s.get("speaker") in customer]
    if roles and not customer:
        return []          # labelled, but nobody is the customer → no customer quotes
    return [q for q in quotes if isinstance(q, str) and _norm(q) and any(_norm(q) in ln for ln in lines)][:3]


def _clean_roles(roles, segments: list[dict]) -> dict:
    """Keep only {S1|S2…: agent|customer} for speakers that actually appear in the transcript."""
    present = {s.get("speaker") for s in segments or [] if s.get("speaker")}
    if not present or not isinstance(roles, dict):
        return {}
    return {k: v for k, v in roles.items() if k in present and v in ("agent", "customer")}


def talk_ratio(segments: list[dict], roles: dict) -> dict:
    """Seconds each side spoke, from the labelled segments — computed, never asked of the LLM."""
    secs = {"agent": 0.0, "customer": 0.0}
    for s in segments or []:
        role = roles.get(s.get("speaker"))
        if role in secs:
            secs[role] += max(0.0, float(s.get("end") or 0) - float(s.get("start") or 0))
    total = secs["agent"] + secs["customer"]
    return {"agent_s": round(secs["agent"], 1), "customer_s": round(secs["customer"], 1),
            "agent_pct": round(100 * secs["agent"] / total) if total else None}


async def _match_customer(db, user, name: str, id_number: str, known_id: str | None = None) -> dict:
    """Who the call was with. A phone call arrives already matched by the caller's number
    (known_id = the row's id_number) — that wins. Otherwise from what was SAID (name / ת.ז)
    matched against the agent's production files. Never guessed: no match → matched=False."""
    from app.models.user import User
    from app.services.office_agent import contacts
    u = await db.get(User, user)
    if known_id:
        hits = [c for c in await contacts(db, u, known_id.lstrip("0"), limit=5)
                if c["kind"] == "customer" and (c["id_number"] or "").lstrip("0") == known_id.lstrip("0")]
        if hits:
            h = hits[0]
            return {"name": h["name"], "id_number": h["id_number"], "email": h["email"] or "", "matched": True}
    want = {"name": name.strip(), "id_number": id_number.strip(), "email": "", "matched": False}
    for q in ([id_number.lstrip("0")] if id_number.strip().isdigit() else []) + ([name.strip()] if name.strip() else []):
        hits = [c for c in await contacts(db, u, q[:60], limit=5) if c["kind"] == "customer"]
        if len(hits) == 1 or (hits and q.isdigit()):
            h = hits[0]
            return {"name": h["name"], "id_number": h["id_number"], "email": h["email"] or "", "matched": True}
    return want


async def _followup(db, call: CallRecording, out: dict) -> dict:
    """The customer-facing summary Nifra Agent offers to send (only on the agent's click)."""
    # the model occasionally leaks its own field tags ("</followup_body>") into the text
    body = re.sub(r"</?\w+_\w+>", "", out.get("followup_body") or "").strip()
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
    customer = await _match_customer(db, call.user_id, out.get("customer_name") or "", out.get("customer_id_number") or "",
                                     known_id=getattr(call, "id_number", None))
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
        if sweep % 24 == 1:    # ~every 2 min: fill whatever a call is missing (calls/sweep.py)
            await _sweep_safely()


async def _sweep_safely() -> None:
    try:
        from app.services.calls.sweep import sweep
        done = await sweep()
        if any(done.values()):
            logger.info("calls: sweep %s", done)
    except Exception:  # noqa: BLE001 — the sweep must never stop the consumer
        logger.exception("calls: sweep failed")


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
