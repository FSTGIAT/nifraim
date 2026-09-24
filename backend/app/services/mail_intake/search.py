"""Find messages FROM chosen senders in an agent's inbox — read-only.

The Hachshara poll (`poller.py`) walks the inbox with its own cursors
(`delta_link`, `last_seen_uid`) and only surfaces attachments. A second reader
must not share those cursors or it would steal messages from the first, so this
is a separate, stateless, targeted search: senders + received-after.
Consumers: the מסלקה approval watcher (one sender) and the AI mail agent (the
agent's watch-list — addresses or whole `@domain`s).

Same read-only guarantees as the rest of mail_intake: IMAP EXAMINE +
BODY.PEEK (nothing marked read), Graph Mail.Read only.
"""

from __future__ import annotations

import asyncio
import base64
import email
import email.policy
import html
import imaplib
import re
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import getaddresses, parseaddr, parsedate_to_datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mailbox_config import MailboxConfig
from app.utils.crypto import decrypt, encrypt

from . import ERR_BAD_APP_PASSWORD, ERR_MAILBOX_UNREACHABLE, ERR_NOT_CONFIGURED, MailIntakeError
from . import graph as graph_path

MAILBOX_KEY = "MAILBOX_ENCRYPTION_KEY"
MAX_MESSAGES = 25
# IMAP OR-trees get deep; search senders in chunks.
_IMAP_SENDER_CHUNK = 20


@dataclass
class FoundMessage:
    message_id: str            # RFC 5322 Message-ID (angle brackets kept)
    received_at: datetime      # naive UTC, like every other timestamp in the app
    subject: str
    from_addr: str             # lower-cased bare address
    text: str                  # plain-text body (HTML flattened)
    auto_submitted: bool = False   # RFC 3834 Auto-Submitted / vacation responder
    provider_id: str | None = None     # IMAP uid (as str) / Graph message id
    from_name: str | None = None
    in_reply_to: str | None = None
    references: str | None = None
    attachments: list[dict] = field(default_factory=list)   # [{name, size, content_type}]
    to_addrs: list[str] = field(default_factory=list)          # lower-cased To + Cc


def sender_matches(sender: str, matcher: str) -> bool:
    """`matcher` is an address, or "@domain" for a whole domain."""
    sender, matcher = (sender or "").strip().lower(), (matcher or "").strip().lower()
    return sender.endswith(matcher) if matcher.startswith("@") else sender == matcher


async def find_messages_from(
    db: AsyncSession, cfg: MailboxConfig, *, sender: str, since: datetime,
) -> list[FoundMessage]:
    """Messages from one `sender` received at/after `since`, newest first."""
    return await find_messages_matching(db, cfg, matchers=[sender], since=since)


async def find_messages_matching(
    db: AsyncSession, cfg: MailboxConfig, *, matchers: list[str], since: datetime,
) -> list[FoundMessage]:
    """Messages from any of `matchers` (addresses / @domains) received at/after
    `since` (naive UTC), newest first."""
    matchers = sorted({m.strip().lower() for m in matchers if m and m.strip()})
    if not matchers:
        return []
    if cfg.mail_host == "google":
        password = _google_password(cfg)
        found: list[FoundMessage] = []
        for i in range(0, len(matchers), _IMAP_SENDER_CHUNK):
            found += await asyncio.to_thread(
                _imap_search, cfg.imap_host or "imap.gmail.com", cfg.imap_port or 993,
                cfg.folder or "INBOX", cfg.email_address, password,
                matchers[i:i + _IMAP_SENDER_CHUNK], since,
            )
    elif cfg.mail_host == "microsoft":
        found = await _graph_search(db, cfg, matchers, since)
    else:
        raise MailIntakeError(ERR_NOT_CONFIGURED, f"cannot read host {cfg.mail_host!r}")
    seen: set[str] = set()
    out = []
    for m in found:
        key = m.message_id or f"{m.provider_id}"
        if key in seen or m.received_at < since:
            continue
        if not any(sender_matches(m.from_addr, x) for x in matchers):
            continue
        seen.add(key)
        out.append(m)
    return sorted(out, key=lambda m: m.received_at, reverse=True)


async def find_sent_to(
    db: AsyncSession, cfg: MailboxConfig, *, matchers: list[str], since: datetime,
) -> list[FoundMessage]:
    """The agent's OWN sent mail addressed to any of `matchers` (addresses /
    @domains), newest first. Read-only; the Sent folder is found by flag."""
    matchers = sorted({m.strip().lower() for m in matchers if m and m.strip()})
    if not matchers:
        return []
    if cfg.mail_host == "google":
        password = _google_password(cfg)
        found: list[FoundMessage] = []
        for i in range(0, len(matchers), _IMAP_SENDER_CHUNK):
            found += await asyncio.to_thread(
                _imap_search_sent, cfg.imap_host or "imap.gmail.com", cfg.imap_port or 993,
                cfg.email_address, password, matchers[i:i + _IMAP_SENDER_CHUNK], since,
            )
    elif cfg.mail_host == "microsoft":
        found = await _graph_sent(db, cfg, since)
    else:
        raise MailIntakeError(ERR_NOT_CONFIGURED, f"cannot read host {cfg.mail_host!r}")
    seen: set[str] = set()
    out = []
    for m in found:
        key = m.message_id or f"{m.provider_id}"
        if key in seen or m.received_at < since:
            continue
        # IMAP TO is a substring match — keep only mail really sent to a watched sender.
        if not any(sender_matches(a, x) for a in m.to_addrs for x in matchers):
            continue
        seen.add(key)
        out.append(m)
    return sorted(out, key=lambda m: m.received_at, reverse=True)


async def fetch_attachment(
    db: AsyncSession, cfg: MailboxConfig, *, provider_id: str, filename: str,
) -> bytes | None:
    """Download one attachment on demand (the intake keeps metadata only)."""
    if cfg.mail_host == "google":
        return await asyncio.to_thread(
            _imap_fetch_attachment, cfg.imap_host or "imap.gmail.com", cfg.imap_port or 993,
            cfg.folder or "INBOX", cfg.email_address, _google_password(cfg), provider_id, filename,
        )
    if cfg.mail_host == "microsoft":
        access = await _graph_access(db, cfg)
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{graph_path._GRAPH}/me/messages/{provider_id}/attachments",
                headers={"Authorization": f"Bearer {access}"},
            )
        if r.status_code >= 400:
            raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, f"graph {r.status_code}")
        for a in r.json().get("value", []):
            if a.get("name") == filename and a.get("contentBytes"):
                return base64.b64decode(a["contentBytes"])
        return None
    raise MailIntakeError(ERR_NOT_CONFIGURED, f"cannot read host {cfg.mail_host!r}")


def _google_password(cfg: MailboxConfig) -> str:
    if not cfg.encrypted_password:
        raise MailIntakeError(ERR_NOT_CONFIGURED)
    return decrypt(cfg.encrypted_password, key_env=MAILBOX_KEY)


# ── Gmail (IMAP) ─────────────────────────────────────────────────────────────
def _imap_connect(host, port, address, password, folder: str | None) -> imaplib.IMAP4_SSL:
    try:
        conn = imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context(), timeout=30)
    except (OSError, imaplib.IMAP4.error) as e:
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, type(e).__name__) from e
    try:
        conn.login(address, password)
    except imaplib.IMAP4.error as e:
        _logout(conn)
        raise MailIntakeError(ERR_BAD_APP_PASSWORD) from e
    if folder is None:                                      # caller will LIST first
        return conn
    # Quoted: "[Gmail]/Sent Mail" has a space; imaplib sends names verbatim.
    status, _ = conn.select(_imap_quote(folder), readonly=True)   # EXAMINE
    if status != "OK":
        _logout(conn)
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, "select failed")
    return conn


def _logout(conn) -> None:
    try:
        conn.logout()
    except Exception:  # noqa: BLE001
        pass


def _imap_quote(name: str) -> str:
    if name.startswith('"'):
        return name
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


_LIST_LINE = re.compile(rb'^\((?P<flags>[^)]*)\) (?:"[^"]*"|NIL) (?P<name>.+)$')


def _imap_sent_folder(conn: imaplib.IMAP4_SSL) -> str | None:
    """The Sent folder by its RFC 6154 \\Sent flag — Gmail localises the name
    ("[Gmail]/דואר יוצא" on a Hebrew UI), so never assume "[Gmail]/Sent Mail".
    Returns the raw (modified UTF-7) name, quoted as the server listed it."""
    status, lines = conn.list()
    if status != "OK":
        return None
    fallback = None
    for line in lines or []:
        if not isinstance(line, bytes):
            continue
        m = _LIST_LINE.match(line)
        if not m:
            continue
        flags = m.group("flags").lower()
        name = m.group("name").decode("ascii", "replace").strip()
        if b"\\sent" in flags:
            return name
        if fallback is None and name.strip('"').lower() in ("sent", "sent items", "sent mail", "inbox.sent"):
            fallback = name
    return fallback


def _imap_from_criteria(matchers: list[str], header: str = "FROM") -> list[str]:
    """FROM a  |  OR FROM a FROM b  |  OR FROM a OR FROM b FROM c … (IMAP prefix OR).
    IMAP FROM is a substring match, so "@domain" works as-is; the exact match
    happens afterwards in find_messages_matching."""
    terms = [[header, f'"{m}"'] for m in matchers]
    crit = terms[-1]
    for t in reversed(terms[:-1]):
        crit = ["OR", *t, *crit]
    return crit


def _imap_search(host, port, folder, address, password, matchers, since, header: str = "FROM") -> list[FoundMessage]:
    conn = _imap_connect(host, port, address, password, folder)
    try:
        return _imap_search_conn(conn, matchers, since, header)
    finally:
        _logout(conn)


def _imap_search_sent(host, port, address, password, matchers, since) -> list[FoundMessage]:
    conn = _imap_connect(host, port, address, password, None)
    try:
        folder = _imap_sent_folder(conn)
        if not folder:
            return []
        status, _ = conn.select(_imap_quote(folder), readonly=True)    # EXAMINE
        if status != "OK":
            return []
        return _imap_search_conn(conn, matchers, since, "TO")
    finally:
        _logout(conn)


def _imap_search_conn(conn, matchers, since, header) -> list[FoundMessage]:
    # SINCE is date-granular and server-local; widen by a day and filter
    # precisely on the parsed Date afterwards.
    since_str = (since - timedelta(days=1)).strftime("%d-%b-%Y")
    status, data = conn.uid("SEARCH", None, *_imap_from_criteria(matchers, header), "SINCE", since_str)
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
            msg = _parse_rfc822(raw, provider_id=uid.decode())
            if msg:
                out.append(msg)
    return out


def _imap_fetch_attachment(host, port, folder, address, password, uid, filename) -> bytes | None:
    conn = _imap_connect(host, port, address, password, folder)
    try:
        status, parts = conn.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if status != "OK":
            return None
        raw = next((p[1] for p in parts if isinstance(p, tuple) and len(p) > 1), None)
        if not raw:
            return None
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        for part in msg.iter_attachments():
            if part.get_filename() == filename:
                return part.get_payload(decode=True)
        return None
    finally:
        _logout(conn)


def _header_text(compat_msg, name: str) -> str:
    """A header as readable text. Some Israeli servers (e.g. Pelephone) put RAW
    Hebrew bytes in From/Subject instead of RFC 2047 encoded-words; the default
    policy turns those into U+FFFD for good. Read the raw bytes instead and
    decode them — UTF-8 first, then Windows-1255 / ISO-8859-8."""
    from email.header import Header, decode_header
    # raw_items(): the value exactly as parsed (8-bit bytes kept as surrogate
    # escapes) — .get() would already have wrapped it in a lossy Header.
    v = next((val for key, val in compat_msg.raw_items() if key.lower() == name.lower()), None)
    if v is None:
        return ""
    if isinstance(v, Header):
        v = str(v)
    v = " ".join(v.split())          # unfold continuation lines
    if any("\udc80" <= c <= "\udcff" for c in v):
        b = v.encode("ascii", "surrogateescape")
        for enc in ("utf-8", "cp1255", "iso-8859-8"):
            try:
                return b.decode(enc)
            except UnicodeDecodeError:
                continue
        return b.decode("utf-8", "replace")
    try:
        parts = decode_header(v)
    except Exception:  # noqa: BLE001 — malformed encoded-word: show it as-is
        return v
    out = []
    for chunk, charset in parts:
        if isinstance(chunk, str):
            out.append(chunk)
            continue
        out.append(_decode_bytes(chunk, charset))
    return "".join(out).strip()


# Charset labels mail clients use that Python's codec registry doesn't know.
# Hebrew mail (Outlook/iOS on Israeli carriers) says "iso-8859-8-i" (logical
# order) — byte-identical to iso-8859-8; unknown, it decoded to U+FFFD.
_CHARSET_ALIASES = {"iso-8859-8-i": "iso-8859-8", "iso-8859-8-e": "iso-8859-8", "windows-1255": "cp1255"}


def _decode_bytes(b: bytes, charset: str | None) -> str:
    cs = (charset or "").strip().lower()
    cs = _CHARSET_ALIASES.get(cs, cs)
    for enc in [c for c in (cs, "utf-8", "cp1255") if c]:
        try:
            return b.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return b.decode("utf-8", "replace")


def _parse_rfc822(raw: bytes, *, provider_id: str | None = None) -> FoundMessage | None:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    compat = email.message_from_bytes(raw, policy=email.policy.compat32)
    try:
        received = parsedate_to_datetime(msg["Date"]).astimezone(timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, AttributeError):
        return None
    body = msg.get_body(preferencelist=("plain", "html"))
    text = ""
    if body is not None:
        try:
            content = body.get_content()
        except (LookupError, UnicodeDecodeError):
            # e.g. charset="iso-8859-8-i" — decode the bytes ourselves
            content = _decode_bytes(body.get_payload(decode=True) or b"", body.get_content_charset())
        text = _html_to_text(content) if body.get_content_type() == "text/html" else content
    name, addr = parseaddr(_header_text(compat, "From"))
    to_addrs = [a.lower() for _, a in getaddresses([_header_text(compat, "To"), _header_text(compat, "Cc")]) if a]
    attachments = []
    for part in msg.iter_attachments():
        fn = part.get_filename()
        if fn:
            payload = part.get_payload(decode=True) or b""
            attachments.append({"name": fn, "size": len(payload), "content_type": part.get_content_type()})
    return FoundMessage(
        message_id=(msg["Message-ID"] or "").strip(),
        received_at=received,
        subject=_header_text(compat, "Subject"),
        from_addr=addr.lower(),
        text=text,
        auto_submitted=(
            str(msg["Auto-Submitted"] or "no").strip().lower() not in ("", "no")
            or bool(msg["X-Autoreply"]) or bool(msg["X-Autorespond"])
        ),
        provider_id=provider_id,
        from_name=name or None,
        in_reply_to=(str(msg["In-Reply-To"]).strip() if msg["In-Reply-To"] else None),
        references=(str(msg["References"]).strip() if msg["References"] else None),
        attachments=attachments,
        to_addrs=to_addrs,
    )


# ── Microsoft 365 (Graph, Mail.Read) ─────────────────────────────────────────
async def _graph_access(db: AsyncSession, cfg: MailboxConfig) -> str:
    if not graph_path.is_configured() or not cfg.encrypted_refresh_token:
        raise MailIntakeError(ERR_NOT_CONFIGURED)
    refresh = decrypt(cfg.encrypted_refresh_token, key_env=MAILBOX_KEY)
    access, rotated = await graph_path.access_token_from_refresh(refresh)
    if rotated and rotated != refresh:
        # Same rule as the poller: persist a rotated token immediately.
        cfg.encrypted_refresh_token = encrypt(rotated, key_env=MAILBOX_KEY)
        await db.flush()
    return access


async def _graph_search(db: AsyncSession, cfg: MailboxConfig, matchers: list[str], since: datetime) -> list[FoundMessage]:
    access = await _graph_access(db, cfg)
    # Filter on time only and match the sender locally — combining a from/
    # filter with receivedDateTime is the classic Graph "InefficientFilter".
    params = {
        "$filter": f"receivedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "$orderby": "receivedDateTime desc",
        "$top": str(MAX_MESSAGES * 2),
        "$select": "id,subject,from,receivedDateTime,internetMessageId,body,internetMessageHeaders,hasAttachments",
        "$expand": "attachments($select=name,size,contentType)",
    }
    headers = {"Authorization": f"Bearer {access}", "Prefer": 'outlook.body-content-type="text"'}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{graph_path._GRAPH}/me/mailFolders/inbox/messages", params=params, headers=headers)
    if r.status_code >= 400:
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, f"graph {r.status_code}")
    out: list[FoundMessage] = []
    for m in r.json().get("value", []):
        sender = (m.get("from") or {}).get("emailAddress") or {}
        addr = (sender.get("address") or "").lower()
        if not any(sender_matches(addr, x) for x in matchers):
            continue
        try:
            received = datetime.fromisoformat(m["receivedDateTime"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        hdrs = {h.get("name", "").lower(): h.get("value") for h in (m.get("internetMessageHeaders") or [])}
        out.append(FoundMessage(
            message_id=(m.get("internetMessageId") or "").strip(),
            received_at=received.astimezone(timezone.utc).replace(tzinfo=None),
            subject=m.get("subject") or "",
            from_addr=addr,
            text=((m.get("body") or {}).get("content") or ""),
            auto_submitted=str(hdrs.get("auto-submitted") or "no").lower() not in ("", "no"),
            provider_id=m.get("id"),
            from_name=sender.get("name"),
            in_reply_to=hdrs.get("in-reply-to"),
            references=hdrs.get("references"),
            attachments=[
                {"name": a.get("name"), "size": a.get("size"), "content_type": a.get("contentType")}
                for a in (m.get("attachments") or []) if a.get("name")
            ],
        ))
    return out


async def _graph_sent(db: AsyncSession, cfg: MailboxConfig, since: datetime) -> list[FoundMessage]:
    access = await _graph_access(db, cfg)
    params = {
        "$filter": f"sentDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "$orderby": "sentDateTime desc",
        "$top": "100",
        "$select": "id,subject,toRecipients,ccRecipients,sentDateTime,internetMessageId,body",
    }
    headers = {"Authorization": f"Bearer {access}", "Prefer": 'outlook.body-content-type="text"'}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{graph_path._GRAPH}/me/mailFolders/sentitems/messages", params=params, headers=headers)
    if r.status_code >= 400:
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, f"graph {r.status_code}")
    out: list[FoundMessage] = []
    for m in r.json().get("value", []):
        try:
            sent = datetime.fromisoformat(m["sentDateTime"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        rcpts = [((x.get("emailAddress") or {}).get("address") or "").lower()
                 for x in (m.get("toRecipients") or []) + (m.get("ccRecipients") or [])]
        out.append(FoundMessage(
            message_id=(m.get("internetMessageId") or "").strip(),
            received_at=sent.astimezone(timezone.utc).replace(tzinfo=None),
            subject=m.get("subject") or "",
            from_addr=(cfg.email_address or "").lower(),
            text=((m.get("body") or {}).get("content") or ""),
            provider_id=m.get("id"),
            to_addrs=[a for a in rcpts if a],
        ))
    return out


_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"(?i)<\s*(br|/p|/div|/tr|/li)\s*/?>")


def _html_to_text(s: str) -> str:
    return html.unescape(_TAG.sub("", _BLOCK.sub("\n", s)))
