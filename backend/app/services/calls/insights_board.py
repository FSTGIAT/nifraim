"""Nifra Insights board — what the agent's calls are about, products first.

Every number here is counted by code from call_recordings.insights. Claude does two things
only, once per change in the calls (cached in calls_insights_cache by `fingerprint`):
  1. groups the free-text products/topics ("קופת גמל להשקעה", "גמל להשקעה", "הטבות מס בגמל")
     into 6–12 themes — it may only use strings it was given;
  2. writes a short analyst read of the FACTS we computed — a sentence carrying a number
     that isn't in the facts is dropped.
Until the pass is ready the board groups by the raw product names (themes_status=computing).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.models.call_recording import CallRecording
from app.models.calls_insights import CallsInsightsCache
from app.services.agent.tools_calls import IL, _customer, promises
from app.services.calls import categories as CAT
from app.services.calls.reminders import task_when
from app.utils.company_norm import known_company_stem

logger = logging.getLogger(__name__)
SENT = ("positive", "neutral", "negative", "mixed")
UNKNOWN_CUSTOMER = "לקוח לא מזוהה"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r'[\'"`׳״]', "", s or "")).strip()


def _strings(c: CallRecording) -> list[str]:
    ins = c.insights or {}
    return [_norm(x) for x in (ins.get("products_mentioned") or []) + (ins.get("topics") or []) if _norm(x)]


def fingerprint(rows: list[CallRecording]) -> str:
    """Changes when what the calls are ABOUT changes — not when a task is ticked."""
    keys = sorted(
        (str(c.id), sorted(_strings(c)), sorted((c.insights or {}).get("companies_mentioned") or []),
         sorted((c.insights or {}).get("objections") or []), sorted((c.insights or {}).get("customer_needs") or []))
        for c in rows)
    return hashlib.sha1(json.dumps(keys, ensure_ascii=False).encode()).hexdigest()


def customer_key(c: CallRecording) -> tuple[str, str]:
    """(key, name) — ONE identity for a call's customer, used by the board AND the header count."""
    cu, ins = _customer(c), c.insights or {}
    name = cu["name"] or ins.get("customer_name") or UNKNOWN_CUSTOMER
    return (cu["id_number"] or "").lstrip("0") or (name if name != UNKNOWN_CUSTOMER else UNKNOWN_CUSTOMER), name


def _call_day(c: CallRecording) -> date | None:
    at = c.started_at or c.created_at
    return at.replace(tzinfo=timezone.utc).astimezone(IL).date() if at else None


def _themes_of(c: CallRecording, themes: list[dict] | None) -> list[str]:
    """Which themes a call belongs to. No cached themes → its own product names (products first);
    a call that names no product → its category."""
    mine = set(_strings(c))
    if themes:
        hit = [t["name"] for t in themes if mine & set(t.get("members") or [])]
        if hit:
            return hit
    prods = [_norm(x) for x in (c.insights or {}).get("products_mentioned") or [] if _norm(x)]
    if prods and not themes:
        return list(dict.fromkeys(prods))
    return [CAT.label(c.category)]


def build(rows: list[CallRecording], themes: list[dict] | None, narrative: list[str] | None,
          days: int = 0, today: date | None = None) -> dict:
    """Pure — tests feed SimpleNamespace rows. rows = ALL visible done calls; `days` filters."""
    from app.services.agent.tools_calls import _today
    today = today or _today()
    if days:
        rows = [c for c in rows if (_call_day(c) or today) >= today - timedelta(days=days)]
    tasks_by_call: dict[str, list[dict]] = {}
    for p in promises(rows, "agent", today):
        tasks_by_call.setdefault(p["call_id"], []).append(p)

    boards: dict[str, dict] = {}
    for c in rows:
        ins = c.insights or {}
        cu = _customer(c)
        ckey, cname = customer_key(c)
        insurers = [s for s in (known_company_stem(x) for x in ins.get("companies_mentioned") or []) if s]
        others = [_norm(x) for x in ins.get("companies_mentioned") or [] if not known_company_stem(x)]
        tasks = []
        for p in tasks_by_call.get(str(c.id), []):
            a = (ins.get("action_items") or [])[p["task_index"]]
            d, t = task_when(a)
            tasks.append({"call_id": p["call_id"], "task_index": p["task_index"], "text": p["text"],
                          "due_date": d or None, "due_time": t or None, "overdue_days": p["overdue_days"]})
        for th in _themes_of(c, themes):
            b = boards.setdefault(th, {"theme": th, "fallback": th in CAT.CATEGORIES.values(), "call_ids": [], "customers": {}, "insurers": Counter(),
                                       "others": Counter(), "sentiment": Counter(), "open": 0, "overdue": 0})
            b["call_ids"].append(str(c.id))
            b["insurers"].update(set(insurers))
            b["others"].update(set(others))
            if ins.get("sentiment") in SENT:
                b["sentiment"][ins["sentiment"]] += 1
            b["open"] += len(tasks)
            b["overdue"] += sum(1 for t in tasks if t["overdue_days"] > 0)
            cust = b["customers"].setdefault(ckey, {"key": ckey, "name": cname, "id_number": cu["id_number"] or None,
                                                    "insurers": [], "tasks": [], "call_ids": []})
            cust["call_ids"].append(str(c.id))
            cust["insurers"] = list(dict.fromkeys(cust["insurers"] + insurers))
            cust["tasks"] += tasks

    products = []
    for b in boards.values():
        custs = sorted(b["customers"].values(), key=lambda x: (x["name"] == UNKNOWN_CUSTOMER, -len(x["call_ids"]), x["name"]))
        products.append({
            "theme": b["theme"], "fallback": b["fallback"], "calls": len(b["call_ids"]), "call_ids": b["call_ids"],
            "customers": custs, "insurers": [k for k, _ in b["insurers"].most_common()],
            "others": [k for k, _ in b["others"].most_common()],
            "sentiment": {k: b["sentiment"].get(k, 0) for k in SENT}, "open": b["open"], "overdue": b["overdue"],
        })
    # a call's category ("אחר", "שירות / בירור") is where unthemed calls land — after the real products
    products.sort(key=lambda p: (p["fallback"], -p["calls"], -p["open"], p["theme"]))
    calls = {str(c.id): {"title": c.title, "tldr": (c.insights or {}).get("tldr"), "when": (_call_day(c) or today).isoformat(),
                         "sentiment": (c.insights or {}).get("sentiment"),
                         "customer": _customer(c)["name"] or (c.insights or {}).get("customer_name") or None}
             for c in rows}
    return {"products": products, "calls": calls, "stats": stats(rows, products, today), "narrative": narrative or []}


def stats(rows: list[CallRecording], products: list[dict], today: date) -> dict:
    n = len(rows)
    agent_open = promises(rows, "agent", today)
    customer_open = promises(rows, "customer", today)
    agent_all = [a for c in rows for a in (c.insights or {}).get("action_items") or [] if a.get("owner") == "agent"]
    customers = Counter(customer_key(c)[0] for c in rows)
    customers.pop(UNKNOWN_CUSTOMER, None)
    ins_calls: dict[str, list[str]] = {}
    for c in rows:
        for s in {known_company_stem(x) for x in (c.insights or {}).get("companies_mentioned") or []}:
            if s:
                ins_calls.setdefault(s, []).append(str(c.id))
    insurers = Counter({k: len(v) for k, v in ins_calls.items()})
    objecting = {customer_key(c)[0] for c in rows if (c.insights or {}).get("objections")} - {UNKNOWN_CUSTOMER}
    sent = Counter((c.insights or {}).get("sentiment") for c in rows if (c.insights or {}).get("sentiment") in SENT)
    top = products[0] if products else None
    return {
        "calls": n, "customers": len(customers),
        "repeat_customers": sum(1 for v in customers.values() if v > 1),
        "top_theme": {"theme": top["theme"], "calls": top["calls"], "pct": round(100 * top["calls"] / n)} if top and n else None,
        "insurers": [{"name": k, "calls": v, "call_ids": ins_calls[k]} for k, v in insurers.most_common(8)],
        "sentiment": {k: sent.get(k, 0) for k in SENT},
        "agent_tasks": len(agent_all), "agent_done": sum(1 for a in agent_all if a.get("done")),
        "agent_open": len(agent_open), "overdue": sum(1 for p in agent_open if p["overdue_days"] > 0),
        "undated": sum(1 for p in agent_open if not p["due_date"]),
        "customer_open": len(customer_open),
        "objecting_customers": len(objecting),
        "needs": sum(len((c.insights or {}).get("customer_needs") or []) for c in rows),
    }


# ───────────────────────── the cached Claude pass ─────────────────────────

THEMES_TOOL = {
    "name": "calls_themes",
    "description": "קיבוץ מוצרים ונושאים משיחות לנושאים, וקריאה של אנליסט",
    "input_schema": {
        "type": "object",
        "properties": {
            "themes": {"type": "array", "minItems": 1, "maxItems": 12, "items": {"type": "object", "properties": {
                "name": {"type": "string", "description": "שם מוצר/נושא קצר, 1–3 מילים, כמו שסוכן אומר ('פנסיה', 'קרן השתלמות', 'גמל להשקעה')"},
                "members": {"type": "array", "items": {"type": "string"}, "description": "המחרוזות מהרשימה בדיוק כפי שנכתבו"},
            }, "required": ["name", "members"]}},
            "narrative": {"type": "array", "maxItems": 5, "items": {"type": "string"},
                          "description": "3–5 תובנות קצרות של אנליסט לסוכן, משפט אחד כל אחת"},
        },
        "required": ["themes", "narrative"],
    },
}

SYSTEM = """אתה אנליסט עסקי של סוכנות ביטוח ופנסיה בישראל. קיבלת את מה שעלה בשיחות של הסוכן עם לקוחותיו.
1) themes: קבץ את המחרוזות (מוצרים ונושאים) ל-6–12 נושאים, מוצרים קודם (פנסיה, קרן השתלמות, גמל להשקעה, ביטוח מנהלים,
   ביטוח בריאות, ביטוח חיים, ניהול תיקים...). כל מחרוזת לנושא אחד לכל היותר; העתק אותן בדיוק. מחרוזת שלא שייכת לשום מוצר
   (תקלה טכנית, תמלול לא ברור) — אל תכניס.
2) narrative: 3–5 תובנות חדות, כמו אנליסט שמדבר עם הסוכן: הזדמנויות (מכירה צולבת, ניוד), סיכונים (התנגדויות, לקוח לא מרוצה),
   ומה לעשות השבוע. מספרים — רק מתוך העובדות שקיבלת, תמיד בספרות (11, לא "אחד-עשר"), בלי לחשב חדשים ובלי אחוזים.
   בלי מספרי שיחות לנושא. בלי שמות לקוחות.
   עברית, עד 22 מילים לתובנה."""


def narrative_facts(st: dict) -> dict:
    """The numbers the analyst may quote — only ones that DON'T depend on how topics get grouped
    (a theme's share is computed after the grouping, so the panel shows it, never the narrative)."""
    return {k: ([{"name": i["name"], "calls": i["calls"]} for i in v] if k == "insurers" else v)
            for k, v in st.items() if k != "top_theme"}


def _facts_numbers(facts: dict) -> set[str]:
    out: set[str] = set()

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            out.add(str(int(v)) if float(v).is_integer() else str(v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(facts)
    return out


_NUMBER_WORDS = re.compile(r"(?<![א-ת])(שתיים|שניים|שלוש|ארבע|חמש|שש|שבע|שמונה|תשע|עשר|עשרים|שלושים|ארבעים|חמישים|שישים|שבעים|שמונים|תשעים|מאה)")


def guard_narrative(lines: list[str], facts: dict) -> list[str]:
    """Drop any sentence carrying a number the facts don't contain — the analyst may not do math.
    A count spelled out in words ("שישים משימות") can't be checked, so it's dropped too."""
    ok = _facts_numbers(facts)
    keep = []
    for ln in lines or []:
        ln = (ln or "").strip()
        if ln and all(n in ok for n in re.findall(r"\d+(?:\.\d+)?", ln)) and not _NUMBER_WORDS.search(ln):
            keep.append(ln)
    return keep[:5]


def clean_themes(themes, allowed: set[str]) -> list[dict]:
    out, used = [], set()
    for t in themes if isinstance(themes, list) else []:
        name = re.sub(r"\s+", " ", (t or {}).get("name") or "").strip()[:40]   # keep אכ"ע quotes
        members = [m for m in (_norm(x) for x in (t or {}).get("members") or []) if m in allowed and m not in used]
        if name and members:
            used.update(members)
            out.append({"name": name, "members": members})
    return out[:12]


async def compute(rows: list[CallRecording]) -> tuple[list[dict], list[str], str]:
    """One Claude pass → (themes, narrative, model). Raises LlmUnavailable."""
    from app.services.calls.summarize import MODELS
    from app.services.mail_agent.llm import call_tool
    strings = Counter(s for c in rows for s in set(_strings(c)))
    facts = narrative_facts(build(rows, None, None)["stats"])
    objections = [o for c in rows for o in (c.insights or {}).get("objections") or []]
    needs = [o for c in rows for o in (c.insights or {}).get("customer_needs") or []]
    user = ("מחרוזות (מחרוזת × מספר שיחות):\n" + "\n".join(f"- {s} × {n}" for s, n in strings.most_common(80)) +
            "\n\nהתנגדויות שעלו:\n" + "\n".join(f"- {o}" for o in objections[:40]) +
            "\n\nצרכים שעלו:\n" + "\n".join(f"- {o}" for o in needs[:40]) +
            "\n\nעובדות (המספרים היחידים שמותר להשתמש בהם):\n" + json.dumps(facts, ensure_ascii=False))
    out, model, _u = await call_tool(models=MODELS, system=SYSTEM, user=user, tool=THEMES_TOOL, max_tokens=2000)
    themes = clean_themes(out.get("themes"), set(strings))
    narrative = guard_narrative(out.get("narrative") or [], facts)
    return themes, narrative, model


_running: set = set()
_tasks: set = set()              # strong refs — asyncio may collect an unreferenced task mid-run
_failed_at: dict = {}            # user_id → monotonic time of the last failed pass (no retry storm)
RETRY_AFTER_S = 600


async def refresh(user_id, fp: str) -> None:
    """Background: recompute the user's themes once; one pass per user at a time."""
    from app.database import async_session
    from app.services.calls.privacy import visible
    if user_id in _running:
        return
    _running.add(user_id)
    try:
        async with async_session() as db:
            rows = (await db.execute(select(CallRecording).where(
                CallRecording.user_id == user_id, CallRecording.status == "done", visible()))).scalars().all()
            themes, narrative, model = await compute(rows)
            if not themes and not narrative:   # nothing usable — don't freeze an empty answer as "ready"
                raise RuntimeError("theme pass returned nothing usable")
            row = await db.get(CallsInsightsCache, user_id)
            if row is None:
                row = CallsInsightsCache(user_id=user_id, fingerprint=fp)
                db.add(row)
            row.fingerprint, row.themes, row.narrative, row.model = fp, themes, "\n".join(narrative), model
            row.computed_at = datetime.utcnow()
            await db.commit()
    except Exception:
        import time as _t
        _failed_at[user_id] = _t.monotonic()
        logger.exception("calls insights: theme pass failed for %s", user_id)
    finally:
        _running.discard(user_id)


def schedule_refresh(user_id, fp: str) -> str:
    """→ themes_status: computing (a pass is running) | unavailable (last pass failed recently)."""
    import time as _t
    if user_id in _running:
        return "computing"
    if _t.monotonic() - _failed_at.get(user_id, -1e9) < RETRY_AFTER_S:
        return "unavailable"
    task = asyncio.get_running_loop().create_task(refresh(user_id, fp))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return "computing"
