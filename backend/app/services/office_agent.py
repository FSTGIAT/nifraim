"""The office agent ("סוכן המשרד") — the agent's back-office AI that talks first.

It does not own new data. It SPEAKS for two workers that already exist:

    Mail Agent (services/mail_agent)   — every mail from a watched sender, triaged:
        summary · category · suggested action · AI draft reply
    Collection agent (collection_agent) — per insurer: unpaid customers, the
        draft to the insurer, reply follow-up, the 7-day reminder

and turns them into ONE short brief: a greeting, then cards ordered by what
needs the agent most, each with its action (send the draft / import the file /
approve the insurer mail / remind / done). Straight to the point, no long chat;
`ask()` answers a short question in ≤3 sentences from the agent's own data.

Every send is still the agent's click on the existing endpoints (mail-agent
/items/{id}/send, collection-agent /cases/{id}/send). Decided 2026-09-29.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.mail_item import OPEN_STATUSES, MailItem
from app.models.user import User
from app.services import collection_agent

logger = logging.getLogger(__name__)
IL = ZoneInfo("Asia/Jerusalem")
MAIL_WINDOW = timedelta(days=14)

CATEGORY_LABEL = {
    "commission_reply": "תשובה מחברה",
    "report_file": "קובץ דוח",
    "customer_question": "שאלת לקוח",
    "info": "עדכון",
    "other": "מייל",
}
# lower = more urgent
PRIORITY = {
    ("unpaid", "read"): 0, ("mail", "customer_question"): 1, ("unpaid", "remind"): 2,
    ("mail", "commission_reply"): 3, ("unpaid", "approve"): 4, ("mail", "report_file"): 5,
    ("unpaid", "contact"): 6, ("mail", "other"): 7, ("mail", "info"): 8, ("unpaid", "wait"): 9,
}


def greeting(now: datetime, user: User) -> str:
    h = now.astimezone(IL).hour
    part = "בוקר טוב" if 5 <= h < 12 else "צהריים טובים" if h < 17 else "ערב טוב" if h < 22 else "לילה טוב"
    first = (user.full_name or "").split(" ")[0]
    return f"{part}{', ' + first if first else ''}"


def _ago(ts: datetime | None, now: datetime) -> str:
    if not ts:
        return ""
    d = now - ts
    if d < timedelta(hours=1):
        return "עכשיו"
    if d < timedelta(days=1):
        return f"לפני {int(d.total_seconds() // 3600)} שע׳"
    return f"לפני {d.days} ימים" if d.days > 1 else "אתמול"


def mail_card(item: MailItem, now: datetime) -> dict:
    cat = item.category or "other"
    actions = []
    if item.suggested_action == "import_file":
        actions.append("import")
    elif item.draft_body:
        actions.append("send_reply")
    elif item.suggested_action == "reply":
        actions.append("make_draft")
    actions.append("done")
    who = item.from_name or item.from_address
    return {
        "id": f"mail:{item.id}", "kind": "mail", "ref": str(item.id), "sub": cat,
        "priority": PRIORITY.get(("mail", cat), 7),
        "title": who,
        "text": item.summary or item.subject or "מייל חדש",
        "meta": " · ".join(x for x in (CATEGORY_LABEL.get(cat, "מייל"), item.linked_company, _ago(item.received_at, now)) if x),
        "subject": item.subject,
        "draft_subject": item.draft_subject, "draft_body": item.draft_body,
        "actions": actions,
    }


def unpaid_card(c: dict) -> dict:
    kind = c["next"]["kind"]
    actions = {
        "approve": ["send_case"], "contact": ["set_email"], "remind": ["remind"],
        "read": ["resolve"], "wait": [], "done": [],
    }.get(kind, [])
    exp = round(c["expected"] or 0)
    return {
        "id": f"unpaid:{c['id']}", "kind": "unpaid", "ref": c["id"], "sub": kind,
        "priority": PRIORITY.get(("unpaid", kind), 9),
        "title": f"{c['company']} — עמלות שלא שולמו",
        "text": c["next"]["text"],
        "meta": f"{c['customers']} לקוחות · ₪{exp:,} צפי",
        "to_email": c["to_email"],
        "draft_subject": c["draft_subject"], "draft_body": c["draft_body"],
        "policies": len(c["items"]),
        "actions": actions,
    }


async def brief(db: AsyncSession, user: User) -> dict:
    now = datetime.now(timezone.utc)
    naive = now.replace(tzinfo=None)
    await collection_agent.refresh_cases(db, user)
    coll = await collection_agent.brief(db, user)
    mails = (await db.execute(
        select(MailItem).where(
            MailItem.user_id == user.id, MailItem.status.in_(OPEN_STATUSES),
            MailItem.received_at >= naive - MAIL_WINDOW,
        ).order_by(MailItem.received_at.desc()).limit(20)
    )).scalars().all()
    cards = [mail_card(m, naive) for m in mails]
    cards += [unpaid_card(c) for c in coll["cases"] if c["status"] != "resolved"]
    cards.sort(key=lambda c: c["priority"])
    todo = [c for c in cards if c["actions"]]
    if todo:
        headline = f"יש {len(todo)} דברים שמחכים לך" if len(todo) > 1 else "יש דבר אחד שמחכה לך"
    else:
        headline = "הכל מטופל — אין כרגע משהו שמחכה לך"
    return {
        "greeting": greeting(now, user),
        "headline": headline,
        "todo_count": len(todo),
        "mailbox": coll["mailbox"],
        "unpaid": {"period_label": coll["period_label"], "open": coll["open_count"],
                   "customers": coll["customers"], "expected": coll["expected"]},
        "cards": cards,
    }


ASK_SYSTEM = (
    "אתה סוכן המשרד של סוכן ביטוח: עוזר back-office. יש לך מפה של הנתונים שלו כאתר Markdown קטן: "
    "index.md מחולק לקטגוריות עם קישורים, ואפשר לרדת לעומק עם הכלי open_page (חברה → לקוח → מייל). "
    "לפני שאתה עונה — פתח את הדפים שרלוונטיים לשאלה (לרוב 1–3 דפים), עקוב אחרי הקישורים כדי לחבר בין הנתונים. "
    "ענה בעברית, ישר לעניין, עד 3 משפטים קצרים בטקסט רגיל — בלי Markdown, בלי כוכביות ובלי כותרות — "
    "וסיים בצעד אחד שהסוכן צריך לעשות. שם של לקוח בלי ת.ז — חפש עם search/<שם>.md. "
    "השתמש רק במה שמופיע בדפים; אם אין — אמור זאת בקצרה. אל תמציא סכומים או שמות."
)
OPEN_PAGE_TOOL = {
    "name": "open_page",
    "description": "פתיחת דף במפת הנתונים של הסוכן (Markdown). נתיבים כמו index.md, companies.md, companies/<key>.md, customers/<ת.ז>.md, search/<שם>.md, unpaid.md, mail.md, agreements.md — בדיוק כפי שמופיעים בקישורים.",
    "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
}
MAX_HOPS = 5


async def ask(db: AsyncSession, user: User, question: str) -> str:
    """Answer a short question by navigating the data map (services/data_map):
    the model starts from index.md and opens linked pages until it can answer."""
    from app.services import data_map

    ctx = await data_map.load(db, user)
    index = data_map.render(ctx, "index.md")
    if not settings.ANTHROPIC_API_KEY:
        return index.splitlines()[0]
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        messages = [{"role": "user", "content": f"index.md:\n{index}\n\nשאלה: {question[:500]}"}]
        for _ in range(MAX_HOPS):
            r = await client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=400, system=ASK_SYSTEM,
                tools=[OPEN_PAGE_TOOL], messages=messages,
            )
            if r.stop_reason != "tool_use":
                return "".join(x.text for x in r.content if getattr(x, "type", "") == "text").strip() or "אין לי תשובה כרגע."
            # plain dicts — re-sending the SDK's block objects trips its serializer
            blocks = []
            for blk in r.content:
                if getattr(blk, "type", "") == "text":
                    blocks.append({"type": "text", "text": blk.text})
                elif getattr(blk, "type", "") == "tool_use":
                    blocks.append({"type": "tool_use", "id": blk.id, "name": blk.name, "input": dict(blk.input or {})})
            messages.append({"role": "assistant", "content": blocks})
            results = []
            for blk in r.content:
                if getattr(blk, "type", "") == "tool_use":
                    page = data_map.render(ctx, (blk.input or {}).get("path", "index.md"))
                    results.append({"type": "tool_result", "tool_use_id": blk.id, "content": page[:6000]})
            messages.append({"role": "user", "content": results})
        return "בדקתי כמה דפים ולא הגעתי לתשובה חד-משמעית — נסו לשאול בצורה ממוקדת יותר."
    except Exception as e:  # noqa: BLE001
        logger.warning("office agent ask failed: %s", e)
        return "לא הצלחתי לענות כרגע — נסו שוב בעוד רגע."


# ─────────────────────────── the written brief (Nifra Agent speaks) ────────

NARRATE_SYSTEM = (
    "אתה Nifra Agent — הסוכן האישי של סוכן ביטוח, שעובד בשבילו על המיילים והעמלות. "
    "כתוב לו תדריך קצר בגוף ראשון, חם וישיר, בטקסט רגיל בלי Markdown. "
    "החזר JSON בלבד: {\"lines\":[{\"text\":\"...\",\"ref\":\"<id של פריט או null>\"}]} "
    "עד 5 שורות, כל שורה משפט אחד קצר (עד 16 מילים): מה הגיע / מה מחכה, ומה כדאי לעשות. "
    "הכי דחוף ראשון. אחד-לאחד מול הפריטים שקיבלת — אל תמציא, ובמיוחד אל תמציא זמנים, דדליינים או סכומים. "
    "השתמש בפעולה המוצעת כפי שהיא כתובה (למשל 'לאשר ולשלוח את הפנייה'). פריט שכבר נענה/אושר — אמור בקצרה מה קרה. "
    "אם אין כלום — שורה אחת שהכל מטופל."
)
ACTION_HE = {
    "send_reply": "לשלוח את התשובה שהכנתי", "make_draft": "להכין טיוטת תשובה", "import": "לטעון את הקובץ",
    "done": "לסמן כטופל", "send_case": "לאשר ולשלוח את הפנייה לחברה", "set_email": "להוסיף מייל של איש קשר",
    "remind": "לשלוח תזכורת", "resolve": "לסמן כטופל",
}
_brief_cache: dict = {}   # user_id -> (signature, payload)


def _fallback_lines(cards: list[dict]) -> list[dict]:
    out = []
    for c in cards[:5]:
        out.append({"text": f"{c['title']}: {c['text']}", "ref": c["id"]})
    return out or [{"text": "הכל מטופל — אין כרגע משהו שמחכה לך.", "ref": None}]


async def narrate(db: AsyncSession, user: User) -> dict:
    """Greeting + ≤5 written lines (each may point at a card = its action).
    Cached per user until the underlying cards change."""
    import json

    b = await brief(db, user)
    cards = b["cards"]
    sig = "|".join(f"{c['id']}:{c['sub']}:{c['text']}" for c in cards)
    hit = _brief_cache.get(user.id)
    if hit and hit[0] == sig:
        return {**hit[1], "cards": cards, "mailbox": b["mailbox"]}
    lines = _fallback_lines(cards)
    if settings.ANTHROPIC_API_KEY and cards:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            items = "\n".join(
                f"- id={c['id']} | {c['title']} | {c['text']} | {c['meta']} | פעולה מוצעת: "
                + (", ".join(ACTION_HE.get(a, a) for a in c['actions']) or "אין — רק לעדכן")
                for c in cards[:20]
            )
            r = await client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=500, system=NARRATE_SYSTEM,
                messages=[{"role": "user", "content": f"הפריטים:\n{items}"}],
            )
            raw = "".join(x.text for x in r.content if getattr(x, "type", "") == "text").strip()
            raw = raw[raw.find("{"): raw.rfind("}") + 1]
            ids = {c["id"] for c in cards}
            parsed = [
                {"text": str(l.get("text", "")).strip()[:160], "ref": l.get("ref") if l.get("ref") in ids else None}
                for l in (json.loads(raw).get("lines") or []) if str(l.get("text", "")).strip()
            ][:5]
            lines = parsed or lines
        except Exception as e:  # noqa: BLE001 — the deterministic lines still say it
            logger.warning("nifra agent narrate failed: %s", e)
    payload = {"greeting": b["greeting"], "lines": lines, "todo_count": b["todo_count"]}
    _brief_cache[user.id] = (sig, payload)
    return {**payload, "cards": cards, "mailbox": b["mailbox"]}
