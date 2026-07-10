"""Path A — Microsoft 365 via Graph OAuth.

Exchange Online has basic authentication **permanently disabled** (Microsoft: no
tenant admin and no Microsoft support ticket can re-enable it), and app passwords
are blocked along with it since they ride the same legacy flow. There is no
password to paste. OAuth is the only door.

Graph's `Mail.Read` needs one multi-tenant Azure app registration — free, one
time, no CASA-style security assessment (that is a *Google* requirement, and the
reason the Gmail path still uses an app password).

We implement the auth-code flow with plain `httpx` rather than adding `msal`:
it is two POSTs, and the dependency would sit on the code path handling the
agent's mailbox.

Only the REFRESH token is persisted (Fernet, MAILBOX_ENCRYPTION_KEY). Access
tokens are re-minted per poll and never stored.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.services.mail_intake import (
    ERR_ADMIN_CONSENT,
    ERR_CONSENT_REVOKED,
    ERR_MAILBOX_UNREACHABLE,
    FetchedAttachment,
    MailIntakeError,
)

logger = logging.getLogger(__name__)

AUTHORITY = "https://login.microsoftonline.com/common"
_AUTH_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
_TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
_GRAPH = "https://graph.microsoft.com/v1.0"

# offline_access is what mints the refresh token. Mail.Read, never Mail.ReadWrite.
SCOPES = "offline_access Mail.Read"

_HTTP_TIMEOUT_S = 20.0
_STATE_TTL_S = 600

# AADSTS65001 = user/admin has not consented. AADSTS650057/AADSTS900971 and the
# admin-consent-required family all mean "an admin must approve this app once".
_ADMIN_CONSENT_CODES = ("aadsts65001", "aadsts900971", "aadsts650057", "consent_required")
_REVOKED_CODES = ("invalid_grant", "aadsts50173", "aadsts700082")


def is_configured() -> bool:
    return bool(settings.MS_OAUTH_CLIENT_ID and settings.MS_OAUTH_CLIENT_SECRET and settings.MS_OAUTH_REDIRECT_URI)


# ── CSRF state: signed + timestamped, so the callback can't be forged or replayed ──


def _state_secret() -> bytes:
    # Reuse the mailbox Fernet key material as an HMAC secret; it is already a
    # deployed, high-entropy per-environment secret.
    return (settings.MAILBOX_ENCRYPTION_KEY or settings.MS_OAUTH_CLIENT_SECRET).encode()


def make_state(user_id: str) -> str:
    payload = json.dumps({"u": str(user_id), "t": int(time.time())}, separators=(",", ":")).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    sig = hmac.new(_state_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def parse_state(state: str) -> str:
    """Return the user_id, or raise. Rejects forged signatures and stale replays."""
    try:
        body, sig = (state or "").rsplit(".", 1)
    except ValueError:
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, "malformed state")
    expected = hmac.new(_state_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, "bad state signature")
    padded = body + "=" * (-len(body) % 4)
    data = json.loads(base64.urlsafe_b64decode(padded))
    if time.time() - int(data["t"]) > _STATE_TTL_S:
        raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, "state expired")
    return data["u"]


def consent_url(user_id: str, login_hint: str | None = None) -> str:
    params = {
        "client_id": settings.MS_OAUTH_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.MS_OAUTH_REDIRECT_URI,
        "response_mode": "query",
        "scope": SCOPES,
        "state": make_state(user_id),
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{_AUTH_URL}?{urlencode(params)}"


def admin_consent_url() -> str:
    """What the agent forwards to their IT admin when the tenant blocks user consent."""
    params = {"client_id": settings.MS_OAUTH_CLIENT_ID, "redirect_uri": settings.MS_OAUTH_REDIRECT_URI}
    return f"{AUTHORITY}/adminconsent?{urlencode(params)}"


# ── Token exchange ──────────────────────────────────────────────────────────


def _classify_token_error(payload: dict) -> str:
    blob = " ".join(
        str(payload.get(k, "")) for k in ("error", "error_description", "suberror")
    ).lower()
    if any(c in blob for c in _ADMIN_CONSENT_CODES):
        return ERR_ADMIN_CONSENT
    if any(c in blob for c in _REVOKED_CODES):
        return ERR_CONSENT_REVOKED
    return ERR_MAILBOX_UNREACHABLE


async def _post_token(form: dict) -> dict:
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_S) as client:
        resp = await client.post(_TOKEN_URL, data=form)
    if resp.status_code >= 400:
        try:
            payload = resp.json()
        except Exception:
            payload = {"error": f"http_{resp.status_code}"}
        code = _classify_token_error(payload)
        # error_description can be long and contains correlation ids — log, never surface.
        logger.warning("graph: token endpoint %s -> %s", resp.status_code, payload.get("error"))
        raise MailIntakeError(code, payload.get("error"))
    return resp.json()


async def exchange_code(code: str) -> dict:
    """Auth code → {refresh_token, access_token, tenant_id}. Only the refresh token is stored."""
    data = await _post_token({
        "client_id": settings.MS_OAUTH_CLIENT_ID,
        "client_secret": settings.MS_OAUTH_CLIENT_SECRET,
        "redirect_uri": settings.MS_OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
        "scope": SCOPES,
        "code": code,
    })
    return {
        "refresh_token": data.get("refresh_token"),
        "access_token": data.get("access_token"),
        "tenant_id": _tenant_from_id_token(data.get("id_token")),
    }


def _tenant_from_id_token(id_token: str | None) -> str | None:
    """Read `tid` from the unverified id_token body. Informational only — never
    used for authorization, so skipping signature validation is safe here."""
    if not id_token or id_token.count(".") != 2:
        return None
    try:
        body = id_token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        return payload.get("tid")
    except Exception:
        return None


async def access_token_from_refresh(refresh_token: str) -> tuple[str, str | None]:
    """Mint an access token. Returns (access_token, rotated_refresh_token|None).

    Microsoft rotates refresh tokens; the caller MUST persist a returned new one
    or the next poll fails with invalid_grant.
    """
    data = await _post_token({
        "client_id": settings.MS_OAUTH_CLIENT_ID,
        "client_secret": settings.MS_OAUTH_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "scope": SCOPES,
        "refresh_token": refresh_token,
    })
    return data["access_token"], data.get("refresh_token")


# ── Delta poll ──────────────────────────────────────────────────────────────


async def fetch_new_attachments(
    access_token: str, delta_link: str | None
) -> tuple[list[FetchedAttachment], str | None]:
    """Walk the inbox delta and pull attachments from messages that have any.

    The delta cursor beats a `receivedDateTime` high-water mark: it can't
    double-deliver on a timestamp tie, and it survives clock skew.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = delta_link or (
        f"{_GRAPH}/me/mailFolders/inbox/messages/delta"
        "?$select=id,subject,hasAttachments,internetMessageId"
    )

    out: list[FetchedAttachment] = []
    next_delta: str | None = None

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_S) as client:
        while url:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 401:
                raise MailIntakeError(ERR_CONSENT_REVOKED, "graph 401")
            if resp.status_code >= 400:
                raise MailIntakeError(ERR_MAILBOX_UNREACHABLE, f"graph {resp.status_code}")
            body = resp.json()

            for msg in body.get("value", []):
                if not msg.get("hasAttachments") or msg.get("@removed"):
                    continue
                out.extend(await _attachments_of(client, headers, msg))

            url = body.get("@odata.nextLink")
            next_delta = body.get("@odata.deltaLink") or next_delta

    return out, next_delta


async def _attachments_of(client: httpx.AsyncClient, headers: dict, msg: dict) -> list[FetchedAttachment]:
    mid = msg["id"]
    resp = await client.get(f"{_GRAPH}/me/messages/{mid}/attachments", headers=headers)
    if resp.status_code >= 400:
        logger.warning("graph: attachments fetch failed for message (status=%s)", resp.status_code)
        return []

    found = []
    for att in resp.json().get("value", []):
        raw = att.get("contentBytes")
        name = att.get("name") or ""
        if not raw:
            continue  # itemAttachment / referenceAttachment — not a file
        try:
            content = base64.b64decode(raw)
        except Exception:
            continue
        found.append(
            FetchedAttachment(
                # Graph message ids are stable per mailbox; qualify by filename so a
                # mail carrying two zips ledgers each one separately.
                external_id=f"{mid}:{name}",
                filename=name,
                content=content,
                message_id=msg.get("internetMessageId"),
            )
        )
    return found
