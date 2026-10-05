"""Nifra Agent may prepare a מסלקה 9100 request ONLY when the agent's שיוך is approved (and the
feature is on, the ID is valid, and no 9100 is already open for that customer). Local DB: test@test.com
is 'approved', late-signup@test.com 'submitted', test_2909@test.com 'not_started'.

    cd backend && python -m pytest -q tests/test_maslaka_agent_gate.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select

from app.config import settings
from app.database import async_session, engine
from app.models.pension_inquiry import PensionInquiry
from app.models.user import User
from app.services.agent.tools_maslaka import propose_maslaka_request

ID = "36148096"


def run(coro):
    async def go():
        try:
            return await coro
        finally:
            await engine.dispose()
    return asyncio.run(go())


def ask(email: str, id_number: str = ID, code: str = "9100"):
    async def go():
        async with async_session() as db:
            u = (await db.execute(select(User).where(User.email == email))).scalar_one()
            ctx = SimpleNamespace(db=db, user=u, proposals=[])
            msg = await propose_maslaka_request(ctx, code=code, id_number=id_number, customer_name="שרית סימון")
            return msg, ctx.proposals
    return run(go())


@pytest.fixture(autouse=True)
def no_open_requests():
    async def clean():
        async with async_session() as db:
            await db.execute(delete(PensionInquiry).where(PensionInquiry.customer_name == "gate-test"))
            await db.commit()
    run(clean())
    yield
    run(clean())


def test_approved_agent_gets_a_proposal(monkeypatch):
    monkeypatch.setattr(settings, "MASLAKA_ENABLED", True)
    msg, props = ask("test@test.com")
    assert len(props) == 1 and props[0]["kind"] == "maslaka" and props[0]["customer_id_number"] == ID
    assert "לאישור" in msg


def test_submitted_but_not_approved_gets_nothing(monkeypatch):
    monkeypatch.setattr(settings, "MASLAKA_ENABLED", True)
    msg, props = ask("late-signup@test.com")
    assert props == [] and "מחכה לאישור המסלקה" in msg


def test_not_started_gets_nothing_and_is_told_where_the_form_is(monkeypatch):
    monkeypatch.setattr(settings, "MASLAKA_ENABLED", True)
    msg, props = ask("test_2909@test.com")
    assert props == [] and "טופס השיוך" in msg


def test_feature_off_gets_nothing_even_when_approved(monkeypatch):
    monkeypatch.setattr(settings, "MASLAKA_ENABLED", False)
    msg, props = ask("test@test.com")
    assert props == [] and "לא פעיל" in msg


def test_invalid_id_gets_nothing(monkeypatch):
    monkeypatch.setattr(settings, "MASLAKA_ENABLED", True)
    msg, props = ask("test@test.com", id_number="12")
    assert props == [] and "ת.ז" in msg


def test_only_9100_is_supported(monkeypatch):
    monkeypatch.setattr(settings, "MASLAKA_ENABLED", True)
    msg, props = ask("test@test.com", code="9101")
    assert props == [] and "9100" in msg


def test_no_second_request_while_one_is_open(monkeypatch):
    monkeypatch.setattr(settings, "MASLAKA_ENABLED", True)

    async def plant():
        async with async_session() as db:
            u = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()
            db.add(PensionInquiry(user_id=u.id, customer_id_number=ID, customer_name="gate-test", status="submitted",
                                  interface_code="EVENTS:9100", request_reference=f"gate-test-{datetime.utcnow().timestamp()}",
                                  created_at=datetime.utcnow()))
            await db.commit()
    run(plant())
    msg, props = ask("test@test.com")
    assert props == [] and "כבר יש בקשת 9100 פתוחה" in msg
