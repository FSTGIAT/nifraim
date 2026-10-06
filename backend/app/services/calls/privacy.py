"""Personal calls and never-upload numbers.

A call is PERSONAL when its summary says so (category 'personal': family, friends, nothing
about work) or when its number is on the agent's never-upload list. A personal call is hidden
everywhere (list, Nifra Agent, data map, semantic search, cards), keeps no tasks / follow-up /
quotes, and its audio is deleted from the gateway at once (not after 7 days). The agent can
restore one (`unhide`). Every reader filters with `visible()` — add it to any new call query.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import select, text

from app.config import settings
from app.models.blocked_phone import BlockedPhone
from app.models.call_recording import CallRecording
from app.services.calls import contract as C
from app.services.calls.ingest import phone_key

logger = logging.getLogger(__name__)
PERSONAL = "personal"


def visible():
    """WHERE clause: not a personal call."""
    return CallRecording.category.is_distinct_from(PERSONAL)


async def delete_audio(call_id) -> None:
    if not settings.CALLS_GATEWAY_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            await http.delete(f"{settings.CALLS_GATEWAY_URL.rstrip('/')}/files/{call_id}",
                              headers={C.SECRET_HEADER: settings.CALLS_SECRET})
    except Exception:  # noqa: BLE001 — retention removes it anyway
        logger.warning("calls: deleting audio of personal call %s failed", call_id)


async def hide_call(db, call: CallRecording, reason: str = "summary") -> None:
    """Mark personal: no tasks, follow-up or quotes, out of search, audio gone."""
    ins = dict(call.insights or {})
    for k in ("action_items", "followup", "customer_quotes", "follow_up", "customer_needs", "objections"):
        ins.pop(k, None)
    ins["personal"] = reason
    if call.category != PERSONAL:
        ins["category_before"] = call.category
    call.insights = ins
    call.category = PERSONAL
    if await _has_chunks(db):
        await db.execute(text("DELETE FROM call_chunks WHERE call_id = :c"), {"c": call.id})
    await delete_audio(call.id)


async def unhide_call(db, call: CallRecording) -> None:
    ins = dict(call.insights or {})
    ins.pop("personal", None)
    call.category = ins.pop("category_before", None) or "other"
    call.insights = ins


async def _has_chunks(db) -> bool:
    return bool((await db.execute(text("SELECT to_regclass('public.call_chunks') IS NOT NULL"))).scalar())


async def blocked_keys(db, user_id) -> set[str]:
    return set((await db.execute(select(BlockedPhone.phone_key).where(BlockedPhone.user_id == user_id))).scalars())


async def is_blocked(db, user_id, phone: str | None) -> bool:
    key = phone_key(phone)
    return bool(key) and key in await blocked_keys(db, user_id)


async def hide_calls_with(db, user_id, key: str) -> int:
    """A number just added to the list: its stored calls become personal too."""
    n = 0
    for c in (await db.execute(select(CallRecording).where(
            CallRecording.user_id == user_id, CallRecording.phone_number.is_not(None), visible()))).scalars():
        if phone_key(c.phone_number) == key:
            await hide_call(db, c, reason="blocked")
            n += 1
    return n
