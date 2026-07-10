"""Mail intake — pull the emailed Hachshara production zip from the agent's inbox.

Three paths, chosen by MX record (`detect.py`), because the providers' auth rules
are mutually incompatible, not because we prefer variety:

    microsoft  graph.py    OAuth (Exchange Online has basic auth permanently off)
    google     gmail.py    IMAP + app password (OAuth needs a paid CASA audit)
    other      resend.py   the agent forwards mail to us; no credential at all

Every path funnels into `ingest_mail_attachment` below. That is the ONLY function
here that touches `upload_ingest`, so swapping a path's transport (e.g. Gmail
app-password → XOAUTH2 when Google finally kills app passwords) never reaches the
parse/persist pipeline.

Error handling contract: these services raise `MailIntakeError(code)` carrying a
STABLE CODE, never a provider message. `AADSTS65001` and `AUTHENTICATIONFAILED`
mean nothing to an insurance agent, and imaplib error strings can echo the failed
LOGIN line — password included. The frontend maps code → Hebrew copy.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mailbox_config import MailboxConfig
from app.models.mailbox_message import MailboxProcessedMessage
from app.models.upload import FileUpload
from app.services.upload_ingest import ingest_file_bytes, schedule_post_ingest

logger = logging.getLogger(__name__)


# Only Hachshara's production bundle is accepted. Checked BEFORE any parsing, so
# an unrelated attachment in the same mailbox never reaches the zip machinery.
MAILBOX_ATTACHMENT_PATTERN = re.compile(r"^Ild_prod_\d+_\d{4,6}_\d{8}\.zip$", re.IGNORECASE)

# The real bundle is ~4 KB. This ceiling is generous by three orders of magnitude
# and exists only to stop a hostile/huge attachment from being read into memory.
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


# ── Error codes (the frontend maps these to Hebrew; see api/mailbox.py) ──────
ERR_ADMIN_CONSENT = "admin_consent_required"
ERR_CONSENT_REVOKED = "consent_revoked"
ERR_BAD_APP_PASSWORD = "bad_app_password"
ERR_MAILBOX_UNREACHABLE = "mailbox_unreachable"
ERR_ATTACHMENT_UNREADABLE = "attachment_unreadable"
ERR_NOT_CONFIGURED = "not_configured"

STATUS_OK = "ok"
STATUS_INGESTED = "ingested"
STATUS_PARSE_ERROR = "parse_error"
STATUS_REJECTED = "rejected"


class MailIntakeError(Exception):
    """Carries a stable error code, never a provider string."""

    def __init__(self, code: str, detail: str | None = None):
        super().__init__(code)
        self.code = code
        self.detail = detail  # server-side logging only — never returned to the UI


class FetchedAttachment:
    """One candidate attachment, provider-agnostic."""

    __slots__ = ("external_id", "filename", "content", "message_id")

    def __init__(self, external_id: str, filename: str, content: bytes, message_id: str | None = None):
        self.external_id = external_id
        self.filename = filename
        self.content = content
        self.message_id = message_id


async def already_processed(db: AsyncSession, mailbox_id: uuid.UUID, external_id: str) -> bool:
    row = await db.execute(
        select(MailboxProcessedMessage.id).where(
            MailboxProcessedMessage.mailbox_id == mailbox_id,
            MailboxProcessedMessage.external_id == external_id,
        )
    )
    return row.scalar_one_or_none() is not None


async def ingest_mail_attachment(
    db: AsyncSession,
    cfg: MailboxConfig,
    att: FetchedAttachment,
) -> FileUpload | None:
    """Guard, ingest, and ledger one attachment. The single seam onto upload_ingest.

    Returns the FileUpload on success, None when the attachment was rejected or
    failed to parse. Never raises for bad *content* — a permanently-unparseable
    attachment is recorded as handled so it can't wedge the poller into retrying
    it on every poll forever.
    """
    if await already_processed(db, cfg.id, att.external_id):
        return None

    if not MAILBOX_ATTACHMENT_PATTERN.match(att.filename or ""):
        # Not Hachshara's bundle — an invoice, a signature image, anything.
        # Ledger it (and COMMIT) so we don't re-examine the same message next poll.
        await _record(db, cfg, att, status=STATUS_REJECTED, error="filename_not_matched")
        await db.commit()
        return None

    if len(att.content) > MAX_ATTACHMENT_BYTES:
        await _record(db, cfg, att, status=STATUS_REJECTED, error="too_large")
        await db.commit()
        logger.warning("mail_intake: %s exceeds %d bytes", att.filename, MAX_ATTACHMENT_BYTES)
        return None

    try:
        upload, fmt = await ingest_file_bytes(
            db, user_id=cfg.user_id, content=att.content, filename=att.filename, commit=False
        )
    except Exception as e:
        # ingest_file_bytes flushes as it goes, so a failure mid-way can leave the
        # transaction aborted — roll back before writing the ledger row, or the
        # ledger write fails too and the bad attachment retries forever.
        await db.rollback()
        await db.refresh(cfg)
        # Recorded as handled ON PURPOSE — see docstring.
        await _record(db, cfg, att, status=STATUS_PARSE_ERROR, error=str(e)[:500])
        await db.commit()
        logger.exception("mail_intake: %s failed to parse", att.filename)
        return None

    await _record(db, cfg, att, status=STATUS_INGESTED, upload_id=upload.id)
    cfg.last_received_at = datetime.utcnow()
    await db.commit()

    # Fire-and-forget snapshot/summary hooks, exactly as the upload route does.
    schedule_post_ingest(cfg.user_id, upload.id, upload.file_category)
    logger.info(
        "mail_intake: ingested %s for user=%s via %s (%d records)",
        att.filename, cfg.user_id, cfg.mail_host, upload.record_count,
    )
    return upload


async def _record(
    db: AsyncSession,
    cfg: MailboxConfig,
    att: FetchedAttachment,
    *,
    status: str,
    error: str | None = None,
    upload_id: uuid.UUID | None = None,
) -> None:
    db.add(
        MailboxProcessedMessage(
            mailbox_id=cfg.id,
            external_id=att.external_id,
            message_id=att.message_id,
            attachment_filename=att.filename,
            status=status,
            error=error,
            upload_id=upload_id,
        )
    )
    await db.flush()
