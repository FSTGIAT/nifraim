"""Walk-in customers (לקוח חדש): the phone joins the Nifraim App's customer list, a call with that
number resolves to the walk-in (name + email for the follow-up), bad input is refused.
Local DB, user test@test.com.

    cd backend && python -m pytest -q tests/test_walkin_customers.py
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.api.walkin_customers import WalkinIn, _clean
from app.database import async_session, engine
from app.models.user import User
from app.models.walkin_customer import WalkinCustomer
from app.services.calls.ingest import customer_phones, match_phone, phone_hash, phone_key

PHONE = "052-7771234"


def run(fn):
    async def go():
        try:
            async with async_session() as db:
                u = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()
                await db.execute(delete(WalkinCustomer).where(WalkinCustomer.user_id == u.id))
                await db.commit()
                try:
                    return await fn(db, u)
                finally:
                    await db.execute(delete(WalkinCustomer).where(WalkinCustomer.user_id == u.id))
                    await db.commit()
        finally:
            await engine.dispose()
    return asyncio.run(go())


async def _add(db, u, **kw):
    vals = _clean(WalkinIn(**{"id_number": "030123456", "first_name": "דנה", "last_name": "לוי", "phone": PHONE,
                              "email": "dana@example.com", **kw}))
    db.add(WalkinCustomer(user_id=u.id, **vals))
    await db.commit()
    return vals


def test_phone_joins_the_customer_list_in_every_format():
    async def t(db, u):
        before = set(await customer_phones(db, u))
        await _add(db, u)
        after = await customer_phones(db, u)
        assert phone_key(PHONE) in after and phone_key(PHONE) not in before
        assert phone_hash(phone_key("+972 52 777 1234")) in {phone_hash(k) for k in after}
        for raw in ("0527771234", "+972527771234", "972-52-777-1234"):
            assert await match_phone(db, u, raw) == "30123456"
    run(t)


def test_a_call_resolves_to_the_walkin_with_email():
    async def t(db, u):
        await _add(db, u)
        from app.services.calls.events_consumer import _match_customer
        got = await _match_customer(db, u.id, "", "", known_id="30123456")
        assert got == {"name": "דנה לוי", "id_number": "30123456", "email": "dana@example.com", "matched": True}
    run(t)


@pytest.mark.parametrize("bad", [{"id_number": "12"}, {"phone": "123"}, {"first_name": " "}, {"email": "not-an-email"}])
def test_bad_input_is_refused(bad):
    base = {"id_number": "30123456", "first_name": "דנה", "phone": PHONE}
    with pytest.raises(HTTPException):
        _clean(WalkinIn(**{**base, **bad}))
