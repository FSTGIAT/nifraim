"""The collection agent ("סוכן גבייה") — back-office AI that chases unpaid commission.

    latest merged comparison (commission_comparisons, category 'merged')
        │  unpaid = only_production customers, product company ∈ the month's
        │  נפרעים companies (no נפרעים at all = "no data", not "unpaid"),
        │  inactive/cancelled products skipped
        ▼
    refresh_cases()  — one CollectionCase per (agent, insurer, month): a DRAFT mail
        │             listing the customers + policies. Never touches a sent case.
        ▼
    agent approves → send_case()  ── send_as_agent (the agreement-request path) ──► insurer
        │
    poll_user() (scheduler, every 15 min) — a reply (threaded, or from the contact
        │  after sent_at) → status=replied + a one-line Hebrew summary (Haiku)
        ▼
    brief() — per insurer: one line + ONE suggested next step (approve / add contact /
        remind after 7 days / read the reply / done). Not a chat: straight to the point.

Nothing is ever sent without the agent's click (decided 2026-09-29).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.collection_case import CollectionCase
from app.models.commission_comparison import CommissionComparison
from app.models.commission_rate import CommissionRate
from app.models.company_contact import CompanyContact
from app.models.user import User
from app.utils.company_norm import company_stem

logger = logging.getLogger(__name__)

REMIND_AFTER = timedelta(days=7)
FOLLOW_WINDOW = timedelta(days=60)
INACTIVE_MARKERS = ("לא פעיל", "מבוטל", "בוטל", "סגור", "הסתיים")


def _key(name: str) -> str:
    return company_stem(name) or (name or "").strip()


def _period(result: dict) -> date | None:
    p = result.get("period_month")
    try:
        return date.fromisoformat(str(p)[:10]) if p else None
    except ValueError:
        return None


# ─────────────────────────── from the comparison ───────────────────────────

async def _latest_comparison(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    row = (await db.execute(
        select(CommissionComparison.result_json)
        .where(CommissionComparison.user_id == user_id, CommissionComparison.category == "merged")
        .order_by(CommissionComparison.computed_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    return row if isinstance(row, dict) else None


def unpaid_by_company(result: dict) -> dict[str, dict]:
    """{company_key: {name, items[], customers, expected}} from a comparison result."""
    sources = {_key(s) for s in (result.get("commission_company_sources") or []) if s}
    out: dict[str, dict] = {}
    for c in result.get("customers") or []:
        if c.get("match_status") != "only_production":
            continue
        name = " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) or c.get("id_number") or ""
        products = c.get("production_products") or (c.get("product_matches") or {}).get("unmatched_production") or []
        for p in products:
            company = p.get("company") or p.get("company_full") or ""
            k = _key(company)
            if not k or (sources and k not in sources):
                continue
            if any(m in (p.get("status") or "") for m in INACTIVE_MARKERS):
                continue
            g = out.setdefault(k, {"name": company, "items": [], "ids": set(), "expected": 0.0, "seen": {}})
            exp = float(p.get("expected_commission") or 0)
            # one line per customer + policy (a policy's riders/coverages come as
            # separate products — the insurer needs the policy once)
            dk = (c.get("id_number"), p.get("policy_number") or p.get("product") or "")
            if dk in g["seen"]:
                g["seen"][dk]["expected"] = round(g["seen"][dk]["expected"] + exp, 2)
            else:
                item = {
                    "id_number": c.get("id_number"), "name": name,
                    "product": p.get("product") or p.get("product_type") or "",
                    "policy": p.get("policy_number") or "",
                    "sign_date": p.get("sign_date") or "",
                    "expected": round(exp, 2),
                }
                g["seen"][dk] = item
                g["items"].append(item)
            g["ids"].add(c.get("id_number"))
            g["expected"] += float(p.get("expected_commission") or 0)
    for g in out.values():
        g["customers"] = len(g.pop("ids"))
        g.pop("seen", None)
        g["expected"] = round(g["expected"], 2)
    return out


def _period_label(p: date | None) -> str:
    from app.services.cycle_service import month_label
    return month_label(p) if p else "החודש האחרון"


def compose_draft(user: User, company: str, contact_name: str | None, period: date | None, items: list[dict]) -> tuple[str, str]:
    agent = (user.full_name or "").strip() or user.email
    hello = f"שלום {contact_name}," if contact_name else "שלום רב,"
    lines = []
    for it in items[:200]:
        pol = f" | פוליסה/חשבון {it['policy']}" if it.get("policy") else ""
        date_s = f" | הצטרפות {it['sign_date']}" if it.get("sign_date") else ""
        lines.append(f"- {it['name']} (ת.ז {it['id_number']}) — {it['product']}{pol}{date_s}")
    more = f"\n…ועוד {len(items) - 200} מוצרים" if len(items) > 200 else ""
    subject = f"עמלות שלא התקבלו — {_period_label(period)} — {agent}"
    body = (
        f"{hello}\n\n"
        f"בבדיקת דוח הנפרעים של {_period_label(period)} מול הפרודוקציה שלי, "
        f"לא התקבלה עמלה עבור הלקוחות הבאים ב{company}:\n\n"
        + "\n".join(lines) + more +
        "\n\nאשמח לבדיקה ולעדכון מתי העמלות ישולמו, או מה חסר כדי שישולמו.\n\n"
        f"תודה רבה,\n{agent}" + (f"\n{user.phone}" if getattr(user, "phone", None) else "") + "\n"
    )
    return subject, body


async def _contacts(db: AsyncSession, user_id: uuid.UUID) -> dict[str, tuple[str, str | None]]:
    """{company_key: (email, contact_name)} — the agent's contacts, then the
    agreement shelf's company emails as a fallback."""
    out: dict[str, tuple[str, str | None]] = {}
    for rate in (await db.execute(
        select(CommissionRate.company_name, CommissionRate.company_email)
        .where(CommissionRate.user_id == user_id, CommissionRate.company_email.is_not(None))
    )).all():
        if rate[1] and "@" in rate[1]:
            out.setdefault(_key(rate[0]), (rate[1].strip().lower(), None))
    for c in (await db.execute(select(CompanyContact).where(CompanyContact.user_id == user_id))).scalars():
        if c.email and "@" in c.email:
            out[_key(c.company_name)] = (c.email.strip().lower(), c.contact_name)
    return out


async def refresh_cases(db: AsyncSession, user: User) -> int:
    """(Re)build the DRAFT cases from the latest comparison. Sent / replied /
    resolved cases are the agent's history — never rewritten. Returns #open drafts."""
    result = await _latest_comparison(db, user.id)
    if not result:
        return 0
    period = _period(result)
    groups = unpaid_by_company(result)
    contacts = await _contacts(db, user.id)
    existing = {
        c.company_key: c for c in (await db.execute(
            select(CollectionCase).where(CollectionCase.user_id == user.id, CollectionCase.period == period)
        )).scalars()
    }
    for k, g in groups.items():
        case = existing.get(k)
        if case is not None and case.status != "draft":
            continue
        email, contact_name = contacts.get(k, (None, None))
        if case is None:
            case = CollectionCase(user_id=user.id, company_key=k, company_name=g["name"][:100], period=period)
            db.add(case)
        case.items, case.customers_count, case.expected_total = g["items"], g["customers"], g["expected"]
        if email and not case.to_email:
            case.to_email, case.contact_name = email, contact_name
        case.draft_subject, case.draft_body = compose_draft(user, case.company_name, case.contact_name, period, g["items"])
    # drafts for insurers that no longer have unpaid customers this month
    stale = [c.id for k, c in existing.items() if c.status == "draft" and k not in groups]
    if stale:
        await db.execute(delete(CollectionCase).where(CollectionCase.id.in_(stale)))
    await db.commit()
    return sum(1 for k in groups if (existing.get(k) is None or existing[k].status == "draft"))


# ─────────────────────────── the brief (what the UI shows) ─────────────────

def suggestion(case: CollectionCase, now: datetime) -> dict:
    if case.status == "resolved":
        return {"kind": "done", "text": "טופל"}
    if case.status == "replied":
        return {"kind": "read", "text": case.reply_summary or "התקבלה תשובה — לקרוא ולסמן כטופל"}
    if case.status == "sent":
        since = case.last_reminder_at or case.sent_at or now
        days = (now - since).days
        if now - since >= REMIND_AFTER:
            return {"kind": "remind", "text": f"אין תשובה {days} ימים — לשלוח תזכורת?"}
        return {"kind": "wait", "text": "נשלח — ממתינים לתשובה"}
    if not case.to_email:
        return {"kind": "contact", "text": f"חסר מייל של איש קשר ב{case.company_name}"}
    return {"kind": "approve", "text": "הפנייה מוכנה — לאשר ולשלוח"}


def case_dict(case: CollectionCase, now: datetime) -> dict:
    return {
        "id": str(case.id), "company": case.company_name, "company_key": case.company_key,
        "period": case.period.isoformat() if case.period else None,
        "customers": case.customers_count, "expected": case.expected_total,
        "items": case.items or [], "to_email": case.to_email, "contact_name": case.contact_name,
        "status": case.status, "draft_subject": case.draft_subject, "draft_body": case.draft_body,
        "sent_at": case.sent_at.isoformat() if case.sent_at else None,
        "reminder_count": case.reminder_count,
        "replied_at": case.replied_at.isoformat() if case.replied_at else None,
        "reply_summary": case.reply_summary, "error": case.error,
        "next": suggestion(case, now),
    }


async def brief(db: AsyncSession, user: User) -> dict:
    from app.services.agreement_requests import mailbox_state

    now = datetime.utcnow()
    cases = (await db.execute(
        select(CollectionCase).where(CollectionCase.user_id == user.id)
        .order_by(CollectionCase.period.desc().nullslast(), CollectionCase.expected_total.desc())
    )).scalars().all()
    # the latest month's cases are the working set; older resolved ones are history
    latest = max((c.period for c in cases if c.period), default=None)
    current = [c for c in cases if c.period == latest or c.status in ("sent", "replied")]
    open_ = [c for c in current if c.status != "resolved"]
    return {
        "period": latest.isoformat() if latest else None,
        "period_label": _period_label(latest) if latest else None,
        "mailbox": await mailbox_state(db, user.id),
        "open_count": len(open_),
        "customers": sum(c.customers_count for c in open_),
        "expected": round(sum(c.expected_total for c in open_), 2),
        "cases": [case_dict(c, now) for c in current],
    }


async def mailbox_state_for(db: AsyncSession, user: User) -> dict:
    from app.services.agreement_requests import mailbox_state
    return await mailbox_state(db, user.id)


# ─────────────────────────── actions (always the agent's click) ────────────

async def _get(db: AsyncSession, user: User, case_id: str) -> CollectionCase:
    case = (await db.execute(
        select(CollectionCase).where(CollectionCase.id == uuid.UUID(case_id), CollectionCase.user_id == user.id)
    )).scalar_one_or_none()
    if case is None:
        raise LookupError("case not found")
    return case


async def update_case(db: AsyncSession, user: User, case_id: str, *, to_email=None, contact_name=None,
                      subject=None, body=None) -> CollectionCase:
    case = await _get(db, user, case_id)
    if to_email is not None:
        case.to_email = to_email.strip().lower() or None
    if contact_name is not None:
        case.contact_name = contact_name.strip() or None
    if subject is not None:
        case.draft_subject = subject[:255]
    if body is not None:
        case.draft_body = body
    await db.commit()
    return case


async def _send(user: User, case: CollectionCase, subject: str, body: str, *, reply_to_id: str | None, db: AsyncSession) -> str:
    from app.services.agreement_requests import _save_contact, mailbox_state
    from app.services.mail_intake.send import send_as_agent

    state = await mailbox_state(db, user.id)
    domain = (state.get("mailbox_address") or "").split("@")[-1] or "nifraim.com"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = case.to_email
    msg["Message-ID"] = make_msgid(domain=domain)
    if reply_to_id:
        msg["In-Reply-To"] = reply_to_id
        msg["References"] = reply_to_id
    msg.set_content(body)
    await send_as_agent(user.id, msg, display_name=user.full_name)
    await _save_contact(db, user.id, case.company_name, case.to_email, case.contact_name)
    return str(msg["Message-ID"])


async def send_case(db: AsyncSession, user: User, case_id: str) -> CollectionCase:
    case = await _get(db, user, case_id)
    if case.status != "draft":
        raise ValueError("already sent")
    if not case.to_email or "@" not in case.to_email:
        raise ValueError("missing contact email")
    try:
        mid = await _send(user, case, case.draft_subject or "", case.draft_body or "", reply_to_id=None, db=db)
    except Exception as e:  # noqa: BLE001 — surface to the agent, keep the draft
        case.error = str(e)[:500]
        await db.commit()
        raise
    case.status, case.sent_at, case.sent_message_id, case.error = "sent", datetime.utcnow(), mid, None
    await db.commit()
    return case


def reminder_text(user: User, case: CollectionCase) -> tuple[str, str]:
    agent = (user.full_name or "").strip() or user.email
    subject = f"תזכורת: {case.draft_subject or 'עמלות שלא התקבלו'}"
    body = (
        f"שלום{(' ' + case.contact_name) if case.contact_name else ''},\n\n"
        f"מזכיר/ה את פנייתי מ-{case.sent_at.strftime('%d.%m') if case.sent_at else ''} לגבי העמלות שלא התקבלו "
        f"עבור {case.customers_count} לקוחות ב{case.company_name}. אשמח לעדכון.\n\n"
        f"תודה,\n{agent}\n"
    )
    return subject, body


async def send_reminder(db: AsyncSession, user: User, case_id: str) -> CollectionCase:
    case = await _get(db, user, case_id)
    if case.status != "sent":
        raise ValueError("nothing to remind")
    subject, body = reminder_text(user, case)
    await _send(user, case, subject, body, reply_to_id=case.sent_message_id, db=db)
    case.reminder_count += 1
    case.last_reminder_at = datetime.utcnow()
    await db.commit()
    return case


async def resolve_case(db: AsyncSession, user: User, case_id: str) -> CollectionCase:
    case = await _get(db, user, case_id)
    case.status, case.resolved_at = "resolved", datetime.utcnow()
    await db.commit()
    return case


# ─────────────────────────── following replies ─────────────────────────────

async def summarize_reply(company: str, text: str) -> str:
    """One Hebrew line: what the insurer answered. Haiku; first line as fallback."""
    snippet = (text or "").strip()
    first = next((l.strip() for l in snippet.splitlines() if len(l.strip()) > 8), snippet[:160])[:160]
    if not settings.ANTHROPIC_API_KEY or not snippet:
        return first
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        r = await client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=80,
            system="סכם בשורה אחת קצרה בעברית (עד 15 מילים) מה חברת הביטוח ענתה לסוכן על עמלות שלא שולמו. בלי הקדמות.",
            messages=[{"role": "user", "content": f"חברה: {company}\n\n{snippet[:3000]}"}],
        )
        out = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
        return out[:200] or first
    except Exception as e:  # noqa: BLE001
        logger.warning("collection reply summary failed: %s", e)
        return first


async def poll_user(db: AsyncSession, user: User) -> int:
    from app.models.mailbox_config import MailboxConfig
    from app.services.mail_intake.search import find_messages_matching, sender_matches

    now = datetime.utcnow()
    cases = (await db.execute(
        select(CollectionCase).where(
            CollectionCase.user_id == user.id, CollectionCase.status == "sent",
            CollectionCase.sent_at.is_not(None), CollectionCase.sent_at >= now - FOLLOW_WINDOW,
        )
    )).scalars().all()
    if not cases:
        return 0
    cfg = (await db.execute(select(MailboxConfig).where(MailboxConfig.user_id == user.id))).scalar_one_or_none()
    if not cfg or not cfg.is_active:
        return 0
    msgs = await find_messages_matching(db, cfg, matchers=[c.to_email for c in cases if c.to_email],
                                        since=min(c.sent_at for c in cases))
    got = 0
    for case in cases:
        mid = (case.sent_message_id or "").strip()
        replies = [
            m for m in msgs
            if not m.auto_submitted and (
                (mid and (mid in (m.in_reply_to or "") or mid in (m.references or "")))
                or (sender_matches(m.from_addr, case.to_email) and m.received_at >= case.sent_at)
            )
        ]
        if not replies:
            continue
        m = max(replies, key=lambda x: x.received_at)
        case.status, case.replied_at, case.reply_message_id = "replied", m.received_at, m.message_id
        case.reply_summary = await summarize_reply(case.company_name, m.text)
        got += 1
        await db.commit()
    return got


async def run_collection_poll() -> None:
    """Scheduler entry: every agent with a sent case. Never raises."""
    from app.database import async_session

    try:
        async with async_session() as db:
            user_ids = (await db.execute(
                select(CollectionCase.user_id).where(CollectionCase.status == "sent").distinct()
            )).scalars().all()
            for uid in user_ids:
                user = await db.get(User, uid)
                if user is None:
                    continue
                try:
                    await poll_user(db, user)
                except Exception as e:  # noqa: BLE001 — one agent never blocks the rest
                    await db.rollback()
                    logger.warning("collection poll failed for %s: %s", uid, e)
    except Exception as e:  # noqa: BLE001
        logger.error("collection poll outer failure: %s", e)
