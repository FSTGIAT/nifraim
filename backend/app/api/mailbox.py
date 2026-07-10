"""Mailbox intake API — connect a mailbox, check status, receive forwarded mail.

Route-order caveat (same trap as `/phone-forward/{token}` in portal_automation):
literal paths must be declared before any catch-all, or FastAPI matches the
literal as a parameter.
"""

from __future__ import annotations

import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user as get_current_user
from app.config import settings
from app.database import get_db
from app.models.mailbox_config import MailboxConfig
from app.models.user import User
from app.services.mail_intake import MailIntakeError, ingest_mail_attachment
from app.services.mail_intake import graph as graph_path
from app.services.mail_intake import resend as resend_path
from app.services.mail_intake.detect import detect_mail_host
from app.services.mail_intake.poller import MAILBOX_KEY, poll_mailbox
from app.utils.crypto import encrypt

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────────


class MailboxOut(BaseModel):
    """Never carries the app password, refresh token, or delta link."""

    email_address: str
    mail_host: str
    is_active: bool
    connected: bool
    last_received_at: str | None = None
    last_status: str | None = None
    last_error: str | None = None      # a stable CODE; the UI maps it to Hebrew
    forward_address: str | None = None  # only for mail_host="other"
    # Which paths this deployment can actually offer. Without these the UI would
    # show a Connect button that 503s, or a "create address" button that yields
    # nothing — a dead end for every agent whose host we can't serve.
    microsoft_available: bool = False
    forwarding_available: bool = False


class MailboxIn(BaseModel):
    email_address: EmailStr
    app_password: str | None = None     # google only
    mail_host: str | None = None        # explicit override of MX detection
    is_active: bool = True


class DetectIn(BaseModel):
    email_address: EmailStr


def _to_out(cfg: MailboxConfig) -> MailboxOut:
    if cfg.mail_host == "microsoft":
        connected = bool(cfg.encrypted_refresh_token)
    elif cfg.mail_host == "google":
        connected = bool(cfg.encrypted_password)
    else:
        connected = bool(cfg.forward_token)

    return MailboxOut(
        email_address=cfg.email_address,
        mail_host=cfg.mail_host,
        is_active=cfg.is_active,
        connected=connected,
        last_received_at=cfg.last_received_at.isoformat() if cfg.last_received_at else None,
        last_status=cfg.last_status,
        last_error=cfg.last_error,
        forward_address=(
            resend_path.forward_address(cfg.forward_token)
            if cfg.mail_host == "other" and cfg.forward_token and settings.RESEND_INBOUND_DOMAIN
            else None
        ),
        microsoft_available=graph_path.is_configured(),
        forwarding_available=resend_path.is_configured(),
    )


async def _get_cfg(db: AsyncSession, user_id: uuid.UUID) -> MailboxConfig | None:
    res = await db.execute(select(MailboxConfig).where(MailboxConfig.user_id == user_id))
    return res.scalar_one_or_none()


# ── Public webhook — declared FIRST, and unauthenticated by design ───────────


@router.post("/inbound/resend")
async def resend_inbound(request: Request, db: AsyncSession = Depends(get_db)):
    """Resend `email.received`. The first write path in this app without a JWT.

    Order is load-bearing: verify the signature BEFORE the tenant lookup and
    before any outbound fetch, so an unsigned caller can neither probe which
    tokens exist nor make us issue requests on their behalf.
    """
    body = await request.body()

    if not resend_path.is_configured():
        raise HTTPException(status_code=503, detail="inbound mail not configured")

    if not resend_path.verify_signature(settings.RESEND_WEBHOOK_SECRET, dict(request.headers), body):
        logger.warning("mailbox: rejected inbound webhook with bad signature")
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = await request.json()
    data = payload.get("data") or {}
    email_id = data.get("email_id") or data.get("id")
    recipients = data.get("to") or []
    if isinstance(recipients, str):
        recipients = [recipients]

    token = next((t for t in (resend_path.token_from_recipient(r) for r in recipients) if t), None)
    if not token or not email_id:
        return {"status": "ok"}

    res = await db.execute(
        select(MailboxConfig).where(
            MailboxConfig.forward_token == token, MailboxConfig.is_active.is_(True)
        )
    )
    cfg = res.scalar_one_or_none()
    if not cfg:
        # 200, never 404 — mirrors /phone-forward/{token}. A distinguishable
        # response would let an attacker enumerate valid tokens.
        # WARNING, not INFO: a real delivery landing here means mail is being
        # dropped, and at default log level an INFO line makes that invisible.
        logger.warning("mailbox: inbound for unknown token %s…", token[:8])
        return {"status": "ok"}

    try:
        attachments = await resend_path.fetch_attachments(email_id)
    except MailIntakeError as e:
        logger.warning("mailbox: resend attachment fetch failed: %s", e.code)
        return {"status": "ok"}

    if not attachments:
        logger.warning("mailbox: inbound email %s carried no attachments", email_id)

    for att in attachments:
        await ingest_mail_attachment(db, cfg, att)
    return {"status": "ok"}


# ── OAuth callback — public (Microsoft redirects the browser here) ───────────


@router.get("/oauth/microsoft/callback")
async def microsoft_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Exchange the auth code and store ONLY the refresh token.

    Authenticated by the signed `state`, not a JWT — the browser arrives here
    from Microsoft, not from our SPA.
    """
    redirect = "/?mailbox=connected"

    if error:
        code_out = (
            "admin_consent_required"
            if "consent" in (error or "").lower()
            else "mailbox_unreachable"
        )
        return RedirectResponse(f"/?mailbox=error&code={code_out}")

    if not code or not state:
        return RedirectResponse("/?mailbox=error&code=mailbox_unreachable")

    try:
        user_id = graph_path.parse_state(state)
    except MailIntakeError:
        logger.warning("mailbox: oauth callback with invalid state")
        raise HTTPException(status_code=400, detail="invalid state")

    try:
        tokens = await graph_path.exchange_code(code)
    except MailIntakeError as e:
        return RedirectResponse(f"/?mailbox=error&code={e.code}")

    cfg = await _get_cfg(db, uuid.UUID(user_id))
    if not cfg:
        return RedirectResponse("/?mailbox=error&code=not_configured")

    if not tokens.get("refresh_token"):
        return RedirectResponse("/?mailbox=error&code=consent_revoked")

    cfg.encrypted_refresh_token = encrypt(tokens["refresh_token"], key_env=MAILBOX_KEY)
    cfg.oauth_tenant_id = tokens.get("tenant_id")
    cfg.mail_host = "microsoft"
    cfg.last_status = "ok"
    cfg.last_error = None
    cfg.consecutive_failures = 0
    await db.commit()
    return RedirectResponse(redirect)


# ── Authenticated routes ────────────────────────────────────────────────────


@router.post("/detect")
async def detect(payload: DetectIn, user: User = Depends(get_current_user)):
    """Resolve the address's MX and say which path it needs. Never asks the user.

    Detection is a hint, not a verdict — split delivery, vanity MX and security
    gateways all mislead it, so `PUT /mailbox` accepts a `mail_host` override and
    the UI must offer one.
    """
    host = await detect_mail_host(payload.email_address)
    return {
        "mail_host": host,
        "microsoft_available": graph_path.is_configured(),
        "forwarding_available": resend_path.is_configured(),
    }


@router.get("", response_model=MailboxOut | None)
async def get_mailbox(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cfg = await _get_cfg(db, user.id)
    return _to_out(cfg) if cfg else None


@router.put("", response_model=MailboxOut)
async def upsert_mailbox(
    payload: MailboxIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host = payload.mail_host or await detect_mail_host(payload.email_address)
    if host not in ("microsoft", "google", "other"):
        raise HTTPException(status_code=400, detail="unknown mail_host")

    cfg = await _get_cfg(db, user.id)
    if not cfg:
        cfg = MailboxConfig(user_id=user.id, email_address=str(payload.email_address), mail_host=host)
        db.add(cfg)

    changed_identity = cfg.email_address != str(payload.email_address) or cfg.mail_host != host
    cfg.email_address = str(payload.email_address)
    cfg.mail_host = host
    cfg.is_active = payload.is_active

    if changed_identity:
        # Credentials and cursors belong to the OLD mailbox. Keeping them would
        # poll the wrong account or replay a stale delta cursor.
        cfg.encrypted_refresh_token = None
        cfg.encrypted_password = None
        cfg.delta_link = None
        cfg.uidvalidity = None
        cfg.last_seen_uid = None
        cfg.last_error = None
        cfg.consecutive_failures = 0

    if host == "google" and payload.app_password:
        # Google shows app passwords as "abcd efgh ijkl mnop"; users paste the spaces.
        cfg.encrypted_password = encrypt(payload.app_password.replace(" ", ""), key_env=MAILBOX_KEY)
    if host == "other" and not cfg.forward_token:
        cfg.forward_token = secrets.token_urlsafe(24)

    await db.commit()
    await db.refresh(cfg)
    return _to_out(cfg)


@router.get("/oauth/microsoft/start")
async def microsoft_start(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not graph_path.is_configured():
        raise HTTPException(status_code=503, detail="microsoft oauth not configured")
    cfg = await _get_cfg(db, user.id)
    # Pre-fill the address on Microsoft's sign-in page. The agent already typed it
    # here; making them type it again is where a one-click flow starts feeling
    # like a login form. It is a hint only — they can still switch accounts.
    login_hint = cfg.email_address if cfg else None
    return {
        "url": graph_path.consent_url(str(user.id), login_hint=login_hint),
        "admin_consent_url": graph_path.admin_consent_url(),
    }


@router.post("/poll-now")
async def poll_now(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cfg = await _get_cfg(db, user.id)
    if not cfg:
        raise HTTPException(status_code=404, detail="no mailbox configured")
    ingested = await poll_mailbox(db, cfg, force=True)
    await db.refresh(cfg)
    return {"ingested": ingested, "status": cfg.last_status, "error": cfg.last_error}


@router.delete("")
async def delete_mailbox(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cfg = await _get_cfg(db, user.id)
    if cfg:
        await db.delete(cfg)
        await db.commit()
    return {"status": "deleted"}
