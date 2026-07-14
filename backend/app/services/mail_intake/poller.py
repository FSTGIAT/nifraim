"""Poll one mailbox. Paths A and B pull; path C is pushed to us by Resend.

Backoff matters here: repeated auth failures against Google or Microsoft get an
account rate-limited or locked, and the agent then can't read their own mail.
So a mailbox that has failed N times in a row is skipped for a while rather than
hammered every 15 minutes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mailbox_config import MailboxConfig
from app.services.mail_intake import (
    ERR_ADMIN_CONSENT,
    ERR_CONSENT_DECLINED,
    ERR_NOT_CONFIGURED,
    STATUS_OK,
    MailIntakeError,
    ingest_mail_attachment,
)
from app.services.mail_intake import gmail as gmail_path
from app.services.mail_intake import graph as graph_path
from app.utils.crypto import decrypt, encrypt

logger = logging.getLogger(__name__)

MAILBOX_KEY = "MAILBOX_ENCRYPTION_KEY"

# Skip a failing mailbox for 2^failures * 15min, capped at 6h. An auth error is
# sticky (a revoked token stays revoked) — retrying it hard achieves nothing but
# a provider-side lockout.
_BACKOFF_BASE = timedelta(minutes=15)
_BACKOFF_CAP = timedelta(hours=6)


def _in_backoff(cfg: MailboxConfig, now: datetime) -> bool:
    if not cfg.consecutive_failures or not cfg.last_polled_at:
        return False
    delay = min(_BACKOFF_BASE * (2 ** (cfg.consecutive_failures - 1)), _BACKOFF_CAP)
    return now < cfg.last_polled_at + delay


async def poll_mailbox(db: AsyncSession, cfg: MailboxConfig, *, force: bool = False) -> int:
    """Fetch + ingest anything new. Returns the number of files ingested.

    Never raises: a failure is recorded as an error CODE on the config row and
    surfaced in the UI as Hebrew copy.
    """
    now = datetime.utcnow()
    if not force and _in_backoff(cfg, now):
        return 0

    try:
        if cfg.mail_host == "microsoft":
            attachments = await _fetch_microsoft(db, cfg)
        elif cfg.mail_host == "google":
            attachments = await _fetch_google(cfg)
        else:
            # "other" is push-only — Resend calls us. Nothing to poll.
            return 0
    except MailIntakeError as e:
        _mark_failure(cfg, e.code, now)
        await db.commit()
        logger.warning("mail_intake: poll failed for user=%s: %s (%s)", cfg.user_id, e.code, e.detail)
        return 0
    except Exception as e:
        _mark_failure(cfg, "mailbox_unreachable", now)
        await db.commit()
        logger.exception("mail_intake: unexpected poll failure for user=%s: %s", cfg.user_id, type(e).__name__)
        return 0

    ingested = 0
    for att in attachments:
        upload = await ingest_mail_attachment(db, cfg, att)
        if upload is not None:
            ingested += 1

    cfg.last_polled_at = now
    cfg.last_status = STATUS_OK
    cfg.last_error = None
    cfg.consecutive_failures = 0
    await db.commit()
    return ingested


# The consent screen already said WHY there is no token. Both of these are answers
# an agent can act on ("approve it", "ask your admin"); ERR_NOT_CONFIGURED is not.
_KEEP_OVER_NOT_CONFIGURED = (ERR_CONSENT_DECLINED, ERR_ADMIN_CONSENT)


def _mark_failure(cfg: MailboxConfig, code: str, now: datetime) -> None:
    cfg.last_polled_at = now
    cfg.last_status = "error"
    # A poll of a token-less microsoft mailbox always yields not_configured. Letting
    # that overwrite a consent refusal downgrades a specific, actionable reason into
    # "החיבור עדיין לא הושלם" — which is what an agent saw after pressing בדיקה.
    if not (code == ERR_NOT_CONFIGURED and cfg.last_error in _KEEP_OVER_NOT_CONFIGURED):
        cfg.last_error = code        # a CODE, never a provider message
    cfg.consecutive_failures = (cfg.consecutive_failures or 0) + 1


async def _fetch_microsoft(db: AsyncSession, cfg: MailboxConfig):
    if not graph_path.is_configured() or not cfg.encrypted_refresh_token:
        raise MailIntakeError(ERR_NOT_CONFIGURED)

    refresh = decrypt(cfg.encrypted_refresh_token, key_env=MAILBOX_KEY)
    access, rotated = await graph_path.access_token_from_refresh(refresh)
    # Microsoft rotates refresh tokens. Persist the new one immediately — losing
    # it means the next poll dies with invalid_grant and the agent must re-consent.
    if rotated and rotated != refresh:
        cfg.encrypted_refresh_token = encrypt(rotated, key_env=MAILBOX_KEY)
        await db.flush()

    attachments, next_delta = await graph_path.fetch_new_attachments(access, cfg.delta_link)
    if next_delta:
        cfg.delta_link = next_delta
    return attachments


async def _fetch_google(cfg: MailboxConfig):
    if not cfg.encrypted_password:
        raise MailIntakeError(ERR_NOT_CONFIGURED)

    password = decrypt(cfg.encrypted_password, key_env=MAILBOX_KEY)
    result = await gmail_path.fetch_new_attachments(
        host=cfg.imap_host,
        port=cfg.imap_port,
        folder=cfg.folder,
        email_address=cfg.email_address,
        password=password,
        uidvalidity=cfg.uidvalidity,
        last_seen_uid=cfg.last_seen_uid,
    )
    # Advance the cursor even when nothing matched our filename filter, or every
    # poll re-walks the same messages forever.
    cfg.uidvalidity = result.uidvalidity
    if result.last_uid is not None:
        cfg.last_seen_uid = result.last_uid
    return result.attachments
