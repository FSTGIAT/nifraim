"""Path C — the universal fallback: the agent forwards the mail, Resend hands it to us.

Works for any mail host (cPanel, a local Exchange box, a provider we've never
seen), and holds **no credential at all** — the strongest privacy posture of the
three paths. The cost is one manual setup step: a forwarding rule.

Resend already carries our outbound SMTP. Its inbound side parses a received mail
and POSTs an `email.received` webhook. The webhook body carries **metadata only**
— attachment bytes must be fetched separately from the Attachments API, which
returns a short-lived `download_url`.

    forwarded mail → Resend → POST /api/mail-inbound/resend (signed)
                            → GET /emails/{id}/attachments  → download_url
                            → ingest_mail_attachment

SECURITY. This is the first unauthenticated write path in the app. Signature
verification is the entire defence and MUST run before the tenant lookup or any
outbound fetch. Resend signs with Svix's scheme; `svix` is not a dependency, so
it is verified here with stdlib `hmac` (constant-time, replay-windowed).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time

import httpx

from app.config import settings
from app.services.mail_intake import ERR_MAILBOX_UNREACHABLE, FetchedAttachment, MailIntakeError

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT_S = 20.0

# Svix rejects timestamps outside ±5 minutes; a replayed capture beyond that
# window is refused even if its signature is valid.
_TOLERANCE_S = 5 * 60


def is_configured() -> bool:
    return bool(settings.RESEND_API_KEY and settings.RESEND_WEBHOOK_SECRET and settings.RESEND_INBOUND_DOMAIN)


def forward_address(token: str) -> str:
    return f"hachshara+{token}@{settings.RESEND_INBOUND_DOMAIN}"


def token_from_recipient(to_addr: str) -> str | None:
    """Pull the per-user token out of `hachshara+<token>@domain`.

    The token in the RECIPIENT is what identifies the tenant. Never trust the
    sender — anyone can forge a From header.

    The local part must NOT be lowercased: `secrets.token_urlsafe` emits mixed
    case, and folding it silently breaks every tenant lookup (the webhook then
    200s as an "unknown token" and the mail is dropped without a trace).
    """
    addr = (to_addr or "").strip()
    if "<" in addr and ">" in addr:                    # "Name <a@b.c>"
        addr = addr[addr.rfind("<") + 1:addr.rfind(">")]
    local = addr.split("@", 1)[0]
    if "+" not in local:
        return None
    token = local.split("+", 1)[1]
    return token.strip() or None


def verify_signature(secret: str, headers: dict, body: bytes) -> bool:
    """Svix webhook signature check. Constant-time, replay-windowed.

    Signed content is `{svix-id}.{svix-timestamp}.{body}`, HMAC-SHA256 under the
    base64 secret that follows the `whsec_` prefix. The `svix-signature` header
    may list several space-separated `v1,<b64>` values during key rotation — any
    one matching is sufficient.
    """
    lowered = {k.lower(): v for k, v in headers.items()}
    msg_id = lowered.get("svix-id") or lowered.get("webhook-id")
    timestamp = lowered.get("svix-timestamp") or lowered.get("webhook-timestamp")
    signature = lowered.get("svix-signature") or lowered.get("webhook-signature")
    if not (msg_id and timestamp and signature and secret):
        return False

    try:
        sent = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - sent) > _TOLERANCE_S:
        logger.warning("resend: webhook timestamp outside tolerance — replay?")
        return False

    key = secret.split("_", 1)[1] if secret.startswith("whsec_") else secret
    try:
        secret_bytes = base64.b64decode(key)
    except Exception:
        return False

    signed = f"{msg_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()

    for part in signature.split():
        version, _, value = part.partition(",")
        if version != "v1":
            continue
        if hmac.compare_digest(value, expected):
            return True
    return False


async def fetch_attachments(email_id: str) -> list[FetchedAttachment]:
    """Pull the actual bytes. The webhook only told us they exist."""
    headers = {"Authorization": f"Bearer {settings.RESEND_API_KEY}"}
    api_base = settings.RESEND_API_BASE.rstrip("/")
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_S) as client:
        resp = await client.get(f"{api_base}/emails/{email_id}/attachments", headers=headers)
        if resp.status_code >= 400:
            raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, f"resend attachments {resp.status_code}")

        out: list[FetchedAttachment] = []
        for att in resp.json().get("data", []):
            filename = att.get("filename") or ""
            url = att.get("download_url")
            if not url:
                continue
            blob = await client.get(url)
            if blob.status_code >= 400:
                logger.warning("resend: attachment download failed (status=%s)", blob.status_code)
                continue
            out.append(
                FetchedAttachment(
                    external_id=f"{email_id}:{filename}",
                    filename=filename,
                    content=blob.content,
                    message_id=email_id,
                )
            )
    return out
