"""Path B — Gmail / Google Workspace via IMAP + app password.

Google killed plain legacy passwords for IMAP in March 2025, but app passwords
still work when 2-Step Verification is on. The "proper" alternative is XOAUTH2
with `gmail.readonly` — a Google **restricted** scope, which drags in a CASA
security assessment by an approved lab, revalidated annually. Not worth it to
read one zip a month, so the app password stands here.

Security posture, in order of importance:
  * An app password grants FULL mailbox access. The UI must say so.
  * We `select(..., readonly=True)`, which issues EXAMINE — `\\Seen` is never
    touched and we never STORE/EXPUNGE/DELETE. Read-only by construction.
  * imaplib's exception strings can echo the failed `LOGIN` command, password
    included. Never let one reach a log line, a DB column, or the UI.

`imaplib` is blocking and this app is fully async, so the whole conversation runs
inside one `asyncio.to_thread` call. Chosen over `aioimaplib` deliberately: the
poll is infrequent and finishes in seconds, so a short-lived thread never starves
the loop, and it avoids a third-party dependency on the path handling the agent's
most sensitive credential.
"""

from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import ssl
from email.message import Message

from app.services.mail_intake import (
    ERR_BAD_APP_PASSWORD,
    ERR_MAILBOX_UNREACHABLE,
    FetchedAttachment,
    MailIntakeError,
)

logger = logging.getLogger(__name__)

_IMAP_TIMEOUT_S = 30
# Gmail returns the whole mailbox for "1:*". On a first connect (no cursor) we
# only look at the newest slice — the Hachshara mail arrives monthly, and
# walking a 100k-message mailbox on first setup would time out.
_FIRST_RUN_LOOKBACK = 200


class ImapResult:
    __slots__ = ("uidvalidity", "last_uid", "attachments")

    def __init__(self, uidvalidity: int, last_uid: int | None, attachments: list[FetchedAttachment]):
        self.uidvalidity = uidvalidity
        self.last_uid = last_uid
        self.attachments = attachments


async def fetch_new_attachments(
    *, host: str, port: int, folder: str, email_address: str, password: str,
    uidvalidity: int | None, last_seen_uid: int | None,
) -> ImapResult:
    return await asyncio.to_thread(
        _fetch_new_attachments_sync,
        host, port, folder, email_address, password, uidvalidity, last_seen_uid,
    )


def _fetch_new_attachments_sync(
    host: str, port: int, folder: str, email_address: str, password: str,
    uidvalidity: int | None, last_seen_uid: int | None,
) -> ImapResult:
    """Blocking. IMAP4_SSL + EXAMINE (read-only). Never STORE/EXPUNGE/DELETE."""
    context = ssl.create_default_context()  # verifies the cert chain + hostname
    try:
        conn = imaplib.IMAP4_SSL(host, port, ssl_context=context, timeout=_IMAP_TIMEOUT_S)
    except Exception as e:
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, type(e).__name__) from None

    try:
        try:
            conn.login(email_address, password)
        except imaplib.IMAP4.error:
            # str(e) can contain the echoed LOGIN line. Never propagate it.
            raise MailIntakeError(ERR_BAD_APP_PASSWORD) from None

        # readonly=True → EXAMINE, not SELECT.
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, "select failed")

        server_uidvalidity = _uidvalidity(conn)

        # A changed UIDVALIDITY invalidates every stored uid — the server has
        # renumbered the mailbox. Restart the cursor rather than silently
        # skipping (or re-ingesting) mail.
        if uidvalidity is not None and server_uidvalidity != uidvalidity:
            logger.info(
                "gmail: UIDVALIDITY changed %s -> %s, resetting cursor",
                uidvalidity, server_uidvalidity,
            )
            last_seen_uid = None

        uids = _search_uids(conn, last_seen_uid)
        attachments: list[FetchedAttachment] = []
        highest = last_seen_uid

        for uid in uids:
            highest = uid if highest is None else max(highest, uid)
            msg = _fetch_message(conn, uid)
            if msg is None:
                continue
            for filename, content in _iter_attachments(msg):
                attachments.append(
                    FetchedAttachment(
                        # A uid is unique only within one UIDVALIDITY epoch, so
                        # the epoch must be part of the dedup key.
                        external_id=f"{server_uidvalidity}:{uid}:{filename}",
                        filename=filename,
                        content=content,
                        message_id=msg.get("Message-ID"),
                    )
                )

        return ImapResult(server_uidvalidity, highest, attachments)
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _uidvalidity(conn: imaplib.IMAP4_SSL) -> int:
    status, data = conn.response("UIDVALIDITY")
    if status == "OK" and data and data[0]:
        try:
            return int(data[0])
        except (TypeError, ValueError):
            pass
    raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, "no UIDVALIDITY")


def _search_uids(conn: imaplib.IMAP4_SSL, last_seen_uid: int | None) -> list[int]:
    if last_seen_uid:
        criteria = f"{last_seen_uid + 1}:*"
    else:
        criteria = "1:*"
    status, data = conn.uid("SEARCH", None, "UID", criteria)
    if status != "OK" or not data or data[0] is None:
        return []
    uids = [int(x) for x in data[0].split()]
    # `n:*` always returns at least the newest message even when n exceeds it,
    # so filter rather than trust the server's range semantics.
    if last_seen_uid:
        uids = [u for u in uids if u > last_seen_uid]
    else:
        uids = uids[-_FIRST_RUN_LOOKBACK:]
    return sorted(uids)


def _fetch_message(conn: imaplib.IMAP4_SSL, uid: int) -> Message | None:
    # BODY.PEEK, not BODY — peeking is what keeps the message unread.
    status, data = conn.uid("FETCH", str(uid), "(BODY.PEEK[])")
    if status != "OK" or not data or not data[0]:
        return None
    raw = data[0][1] if isinstance(data[0], tuple) else None
    if not raw:
        return None
    return email.message_from_bytes(raw)


def _iter_attachments(msg: Message):
    """Yield (filename, bytes) for each real file attachment."""
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if not filename:
            continue
        try:
            payload = part.get_payload(decode=True)  # handles base64 / quoted-printable
        except Exception:
            continue
        if payload:
            yield filename, payload
