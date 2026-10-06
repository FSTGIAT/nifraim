"""Personal calls + never-upload numbers: a blocked number hides its stored calls, leaves the app's
customer list and goes to its block list; a personal call loses tasks / follow-up and disappears from
every reader; restore brings it back. Local DB, user test@test.com.

    cd backend && python -m pytest -q tests/test_calls_privacy.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import delete, select

from app.api.blocked_phones import block
from app.database import async_session, engine
from app.models.blocked_phone import BlockedPhone
from app.models.call_recording import CallRecording
from app.models.user import User
from app.services.calls.ingest import phone_hash, phone_key
from app.services.calls.privacy import PERSONAL, blocked_keys, hide_call, is_blocked, unhide_call, visible

PHONE = "052-6660001"


def run(fn):
    async def go():
        try:
            async with async_session() as db:
                u = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()

                async def clean():
                    await db.execute(delete(BlockedPhone).where(BlockedPhone.user_id == u.id))
                    await db.execute(delete(CallRecording).where(CallRecording.user_id == u.id, CallRecording.source_ref.like("privacy-test%")))
                    await db.commit()
                await clean()
                try:
                    return await fn(db, u)
                finally:
                    await clean()
        finally:
            await engine.dispose()
    return asyncio.run(go())


async def _call(db, u, phone=PHONE, ref="privacy-test-1", category="service"):
    c = CallRecording(user_id=u.id, status="done", source="phone_android", phone_number=phone.replace("-", ""),
                      source_ref=ref, category=category, title="בדיקה", done_at=datetime.utcnow(),
                      insights={"action_items": [{"text": "לשלוח טופס", "owner": "agent"}], "followup": {"status": "ready"}})
    db.add(c)
    await db.commit()
    return c


async def _visible_ids(db, u):
    return {c.id for c in (await db.execute(select(CallRecording).where(CallRecording.user_id == u.id, visible()))).scalars()}


def test_blocking_a_number_hides_its_calls_and_leaves_the_customer_list():
    async def t(db, u):
        c = await _call(db, u)
        assert c.id in await _visible_ids(db, u)
        _, hidden = await block(db, u, "+972 52 666 0001", "אמא")
        assert hidden == 1
        await db.refresh(c)
        assert c.category == PERSONAL and "action_items" not in c.insights and "followup" not in c.insights
        assert c.id not in await _visible_ids(db, u)
        assert await is_blocked(db, u.id, "0526660001") and phone_key(PHONE) in await blocked_keys(db, u.id)
        assert phone_hash(phone_key(PHONE)) == phone_hash("526660001")   # the hash the app compares
    run(t)


def test_personal_call_is_hidden_and_restore_brings_it_back():
    async def t(db, u):
        c = await _call(db, u, phone="054-1110000", ref="privacy-test-2", category="health_life")
        await hide_call(db, c, reason="agent")
        await db.commit()
        assert c.id not in await _visible_ids(db, u)
        await unhide_call(db, c)
        await db.commit()
        assert c.category == "health_life" and c.id in await _visible_ids(db, u)
    run(t)


def test_not_blocked_is_not_blocked():
    async def t(db, u):
        assert not await is_blocked(db, u.id, "050-0000000")
        assert not await is_blocked(db, u.id, None)
    run(t)
