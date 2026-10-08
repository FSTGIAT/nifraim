"""Ask each insurer for the agent's commission agreement — by email, from the
agent's own mailbox — and load the PDF that comes back.

    setup wizard "מדף ההסכמים"
        │  agent types one contact email per company
        ▼
    send_requests()  ── send_as_agent (Gmail app-password today) ──►  insurer
        │  AgreementRequest(status=sent, sent_message_id)
        ▼
    poll_user() / run_agreement_request_poll  (scheduler, every 15 min)
        │  find_messages_matching(contact addresses, since=sent_at)
        │  reply = In-Reply-To/References ∋ sent_message_id, or from the contact after sent_at
        ▼
    PDF attachment → api.ai_documents.upload_document (rates_only)  ── the SAME path
        as a manual agreement-shelf upload (dedupe, Claude extraction, rate upsert)
        → status=imported, document_id

Companies offered = the agent's own insurers: brands of their portal logins +
their production book + companies they already have contacts for. A brand-new
agent with none of those gets the common insurers list. Company identity is
`company_stem` (brand key), never the raw display string.
"""
from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agreement_request import AgreementRequest
from app.models.company_contact import CompanyContact
from app.models.mailbox_config import MailboxConfig
from app.models.portal_credential import PortalCredential
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.models.user import User
from app.utils.company_norm import company_stem

logger = logging.getLogger(__name__)

# Shown when the agent has no portals, production or contacts yet.
COMMON_INSURERS = ["הראל", "מגדל", "כלל", "הפניקס", "מנורה", "איילון", "הכשרה", "מור", "מיטב", "אלטשולר", "ילין לפידות", "אנליסט"]
# Stop following a request after this long with no answer.
FOLLOW_WINDOW = timedelta(days=45)
OPEN_STATUSES = ("sent", "replied")


def _key(name: str) -> str:
    return company_stem(name) or (name or "").strip()


# ─────────────────────────── mailbox capability ────────────────────────────

async def mailbox_state(db: AsyncSession, user_id: uuid.UUID) -> dict:
    cfg = (await db.execute(
        select(MailboxConfig).where(MailboxConfig.user_id == user_id)
    )).scalar_one_or_none()
    connected = bool(cfg and cfg.is_active)
    # Mirrors services/mail_intake/send.py: only a Gmail app-password mailbox can
    # send today (Outlook needs Mail.Send consent; forwarding-only never can).
    can_send = bool(connected and cfg.mail_host == "google" and cfg.encrypted_password)
    reason = None
    if not connected:
        reason = "not_connected"
    elif not can_send:
        reason = "cannot_send"
    return {
        "mailbox_connected": connected,
        "mailbox_address": cfg.email_address if cfg else None,
        "mail_host": cfg.mail_host if cfg else None,
        "can_send": can_send,
        "reason": reason,
    }


# ─────────────────────────── the agent's companies ─────────────────────────

async def agent_companies(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """Display names of the agent's insurers, one per brand, stable order."""
    from app.services.portal_automation.companies import PORTAL_META

    names: list[str] = []
    kinds = (await db.execute(
        select(PortalCredential.portal_kind).where(PortalCredential.user_id == user_id)
    )).scalars().all()
    from app.services.portal_automation.companies import NON_INSURER_PORTALS
    names += [PORTAL_META[k][0] for k in kinds if k in PORTAL_META and k not in NON_INSURER_PORTALS]

    prod = (await db.execute(
        select(ClientRecord.receiving_company)
        .join(FileUpload, FileUpload.id == ClientRecord.upload_id)
        .where(ClientRecord.user_id == user_id, FileUpload.is_production.is_(True),
               ClientRecord.receiving_company.is_not(None))
        .distinct()
    )).scalars().all()
    names += [company_stem(n) or n for n in prod if n and n not in ("nan", "None")]

    contacts = (await db.execute(
        select(CompanyContact.company_name).where(CompanyContact.user_id == user_id)
    )).scalars().all()
    names += list(contacts)

    if not names:
        names = list(COMMON_INSURERS)

    seen, out = set(), []
    for n in names:
        k = _key(n)
        if k and k not in seen:
            seen.add(k)
            out.append(n.strip())
    return out


async def overview(db: AsyncSession, user: User) -> dict:
    """Everything the wizard panel needs: mailbox capability + one row per
    company with its saved contact and request status."""
    state = await mailbox_state(db, user.id)
    contacts = (await db.execute(
        select(CompanyContact).where(CompanyContact.user_id == user.id)
    )).scalars().all()
    reqs = {r.company_key: r for r in (await db.execute(
        select(AgreementRequest).where(AgreementRequest.user_id == user.id)
    )).scalars().all()}

    rows = []
    for name in await agent_companies(db, user.id):
        k = _key(name)
        contact = next((c for c in contacts if _key(c.company_name) == k), None)
        r = reqs.get(k)
        rows.append({
            "company": name,
            "email": (r.to_email if r else None) or (contact.email if contact else ""),
            "contact_name": (r.contact_name if r else None) or (contact.contact_name if contact else None),
            "status": r.status if r else None,
            "sent_at": r.sent_at.isoformat() if r and r.sent_at else None,
            "replied_at": r.replied_at.isoformat() if r and r.replied_at else None,
            "document_id": str(r.document_id) if r and r.document_id else None,
            "error": r.error if r else None,
        })
    return {**state, "companies": rows,
            "sent_count": sum(1 for r in reqs.values() if r.status in ("sent", "replied", "imported"))}


# ─────────────────────────── sending ───────────────────────────────────────

def _compose(user: User, company: str, contact_name: str | None, mailbox_domain: str) -> EmailMessage:
    agent = (user.full_name or "").strip() or user.email
    hello = f"שלום {contact_name}," if contact_name else "שלום רב,"
    phone = f"\n{user.phone}" if getattr(user, "phone", None) else ""
    msg = EmailMessage()
    msg["Subject"] = f"בקשה להסכם עמלות — {agent}"
    msg["Message-ID"] = make_msgid(domain=mailbox_domain or "nifraim.com")
    msg.set_content(
        f"{hello}\n\n"
        f"אני {agent}, סוכן/ת ביטוח שעובד/ת מול {company}.\n"
        f"אשמח לקבל את הסכם העמלות העדכני שלי מול {company} (קובץ PDF), "
        f"כדי לעדכן את מערכת בקרת העמלות שלי.\n\n"
        f"תודה רבה,\n{agent}{phone}\n"
    )
    return msg


async def _save_contact(db: AsyncSession, user_id, company: str, email: str, contact_name: str | None):
    k = _key(company)
    rows = (await db.execute(
        select(CompanyContact).where(CompanyContact.user_id == user_id)
    )).scalars().all()
    c = next((c for c in rows if _key(c.company_name) == k), None)
    if c is None:
        db.add(CompanyContact(user_id=user_id, company_name=company[:100], email=email[:255],
                              contact_name=(contact_name or None)))
    else:
        c.email = email[:255]
        if contact_name:
            c.contact_name = contact_name[:100]


async def send_requests(db: AsyncSession, user: User, items: list[dict]) -> list[dict]:
    """Send one agreement request per item {company, email, contact_name?}.
    Returns [{company, ok, error?}]. Never raises for a single failed row."""
    from app.services.mail_intake import MailIntakeError
    from app.services.mail_intake.send import NoSendableMailbox, send_as_agent

    state = await mailbox_state(db, user.id)
    domain = (state.get("mailbox_address") or "").split("@")[-1]
    results = []
    for it in items:
        company = (it.get("company") or "").strip()
        email = (it.get("email") or "").strip().lower()
        contact_name = (it.get("contact_name") or "").strip() or None
        if not company or "@" not in email:
            results.append({"company": company, "ok": False, "error": "invalid"})
            continue
        await _save_contact(db, user.id, company, email, contact_name)
        msg = _compose(user, company, contact_name, domain)
        msg["To"] = email
        k = _key(company)
        req = (await db.execute(
            select(AgreementRequest).where(AgreementRequest.user_id == user.id, AgreementRequest.company_key == k)
        )).scalar_one_or_none()
        if req is None:
            req = AgreementRequest(user_id=user.id, company_key=k, company_name=company[:100], to_email=email)
            db.add(req)
        req.to_email, req.contact_name, req.subject = email, contact_name, str(msg["Subject"])[:255]
        req.reply_message_id, req.replied_at, req.document_id, req.error = None, None, None, None
        try:
            await send_as_agent(user.id, msg, display_name=user.full_name)
            req.status, req.sent_at, req.sent_message_id = "sent", datetime.utcnow(), str(msg["Message-ID"])
            results.append({"company": company, "ok": True})
        except (NoSendableMailbox, MailIntakeError) as e:
            req.status, req.error = "failed", type(e).__name__
            results.append({"company": company, "ok": False, "error": str(e)[:200]})
        await db.commit()
    return results


# ─────────────────────────── following replies ─────────────────────────────

def _is_reply_to(m, req: AgreementRequest) -> bool:
    from app.services.mail_intake.search import sender_matches
    mid = (req.sent_message_id or "").strip()
    threaded = bool(mid) and (mid in (m.in_reply_to or "") or mid in (m.references or ""))
    from_contact = sender_matches(m.from_addr, req.to_email) and req.sent_at and m.received_at >= req.sent_at
    return threaded or bool(from_contact)


async def _import_pdf(user: User, filename: str, content: bytes):
    """Run the attachment through the agreement-shelf upload itself, so the
    dedupe / extraction / rate upsert / race handling are exactly the manual
    path's. Returns the AiDocument (or raises)."""
    from starlette.datastructures import Headers, UploadFile
    from app.api.ai_documents import upload_document
    from app.database import async_session

    upload = UploadFile(file=io.BytesIO(content), filename=filename,
                        headers=Headers({"content-type": "application/pdf"}))
    async with async_session() as db:
        return await upload_document(file=upload, rates_only=True, db=db, user=user)


async def poll_user(db: AsyncSession, user: User) -> int:
    """Check this agent's open requests for replies. Returns #agreements loaded."""
    from app.services.mail_intake.search import fetch_attachment, find_messages_matching

    now = datetime.utcnow()
    reqs = (await db.execute(
        select(AgreementRequest).where(
            AgreementRequest.user_id == user.id,
            AgreementRequest.status.in_(OPEN_STATUSES),
            AgreementRequest.sent_at.is_not(None),
            AgreementRequest.sent_at >= now - FOLLOW_WINDOW,
        )
    )).scalars().all()
    if not reqs:
        return 0
    cfg = (await db.execute(
        select(MailboxConfig).where(MailboxConfig.user_id == user.id)
    )).scalar_one_or_none()
    if not cfg or not cfg.is_active:
        return 0

    since = min(r.sent_at for r in reqs)
    msgs = await find_messages_matching(db, cfg, matchers=[r.to_email for r in reqs], since=since)
    loaded = 0
    for req in reqs:
        for m in sorted((m for m in msgs if _is_reply_to(m, req)), key=lambda m: m.received_at):
            if m.auto_submitted:
                continue
            req.replied_at = req.replied_at or m.received_at
            req.reply_message_id = m.message_id
            pdfs = [a for a in (m.attachments or []) if (a.get("name") or "").lower().endswith(".pdf")]
            if not pdfs:
                req.status = "replied" if req.status != "imported" else req.status
                continue
            for a in pdfs:
                try:
                    content = await fetch_attachment(db, cfg, provider_id=m.provider_id, filename=a["name"])
                    if not content:
                        continue
                    doc = await _import_pdf(user, a["name"], content)
                    req.document_id = req.document_id or doc.id
                    req.status, req.error = "imported", None
                    loaded += 1
                except Exception as e:  # noqa: BLE001 — keep following the other companies
                    logger.warning("agreement import failed (user %s, %s): %s", user.id, req.company_name, e)
                    req.error = str(e)[:500]
        await db.commit()
    return loaded


async def run_agreement_request_poll() -> None:
    """Scheduler entry: every agent with an open request. Never raises."""
    from app.database import async_session

    try:
        async with async_session() as db:
            user_ids = (await db.execute(
                select(AgreementRequest.user_id).where(
                    AgreementRequest.status.in_(OPEN_STATUSES),
                    AgreementRequest.sent_at >= datetime.utcnow() - FOLLOW_WINDOW,
                ).distinct()
            )).scalars().all()
            for uid in user_ids:
                user = await db.get(User, uid)
                if user is None:
                    continue
                try:
                    n = await poll_user(db, user)
                    if n:
                        logger.info("agreement requests: loaded %d agreement(s) for user %s", n, uid)
                except Exception as e:  # noqa: BLE001
                    await db.rollback()
                    logger.warning("agreement request poll failed for %s: %s", uid, e)
    except Exception as e:  # noqa: BLE001
        logger.error("agreement request poll outer failure: %s", e)
