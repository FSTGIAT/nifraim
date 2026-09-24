"""Send mail FROM the agent's own connected mailbox.

The rest of mail_intake is read-only by design. This is the one outbound seam,
used where the recipient must see the AGENT as the sender — first consumer: the
מסלקה שיוך form, which the helpdesk expects from the agent, not from Nifraim.

Providers:
- **google** (personal @gmail.com): the app password the agent already gave us
  for IMAP also authenticates Gmail SMTP — no new consent. smtp.gmail.com:587
  with STARTTLS (Railway blocks 25/465).
- **microsoft**: needs Graph `Mail.Send`, which the current consent does not
  include (graph.py SCOPES = Mail.Read). Until that consent exists, a Microsoft
  mailbox is reported as not send-capable and the caller falls back.
- **other**: forwarding-only; cannot send.
"""

from __future__ import annotations

import logging
import uuid
from email.message import EmailMessage
from email.utils import formataddr

import aiosmtplib
from sqlalchemy import select

from app.database import async_session
from app.models.mailbox_config import MailboxConfig
from app.utils.crypto import decrypt

from . import ERR_BAD_APP_PASSWORD, ERR_MAILBOX_UNREACHABLE, MailIntakeError

logger = logging.getLogger(__name__)

MAILBOX_KEY = "MAILBOX_ENCRYPTION_KEY"
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


class NoSendableMailbox(Exception):
    """The agent has no connected mailbox we can send from. Not an error — the
    caller decides the fallback."""


async def send_as_agent(user_id: uuid.UUID, msg: EmailMessage, *, display_name: str | None = None) -> str:
    """Send `msg` from the agent's connected mailbox; returns the sending address.

    Raises `NoSendableMailbox` when there is nothing to send from, and
    `MailIntakeError` when there is a mailbox but the send failed — the caller
    must NOT silently fall back then, or the agent believes the form left their
    own mailbox when it did not.
    """
    async with async_session() as db:
        cfg = (await db.execute(
            select(MailboxConfig).where(MailboxConfig.user_id == user_id)
        )).scalar_one_or_none()

    if cfg is None or not cfg.is_active:
        raise NoSendableMailbox("no mailbox connected")
    if cfg.mail_host != "google" or not cfg.encrypted_password:
        raise NoSendableMailbox(f"mailbox host {cfg.mail_host!r} cannot send yet")

    password = decrypt(cfg.encrypted_password, key_env=MAILBOX_KEY)
    address = cfg.email_address
    if "From" in msg:
        del msg["From"]
    msg["From"] = formataddr((display_name, address)) if display_name else address

    smtp = aiosmtplib.SMTP(
        hostname=GMAIL_SMTP_HOST, port=GMAIL_SMTP_PORT, start_tls=True, timeout=30,
    )
    try:
        await smtp.connect()
        await smtp.login(address, password)
        await smtp.send_message(msg)
    except aiosmtplib.SMTPAuthenticationError as e:
        # Never pass the provider text on — it can echo the credential.
        raise MailIntakeError(ERR_BAD_APP_PASSWORD) from e
    except (aiosmtplib.SMTPException, OSError) as e:
        logger.warning("mail_intake.send: gmail smtp failed for user=%s: %s", user_id, type(e).__name__)
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, type(e).__name__) from e
    finally:
        try:
            await smtp.quit()
        except Exception:  # noqa: BLE001 — already failed or closed
            pass
    return address
