"""AI mail agent API — the "דואר" tab.

Everything is scoped to the calling user. The agent decides which senders the
AI reads (watch-list); the AI summarises and drafts; nothing is sent until the
agent presses send (`POST /items/{id}/send`).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user
from app.config import settings
from app.database import get_db
from app.models.company_contact import CompanyContact
from app.models.mail_item import DISMISSED, DONE, OPEN_STATUSES, SENT, MailItem
from app.models.mail_watch_sender import KINDS, MailWatchSender
from app.models.mailbox_config import MailboxConfig
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.models.user import User
from app.services.mail_agent import intake, usage

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMPORT_BYTES = 25 * 1024 * 1024


# ── schemas ────────────────────────────────────────────────────────────────
class SenderIn(BaseModel):
    address: str = Field(min_length=3, max_length=255)
    label: str | None = None
    kind: str = "other"
    company_name: str | None = None
    customer_id_number: str | None = None


class DraftIn(BaseModel):
    subject: str = Field(max_length=998)
    body: str


def _sender_out(s: MailWatchSender) -> dict:
    return {"id": str(s.id), "address": s.address, "label": s.label, "kind": s.kind,
            "company_name": s.company_name, "customer_id_number": s.customer_id_number}


def _item_out(i: MailItem, *, full: bool = False) -> dict:
    out = {
        "id": str(i.id), "from_address": i.from_address, "from_name": i.from_name,
        "subject": i.subject, "received_at": i.received_at.isoformat() + "Z" if i.received_at else None,
        "category": i.category, "summary": i.summary, "status": i.status,
        "suggested_action": i.suggested_action, "ai_skipped_reason": i.ai_skipped_reason,
        "linked_company": i.linked_company, "linked_customer_id_number": i.linked_customer_id_number,
        "has_draft": bool(i.draft_body), "attachments": i.attachments or [],
        "sent_at": i.sent_at.isoformat() + "Z" if i.sent_at else None,
        "imported_upload_id": str(i.imported_upload_id) if i.imported_upload_id else None,
    }
    if full:
        out.update({
            "body": intake.body_of(i), "entities": i.entities or {},
            "draft_subject": i.draft_subject, "draft_body": i.draft_body,
            "draft_warnings": i.draft_warnings or [], "draft_model": i.draft_model,
            "draft_edited": i.draft_edited,
        })
    return out


async def _own_item(db: AsyncSession, user: User, item_id: uuid.UUID) -> MailItem:
    item = await db.get(MailItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "המייל לא נמצא")
    return item


async def _mailbox(db: AsyncSession, user: User) -> MailboxConfig | None:
    return (await db.execute(select(MailboxConfig).where(MailboxConfig.user_id == user.id))).scalar_one_or_none()


def _norm_address(a: str) -> str:
    a = (a or "").strip().lower()
    if a.startswith("@"):
        if "." not in a[1:]:
            raise HTTPException(400, "דומיין לא תקין")
        return a
    if "@" not in a or "." not in a.split("@", 1)[1]:
        raise HTTPException(400, "כתובת מייל לא תקינה")
    return a


# ── watch-list ─────────────────────────────────────────────────────────────
@router.get("/senders")
async def list_senders(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    rows = (await db.execute(
        select(MailWatchSender).where(MailWatchSender.user_id == user.id).order_by(MailWatchSender.created_at)
    )).scalars().all()
    return [_sender_out(s) for s in rows]


@router.post("/senders")
async def add_sender(body: SenderIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    address = _norm_address(body.address)
    cfg = await _mailbox(db, user)
    own = (cfg.email_address or "").strip().lower() if cfg else ""
    if own and (address == own or (address.startswith("@") and own.endswith(address))):
        raise HTTPException(400, "זו כתובת תיבת המייל שלכם — ה-AI עונה רק למיילים שמגיעים מאחרים")
    if body.kind not in KINDS:
        raise HTTPException(400, "סוג שולח לא תקין")
    dup = (await db.execute(select(MailWatchSender).where(
        MailWatchSender.user_id == user.id, MailWatchSender.address == address))).scalar_one_or_none()
    if dup:
        return _sender_out(dup)
    s = MailWatchSender(user_id=user.id, address=address, label=(body.label or None),
                        kind=body.kind, company_name=body.company_name,
                        customer_id_number=(body.customer_id_number or None))
    db.add(s)
    await db.commit()
    return _sender_out(s)


@router.delete("/senders/{sender_id}")
async def remove_sender(sender_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    s = await db.get(MailWatchSender, sender_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "השולח לא נמצא")
    await db.delete(s)
    await db.commit()
    return {"status": "deleted"}


@router.get("/senders/suggestions")
async def sender_suggestions(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """Insurers from the agent's contacts, customers from their production —
    minus what is already watched. Suggestions only; adding is the agent's click."""
    watched = set((await db.execute(
        select(MailWatchSender.address).where(MailWatchSender.user_id == user.id))).scalars().all())
    cfg = await _mailbox(db, user)
    if cfg and cfg.email_address:
        watched.add(cfg.email_address.strip().lower())       # never suggest their own address
    out: list[dict] = []
    for c in (await db.execute(select(CompanyContact).where(CompanyContact.user_id == user.id))).scalars():
        a = (c.email or "").strip().lower()
        if a and a not in watched:
            out.append({"address": a, "label": c.company_name, "kind": "insurer", "company_name": c.company_name})
            watched.add(a)
    rows = (await db.execute(
        select(func.lower(ClientRecord.client_email), func.max(ClientRecord.first_name),
               func.max(ClientRecord.last_name), func.max(ClientRecord.id_number))
        .join(FileUpload, FileUpload.id == ClientRecord.upload_id)
        .where(ClientRecord.user_id == user.id, FileUpload.is_production.is_(True),
               ClientRecord.client_email.isnot(None), ClientRecord.client_email.contains("@"))
        .group_by(func.lower(ClientRecord.client_email))
        .limit(200)
    )).all()
    for email_addr, first, last, id_number in rows:
        a = (email_addr or "").strip()
        if a and a not in watched:
            out.append({"address": a, "label": " ".join(x for x in (first, last) if x) or None,
                        "kind": "customer", "customer_id_number": id_number})
    return out


# ── items ──────────────────────────────────────────────────────────────────
@router.get("/items")
async def list_items(status: str = "open", db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    q = select(MailItem).where(MailItem.user_id == user.id)
    if status == "open":
        q = q.where(MailItem.status.in_(OPEN_STATUSES))
    elif status != "all":
        q = q.where(MailItem.status == status)
    rows = (await db.execute(q.order_by(MailItem.received_at.desc()).limit(200))).scalars().all()
    return [_item_out(i) for i in rows]


@router.get("/items/{item_id}")
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    return _item_out(await _own_item(db, user, item_id), full=True)


@router.post("/items/{item_id}/draft")
async def regenerate_draft(item_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    item = await _own_item(db, user, item_id)
    if item.status == SENT:
        raise HTTPException(409, "התשובה כבר נשלחה")
    sender = await db.get(MailWatchSender, item.watch_sender_id) if item.watch_sender_id else None
    if item.category is None:                          # never triaged (cap / AI down) — do both
        await intake.analyze(db, item, sender, intake.body_of(item))
        if not item.draft_body:
            await intake.make_draft(db, item, sender)
    else:
        await intake.make_draft(db, item, sender)
    await db.commit()
    if item.ai_skipped_reason == "daily_cap":
        raise HTTPException(429, "הגעתם למכסת ה-AI היומית. אפשר לכתוב תשובה ידנית או לנסות מחר.")
    if item.ai_skipped_reason == "ai_unavailable":
        raise HTTPException(503, "שירות ה-AI לא זמין כרגע. נסו שוב בעוד כמה דקות.")
    return _item_out(item, full=True)


@router.put("/items/{item_id}/draft")
async def save_draft(item_id: uuid.UUID, body: DraftIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    item = await _own_item(db, user, item_id)
    if item.status == SENT:
        raise HTTPException(409, "התשובה כבר נשלחה")
    item.draft_subject, item.draft_body, item.draft_edited = body.subject, body.body, True
    if item.status not in (SENT,):
        item.status = "drafted"
    await db.commit()
    return _item_out(item, full=True)


@router.post("/items/{item_id}/send")
async def send_reply(item_id: uuid.UUID, body: DraftIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """The ONLY path that sends — the agent pressed send on text they saw."""
    from app.services.mail_intake import MailIntakeError
    from app.services.mail_intake.send import NoSendableMailbox, send_as_agent

    item = await _own_item(db, user, item_id)
    if item.status == SENT:
        raise HTTPException(409, "התשובה כבר נשלחה")
    if not body.body.strip():
        raise HTTPException(400, "התשובה ריקה")
    if "[להשלים" in body.body:
        raise HTTPException(400, "בטיוטה נשארו חלקים שמסומנים [להשלים] — השלימו אותם לפני שליחה")
    cfg = await _mailbox(db, user)
    msg = EmailMessage()
    domain = (cfg.email_address.split("@", 1)[1] if cfg and "@" in cfg.email_address else "nifraim.com")
    msg["Message-ID"] = make_msgid(domain=domain)
    msg["To"] = item.from_address
    msg["Subject"] = body.subject
    if item.internet_message_id:
        msg["In-Reply-To"] = item.internet_message_id
        msg["References"] = " ".join(x for x in (item.references, item.internet_message_id) if x)
    msg.set_content(body.body)
    item.draft_subject, item.draft_body = body.subject, body.body
    try:
        await send_as_agent(user.id, msg, display_name=user.full_name)
    except NoSendableMailbox:
        await db.commit()
        raise HTTPException(409, "אין תיבת מייל מחוברת שאפשר לשלוח ממנה (כרגע נתמך Gmail). הטיוטה נשמרה.")
    except MailIntakeError as e:
        await db.commit()
        raise HTTPException(502, "השליחה מתיבת המייל נכשלה"
                            + (" — סיסמת האפליקציה לא התקבלה" if e.code == "bad_app_password" else "")
                            + ". הטיוטה נשמרה.")
    item.sent_message_id = msg["Message-ID"]
    item.sent_at = datetime.utcnow()
    item.status = SENT
    await db.commit()
    return _item_out(item, full=True)


@router.post("/items/{item_id}/dismiss")
async def dismiss_item(item_id: uuid.UUID, done: bool = False, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    item = await _own_item(db, user, item_id)
    if item.status != SENT:
        item.status = DONE if done else DISMISSED
    await db.commit()
    return _item_out(item)


@router.post("/items/{item_id}/import")
async def import_attachment(item_id: uuid.UUID, filename: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    from app.services.mail_intake import MailIntakeError
    from app.services.mail_intake.search import fetch_attachment
    from app.services.upload_ingest import ingest_file_bytes

    item = await _own_item(db, user, item_id)
    if not any(a.get("name") == filename for a in (item.attachments or [])):
        raise HTTPException(404, "הקובץ לא נמצא במייל")
    cfg = await _mailbox(db, user)
    if not cfg or not item.provider_id:
        raise HTTPException(409, "תיבת המייל לא מחוברת")
    try:
        content = await fetch_attachment(db, cfg, provider_id=item.provider_id, filename=filename)
    except MailIntakeError:
        raise HTTPException(502, "לא הצלחנו להוריד את הקובץ מתיבת המייל")
    if not content:
        raise HTTPException(404, "הקובץ לא נמצא בתיבת המייל (אולי נמחק)")
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(400, "הקובץ גדול מדי")
    try:
        upload, fmt = await ingest_file_bytes(db, user.id, content, filename)
    except Exception as e:  # noqa: BLE001 — parser errors surface as a readable message
        logger.warning("mail_agent.import: %s failed for user %s: %s", filename, user.id, e)
        raise HTTPException(422, f"לא הצלחנו לקרוא את הקובץ: {e}")
    item.imported_upload_id = upload.id
    item.status = DONE
    await db.commit()
    return {"upload_id": str(upload.id), "format": fmt, "item": _item_out(item)}


# ── summary + manual poll ──────────────────────────────────────────────────
@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    all_counts = dict((await db.execute(
        select(MailItem.status, func.count(MailItem.id))
        .where(MailItem.user_id == user.id)
        .group_by(MailItem.status)
    )).all())
    counts = {k: v for k, v in all_counts.items() if k in OPEN_STATUSES}
    cfg = await _mailbox(db, user)
    watched = (await db.execute(
        select(func.count(MailWatchSender.id)).where(MailWatchSender.user_id == user.id))).scalar_one()
    return {
        "open": sum(counts.values()), "by_status": counts, "watched_senders": watched,
        "processed": sum(all_counts.values()), "sent": all_counts.get(SENT, 0),
        "mailbox_connected": bool(cfg and cfg.is_active and cfg.mail_host in ("google", "microsoft")),
        "mailbox_address": cfg.email_address if cfg else None,
        "can_send": bool(cfg and cfg.mail_host == "google" and cfg.encrypted_password),
        "last_checked_at": cfg.mail_agent_checked_at.isoformat() + "Z" if cfg and cfg.mail_agent_checked_at else None,
        "ai_calls_today": await usage.calls_today(db, user.id),
        "poll_minutes": settings.MAIL_AGENT_POLL_MINUTES,
    }


@router.post("/poll-now")
async def poll_now(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    from app.services.mail_intake import MailIntakeError

    cfg = await _mailbox(db, user)
    if not cfg or not cfg.is_active or cfg.mail_host not in ("google", "microsoft"):
        raise HTTPException(409, "אין תיבת מייל מחוברת")
    try:
        stored = await intake.poll_mailbox(db, cfg)
    except MailIntakeError as e:
        raise HTTPException(502, f"לא הצלחנו לקרוא את תיבת המייל ({e.code})")
    return {"new": stored}
