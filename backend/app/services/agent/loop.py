"""The agent turn: cache → fast lane → streamed tool loop. Yields SSE-ready dicts:

    {"status": "בודק עמלות שלא שולמו"}   a tool is running (shown as a chip, <1s)
    {"text": "..."}                      answer text (streamed)
    {"viz": {...}}                       a chart (native registry payload)
    {"proposal": {...}}                  an action awaiting the agent's click (/office-agent/act)
    {"done": true, "lane": "...", "ms": N}
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.config import settings
from app.models.ai_memory import AiIntentLog
from app.models.ai_usage import AiUsage
from app.services.agent import cache, prompt, registry, router
from app.services.agent.context import ToolContext
from app.services.agent.versioning import current as current_version

logger = logging.getLogger(__name__)
trace = logging.getLogger("uvicorn.error")
IL = ZoneInfo("Asia/Jerusalem")

# Sonnet 5 with thinking OFF (measured 2026-10-02): Sonnet 5.5 can't disable thinking — even
# "between_tools" reasons ~5s after every tool result and releases the answer in one burst at
# the end. Sonnet 5 streams the first word ~1.5s into the call. The user chose speed here.
MODEL = "claude-sonnet-5"
FALLBACK_MODEL = "claude-sonnet-5-5"
MODEL_PARAMS = {
    "claude-sonnet-5": {"output_config": {"effort": "low"}, "thinking": {"type": "disabled"}},
    "claude-sonnet-5-5": {"output_config": {"effort": "low"}, "thinking": {"type": "between_tools"}},
}
MAX_HOPS = 4
MAX_TOKENS = 4000
HOLD = 120                                  # chars held per hop before streaming (drops pre-tool filler)
RATE_PER_HOUR = 60                          # questions per agent per hour (DB-backed)
ANSWER_TTL = 600
HE_DAYS = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]


# A follow-up leans on the previous turn ("ושל מגדל?", "תפרט", "אותו לקוח"). Anything else is
# self-contained: the chat always sends history, but "כמה לא שולם לי?" means the same thing
# with or without it — so it still gets the answer cache and the fast lane.
FOLLOW_UP = re.compile(r"^(?:ו|ומה|ומי|וכמה|ושל|ול|גם|ו?תפרט|ו?תרחיב|עוד|ואם)\b|\b(?:אותו|אותה|אותם|לו|לה|להם|איתו|איתה|איתם|שלו|שלה|שלהם|זה|הזה|הזאת|הנ\"ל|למעלה|קודם|שאמרת|הקודם)\b")


def standalone(question: str) -> bool:
    q = " ".join((question or "").split())
    return bool(q) and not FOLLOW_UP.search(q)


def _norm_q(q: str) -> str:
    return re.sub(r"[\s?!.,]+", " ", (q or "").strip().lower())


async def _rate_limited(db, user_id) -> bool:
    n = (await db.execute(select(func.count()).select_from(AiIntentLog).where(
        AiIntentLog.user_id == user_id, AiIntentLog.created_at >= datetime.utcnow() - timedelta(hours=1)))).scalar_one()
    return n >= RATE_PER_HOUR


async def _log(db, user_id, intent, lane, ms, question, usage=None, model=None):
    try:
        db.add(AiIntentLog(user_id=user_id, intent=intent, lane=lane, ms=int(ms), question=(question or "")[:500]))
        if usage is not None:
            db.add(AiUsage(user_id=user_id, feature="agent", model=model or MODEL,
                           input_tokens=int(usage.get("in", 0)), output_tokens=int(usage.get("out", 0))))
        await db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("agent log failed: %s", e)
        await db.rollback()


def _history_messages(history: list[dict] | None) -> list[dict]:
    msgs: list[dict] = []
    for turn in (history or [])[-8:]:
        role = "assistant" if turn.get("role") in ("agent", "assistant") else "user"
        text = str(turn.get("text") or turn.get("content") or "").strip()[:1500]
        if not text:
            continue
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"] += "\n" + text
        else:
            msgs.append({"role": role, "content": text})
    while msgs and msgs[0]["role"] == "assistant":
        msgs.pop(0)
    return msgs


async def run(db, user, question: str, history: list[dict] | None = None, mentions: list[dict] | None = None,
              *, allow_fast: bool = True, view_context: str | None = None, surface: str = "chat"):
    t0 = time.monotonic()
    uid = user.id          # captured: a rollback inside a tool expires ORM objects
    question = (question or "").strip()[:800]
    if await _rate_limited(db, uid):
        yield {"text": "הגעת למכסת השאלות לשעה הזו — נסו שוב בעוד כמה דקות."}
        yield {"done": True, "lane": "limit", "ms": 0}
        return
    version = await current_version(db, uid)
    ctx = ToolContext(db=db, user=user, data_version=version)

    # 1) answer cache — only for a first question (follow-ups depend on history)
    akey = ("answer", surface, hashlib.sha1(_norm_q(question).encode()).hexdigest())
    fresh = not mentions and (not history or standalone(question))
    if fresh:
        hit = cache.get(uid, version, akey)
        if hit:
            for ev in hit:
                yield ev
            ms = (time.monotonic() - t0) * 1000
            yield {"done": True, "lane": "cache", "ms": int(ms)}
            await _log(db, uid, "cache", "cache", ms, question)
            return

    # 2) fast lane
    r = router.route(question) if (allow_fast and fresh) else None
    if r:
        try:
            t = registry.get(r.tool)
            yield {"status": t.status_he if t else "בודק"}
            out = await router.answer(ctx, r)
        except Exception as e:  # noqa: BLE001 — fall through to the agent lane
            logger.warning("fast lane %s failed: %r", r.intent, e)
            await db.rollback()
            await db.refresh(user)      # the rollback expired it; the agent lane reads user.* next
            out = None
        if out:
            events = [{"text": out["text"]}] + [{"viz": v} for v in out["vizs"]] + \
                     ([{"proposal": out["proposal"]}] if out.get("proposal") else [])
            for ev in events:
                yield ev
            if not out.get("proposal"):      # an instruction ("record") must never replay from cache
                cache.put(uid, version, akey, events, ttl=ANSWER_TTL)
            ms = (time.monotonic() - t0) * 1000
            yield {"done": True, "lane": "fast", "intent": r.intent, "ms": int(ms)}
            await _log(db, uid, r.intent, "fast", ms, question)
            trace.info("NIFRA-AGENT fast user=%s intent=%s %.0fms | Q: %s", user.email, r.intent, ms, question[:200])
            return

    # 3) agent lane
    if not settings.ANTHROPIC_API_KEY:
        yield {"text": "ה-AI לא מוגדר בסביבה הזו."}
        yield {"done": True, "lane": "agent", "ms": 0}
        return
    yield {"status": "חושב"}          # feedback within ~0.1s; the model's first token is ~2s away
    events: list[dict] = []
    usage = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
    model_used = MODEL
    async for ev in _agent(ctx, question, history, mentions, usage, view_context, surface):
        if ev.get("_model"):
            model_used = ev["_model"]
            continue
        events.append(ev)
        yield ev
    if not ctx.vizs and not ctx.proposals:
        auto = _auto_chart(ctx)
        if auto:
            ctx.vizs.append(auto)
    for v in ctx.vizs:
        yield {"viz": v}
        events.append({"viz": v})
    for p in ctx.proposals[:1]:
        yield {"proposal": p}
        events.append({"proposal": p})
    ms = (time.monotonic() - t0) * 1000
    if not ctx.proposals and fresh and not view_context:
        cache.put(uid, version, akey, [e for e in events if "status" not in e], ttl=ANSWER_TTL)
    yield {"done": True, "lane": "agent", "ms": int(ms), "cache_read": usage["cache_read"]}
    await _log(db, uid, None, "agent", ms, question, usage, model_used)
    trace.info("NIFRA-AGENT agent user=%s %.0fms in=%d out=%d cache_read=%d | Q: %s",
               user.email, ms, usage["in"], usage["out"], usage["cache_read"], question[:200])


async def _agent(ctx: ToolContext, question: str, history, mentions, usage: dict, view_context: str | None = None,
                 surface: str = "chat"):
    import anthropic
    from app.services.agent.tools_memory import memory_block
    from app.services.agreement_requests import mailbox_state

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=1, timeout=60)
    now = datetime.now(IL)
    own = (await mailbox_state(ctx.db, ctx.user.id)).get("mailbox_address") or ctx.user.email
    mem = await memory_block(ctx.db, ctx.user.id)
    dyn = prompt.dynamic_block(f"יום {HE_DAYS[now.weekday()]} {now:%Y-%m-%d %H:%M}", ctx.user.full_name or "", own, mem)
    q = question
    if mentions:
        rows = [" · ".join(x for x in (str(m.get("name") or "")[:80],
                                        f"ת.ז {m['id_number']}" if m.get("id_number") else "",
                                        f"מייל {m['email']}" if m.get("email") else "") if x) for m in mentions[:10]]
        q += "\nאנשי קשר שסומנו ב-@ (מדויקים):\n" + "\n".join("- " + r for r in rows)
    if surface == "panel":
        q += "\n(ענה בטקסט רגיל בלבד — בלי Markdown, בלי כוכביות ובלי כותרות; רשימה רק עם מקפים פשוטים.)"
    if view_context:
        q += "\nמה שהסוכן רואה עכשיו על המסך (הקשר בלבד, המספרים בכלים):\n" + view_context[:4000]
    # prefetch the obvious tools so the model can answer in ONE call (prefetch.py)
    from app.services.agent.prefetch import run_prefetch
    async for ev in run_prefetch(ctx, question):
        yield ev
    if ctx.prefetched:
        q += ("\n\nנתונים שכבר נשלפו בשבילך מהכלים (מספרים אמיתיים — ענה מהם ישירות; קרא לכלי נוסף רק אם חסר משהו):\n"
              + ctx.prefetched)
    messages = _history_messages(history)
    messages.append({"role": "user", "content": f"{dyn}\n\nבקשה: {q}"})
    from app.services.office_agent import wants_action
    # ONE stable tool list (prompt-cache prefix); a question just can't trigger an action (dispatch guard)
    ctx.allow_actions = wants_action(question, history)
    tools = registry.anthropic_tools()
    model = MODEL
    for hop in range(MAX_HOPS):
        kwargs = dict(
            model=model, max_tokens=MAX_TOKENS, system=prompt.system_blocks(), tools=tools, messages=messages,
            extra_body=MODEL_PARAMS.get(model, {"output_config": {"effort": "low"}}),
        )
        th = time.monotonic()
        try:
            async with client.messages.stream(**kwargs) as stream:
                # Hold the first words of each hop: a short "אבדוק…" before a tool call is
                # filler (the status chip already says what's happening) — drop it. Real
                # answers pass HOLD chars quickly and then stream normally.
                held, flushed = "", False
                ttft = None
                async for event in stream:
                    if ttft is None and event.type in ("text", "content_block_start", "thinking"):
                        ttft = time.monotonic() - th
                    if event.type == "content_block_start" and getattr(event.content_block, "type", "") == "tool_use":
                        held = "" if not flushed else held
                        t = registry.get(event.content_block.name)
                        yield {"status": t.status_he if t else "עובד"}
                    elif event.type == "text":
                        if flushed:
                            yield {"text": event.text}
                        else:
                            held += event.text
                            if len(held) > HOLD:
                                flushed = True
                                yield {"text": held}
                                held = ""
                msg = await stream.get_final_message()
                if held and msg.stop_reason != "tool_use":
                    yield {"text": held}
        except anthropic.NotFoundError:
            if model == MODEL:
                model = FALLBACK_MODEL
                yield {"_model": model}
                continue
            raise
        except anthropic.BadRequestError as e:
            # strict tools / output_config not accepted by this model or SDK — degrade once
            if hop == 0 and any(k in str(e) for k in ("strict", "output_config", "thinking")):
                logger.warning("agent: degrading request after 400: %s", e)
                tools = [{k: v for k, v in t.items() if k != "strict"} for t in tools]
                kwargs.pop("extra_body", None)
                continue
            raise
        u = msg.usage
        trace.info("NIFRA-AGENT hop=%d model=%s %.2fs ttft=%.2fs stop=%s in=%s out=%s cache_read=%s", hop, model, time.monotonic() - th,
                   ttft or 0, msg.stop_reason, u.input_tokens, u.output_tokens, getattr(u, "cache_read_input_tokens", 0))
        usage["in"] += (u.input_tokens or 0)
        usage["out"] += (u.output_tokens or 0)
        usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
        usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0
        if msg.stop_reason == "refusal":
            yield {"text": "אני לא יכול לענות על זה."}
            return
        if msg.stop_reason != "tool_use":
            return
        # echo the assistant turn back unchanged (thinking blocks keep their signature)
        messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in msg.content]})
        calls = [b for b in msg.content if getattr(b, "type", "") == "tool_use"]
        # sequential: every tool shares the request's AsyncSession (no concurrent queries on one session)
        tt = time.monotonic()
        outs = [await registry.dispatch(ctx, b.name, dict(b.input or {})) for b in calls]
        trace.info("NIFRA-AGENT tools=%s %.2fs", [b.name for b in calls], time.monotonic() - tt)
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id, "content": o[:12000]} for b, o in zip(calls, outs)]})
        if ctx.proposals:
            # one action per turn — confirm it in one line, no further hops
            yield {"text": ("\n" if hop or msg.content and any(getattr(b, "type", "") == "text" for b in msg.content) else "")
                   + proposal_line(ctx.proposals[0], own)}
            return
    yield {"text": "\nבדקתי כמה מקורות — אם חסר משהו, שאלו בצורה ממוקדת יותר."}


def proposal_line(p: dict, own_email: str = "") -> str:
    if p.get("kind") == "record_call":
        return "מקליט" + (f" את השיחה {p['about']}" if p.get("about") else "") + ". כשתסיימו — לחצו עצור או כתבו 'עצור', והסיכום יגיע לכאן."
    if p.get("kind") == "stop_call":
        return "עצרתי — ההקלטה נשלחה לתמלול וסיכום. אעדכן כאן כשהסיכום מוכן."
    if p.get("kind") == "maslaka":
        return f"הכנתי בקשת {p['code']} ({p['code_he']}) ל{p.get('customer_name') or 'ת.ז ' + p['customer_id_number']}. מחכה לאישור שלך."
    if p.get("kind") == "collection":
        return f"הכנתי תזכורת ל{p['company']} על {p['customers']} לקוחות (צפי ₪{p['expected']:,}). מחכה לאישור שלך."
    from app.services.office_agent import _proposal_line
    return _proposal_line(p, own_email)


_MONTH = re.compile(r"^\d{4}-\d{2}$|^\d{2}/\d{2,4}$")


def _auto_chart(ctx):
    """The model answered with a ranking/trend but skipped render_chart — draw the LAST
    kept result when it's chartable (≥3 rows with values). Same payload as render_chart."""
    from app.services.agent.tools_viz import build_viz
    for kept in reversed(list(ctx.results.values())):
        rows = [r for r in kept["rows"] if isinstance(r.get("value"), (int, float))]
        if len(rows) < 3 or not any(r["value"] for r in rows):
            continue
        months = all(_MONTH.match(str(r.get("label", ""))) for r in rows)
        return build_viz(kept, "trend" if months else "bar")
    return None
