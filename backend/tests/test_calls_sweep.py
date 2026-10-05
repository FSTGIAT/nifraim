"""Calls sweep + semantic search — 20 tests against the LOCAL database (real pgvector, real
e5 embeddings; Claude replaced by fakes). Fixture calls belong to test@test.com and carry
source_ref 'sweeptest:*'; every test removes its own rows.

    cd backend && python -m pytest -q tests/test_calls_sweep.py
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select, text

from app.database import async_session
from app.models.call_recording import CallRecording
from app.models.user import User
from app.services.calls import embeddings, summarize
from app.services.calls import sweep as SW
from app.services.calls.events_consumer import SUMMARY_UNAVAILABLE, index_safely, one_voice_unlabelled, verified_quotes

OLD = datetime.utcnow() - timedelta(minutes=30)


def run(coro):
    """Each test step runs in its own event loop — the app's pooled connections belong to the
    loop that opened them, so the pool is closed before the loop ends."""
    from app.database import engine

    async def go():
        try:
            return await coro
        finally:
            await engine.dispose()
    return asyncio.run(go())


async def _user(db, email="test@test.com"):
    return (await db.execute(select(User).where(User.email == email))).scalar_one()


async def _make(**kw) -> uuid.UUID:
    async with async_session() as db:
        u = await _user(db, kw.pop("email", "test@test.com"))
        segs = kw.pop("segments", [
            {"start": 0, "end": 4, "speaker": "S1", "text": "שלום, מדבר הסוכן, רצית לדבר על ביטוח משכנתא?"},
            {"start": 4, "end": 12, "speaker": "S2", "text": "כן, אנחנו לוקחים משכנתא בבנק לאומי בחודש הבא ואני רוצה ביטוח זול יותר"},
        ])
        c = CallRecording(user_id=u.id, status=kw.pop("status", "done"), source="phone_android",
                          source_ref=f"sweeptest:{uuid.uuid4().hex[:8]}", created_at=kw.pop("created_at", OLD),
                          done_at=kw.pop("done_at", OLD), segments=segs,
                          transcript_text=" ".join(s["text"] for s in segs), duration_s=12.0, **kw)
        db.add(c)
        await db.commit()
        return c.id


async def _get(cid) -> CallRecording:
    async with async_session() as db:
        return await db.get(CallRecording, cid)


async def _chunks(cid, model=None) -> int:
    async with async_session() as db:
        return (await db.execute(text("SELECT count(*) FROM call_chunks WHERE call_id = :c" + (" AND model = :m" if model else "")),
                                 {"c": cid, **({"m": model} if model else {})})).scalar()


@pytest.fixture(autouse=True)
def cleanup():
    yield

    async def go():
        async with async_session() as db:
            await db.execute(delete(CallRecording).where(CallRecording.source_ref.like("sweeptest:%")))
            await db.commit()
    run(go())


@pytest.fixture
def fake_claude(monkeypatch):
    calls = {"summarize": 0, "classify": 0}

    async def fake_summarize(segments, duration_s, agent_name=None, customer_name=None, call_date=None):
        calls["summarize"] += 1
        return ({"title": "ביטוח משכנתא", "tldr": "לקוח מבקש ביטוח משכנתא זול", "summary": "הלקוח לוקח משכנתא בלאומי.",
                 "key_points": [], "sentiment": "neutral", "category": "mortgage", "topics": ["משכנתא"],
                 "action_items": [{"text": "לשלוח הצעה", "owner": "agent", "due": "מחר", "due_date": "2026-10-06"}],
                 "speaker_roles": {"S1": "agent", "S2": "customer"}, "customer_quotes": ["אנחנו לוקחים משכנתא בבנק לאומי"]}, "fake")

    async def fake_classify(title, summary, tasks, transcript, call_date=None):
        calls["classify"] += 1
        return {"category": "mortgage", "topics": ["משכנתא"], "due_dates": ["2026-10-07"] * len(tasks)}

    monkeypatch.setattr(summarize, "summarize_call", fake_summarize)
    monkeypatch.setattr(summarize, "classify_call", fake_classify)
    return calls


# ── the sweep ────────────────────────────────────────────────────────────

def test_01_sweep_resummarizes_when_claude_was_down(fake_claude):
    cid = run(_make(error=SUMMARY_UNAVAILABLE))
    run(SW.sweep({"category": 0, "passages": 0}))
    c = run(_get(cid))
    assert c.error is None and c.title == "ביטוח משכנתא" and c.category == "mortgage"
    assert c.insights["speaker_roles"] == {"S1": "agent", "S2": "customer"}


def test_02_resummarized_call_is_also_indexed(fake_claude):
    cid = run(_make(error=SUMMARY_UNAVAILABLE))
    run(SW.sweep({"category": 0, "passages": 0}))
    assert run(_chunks(cid, embeddings.model_name())) >= 2


def test_03_sweep_categorizes_old_calls_without_touching_summary(fake_claude):
    cid = run(_make(title="ישן", summary="סיכום ישן", insights={"action_items": [{"text": "לחזור", "owner": "agent"}],
                                                             "followup": {"status": "sent", "body": "נשלח"}}))
    run(SW.sweep({"summary": 0, "passages": 0}))
    c = run(_get(cid))
    assert c.category == "mortgage" and c.summary == "סיכום ישן" and c.insights["followup"]["status"] == "sent"
    assert c.insights["action_items"][0]["due_date"] == "2026-10-07"


def test_04_categorize_keeps_existing_topics(fake_claude):
    cid = run(_make(title="x", summary="y", insights={"topics": ["קיים"]}))
    run(SW.sweep({"summary": 0, "passages": 0}))
    assert run(_get(cid)).insights["topics"] == ["קיים"]


def test_05_sweep_indexes_calls_missing_passages():
    cid = run(_make(title="ביטוח משכנתא", summary="משכנתא", category="mortgage"))
    assert run(_chunks(cid)) == 0
    run(SW.sweep({"summary": 0, "category": 0}))
    assert run(_chunks(cid, embeddings.model_name())) >= 2


def test_06_sweep_reindexes_after_model_change():
    cid = run(_make(title="t", summary="s", category="other"))

    async def stale():
        async with async_session() as db:
            c = await db.get(CallRecording, cid)
            await embeddings.index_call(db, c)
            await db.execute(text("UPDATE call_chunks SET model = 'old-model' WHERE call_id = :c"), {"c": cid})
            await db.commit()
    run(stale())
    assert run(_chunks(cid, embeddings.model_name())) == 0
    run(SW.sweep({"summary": 0, "category": 0}))
    assert run(_chunks(cid, embeddings.model_name())) >= 2 and run(_chunks(cid, "old-model")) == 0


def test_07_sweep_leaves_just_finished_calls_to_the_pipeline(fake_claude):
    cid = run(_make(error=SUMMARY_UNAVAILABLE, done_at=datetime.utcnow()))
    run(SW.sweep())
    assert run(_get(cid)).error == SUMMARY_UNAVAILABLE and fake_claude["summarize"] == 0


def test_08_sweep_ignores_unfinished_calls(fake_claude):
    cid = run(_make(status="transcribing", summary="s"))
    run(SW.sweep())
    c = run(_get(cid))
    assert c.category is None and run(_chunks(cid)) == 0


def test_09_gives_up_after_max_tries(monkeypatch):
    from app.services.mail_agent.llm import LlmUnavailable

    async def down(*a, **k):
        raise LlmUnavailable("down")
    monkeypatch.setattr(summarize, "summarize_call", down)
    cid = run(_make(error=SUMMARY_UNAVAILABLE))
    for _ in range(SW.MAX_TRIES + 2):
        run(SW.sweep({"category": 0, "passages": 0}))
    assert run(_get(cid)).insights["_sweep"]["summary"] == SW.MAX_TRIES


def test_10_batch_limit(fake_claude):
    ids = [run(_make(title="t", summary="s")) for _ in range(3)]
    out = run(SW.sweep({"summary": 0, "category": 2, "passages": 0}))
    assert out["category"] == 2 and sum(run(_get(i)).category is not None for i in ids) == 2


def test_11_index_safely_never_raises(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("model crashed")
    monkeypatch.setattr(embeddings, "embed_docs", boom)
    cid = run(_make(title="t", summary="s"))

    async def go():
        async with async_session() as db:
            return await index_safely(db, await db.get(CallRecording, cid))
    assert run(go()) == 0


# ── semantic search ──────────────────────────────────────────────────────

async def _ctx():
    db = async_session()
    s = await db.__aenter__()
    return s, SimpleNamespace(db=s, user=await _user(s), proposals=[])


def _search(**kw):
    from app.services.agent.tools_calls import search_calls

    async def go():
        db, ctx = await _ctx()
        try:
            return await search_calls(ctx, **kw)
        finally:
            await db.close()
    return run(go())


def _ref(cid):
    return str(cid)


def test_12_search_finds_by_meaning_not_words():
    cid = run(_make(title="שיחה", summary="שיחה", category="mortgage"))
    run(SW.sweep({"summary": 0, "category": 0}))
    out = _search(query="הלוואה לקניית דירה", limit=30)
    assert out.get("by") == "meaning" and _ref(cid) in [c["call_id"] for c in out["calls"]]


def test_13_search_returns_labelled_lines():
    cid = run(_make(title="שיחה", summary="שיחה", category="mortgage", insights={"speaker_roles": {"S1": "agent", "S2": "customer"}}))
    run(SW.sweep({"summary": 0, "category": 0}))
    row = next(c for c in _search(query="הלוואה לקניית דירה", limit=30)["calls"] if c["call_id"] == _ref(cid))
    assert any("לקוח:" in s for s in row.get("said", []))


def test_14_search_is_scoped_to_the_user():
    cid = run(_make(title="שיחה", summary="משכנתא", category="mortgage", email="late-signup@test.com"))
    run(SW.sweep({"summary": 0, "category": 0}))
    assert _ref(cid) not in [c["call_id"] for c in _search(query="משכנתא בבנק לאומי", limit=30)["calls"]]


def test_15_search_falls_back_to_words_without_embeddings(monkeypatch):
    async def none(*a, **k):
        return None
    monkeypatch.setattr(embeddings, "search", none)
    cid = run(_make(title="שיחה על משכנתא", summary="s", category="mortgage"))
    out = _search(query="משכנתא", limit=30)
    assert out.get("by") == "words" and _ref(cid) in [c["call_id"] for c in out["calls"]]


def test_16_search_respects_time_window():
    old = datetime.utcnow() - timedelta(days=200)
    cid = run(_make(title="שיחה", summary="משכנתא", category="mortgage", created_at=old, done_at=old, started_at=old))
    run(SW.sweep({"summary": 0, "category": 0}))
    in_window = [c["call_id"] for c in _search(query="משכנתא", since_days=240, until_days=120, limit=30)["calls"]]
    recent = [c["call_id"] for c in _search(query="משכנתא", since_days=30, limit=30)["calls"]]
    assert _ref(cid) in in_window and _ref(cid) not in recent


# ── pieces the sweep relies on ───────────────────────────────────────────

def test_17_one_voice_drops_labels_two_voices_keep():
    one = [{"text": "a", "speaker": "S1"}, {"text": "b", "speaker": "S1"}]
    two = [{"text": "a", "speaker": "S1"}, {"text": "b", "speaker": "S2"}]
    assert all("speaker" not in s for s in one_voice_unlabelled(one)) and one_voice_unlabelled(two) == two


def test_18_quote_said_by_agent_is_rejected():
    seg = [{"text": "אני אשלח לך הצעה מחר", "speaker": "S1"}, {"text": "אני משלמת יותר מדי", "speaker": "S2"}]
    assert verified_quotes(["אני אשלח לך הצעה מחר", "אני משלמת יותר מדי"], seg,
                           {"S1": "agent", "S2": "customer"}) == ["אני משלמת יותר מדי"]


def test_19_router_sends_said_questions_to_the_agent_lane():
    from app.services.agent.router import route
    assert route("מה הלקוח אמר על משכנתא?") is None and route("מי התלוננה על המחיר") is None
    assert route("תקליט את השיחה").tool == "start_call_recording"


def test_20_passages_skip_empty_and_have_summary():
    c = SimpleNamespace(segments=[{"start": 0, "end": 1, "speaker": "S1", "text": "  "},
                                  {"start": 1, "end": 3, "speaker": "S1", "text": "אני רוצה לבטל את הפוליסה"}],
                        insights={}, title="ביטול", summary="הלקוח רוצה לבטל")
    ps = embeddings.passages(c)
    assert [p["kind"] for p in ps] == ["said", "summary"] and ps[0]["text"] == "אני רוצה לבטל את הפוליסה"
