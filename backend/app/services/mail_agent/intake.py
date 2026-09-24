"""Poll each connected mailbox for mail from the agent's watched senders, store
it (body encrypted), and let the AI triage it and — when a reply is expected —
draft one. Nothing is ever sent from here."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.mail_item import DRAFTED, NEEDS_REPLY, NEW, MailItem
from app.models.mail_watch_sender import MailWatchSender
from app.models.mailbox_config import MailboxConfig
from app.models.user import User
from app.services.mail_intake import MailIntakeError
from app.services.mail_intake.search import FoundMessage, find_messages_matching, sender_matches
from app.services.maslaka.approval_watch import _is_auto_reply, reply_text
from app.utils.crypto import decrypt, encrypt

from . import context, usage
from .draft import draft_reply
from . import profile as style_profile
from .llm import LlmUnavailable
from .triage import triage

logger = logging.getLogger(__name__)
KEY = "MAILBOX_ENCRYPTION_KEY"
FIRST_RUN_LOOKBACK = timedelta(days=3)
OVERLAP = timedelta(minutes=10)      # clock skew between us and the mail server


def body_of(item: MailItem) -> str:
    return decrypt(item.encrypted_body, key_env=KEY) if item.encrypted_body else ""


async def poll_mailbox(db: AsyncSession, cfg: MailboxConfig) -> int:
    """Returns how many new items were stored."""
    senders = (await db.execute(
        select(MailWatchSender).where(MailWatchSender.user_id == cfg.user_id)
    )).scalars().all()
    if not senders:
        return 0
    now = datetime.utcnow()
    since = (cfg.mail_agent_checked_at - OVERLAP) if cfg.mail_agent_checked_at else now - FIRST_RUN_LOOKBACK
    messages = await find_messages_matching(db, cfg, matchers=[s.address for s in senders], since=since)

    # Our own outgoing replies can land in the inbox (agent watching their own
    # address, CC-to-self) — never treat them as new mail.
    ours = set((await db.execute(
        select(MailItem.sent_message_id).where(MailItem.user_id == cfg.user_id, MailItem.sent_message_id.isnot(None))
    )).scalars().all())

    own_address = (cfg.email_address or "").strip().lower()
    stored = 0
    for m in reversed(messages):                       # oldest first
        if not m.message_id or m.message_id in ours or _is_auto_reply(m):
            continue
        # Mail FROM the connected mailbox itself is the agent's own outgoing
        # mail (forms they sent, notes-to-self) — never something to answer.
        # Without this, watching your own address made the AI reply to you.
        if m.from_addr == own_address:
            continue
        exists = (await db.execute(
            select(MailItem.id).where(MailItem.user_id == cfg.user_id, MailItem.internet_message_id == m.message_id)
        )).scalar_one_or_none()
        if exists:
            continue
        sender = next((s for s in senders if sender_matches(m.from_addr, s.address)), None)
        item = _new_item(cfg.user_id, sender, m)
        db.add(item)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            continue
        await analyze(db, item, sender, m.text)
        await db.commit()          # per item: a later failure must not undo this one
        stored += 1
    cfg.mail_agent_checked_at = now
    await db.commit()
    return stored


def _new_item(user_id: uuid.UUID, sender: MailWatchSender | None, m: FoundMessage) -> MailItem:
    return MailItem(
        user_id=user_id,
        watch_sender_id=sender.id if sender else None,
        provider_id=m.provider_id,
        internet_message_id=m.message_id[:512],
        in_reply_to=(m.in_reply_to or None) and m.in_reply_to[:512],
        references=m.references,
        from_address=m.from_addr,
        from_name=m.from_name,
        subject=(m.subject or "")[:998],
        received_at=m.received_at,
        encrypted_body=encrypt(m.text or "", key_env=KEY),
        attachments=m.attachments or [],
        linked_company=sender.company_name if sender else None,
        linked_customer_id_number=sender.customer_id_number if sender else None,
        status=NEW,
    )


def _sender_label(item: MailItem, sender: MailWatchSender | None) -> tuple[str, str]:
    label = (sender.label if sender and sender.label else None) or item.from_name or item.from_address
    return f"{label} <{item.from_address}>", (sender.kind if sender else "other")


async def analyze(db: AsyncSession, item: MailItem, sender: MailWatchSender | None, text: str) -> None:
    """Triage, then draft when a reply is expected. Respects the daily cap."""
    own = reply_text(text) or text
    label, kind = _sender_label(item, sender)
    if not await usage.under_cap(db, item.user_id):
        item.ai_skipped_reason = "daily_cap"
        return
    try:
        result, model, u = await triage(
            sender_label=label, sender_kind=kind, subject=item.subject or "",
            own_text=own, attachments=item.attachments or [],
        )
    except LlmUnavailable as e:
        logger.warning("mail_agent: triage unavailable for item %s: %s", item.id, e)
        item.ai_skipped_reason = "ai_unavailable"
        return
    usage.record(db, item.user_id, "mail_triage", model, u)
    item.ai_skipped_reason = None
    item.category = result.get("category")
    item.summary = result.get("summary")
    item.suggested_action = result.get("suggested_action")
    item.entities = {k: result.get(k) for k in ("id_numbers", "policy_numbers", "company", "amounts_quoted") if result.get(k)}
    if not item.linked_company and result.get("company"):
        item.linked_company = result["company"][:100]
    ids = [x.lstrip("0") for x in (result.get("id_numbers") or []) if x]
    if not item.linked_customer_id_number and ids:
        item.linked_customer_id_number = ids[0][:20]
    if result.get("needs_reply"):
        item.status = NEEDS_REPLY
        await make_draft(db, item, sender, own)


async def make_draft(db: AsyncSession, item: MailItem, sender: MailWatchSender | None, own: str | None = None) -> bool:
    """(Re)generate the reply draft. Returns False when capped/unavailable."""
    if own is None:
        own = reply_text(body_of(item)) or body_of(item)
    if not await usage.under_cap(db, item.user_id):
        item.ai_skipped_reason = "daily_cap"
        return False
    user = await db.get(User, item.user_id)
    label, kind = _sender_label(item, sender)
    ids = context.ids_in(own) | set((item.entities or {}).get("id_numbers") or [])
    if item.linked_customer_id_number:
        ids.add(item.linked_customer_id_number)
    ids = {i.lstrip("0") for i in ids if i}
    facts = {
        "חברות שיש להן קובץ נפרעים במערכת": await context.commission_boundaries(db, item.user_id),
        "מוצרי הלקוחות הרלוונטיים (מהפרודוקציה)": await context.customer_products(
            db, item.user_id, id_numbers=ids, email=item.from_address if kind == "customer" else None,
        ),
    }
    try:
        result, model, u = await draft_reply(
            agent_name=(user.full_name if user and user.full_name else ""),
            sender_label=label, subject=item.subject or "", own_text=own,
            summary=item.summary or "", facts=facts,
            profile=await style_profile.load(db, item.user_id), kind=kind,
        )
    except LlmUnavailable as e:
        logger.warning("mail_agent: draft unavailable for item %s: %s", item.id, e)
        item.ai_skipped_reason = "ai_unavailable"
        return False
    usage.record(db, item.user_id, "mail_draft", model, u)
    subj = item.subject or ""
    item.draft_subject = (result.get("subject") or (subj if subj.lower().startswith("re:") else f"Re: {subj}"))[:998]
    item.draft_body = result.get("body") or ""
    item.draft_warnings = result.get("warnings") or []
    item.draft_model = model
    item.draft_edited = False
    item.status = DRAFTED
    return True


async def run_mail_agent_poll() -> None:
    """Scheduler entry point. One session + try per mailbox."""
    if not settings.MAIL_AGENT_ENABLED:
        return
    try:
        async with async_session() as db:
            cfg_ids = (await db.execute(
                select(MailboxConfig.id)
                .where(MailboxConfig.is_active.is_(True), MailboxConfig.mail_host.in_(("google", "microsoft")))
                .where(MailboxConfig.user_id.in_(select(MailWatchSender.user_id)))
            )).scalars().all()
    except Exception as e:  # noqa: BLE001
        logger.error("mail_agent.poll: could not list mailboxes: %s", e)
        return
    for cfg_id in cfg_ids:
        try:
            async with async_session() as db:
                cfg = await db.get(MailboxConfig, cfg_id)
                if cfg:
                    n = await poll_mailbox(db, cfg)
                    if n:
                        logger.info("mail_agent.poll: user=%s stored %d new", cfg.user_id, n)
        except MailIntakeError as e:
            logger.warning("mail_agent.poll: mailbox %s: %s", cfg_id, e.code)
        except Exception:  # noqa: BLE001
            logger.exception("mail_agent.poll: failed for mailbox %s", cfg_id)


async def purge_old_bodies() -> None:
    """Retention: drop email bodies after MAIL_AGENT_RETENTION_DAYS (metadata,
    summary and the sent reply stay)."""
    from sqlalchemy import update
    cutoff = datetime.utcnow() - timedelta(days=settings.MAIL_AGENT_RETENTION_DAYS)
    async with async_session() as db:
        await db.execute(
            update(MailItem).where(MailItem.received_at < cutoff, MailItem.encrypted_body.isnot(None))
            .values(encrypted_body=None)
        )
        await db.commit()
