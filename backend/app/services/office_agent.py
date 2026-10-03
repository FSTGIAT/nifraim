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
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.mail_item import OPEN_STATUSES, MailItem
from app.models.user import User
from app.services import collection_agent

logger = logging.getLogger(__name__)
# one line per Nifra Agent turn — uvicorn's logger is the one that reaches the server log
trace = logging.getLogger("uvicorn.error")
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
    ("call", "followup"): 0.5,
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


def call_card(call, customer: dict, followup: dict, now: datetime) -> dict:
    """A recorded call whose summary is ready — Nifra Agent offers the customer-facing
    follow-up it drafted. Sending is still the agent's click (POST /calls/{id}/followup/send)."""
    at = call.created_at.replace(tzinfo=timezone.utc).astimezone(IL).strftime("%H:%M") if call.created_at else ""
    who = (customer or {}).get("name") or ""
    return {
        "id": f"call:{call.id}", "kind": "call", "ref": str(call.id), "sub": "followup",
        "priority": PRIORITY[("call", "followup")],
        "title": f"סיכום הפגישה בשעה {at}" if at else "סיכום פגישה",
        "text": (call.insights or {}).get("tldr") or call.title or "סיכום השיחה מוכן",
        "meta": " · ".join(x for x in (who, call.title, _ago(call.done_at, now)) if x),
        "at": at, "call_title": call.title,
        "to_email": (customer or {}).get("email") or "", "to_name": who,
        "customer_matched": bool((customer or {}).get("matched")),
        "draft_subject": followup.get("subject"), "draft_body": followup.get("body"),
        "actions": ["send_followup", "dismiss_followup"],
    }


async def _call_cards(db: AsyncSession, user: User, naive: datetime) -> list[dict]:
    from app.models.call_recording import CallRecording
    rows = (await db.execute(
        select(CallRecording).where(
            CallRecording.user_id == user.id, CallRecording.status == "done",
            CallRecording.done_at >= naive - MAIL_WINDOW,
        ).order_by(CallRecording.done_at.desc()).limit(10)
    )).scalars().all()
    out = []
    for c in rows:
        f = (c.insights or {}).get("followup") or {}
        if f.get("status") == "ready" and f.get("body"):
            out.append(call_card(c, (c.insights or {}).get("customer") or {}, f, naive))
    return out


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
    cards += await _call_cards(db, user, naive)
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
    "אתה Nifra Agent — הסוכן האישי שעובד בשביל סוכן ביטוח. אתה לא רק עונה, אתה עושה: "
    "יש לך ידיים — propose_email מכין מייל, propose_meeting קובע פגישה (זימון יומן עם אישור/דחייה). "
    "הם לא שולחים לבד: הסוכן רואה את מה שהכנת ולוחץ אישור. לכן לעולם אל תגיד 'אני לא יכול לקבוע פגישה' או 'לשלוח מייל'. "
    "שאלה ('מה/מי/אילו/למה/האם…') = תשובה בלבד, בלי להכין פעולה. מכין מייל/פגישה רק כשביקשו במפורש לפעול (שלח, תכין, קבע, תזכיר, תענה). "
        "כשמבקשים ממך פעולה — עשה אותה מיד עם הכלי. הפרט היחיד שמותר לשאול עליו הוא כתובת המייל של הנמען, ורק אם אין לך אותה "
    "(בשיחה או בדפים). לעולם אל תשאל על שם, תוכן, אורך או ניסוח — אתה כותב את המייל בעצמך, קצר ומקצועי, בגוף ראשון של הסוכן. "
    "to_name — רק שם אמיתי שידוע לך; אחרת השאר ריק (לא 'לקוח'). "
    "תזכורת לסוכן עצמו ('תזכיר לי…') = propose_meeting אל המייל של הסוכן עצמו (מופיע למטה), 15 דקות, כותרת 'תזכורת: …'; 'בבוקר' = 09:00. "
    "כתובת מייל של לקוח שכתב לסוכן מופיעה בדפי המייל/החיפוש בתוך <…> — השתמש בה. "
    "'הלקוח הכי גדול/הגדולים' → top.md (ברירת מחדל: לפי צבירה, ואמור לפי מה דירגת). מילה קטועה או שגיאת כתיב — הבן לבד ואל תשאל. "
    "מייל 'עם מידע מפורט' ללקוח = פתח את דף הלקוח וכתוב את המוצרים שלו (חברה, מוצר, צבירה) מהדף בלבד. "
        "מפת היכולות: 'מה חסר ללקוח / כפל / מה להציע' → דף הלקוח (תמונת תיק) או crosssell.md; "
    "'למה העמלה נמוכה / איפה פער / האם קיבלתי עמלה על פוליסה X' → reconcile.md, policy/<מספר>.md; "
    "'מי בפיגור / בסכנת נטישה' → retention.md; 'מה פתוח לי היום' → tasks.md. "
    "אין לך נתוני שוק (תשואות, דמי ניהול בשוק, מסלולים מומלצים) ואין בקבצים תאריכי סיום פוליסה או תאריכי לידה — "
    "על שאלות כאלה אמור בפשטות שהנתון לא קיים אצלך, בלי להמציא ובלי לנחש. "
        "אל תיתן ייעוץ מקצועי משלך (מס, משפטי, סכומים שלא בדפים). כשיש טיוטת תשובה מוכנה — סכם אותה והצע לשלוח אותה. "
        "יום ושעה שהסוכן אמר — קובעים בדיוק אותם, בלי ויכוח ובלי הערות על חגים. נמען שהסוכן נתן — לא צריך לאמת אותו מול הנתונים. "
    "שעה שלא נאמרה — הצע בעצמך את יום העבודה הקרוב ב-10:00, 30 דקות (ימים א-ה); אל תשאל על זה. "
    "כותרת ברירת מחדל: 'פגישת היכרות' ללקוח חדש, אחרת לפי ההקשר. "
    "יש לך גם מפה של הנתונים שלו כאתר Markdown: index.md מחולק לקטגוריות עם קישורים, ואפשר לרדת לעומק עם open_page "
    "(חברה → לקוח → מייל). לשאלות על הנתונים — פתח את הדפים הרלוונטיים (1–3) לפני שאתה עונה. "
    "שם של לקוח בלי ת.ז — search/<שם>.md. השתמש רק במה שמופיע בדפים; אל תמציא סכומים או שמות. "
    "ענה בעברית, ישר לעניין, עד 3 משפטים קצרים בטקסט רגיל — בלי Markdown, בלי כוכביות ובלי רשימות. "
    "אחרי שהכנת פעולה — משפט אחד שאומר מה הכנת ושהיא מחכה לאישור שלו."
)
OPEN_PAGE_TOOL = {
    "name": "open_page",
    "description": "פתיחת דף במפת הנתונים של הסוכן (Markdown). נתיבים כמו index.md, companies.md, companies/<key>.md, customers/<ת.ז>.md, search/<שם>.md, unpaid.md, mail.md, agreements.md — בדיוק כפי שמופיעים בקישורים.",
    "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
}
MAX_HOPS = 7
# Sonnet, not Haiku: Haiku kept asking for details it didn't need instead of acting
ASK_MODEL = "claude-sonnet-5"


def _proposal_line(p: dict, own_email: str = "") -> str:
    from app.services.agent_actions import when_he
    if p["kind"] == "meeting" and own_email and p["to_email"].lower() == own_email.lower():
        return f"שמתי לך ביומן «{p['title']}» — {when_he(p['start'], p['duration_min'])}. מחכה לאישור שלך."
    who = p.get("to_name") or p["to_email"]
    to = "ל" + ("" if "\u0590" <= who[:1] <= "\u05ff" else "-") + who
    if p["kind"] == "meeting":
        return f"הכנתי זימון ל{p['title']} עם {who} — {when_he(p['start'], p['duration_min'])}. מחכה לאישור שלך."
    return f"הכנתי מייל {to}: «{p['subject']}». מחכה לאישור שלך."


async def ask(db: AsyncSession, user: User, question: str, history: list[dict] | None = None, mentions: list[dict] | None = None) -> dict:
    import time as _t
    t0 = _t.monotonic()
    out = await _ask(db, user, question, history, mentions)
    p = out.get("proposal")
    trace.info("NIFRA-ASK user=%s hist=%d @%d %.1fs | Q: %s | A: %s%s", user.email, len(history or []), len(mentions or []), _t.monotonic() - t0,
               question.replace("\n", " ")[:300], (out.get("answer") or "").replace("\n", " ")[:400],
               f" | PROPOSAL {p}" if p else "")
    return out


# Only an explicit ask to ACT unlocks the action tools. "אילו משימות פתוחות יש לי?"
# kept turning into a drafted email because the tasks page shows a ready draft.
ACTION_RE = re.compile(
    r"(?:^|[\s,.@])(?:ו|ש)?(?:ת?שלח|ת?כין|הכן|ת?קבע|קבע|ת?זמן|ת?זכיר|תענה|ענה|ת?כתוב|כתוב|ת?זיז|תשנה|שנה|ת?אשר|להכין|לשלוח|לקבוע|ת?בקש|לבקש|תגיש|להגיש)"
    r"|\b(?:send|email|mail|schedule|remind|draft|reply|book)\b",
    re.IGNORECASE,
)


def wants_action(question: str, history: list[dict] | None) -> bool:
    if ACTION_RE.search(question or ""):
        return True
    # a follow-up that answers the agent's question about a pending action ("הוא לקוח חדש, המייל…")
    users = [t.get("text") or "" for t in (history or []) if t.get("role") != "agent"]
    return bool(users) and bool(ACTION_RE.search(users[-1]))


async def _ask(db: AsyncSession, user: User, question: str, history: list[dict] | None = None, mentions: list[dict] | None = None) -> dict:
    """Answer — or ACT on — a short request. The model reads the data map
    (services/data_map) and may prepare ONE action (services/agent_actions):
    an email or a meeting invitation, returned as `proposal` for the agent to
    approve. `history` = the recent turns of this panel, so "לקוח" after
    "תקבע פגישה" is understood."""
    from app.services import agent_actions, data_map

    ctx = await data_map.load(db, user)
    index = data_map.render(ctx, "index.md")
    if not settings.ANTHROPIC_API_KEY:
        return {"answer": index.splitlines()[0], "proposal": None}
    now = datetime.now(IL)
    from app.services.agreement_requests import mailbox_state
    own_email = (await mailbox_state(db, user.id)).get("mailbox_address") or user.email
    system = ASK_SYSTEM + f" עכשיו: יום {agent_actions.HE_DAYS[now.weekday()]} {now:%Y-%m-%d %H:%M} (שעון ישראל). שם הסוכן: {user.full_name or ''}. המייל של הסוכן: {own_email}."
    messages: list[dict] = []
    for turn in (history or [])[-8:]:
        role = "assistant" if turn.get("role") == "agent" else "user"
        text = str(turn.get("text") or "").strip()[:1500]
        if text and (not messages or messages[-1]["role"] != role):
            messages.append({"role": role, "content": text})
        elif text:
            messages[-1]["content"] += "\n" + text
    if messages and messages[0]["role"] == "assistant":
        messages.insert(0, {"role": "user", "content": "שלום"})
    q = f"index.md:\n{index}\n\nבקשה: {question[:500]}"
    if mentions:
        await data_map.add_production_customers(db, ctx, [m.get("id_number") for m in mentions if m.get("id_number")])
        # the agent @-picked these from their contacts — exact, use them as given
        rows = []
        for m in mentions[:10]:
            bits = [str(m.get("name") or "")[:80]]
            if m.get("id_number"):
                bits.append(f"ת.ז {str(m['id_number'])[:12]} (customers/{str(m['id_number'])[:12]}.md)")
            if m.get("email"):
                bits.append(f"מייל {str(m['email'])[:120]}")
            bits.append({"customer": "לקוח", "company": "איש קשר בחברה", "mail": "שלח מייל"}.get(m.get("kind"), ""))
            rows.append(" · ".join(b for b in bits if b))
        q += "\nאנשי קשר שסומנו ב-@ (מדויקים):\n" + "\n".join("- " + r for r in rows)
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] += "\n" + q
    else:
        messages.append({"role": "user", "content": q})
    proposal = None
    nudged = False
    act = wants_action(question, history)
    tools = [OPEN_PAGE_TOOL, *agent_actions.TOOLS] if act else [OPEN_PAGE_TOOL]
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        for _ in range(MAX_HOPS):
            r = await client.messages.create(
                model=ASK_MODEL, max_tokens=2500, system=system,
                tools=tools, messages=messages,
            )
            text = "".join(x.text for x in r.content if getattr(x, "type", "") == "text").strip()
            if r.stop_reason != "tool_use":
                claims = act and not proposal and any(w in text for w in ("הכנתי", "מחכה לאישור", "מחכה לאישורך"))
                if claims and not nudged:
                    # it SAID it prepared something but never called the tool (or the call
                    # was cut off by max_tokens) — send it back once to actually do it
                    nudged = True
                    messages.append({"role": "assistant", "content": text or "…"})
                    messages.append({"role": "user", "content": "לא הכנת בפועל — לא קראת לכלי. קרא עכשיו ל-propose_email / propose_meeting עם הפרטים. גוף מייל עד 15 שורות."})
                    continue
                if claims:
                    text = "לא הצלחתי להכין את זה עד הסוף — נסו לבקש שוב בקצרה."
                return {"answer": text or ("הכנתי — מחכה לאישור שלך." if proposal else "אין לי תשובה כרגע."), "proposal": proposal}
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
                if getattr(blk, "type", "") != "tool_use":
                    continue
                args = dict(blk.input or {})
                if blk.name == "open_page":
                    content = data_map.render(ctx, args.get("path", "index.md"))[:6000]
                else:
                    kind = "email" if blk.name == "propose_email" else "meeting"
                    try:
                        proposal = agent_actions.normalize(kind, args)
                        content = "הוכן והוצג לסוכן לאישור. אל תכין שוב — כתוב משפט אחד."
                    except agent_actions.ActionError as e:
                        content = ("כתובת המייל לא תקינה — אמור לסוכן בדיוק איזו כתובת קיבלת ושהיא נראית שגויה, ובקש את הכתובת הנכונה. אל תכין בלי כתובת תקינה."
                                   if str(e) == "bad_email" else f"לא תקין ({e}).")
                results.append({"type": "tool_result", "tool_use_id": blk.id, "content": content})
            messages.append({"role": "user", "content": results})
            if proposal:
                return {"answer": _proposal_line(proposal, own_email), "proposal": proposal}
        return {"answer": "בדקתי כמה דפים ולא הגעתי לתשובה חד-משמעית — נסו לשאול בצורה ממוקדת יותר.", "proposal": proposal}
    except Exception as e:  # noqa: BLE001
        trace.warning("NIFRA-ASK failed: %r", e)
        return {"answer": "לא הצלחתי לענות כרגע — נסו שוב בעוד רגע.", "proposal": None}


# ─────────────────────────── @ contacts (the ask box mention search) ───────

async def contacts(db: AsyncSession, user: User, q: str = "", limit: int = 12) -> list[dict]:
    """Who the agent can @-mention: customers from the active production files
    (name · ת.ז · email/phone when the file has them), saved insurer contacts,
    and people who mailed in. `q` matches name, ID prefix or email."""
    from sqlalchemy import func, or_
    from app.api.production import _get_production_upload_ids
    from app.models.company_contact import CompanyContact
    from app.models.record import ClientRecord

    q = (q or "").strip()
    out: list[dict] = []
    ql = q.lower()
    # insurer contacts + mail senders first — few, and usually what an action needs
    for c in (await db.execute(select(CompanyContact).where(CompanyContact.user_id == user.id))).scalars():
        if not q or ql in (c.company_name or "").lower() or ql in (c.contact_name or "").lower() or ql in (c.email or "").lower():
            out.append({"kind": "company", "name": c.company_name, "sub": c.contact_name or "", "email": c.email, "id_number": None})
    seen_mail = set()
    for m in (await db.execute(select(MailItem).where(MailItem.user_id == user.id).order_by(MailItem.received_at.desc()).limit(200))).scalars():
        addr = (m.from_address or "").lower()
        if addr in seen_mail:
            continue
        seen_mail.add(addr)
        if not q or ql in (m.from_name or "").lower() or ql in addr:
            out.append({"kind": "mail", "name": m.from_name or m.from_address, "sub": "", "email": m.from_address, "id_number": None})

    ids = await _get_production_upload_ids(db, user.id)
    if ids:
        full = func.concat(func.coalesce(ClientRecord.first_name, ""), " ", func.coalesce(ClientRecord.last_name, ""))
        stmt = (
            select(ClientRecord.id_number, func.max(ClientRecord.first_name), func.max(ClientRecord.last_name),
                   func.max(ClientRecord.client_email), func.max(ClientRecord.client_phone))
            .where(ClientRecord.user_id == user.id, ClientRecord.upload_id.in_(ids), ClientRecord.id_number.isnot(None))
            .group_by(ClientRecord.id_number)
            .order_by(func.max(ClientRecord.last_name), func.max(ClientRecord.first_name))
            .limit(limit)
        )
        if q:
            digits = q.lstrip("0")
            conds = [full.ilike(f"%{q}%"), func.concat(func.coalesce(ClientRecord.last_name, ""), " ",
                     func.coalesce(ClientRecord.first_name, "")).ilike(f"%{q}%"), ClientRecord.client_email.ilike(f"%{q}%")]
            if digits.isdigit():
                conds.append(func.ltrim(ClientRecord.id_number, "0").like(f"{digits}%"))
            stmt = stmt.where(or_(*conds))
        for idn, fn, ln, em, ph in (await db.execute(stmt)).all():
            name = " ".join(x for x in (fn, ln) if x).strip() or str(idn)
            out.append({"kind": "customer", "name": name, "sub": ph or "", "email": em or "", "id_number": str(idn)})
    return out[: limit + 6]


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
    "send_followup": "לאשר ולשלוח ללקוח את סיכום השיחה שהכנתי (או להוסיף משהו)", "dismiss_followup": "לסמן כטופל",
}
_brief_cache: dict = {}   # user_id -> (signature, payload)
SETUP_MAIL = "setup:mail"   # a narration line whose action is "connect the mailbox"


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
    connected = bool((b.get("mailbox") or {}).get("mailbox_connected"))
    sig = f"mail={connected}|" + "|".join(f"{c['id']}:{c['sub']}:{c['text']}" for c in cards)
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
    # a finished call leads, in fixed words (the time and the customer are facts on the card —
    # never left to the model to paraphrase or drop)
    call_lines = []
    for c in (c for c in cards if c["kind"] == "call"):
        who = f" עם {c['to_name']}" if c.get("to_name") else ""
        call_lines.append({"text": f"הסיכום מהפגישה בשעה {c['at']}{who} מוכן — הכנתי לך סיכום שיחה ללקוח. "
                                   "לאשר שליחה, או שתרצה להוסיף משהו?", "ref": c["id"]})
    if call_lines:
        lines = (call_lines + [l for l in lines if not str(l.get("ref") or "").startswith("call:")])[:5]
    if not connected:
        # a new agent (or one who never connected mail) — the first thing is the
        # mailbox: without it the agent can't read, answer or send anything
        lines = [{"text": "קודם כל — חברו את Nifraim Mail Agent: כך אקרא את המיילים מהחברות ומהלקוחות, אכין תשובות ואשלח פניות בשמכם.",
                  "ref": SETUP_MAIL}] + [l for l in lines if l.get("ref")][:4]
    elif not cards:
        lines = [{"text": "הכל מטופל — אין כרגע משהו שמחכה לך. אפשר לשאול אותי על עמלות ולקוחות, או לבקש שאקבע פגישה או אכין מייל.", "ref": None}]
    payload = {"greeting": b["greeting"], "lines": lines, "todo_count": b["todo_count"]}
    _brief_cache[user.id] = (sig, payload)
    return {**payload, "cards": cards, "mailbox": b["mailbox"]}
