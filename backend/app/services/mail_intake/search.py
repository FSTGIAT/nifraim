"""Find messages FROM a given sender in an agent's inbox — read-only.

The Hachshara poll (`poller.py`) walks the inbox with its own cursors
(`delta_link`, `last_seen_uid`) and only surfaces attachments. A second reader
must not share those cursors or it would steal messages from the first, so this
is a separate, stateless, targeted search: sender + received-after. First
consumer: the מסלקה approval watcher.

Same read-only guarantees as the rest of mail_intake: IMAP EXAMINE +
BODY.PEEK (nothing marked read), Graph Mail.Read only.
"""

from __future__ import annotations

import asyncio
import email
import email.policy
import html
import imaplib
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr, parsedate_to_datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mailbox_config import MailboxConfig
from app.utils.crypto import decrypt, encrypt

from . import ERR_BAD_APP_PASSWORD, ERR_MAILBOX_UNREACHABLE, ERR_NOT_CONFIGURED, MailIntakeError
from . import graph as graph_path

MAILBOX_KEY = "MAILBOX_ENCRYPTION_KEY"
MAX_MESSAGES = 25


@dataclass
class FoundMessage:
    message_id: str            # RFC 5322 Message-ID (angle brackets kept)
    received_at: datetime      # naive UTC, like every other timestamp in the app
    subject: str
    from_addr: str             # lower-cased bare address
    text: str                  # plain-text body (HTML flattened)
    auto_submitted: bool = False   # RFC 3834 Auto-Submitted / vacation responder


async def find_messages_from(
    db: AsyncSession, cfg: MailboxConfig, *, sender: str, since: datetime,
) -> list[FoundMessage]:
    """Messages from `sender` received at/after `since` (naive UTC), newest first."""
    sender = sender.strip().lower()
    if cfg.mail_host == "google":
        if not cfg.encrypted_password:
            raise MailIntakeError(ERR_NOT_CONFIGURED)
        password = decrypt(cfg.encrypted_password, key_env=MAILBOX_KEY)
        found = await asyncio.to_thread(
            _imap_search, cfg.imap_host or "imap.gmail.com", cfg.imap_port or 993,
            cfg.folder or "INBOX", cfg.email_address, password, sender, since,
        )
    elif cfg.mail_host == "microsoft":
        found = await _graph_search(db, cfg, sender, since)
    else:
        raise MailIntakeError(ERR_NOT_CONFIGURED, f"cannot read host {cfg.mail_host!r}")
    found = [m for m in found if m.from_addr == sender and m.received_at >= since]
    return sorted(found, key=lambda m: m.received_at, reverse=True)


# ── Gmail (IMAP) ─────────────────────────────────────────────────────────────
def _imap_search(host, port, folder, address, password, sender, since) -> list[FoundMessage]:
    try:
        conn = imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context(), timeout=30)
    except (OSError, imaplib.IMAP4.error) as e:
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, type(e).__name__) from e
    try:
        try:
            conn.login(address, password)
        except imaplib.IMAP4.error as e:
            raise MailIntakeError(ERR_BAD_APP_PASSWORD) from e
        status, _ = conn.select(folder, readonly=True)          # EXAMINE
        if status != "OK":
            raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, "select failed")
        # SINCE is date-granular and server-local; widen by a day and filter
        # precisely on the parsed Date afterwards.
        since_str = (since - timedelta(days=1)).strftime("%d-%b-%Y")
        status, data = conn.uid("SEARCH", None, "FROM", f'"{sender}"', "SINCE", since_str)
        if status != "OK" or not data or not data[0]:
            return []
        uids = data[0].split()[-MAX_MESSAGES:]
        out: list[FoundMessage] = []
        for uid in uids:
            status, parts = conn.uid("FETCH", uid, "(BODY.PEEK[])")   # PEEK: stays unread
            if status != "OK":
                continue
            raw = next((p[1] for p in parts if isinstance(p, tuple) and len(p) > 1), None)
            if raw:
                msg = _parse_rfc822(raw)
                if msg:
                    out.append(msg)
        return out
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001
            pass


def _parse_rfc822(raw: bytes) -> FoundMessage | None:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    try:
        received = parsedate_to_datetime(msg["Date"]).astimezone(timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, AttributeError):
        return None
    body = msg.get_body(preferencelist=("plain", "html"))
    text = ""
    if body is not None:
        content = body.get_content()
        text = _html_to_text(content) if body.get_content_type() == "text/html" else content
    return FoundMessage(
        message_id=(msg["Message-ID"] or "").strip(),
        received_at=received,
        subject=str(msg["Subject"] or ""),
        from_addr=parseaddr(str(msg["From"] or ""))[1].lower(),
        text=text,
        auto_submitted=(
            str(msg["Auto-Submitted"] or "no").strip().lower() not in ("", "no")
            or bool(msg["X-Autoreply"]) or bool(msg["X-Autorespond"])
        ),
    )


# ── Microsoft 365 (Graph, Mail.Read) ─────────────────────────────────────────
async def _graph_search(db: AsyncSession, cfg: MailboxConfig, sender: str, since: datetime) -> list[FoundMessage]:
    if not graph_path.is_configured() or not cfg.encrypted_refresh_token:
        raise MailIntakeError(ERR_NOT_CONFIGURED)
    refresh = decrypt(cfg.encrypted_refresh_token, key_env=MAILBOX_KEY)
    access, rotated = await graph_path.access_token_from_refresh(refresh)
    if rotated and rotated != refresh:
        # Same rule as the poller: persist a rotated token immediately.
        cfg.encrypted_refresh_token = encrypt(rotated, key_env=MAILBOX_KEY)
        await db.flush()

    # Filter on time only and match the sender locally — combining a from/
    # filter with receivedDateTime is the classic Graph "InefficientFilter".
    params = {
        "$filter": f"receivedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "$orderby": "receivedDateTime desc",
        "$top": str(MAX_MESSAGES * 2),
        "$select": "subject,from,receivedDateTime,internetMessageId,body",
    }
    headers = {"Authorization": f"Bearer {access}", "Prefer": 'outlook.body-content-type="text"'}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{graph_path._GRAPH}/me/mailFolders/inbox/messages", params=params, headers=headers)
    if r.status_code >= 400:
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, f"graph {r.status_code}")
    out: list[FoundMessage] = []
    for m in r.json().get("value", []):
        addr = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()
        if addr != sender:
            continue
        try:
            received = datetime.fromisoformat(m["receivedDateTime"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        out.append(FoundMessage(
            message_id=(m.get("internetMessageId") or "").strip(),
            received_at=received.astimezone(timezone.utc).replace(tzinfo=None),
            subject=m.get("subject") or "",
            from_addr=addr,
            text=((m.get("body") or {}).get("content") or ""),
        ))
    return out


_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"(?i)<\s*(br|/p|/div|/tr|/li)\s*/?>")


def _html_to_text(s: str) -> str:
    return html.unescape(_TAG.sub("", _BLOCK.sub("\n", s)))
