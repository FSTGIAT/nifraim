"""Calls (שיחות) — the agent records a conversation when asked, and reads summaries back.

Recording happens in the AGENT'S BROWSER (microphone → calls store → /api/calls →
ivrit.ai transcript → Claude summary; see api/calls.py). So these tools don't record on
the server: they hand the open app an instruction (`proposal` kind record_call /
stop_call) that the chat surfaces execute at once — the agent's own request is the
consent, and nothing leaves the app. When the summary is ready the app posts it back
into the conversation (frontend utils/agentCalls.js).
"""
from __future__ import annotations

from sqlalchemy import select

from app.models.call_recording import CALL_TERMINAL, CallRecording
from app.services.calls.privacy import visible
from app.services.agent.registry import tool


def call_brief(c: CallRecording) -> dict:
    ins = c.insights or {}
    return {
        "id": str(c.id), "status": c.status, "title": c.title,
        "when": c.created_at.strftime("%d/%m %H:%M") if c.created_at else None,
        "minutes": round((c.duration_s or 0) / 60, 1) if c.duration_s else None,
        "tldr": ins.get("tldr"), "summary": c.summary,
        "action_items": ins.get("action_items"), "follow_up": ins.get("follow_up"),
        "customer_needs": ins.get("customer_needs"), "sentiment": ins.get("sentiment"),
    }


@tool("start_call_recording", "התחלת הקלטה של שיחה עם לקוח (מהמיקרופון בדפדפן של הסוכן). כשהשיחה תסתיים והסוכן יעצור — היא מתומללת ומסוכמת, והסיכום יגיע לכאן אוטומטית.",
      {"about": {"type": "string", "description": "עם מי / על מה השיחה, אם נאמר"}},
      category="calls", status_he="מתחיל להקליט")
async def start_call_recording(ctx, about: str = ""):
    ctx.proposals.append({"kind": "record_call", "about": (about or "")[:120]})
    return "ההקלטה מתחילה עכשיו בדפדפן. כתוב משפט אחד: שאתה מקליט, ושיגידו 'עצור' (או ילחצו עצור) בסוף — והסיכום יגיע לכאן."


@tool("stop_call_recording", "עצירת ההקלטה שרצה ושליחתה לתמלול וסיכום. הסיכום יגיע לכאן כשיהיה מוכן (בדרך כלל דקות).",
      category="calls", status_he="עוצר את ההקלטה")
async def stop_call_recording(ctx):
    ctx.proposals.append({"kind": "stop_call"})
    return "ההקלטה נעצרת ונשלחת לסיכום. כתוב משפט אחד שהסיכום יגיע לכאן כשיהיה מוכן."


@tool("get_call_summaries", "רק לשיחה האחרונה או לכמה סיכומים אחרונים (which=last). לא לספירה ולא לנושאים (→ calls_stats), לא לחיפוש (→ search_calls), לא ללקוח אחד (→ customer_calls).",
      {"which": {"type": "string", "description": "last, או מילה לחיפוש"}, "n": {"type": "integer"}},
      category="calls", status_he="קורא את סיכומי השיחות")
async def get_call_summaries(ctx, which: str = "last", n: int = 3):
    rows = (await ctx.db.execute(select(CallRecording).where(CallRecording.user_id == ctx.user.id, visible())
                                 .order_by(CallRecording.created_at.desc()).limit(100))).scalars().all()
    if not rows:
        return {"calls": [], "note": "עוד לא הוקלטו שיחות. אפשר לבקש ממני 'תקליט את השיחה'."}
    q = (which or "last").strip()
    if q and q != "last":
        rows = [c for c in rows if q in (c.title or "") or q in (c.summary or "") or q in (c.transcript_text or "")]
    pending = [c for c in rows if c.status not in CALL_TERMINAL]
    done = [c for c in rows if c.status == "done" and (c.summary or c.title)]
    out = {"calls": [call_brief(c) for c in done[: max(1, min(int(n or 3), 10))]]}
    if pending:
        out["in_progress"] = len(pending)
        out["note"] = f"{len(pending)} שיחות עדיין בעיבוד — הסיכום יגיע לכאן כשיהיה מוכן."
    if not done and not pending:
        out["note"] = f"לא נמצאה שיחה שמתאימה ל«{q}»."
    return out


# ─────────────────────── calls intelligence (2026-10-05) ───────────────────────
# Every call is categorised (services/calls/categories.py), linked to a customer (by phone
# or by name) and its tasks carry a real due_date + done flag. These tools read that; the
# only write (a task done) is a proposal the agent approves.

from datetime import date, datetime, timedelta, timezone  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

from app.services.calls import categories as CAT  # noqa: E402

IL = ZoneInfo("Asia/Jerusalem")
ROLE_HE = {"agent": "סוכן", "customer": "לקוח"}
SOURCE_HE = {"phone_android": "טלפון", "phone_ios": "טלפון", "widget": "הקלטה באתר"}


def _today() -> date:
    return datetime.now(timezone.utc).astimezone(IL).date()


async def _calls(ctx, limit: int = 500) -> list[CallRecording]:
    return (await ctx.db.execute(
        select(CallRecording).where(CallRecording.user_id == ctx.user.id, CallRecording.status == "done", visible())
        .order_by(CallRecording.created_at.desc()).limit(limit)
    )).scalars().all()


def _customer(c: CallRecording) -> dict:
    cu = (c.insights or {}).get("customer") or {}
    return {"name": cu.get("name") or "", "id_number": c.id_number or cu.get("id_number") or "",
            "email": (cu.get("email") or "").lower(), "matched": bool(c.id_number or cu.get("matched"))}


def _when(c: CallRecording) -> str:
    at = c.started_at or c.created_at
    return at.replace(tzinfo=timezone.utc).astimezone(IL).strftime("%d/%m/%Y %H:%M") if at else ""


def _row(c: CallRecording) -> dict:
    ins = c.insights or {}
    open_tasks = [a for a in ins.get("action_items") or [] if not a.get("done")]
    cu = _customer(c)
    return {
        "call_id": str(c.id), "when": _when(c), "title": c.title,
        "category": CAT.label(c.category) if c.category else None,
        "customer": cu["name"] or None, "id_number": cu["id_number"] or None, "email": cu["email"] or None,
        "source": SOURCE_HE.get(c.source or "widget"), "direction": {"in": "נכנסת", "out": "יוצאת"}.get(c.direction or ""),
        "minutes": round((c.duration_s or 0) / 60, 1) if c.duration_s else None,
        "tldr": ins.get("tldr"), "open_tasks": len(open_tasks),
        "topics": ins.get("topics") or [],
    }


def _matches_customer(c: CallRecording, who: str) -> bool:
    w = (who or "").strip()
    if not w:
        return True
    cu = _customer(c)
    digits = "".join(ch for ch in w if ch.isdigit())
    if digits and len(digits) >= 7:
        if cu["id_number"] and cu["id_number"].lstrip("0") == digits.lstrip("0"):
            return True
        return bool(c.phone_number and digits.lstrip("0")[-8:] in (c.phone_number or ""))
    name = cu["name"]
    if w in name or all(part in name for part in w.split()):
        return True
    # "שרית בהראל", "חיים מהמשכנתא": a word of the question that IS one of the name's words
    words = set(name.split())
    return any(len(p) >= 2 and p in words for p in w.split())


def _lines(c: CallRecording) -> list[str]:
    roles = (c.insights or {}).get("speaker_roles") or {}
    out = []
    for s in c.segments or []:
        t = int(s.get("start") or 0)
        who = ROLE_HE.get(roles.get(s.get("speaker")), "")
        out.append(f"[{t // 60:02d}:{t % 60:02d}] {who + ': ' if who else ''}{s.get('text', '')}")
    return out


@tool("search_calls",
      "חיפוש בכל השיחות (מהטלפון ומהאתר) לפי משמעות — לא רק מילים: 'הלוואה לדירה' מוצא שיחה על משכנתא. "
      "מחזיר את הקטעים עצמם מהתמלול (מי אמר, מתי בשיחה) לכל שיחה. אפשר לצמצם לפי נושא, לקוח, כיוון ותקופה "
      "(since_days = עד כמה ימים אחורה, until_days = לא חדש מ-N ימים — 'לפני חצי שנה' ≈ since_days=240, until_days=120).",
      {"query": {"type": "string", "description": "מה לחפש, במילים חופשיות — או ריק"},
       "category": {"type": "string", "description": "נושא: " + ", ".join(CAT.CATEGORIES.values())},
       "customer": {"type": "string", "description": "שם, ת.ז או טלפון של לקוח"},
       "since_days": {"type": "integer", "description": "רק מ-N הימים האחרונים (0 = הכל)"},
       "until_days": {"type": "integer", "description": "רק שיחות ישנות מ-N ימים (0 = עד היום)"},
       "direction": {"type": "string", "enum": ["", "in", "out"]},
       "limit": {"type": "integer"}},
      category="calls", status_he="מחפש בשיחות")
async def search_calls(ctx, query: str = "", category: str = "", customer: str = "", since_days: int = 0,
                       until_days: int = 0, direction: str = "", limit: int = 10):
    from app.services.calls import embeddings
    rows = await _calls(ctx)
    cat = CAT.key_for(category)
    if category and not cat:
        return {"calls": [], "note": f"אין נושא «{category}». הנושאים: " + ", ".join(CAT.CATEGORIES.values())}
    now = datetime.utcnow()
    since = now - timedelta(days=since_days) if since_days and since_days > 0 else None
    until = now - timedelta(days=until_days) if until_days and until_days > 0 else None

    def keep(c):
        at = c.started_at or c.created_at
        return ((not cat or c.category == cat) and (direction not in ("in", "out") or c.direction == direction)
                and (not since or at >= since) and (not until or at <= until) and _matches_customer(c, customer))

    pool = {c.id: c for c in rows if keep(c)}
    limit = max(1, min(int(limit or 10), 30))
    if not query.strip():
        out = [_row(c) for c in list(pool.values())[:limit]]
        return {"calls": out, "count": len(out)} if out else {"calls": [], "note": "לא נמצאה שיחה שמתאימה." if rows else "עוד אין שיחות."}

    # 1) by MEANING (pgvector) — passages ranked, grouped per call, best call first
    said: dict = {}
    order: list = []
    sem = await embeddings.search(ctx.db, ctx.user.id, query, k=60, since=since, until=until, call_ids=list(pool)) if pool else []
    for p in sem or []:
        cid = p["call_id"]
        if cid not in pool:
            continue
        if cid not in said:
            said[cid] = []
            order.append(cid)
        t = int(p["start_s"] or 0)
        line = (p["text"] if p["kind"] == "summary" else
                f"[{t // 60:02d}:{t % 60:02d}] {ROLE_HE.get(p['role'], '') + ': ' if p['role'] else ''}{p['text']}")
        if line not in said[cid] and len(said[cid]) < 3:
            said[cid].append(line)
    # 2) exact words — anything the meaning search didn't already bring
    words = [w for w in query.split() if len(w) > 1]
    for c in pool.values():
        if c.id in said:
            continue
        hit = [ln for ln in _lines(c) if any(w in ln for w in words)]
        hay = " ".join([c.title or "", c.summary or "", " ".join((c.insights or {}).get("topics") or [])])
        if hit or any(w in hay for w in words):
            said[c.id] = hit[:3]
            order.append(c.id)
    out = []
    for cid in order[:limit]:
        r = _row(pool[cid])
        if said[cid]:
            r["said"] = said[cid]
        out.append(r)
    if not out:
        return {"calls": [], "note": "לא נמצאה שיחה שמתאימה." if rows else "עוד אין שיחות."}
    return {"calls": out, "count": len(out), "by": "meaning" if sem else "words",
            "note": "מסודר לפי קרבה במשמעות — בדוק בשורות 'said' שזה באמת מה שנשאל לפני שאתה עונה."}


@tool("customer_calls",
      "כל ההיסטוריה של השיחות עם לקוח אחד (לפי שם, ת.ז או טלפון): מתי דיברו, על מה, מה הלקוח אמר, ומה עוד פתוח — "
      "open_agent = מה הסוכן הבטיח, open_customer = מה הלקוח צריך לעשות, done = מה כבר בוצע. אל תערבב ביניהם.",
      {"customer": {"type": "string"}}, ["customer"], category="calls", status_he="קורא את השיחות עם הלקוח")
async def customer_calls(ctx, customer: str):
    rows = [c for c in await _calls(ctx) if _matches_customer(c, customer)]
    if not rows:
        return {"calls": [], "note": f"אין שיחות מוקלטות עם «{customer}»."}
    calls = []
    for c in rows[:15]:
        r = _row(c)
        ins = c.insights or {}
        r["customer_quotes"] = ins.get("customer_quotes") or []
        # WHO owes each task — without it the model listed the customer's task as the agent's promise
        r["open_agent"] = [a["text"] + (f" (עד {a['due']})" if a.get("due") else "")
                           for a in ins.get("action_items") or [] if not a.get("done") and a.get("owner") == "agent"]
        r["open_customer"] = [a["text"] + (f" (עד {a['due']})" if a.get("due") else "")
                              for a in ins.get("action_items") or [] if not a.get("done") and a.get("owner") == "customer"]
        r["done"] = [a["text"] for a in ins.get("action_items") or [] if a.get("done")]
        calls.append(r)
    return {"customer": _customer(rows[0])["name"] or customer, "count": len(rows), "calls": calls}


@tool("get_call",
      "שיחה אחת במלואה: סיכום, נקודות, משימות (עם מספר משימה ומצב), ציטוטי לקוח, צרכים, התנגדויות, חלוקת זמן דיבור, "
      "ואם with_transcript — שורות התמלול מסומנות סוכן/לקוח.",
      {"call_id": {"type": "string"}, "with_transcript": {"type": "boolean"}}, ["call_id"],
      category="calls", status_he="פותח את השיחה")
async def get_call(ctx, call_id: str, with_transcript: bool = False):
    import uuid as _uuid
    try:
        cid = _uuid.UUID(str(call_id))
    except ValueError:
        return "מזהה שיחה לא תקין — קח call_id מ-search_calls."
    c = (await ctx.db.execute(select(CallRecording).where(
        CallRecording.id == cid, CallRecording.user_id == ctx.user.id, visible()))).scalar_one_or_none()
    if not c:
        return "לא נמצאה שיחה כזו."
    ins = c.insights or {}
    out = _row(c) | {
        "summary": c.summary, "key_points": ins.get("key_points"),
        "tasks": [{"task_index": i, "text": a.get("text"), "owner": ROLE_HE.get(a.get("owner"), a.get("owner")),
                   "due": a.get("due") or None, "due_date": a.get("due_date") or None, "done": bool(a.get("done"))}
                  for i, a in enumerate(ins.get("action_items") or [])],
        "customer_quotes": ins.get("customer_quotes") or [], "customer_needs": ins.get("customer_needs") or [],
        "objections": ins.get("objections") or [], "companies_mentioned": ins.get("companies_mentioned") or [],
        "sentiment": ins.get("sentiment"), "talk_ratio": ins.get("talk_ratio"), "phone": c.phone_number,
    }
    if with_transcript:
        out["transcript"] = _lines(c)[:120]
    return out


def promises(rows: list[CallRecording], owner: str = "agent", today: date | None = None) -> list[dict]:
    """Open tasks across calls, overdue first. Pure — also feeds the office-agent card."""
    today = today or _today()
    out = []
    for c in rows:
        for i, a in enumerate((c.insights or {}).get("action_items") or []):
            if a.get("done") or (owner in ("agent", "customer") and a.get("owner") != owner):
                continue
            d = None
            try:   # a date the agent confirmed for the reminder beats the one heard in the call
                d = date.fromisoformat(a.get("sched_date") or a["due_date"]) if (a.get("sched_date") or a.get("due_date")) else None
            except ValueError:
                pass
            out.append({"call_id": str(c.id), "task_index": i, "text": a.get("text"),
                        "owner": ROLE_HE.get(a.get("owner"), a.get("owner")),
                        "customer": _customer(c)["name"] or None, "call_title": c.title, "call_when": _when(c),
                        "due": a.get("due") or None, "due_date": d.isoformat() if d else None,
                        "overdue_days": (today - d).days if d and d < today else 0})
    out.sort(key=lambda p: (-p["overdue_days"], p["due_date"] or "9999"))
    return out


@tool("open_promises",
      "מה עוד לא בוצע מהשיחות: משימות שהסוכן התחייב אליהן (owner=agent) או שהלקוח התחייב (owner=customer), "
      "כולל מועד וכמה ימים עבר. 'מה הבטחתי ללקוחות ועוד לא עשיתי?'",
      {"owner": {"type": "string", "enum": ["agent", "customer", "all"]},
       "only_overdue": {"type": "boolean"}},
      category="calls", status_he="בודק מה הובטח ועוד פתוח")
async def open_promises(ctx, owner: str = "agent", only_overdue: bool = False):
    items = promises(await _calls(ctx), owner)
    if only_overdue:
        items = [p for p in items if p["overdue_days"] > 0]
    if not items:
        return {"promises": [], "note": "אין משימות פתוחות מהשיחות." if not only_overdue else "אין משימות שעבר המועד שלהן."}
    return {"promises": items[:25], "count": len(items), "overdue": sum(1 for p in items if p["overdue_days"] > 0)}


@tool("calls_stats",
      "תמונת מצב של השיחות בתקופה: כמה שיחות, לפי נושא, לפי מקור (טלפון/אתר) וכיוון, סנטימנט, "
      "אחוז הדיבור הממוצע של הסוכן, משימות פתוחות ושעבר מועדן, ולקוחות שדיברו איתם הכי הרבה.",
      {"days": {"type": "integer", "description": "כמה ימים אחורה (ברירת מחדל 30)"}},
      category="calls", status_he="מסכם את השיחות")
async def calls_stats(ctx, days: int = 30):
    from collections import Counter
    since = datetime.utcnow() - timedelta(days=max(1, int(days or 30)))
    rows = [c for c in await _calls(ctx, 2000) if (c.started_at or c.created_at) >= since]
    if not rows:
        return {"calls": 0, "note": f"אין שיחות ב-{days} הימים האחרונים."}
    pct = [r["agent_pct"] for c in rows if (r := (c.insights or {}).get("talk_ratio") or {}).get("agent_pct") is not None]
    who = Counter(_customer(c)["name"] for c in rows if _customer(c)["name"])
    prom = promises(rows, "agent")
    by_cat = Counter(c.category or "other" for c in rows).most_common()
    sent = Counter((c.insights or {}).get("sentiment") or "לא ידוע" for c in rows)
    SENT_HE = {"positive": "חיובית", "neutral": "ניטרלית", "negative": "שלילית", "mixed": "מעורבת"}
    # chartable rows (render_chart / the automatic chart): topics first — the question is
    # almost always "על מה מדברים" — then sentiment; kept LAST = the default chart
    sent_rid = ctx.keep([{"label": SENT_HE.get(k, k), "value": n} for k, n in sent.most_common()],
                        label="סנטימנט", value="שיחות", unit="", title=f"סנטימנט השיחות — {days} ימים", chart="donut")
    topic_rid = ctx.keep([{"label": CAT.label(k), "value": n} for k, n in by_cat],
                         label="נושא", value="שיחות", unit="", title=f"על מה מדברים — {len(rows)} שיחות ב-{days} ימים", chart="donut")
    return {
        "result_id": topic_rid, "sentiment_result_id": sent_rid,
        "days": days, "calls": len(rows),
        "minutes": round(sum((c.duration_s or 0) for c in rows) / 60),
        "by_category": {CAT.label(k): n for k, n in by_cat},
        "by_source": dict(Counter(SOURCE_HE.get(c.source or "widget") for c in rows)),
        "by_direction": dict(Counter({"in": "נכנסת", "out": "יוצאת"}.get(c.direction or "", "לא ידוע") for c in rows)),
        "sentiment": dict(Counter((c.insights or {}).get("sentiment") or "לא ידוע" for c in rows)),
        "agent_talk_pct_avg": round(sum(pct) / len(pct)) if pct else None,
        "open_agent_tasks": len(prom), "overdue_agent_tasks": sum(1 for p in prom if p["overdue_days"] > 0),
        "top_customers": who.most_common(5),
    }


@tool("mark_call_task_done",
      "סימון משימה משיחה כבוצעה (call_id + task_index מ-get_call או open_promises). מוכן לאישור הסוכן — לא מסומן עד שהוא מאשר.",
      {"call_id": {"type": "string"}, "task_index": {"type": "integer"}}, ["call_id", "task_index"],
      category="calls", status_he="מכין סימון משימה", action=True)
async def mark_call_task_done(ctx, call_id: str, task_index: int):
    import uuid as _uuid
    try:
        cid = _uuid.UUID(str(call_id))
    except ValueError:
        return "מזהה שיחה לא תקין."
    c = (await ctx.db.execute(select(CallRecording).where(
        CallRecording.id == cid, CallRecording.user_id == ctx.user.id, visible()))).scalar_one_or_none()
    items = ((c.insights or {}).get("action_items") or []) if c else []
    if not c or not 0 <= task_index < len(items):
        return "לא נמצאה משימה כזו — קח call_id ו-task_index מ-open_promises."
    if items[task_index].get("done"):
        return "המשימה כבר מסומנת כבוצעה."
    ctx.proposals.append({"kind": "call_task", "call_id": str(c.id), "task_index": task_index,
                          "text": items[task_index].get("text"), "customer": _customer(c)["name"], "call_title": c.title})
    return "הוכן לאישור הסוכן. כתוב משפט אחד."



@tool("pending_followups",
      "סיכומי שיחה שהוכנו ללקוחות ועוד לא נשלחו (ולא סומנו כטופל): לקוח, מייל, נושא, מתי. 'איזה סיכומים לא שלחתי?'",
      category="calls", status_he="בודק סיכומים שלא נשלחו")
async def pending_followups(ctx):
    rows = [c for c in await _calls(ctx) if ((c.insights or {}).get("followup") or {}).get("status") == "ready"]
    if not rows:
        return {"followups": [], "note": "אין סיכומי שיחה שמחכים לשליחה."}
    out = [{"call_id": str(c.id), "when": _when(c), "customer": _customer(c)["name"] or None,
            "email": _customer(c)["email"] or None, "subject": (c.insights["followup"].get("subject") or c.title)}
           for c in rows[:20]]
    return {"followups": out, "count": len(rows), "note": "שליחה: הסוכן מאשר בכרטיס של Nifra Agent (לסיכום שהכנתי)."}


@tool("calls_with_unpaid",
      "הצלבה: לקוחות שדיברת איתם בשיחות ושיש להם גם עמלות שלא שולמו — לקוח, חברה, צפי שלא שולם, ומתי השיחה האחרונה ועל מה. "
      "'למי מהלקוחות שדיברתי איתם יש חוב?', 'מי מחייבי מנורה דיבר איתי?'.",
      {"company": {"type": "string", "description": "לצמצם לחברה אחת, או ריק"}},
      category="calls", status_he="מצליב שיחות מול עמלות שלא שולמו")
async def calls_with_unpaid(ctx, company: str = ""):
    # ONE source with get_unpaid: the same per-company unpaid lists (partial gaps included)
    from app.api import comparison
    from app.services.agent.tools_data import _cached, _match_company, get_unpaid
    last_call: dict = {}
    for c in await _calls(ctx):
        idn = (_customer(c)["id_number"] or "").lstrip("0")
        if idn and idn not in last_call:
            last_call[idn] = c
    if not last_call:
        return {"customers": [], "note": "עוד אין שיחות שמקושרות ללקוח."}
    overall = await get_unpaid(ctx)
    gaps: dict = {}
    for co in overall.get("by_company") or []:
        if company and not _match_company(co["label"], company):
            continue
        # the FULL list (get_unpaid shows the top 50 — Phoenix has 188), same cached source
        d = await _cached(ctx, ("company_unpaid", co["label"]),
                          lambda co=co: comparison.company_unpaid(company=co["label"], db=ctx.db, user=ctx.user))
        for row in d.get("customers") or []:
            idn = str(row.get("id_number") or "").lstrip("0")
            if idn in last_call and float(row.get("expected") or 0) >= 0.5:
                gaps.setdefault(idn, {"customer": row.get("name") or idn, "unpaid": []})["unpaid"].append(
                    {"company": co["label"], "missing": round(float(row["expected"])), "kind": "לא שולם כלל"})
    # partial payments too — the card's "חסר ₪X" (paid less than expected), same rule as agent_insights
    from app.services.agent_insights import suspicious
    m = await ctx.map()
    for cu in m.customers:
        idn = str(cu.get("id_number") or "").lstrip("0")
        if idn not in last_call:
            continue
        for p in cu.get("commission_products") or []:
            co = p.get("company") or p.get("company_full") or ""
            paid, exp = float(p.get("commission") or 0), float(p.get("expected_commission") or 0)
            if company and not _match_company(co, company):
                continue
            if exp - paid > 1 and not suspicious(paid, exp):
                name = " ".join(x for x in (cu.get("first_name"), cu.get("last_name")) if x) or idn
                gaps.setdefault(idn, {"customer": name, "unpaid": []})["unpaid"].append(
                    {"company": co, "expected": round(exp), "paid": round(paid), "missing": round(exp - paid), "kind": "חלקי"})
    out = []
    for idn, g in gaps.items():
        c = last_call[idn]
        out.append({**g, "id_number": idn, "last_call": _when(c), "call_title": c.title, "call_id": str(c.id)})
    if not out:
        return {"customers": [], "note": "אף לקוח שדיברת איתו בשיחה לא מופיע ברשימות הלא-משולמים" + (f" של {company}." if company else ".")}
    return {"customers": sorted(out, key=lambda r: -sum(u["missing"] for u in r["unpaid"])), "count": len(out)}
