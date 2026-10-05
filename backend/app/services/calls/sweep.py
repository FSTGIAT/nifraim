"""The calls self-healing sweep — fills in whatever a finished call is missing.

Runs from the calls events consumer every ~2 minutes (events_consumer._run). Newest calls
first, small batches, so the API stays responsive and a fresh deploy catches up by itself:

  1. summary   — Claude was down when the call finished (error = SUMMARY_UNAVAILABLE)
  2. category  — summarised before categories existed (category IS NULL) → Haiku classify
  3. passages  — no semantic-search passages for the CURRENT model (new call that failed
                 to index, calls from before calls_04, or CALLS_EMBED_MODEL changed)

Each call gets at most MAX_TRIES per job (insights._sweep), so a call that can never be
fixed (no text, a model that keeps refusing) is not retried forever. Never raises.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select, text

from app.database import async_session
from app.models.call_recording import CallRecording

logger = logging.getLogger(__name__)

BATCH = {"summary": 2, "category": 8, "passages": 20}
MAX_TRIES = 3
SETTLE = timedelta(minutes=2)       # leave calls that just finished to the live pipeline


def _tries(call: CallRecording, job: str) -> int:
    return int(((call.insights or {}).get("_sweep") or {}).get(job, 0))


def _bump(call: CallRecording, job: str) -> None:
    ins = dict(call.insights or {})
    sw = dict(ins.get("_sweep") or {})
    sw[job] = sw.get(job, 0) + 1
    ins["_sweep"] = sw
    call.insights = ins


async def _has_chunks_table(db) -> bool:
    return bool((await db.execute(text("SELECT to_regclass('public.call_chunks') IS NOT NULL"))).scalar())


async def categorize(db, call: CallRecording) -> bool:
    """Category, topics, companies, urgency and task due dates for an already-summarised call
    (Haiku). Never rewrites the summary or the follow-up the agent may already have sent."""
    from app.services.calls.categories import CATEGORIES
    from app.services.calls.events_consumer import call_day, clean_tasks
    from app.services.calls.summarize import classify_call
    ins = dict(call.insights or {})
    tasks = clean_tasks(ins.get("action_items"))
    out = await classify_call(call.title or "", call.summary or "", tasks, call.transcript_text or "", call_day(call))
    dates = out.get("due_dates") or []
    for i, t in enumerate(tasks):
        if not t["due_date"] and i < len(dates):
            t["due_date"] = dates[i] or ""
    ins["action_items"] = clean_tasks(tasks)
    for k in ("topics", "companies_mentioned", "urgency"):
        if out.get(k) and not ins.get(k):
            ins[k] = out[k]
    call.category = out.get("category") if out.get("category") in CATEGORIES else "other"
    call.insights = ins
    return True


async def _candidates(db, where, limit: int, job: str) -> list[CallRecording]:
    rows = (await db.execute(
        select(CallRecording).where(CallRecording.status == "done", CallRecording.done_at < datetime.utcnow() - SETTLE, *where)
        .order_by(CallRecording.created_at.desc()).limit(limit * 4)
    )).scalars().all()
    return [c for c in rows if _tries(c, job) < MAX_TRIES][:limit]


async def sweep(batch: dict | None = None) -> dict:
    """One pass. Returns {"summary": n, "category": n, "passages": n} fixed this pass."""
    from app.services.calls import embeddings
    from app.services.calls.events_consumer import SUMMARY_UNAVAILABLE, index_safely, summarize_into

    b = {**BATCH, **(batch or {})}
    done = {"summary": 0, "category": 0, "passages": 0}
    async with async_session() as db:
        # 1) summaries Claude couldn't write at the time
        for c in await _candidates(db, [CallRecording.error == SUMMARY_UNAVAILABLE, CallRecording.transcript_text.is_not(None)],
                                   b["summary"], "summary"):
            _bump(c, "summary")
            if await summarize_into(db, c):
                done["summary"] += 1
            await db.commit()
            await index_safely(db, c)

        # 2) categories for calls summarised before they existed
        for c in await _candidates(db, [CallRecording.category.is_(None), CallRecording.summary.is_not(None)],
                                   b["category"], "category"):
            _bump(c, "category")
            try:
                if await categorize(db, c):
                    done["category"] += 1
            except Exception:  # noqa: BLE001 — try again next pass (up to MAX_TRIES)
                logger.exception("calls sweep: categorize %s failed", c.id)
            await db.commit()

        # 3) semantic-search passages for the current model
        if await _has_chunks_table(db) and await embeddings.embed_query("בדיקה") is not None:
            model = embeddings.model_name()
            missing = text("NOT EXISTS (SELECT 1 FROM call_chunks ch WHERE ch.call_id = call_recordings.id AND ch.model = :m)"
                           ).bindparams(m=model)
            has_text = or_(CallRecording.segments.is_not(None), CallRecording.summary.is_not(None))
            for c in await _candidates(db, [and_(missing, has_text)], b["passages"], "passages"):
                n = await index_safely(db, c)
                if n:
                    done["passages"] += 1
                else:
                    _bump(c, "passages")
                    await db.commit()
    return done
