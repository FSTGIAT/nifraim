"""Portal automation API.

Endpoints:
    GET    /credentials                    list user's portal credentials
    POST   /credentials                    create (encrypts password)
    PUT    /credentials/{id}                update (re-encrypts only if password provided)
    DELETE /credentials/{id}
    POST   /credentials/{id}/run            trigger an automation run (async)
    GET    /runs/{run_id}                   poll status
    GET    /runs?credential_id=&limit=20    recent runs
    POST   /runs/{run_id}/submit-otp        manual OTP fallback
    GET    /portal-kinds                    list supported portals (for UI dropdown)
    GET    /twilio-webhook                  health check
    POST   /twilio-webhook                  PUBLIC inbound SMS handler (Twilio HMAC-verified)
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.agent_twilio_number import AgentTwilioNumber
from app.models.otp_inbox import OtpInbox
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.user import User
from app.schemas.portal_automation import (
    OtpInboxOut,
    OtpSubmitIn,
    PortalCredentialIn,
    PortalCredentialOut,
    PortalCredentialScheduleIn,
    PortalCredentialUpdate,
    PortalRunOut,
    RunStartOut,
    TwilioNumberOut,
)
from app.services import twilio_provisioning
from app.services.portal_automation.companies import PORTAL_LABELS, REGISTRY
from app.services.portal_automation.runner import run_automation, run_phone_change
from app.utils.crypto import encrypt

logger = logging.getLogger(__name__)
router = APIRouter()


OTP_REGEX = re.compile(r"\b(\d{4,8})\b")
ACTIVE_RUN_STATUSES = {"pending", "running", "awaiting_otp", "downloading", "parsing"}
TERMINAL_RUN_STATUSES = {"success", "failed", "timeout"}


def _cred_to_out(c: PortalCredential) -> PortalCredentialOut:
    return PortalCredentialOut(
        id=str(c.id),
        portal_kind=c.portal_kind,
        username=c.username,
        twilio_to_number=c.twilio_to_number,
        contact_phone_synced_to=c.contact_phone_synced_to,
        is_active=c.is_active,
        schedule_kind=c.schedule_kind,
        category_hint=c.category_hint,
        last_run_at=c.last_run_at,
        last_run_status=c.last_run_status,
        last_error=c.last_error,
        created_at=c.created_at,
    )


def _twilio_to_out(n: AgentTwilioNumber) -> TwilioNumberOut:
    return TwilioNumberOut(
        id=str(n.id),
        phone_number=n.phone_number,
        twilio_sid=n.twilio_sid,
        provisioned_at=n.provisioned_at,
        released_at=n.released_at,
    )


def _run_to_out(r: PortalRun) -> PortalRunOut:
    return PortalRunOut(
        id=str(r.id),
        credential_id=str(r.credential_id),
        status=r.status,
        stage=r.stage,
        started_at=r.started_at,
        finished_at=r.finished_at,
        error_message=r.error_message,
        downloaded_filename=r.downloaded_filename,
        upload_id=str(r.upload_id) if r.upload_id else None,
    )


# ──────────────────────────────────────────────────────────────────────────
# Portal kinds (public catalog for the UI dropdown)
# ──────────────────────────────────────────────────────────────────────────

IMPLEMENTED_PORTALS = {"phoenix", "migdal"}


@router.get("/portal-kinds")
async def list_portal_kinds(user: User = Depends(get_current_user)):
    return [
        {"id": kind, "label": PORTAL_LABELS[kind], "implemented": kind in IMPLEMENTED_PORTALS}
        for kind in REGISTRY.keys()
    ]


# ──────────────────────────────────────────────────────────────────────────
# Credentials CRUD
# ──────────────────────────────────────────────────────────────────────────

@router.get("/credentials", response_model=list[PortalCredentialOut])
async def list_credentials(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PortalCredential)
        .where(PortalCredential.user_id == user.id)
        .order_by(PortalCredential.portal_kind)
    )
    return [_cred_to_out(c) for c in result.scalars().all()]


@router.post("/credentials", response_model=PortalCredentialOut)
async def create_credential(
    payload: PortalCredentialIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.portal_kind not in REGISTRY:
        raise HTTPException(status_code=400, detail="Unknown portal_kind")

    existing = await db.execute(
        select(PortalCredential).where(
            PortalCredential.user_id == user.id,
            PortalCredential.portal_kind == payload.portal_kind,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Credential for this portal already exists")

    try:
        encrypted = encrypt(payload.password)
    except RuntimeError as e:
        # Almost always: PORTAL_CRED_FERNET_KEY missing from env. Surface clearly
        # instead of returning a generic 500.
        raise HTTPException(status_code=503, detail=f"Server crypto not configured: {e}")

    cred = PortalCredential(
        user_id=user.id,
        portal_kind=payload.portal_kind,
        username=payload.username,
        encrypted_password=encrypted,
        twilio_to_number=payload.twilio_to_number,
        schedule_kind=payload.schedule_kind,
        category_hint=payload.category_hint,
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return _cred_to_out(cred)


@router.put("/credentials/{cred_id}", response_model=PortalCredentialOut)
async def update_credential(
    cred_id: str,
    payload: PortalCredentialUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PortalCredential).where(
            PortalCredential.id == uuid.UUID(cred_id),
            PortalCredential.user_id == user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        cred.encrypted_password = encrypt(data.pop("password"))
    elif "password" in data:
        data.pop("password")

    for key, value in data.items():
        setattr(cred, key, value)

    await db.commit()
    await db.refresh(cred)
    return _cred_to_out(cred)


@router.patch("/credentials/{cred_id}/schedule", response_model=PortalCredentialOut)
async def update_credential_schedule(
    cred_id: str,
    payload: PortalCredentialScheduleIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set the recurring-run cadence for a credential without touching anything else."""
    result = await db.execute(
        select(PortalCredential).where(
            PortalCredential.id == uuid.UUID(cred_id),
            PortalCredential.user_id == user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    cred.schedule_kind = payload.schedule_kind
    await db.commit()
    await db.refresh(cred)
    return _cred_to_out(cred)


@router.delete("/credentials/{cred_id}")
async def delete_credential(
    cred_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PortalCredential).where(
            PortalCredential.id == uuid.UUID(cred_id),
            PortalCredential.user_id == user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    await db.delete(cred)
    await db.commit()
    return {"status": "deleted"}


# ──────────────────────────────────────────────────────────────────────────
# Runs
# ──────────────────────────────────────────────────────────────────────────

@router.post("/credentials/{cred_id}/run", response_model=RunStartOut)
async def trigger_run(
    cred_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cred_result = await db.execute(
        select(PortalCredential).where(
            PortalCredential.id == uuid.UUID(cred_id),
            PortalCredential.user_id == user.id,
        )
    )
    cred = cred_result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    if not cred.is_active:
        raise HTTPException(status_code=400, detail="Credential is not active")

    # Reject if an active run already exists for this credential
    active_result = await db.execute(
        select(PortalRun).where(
            PortalRun.credential_id == cred.id,
            PortalRun.status.in_(ACTIVE_RUN_STATUSES),
        )
    )
    if active_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A run is already in progress for this credential")

    run = PortalRun(
        user_id=user.id,
        credential_id=cred.id,
        status="pending",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Fire and forget — runner owns its own DB session.
    asyncio.create_task(run_automation(run.id))

    return RunStartOut(run_id=str(run.id))


@router.get("/runs/{run_id}", response_model=PortalRunOut)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PortalRun).where(
            PortalRun.id == uuid.UUID(run_id),
            PortalRun.user_id == user.id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_out(run)


@router.get("/runs", response_model=list[PortalRunOut])
async def list_runs(
    credential_id: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(PortalRun)
        .where(PortalRun.user_id == user.id)
        .order_by(PortalRun.started_at.desc())
        .limit(min(limit, 100))
    )
    if credential_id:
        stmt = stmt.where(PortalRun.credential_id == uuid.UUID(credential_id))
    result = await db.execute(stmt)
    return [_run_to_out(r) for r in result.scalars().all()]


@router.post("/runs/{run_id}/submit-otp")
async def submit_otp(
    run_id: str,
    payload: OtpSubmitIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manual OTP fallback — inserts a synthetic OtpInbox row that the
    runner's wait loop picks up exactly like a real Twilio-delivered SMS."""
    run_result = await db.execute(
        select(PortalRun).where(
            PortalRun.id == uuid.UUID(run_id),
            PortalRun.user_id == user.id,
        )
    )
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_otp":
        raise HTTPException(status_code=400, detail=f"Run is not awaiting OTP (status={run.status})")

    db.add(OtpInbox(
        user_id=user.id,
        from_number="manual",
        to_number="manual",
        body=f"Manual OTP submission for run {run.id}",
        otp_code=payload.otp,
    ))
    await db.commit()
    return {"status": "submitted"}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark an in-flight run as failed (cancelled by the user). The runner
    coroutine itself can't be aborted from here, but flipping the status
    means the UI no longer waits and the next run won't be blocked by a
    409 stale-run check."""
    run_result = await db.execute(
        select(PortalRun).where(
            PortalRun.id == uuid.UUID(run_id),
            PortalRun.user_id == user.id,
        )
    )
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in ACTIVE_RUN_STATUSES:
        return {"status": run.status, "noop": True}
    run.status = "failed"
    run.stage = None
    run.error_message = "בוטל ע\"י המשתמש"
    run.finished_at = datetime.utcnow()
    await db.commit()
    return {"status": "failed", "cancelled": True}


# ──────────────────────────────────────────────────────────────────────────
# Recent OTPs (debug + visibility)
# ──────────────────────────────────────────────────────────────────────────

@router.get("/otp-inbox", response_model=list[OtpInboxOut])
async def list_recent_otps(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List recent inbound SMS messages for the current user. Includes both
    SMS scoped to this user (matched via Twilio `to` number) and broadcast
    rows (user_id IS NULL). Sorted newest-first."""
    stmt = (
        select(OtpInbox)
        .where((OtpInbox.user_id == user.id) | (OtpInbox.user_id.is_(None)))
        .order_by(OtpInbox.received_at.desc())
        .limit(min(limit, 100))
    )
    result = await db.execute(stmt)
    return [
        OtpInboxOut(
            id=str(r.id),
            from_number=r.from_number,
            to_number=r.to_number,
            body=r.body,
            otp_code=r.otp_code,
            received_at=r.received_at,
            consumed_at=r.consumed_at,
            portal_run_id=str(r.portal_run_id) if r.portal_run_id else None,
        )
        for r in result.scalars().all()
    ]


# ──────────────────────────────────────────────────────────────────────────
# Agent Twilio number provisioning
# ──────────────────────────────────────────────────────────────────────────

@router.get("/twilio-numbers/me", response_model=TwilioNumberOut | None)
async def get_my_twilio_number(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = await twilio_provisioning.get_active_for_user(db, user.id)
    return _twilio_to_out(row) if row else None


@router.post("/twilio-numbers/provision", response_model=TwilioNumberOut)
async def provision_my_twilio_number(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Buy a Twilio +972 number under Nifraim's account and assign it to this
    agent. Idempotent: if the agent already has one, returns the existing row."""
    try:
        row = await twilio_provisioning.provision_for_user(db, user.id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return _twilio_to_out(row)


@router.delete("/twilio-numbers/me")
async def release_my_twilio_number(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    released = await twilio_provisioning.release_for_user(db, user.id)
    if not released:
        raise HTTPException(status_code=404, detail="No active Twilio number")
    return {"status": "released"}


# ──────────────────────────────────────────────────────────────────────────
# Sync contact phone in a portal (one-time per agent + portal)
# ──────────────────────────────────────────────────────────────────────────

@router.post("/credentials/{cred_id}/sync-contact-phone", response_model=RunStartOut)
async def sync_contact_phone(
    cred_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger the one-time contact-phone migration: log into the portal as
    the agent, navigate to settings, change the contact number to the agent's
    Twilio number, and confirm via SMS to the OLD phone (manual OTP fallback).
    """
    cred_result = await db.execute(
        select(PortalCredential).where(
            PortalCredential.id == uuid.UUID(cred_id),
            PortalCredential.user_id == user.id,
        )
    )
    cred = cred_result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    if not cred.is_active:
        raise HTTPException(status_code=400, detail="Credential is not active")

    twilio_row = await twilio_provisioning.get_active_for_user(db, user.id)
    if not twilio_row:
        raise HTTPException(
            status_code=400,
            detail="Provision a Twilio number first via /twilio-numbers/provision",
        )

    active_result = await db.execute(
        select(PortalRun).where(
            PortalRun.credential_id == cred.id,
            PortalRun.status.in_(ACTIVE_RUN_STATUSES),
        )
    )
    if active_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A run is already in progress for this credential")

    run = PortalRun(
        user_id=user.id,
        credential_id=cred.id,
        kind="phone_change",
        status="pending",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    asyncio.create_task(run_phone_change(run.id, twilio_row.phone_number))

    return RunStartOut(run_id=str(run.id))


# ──────────────────────────────────────────────────────────────────────────
# Twilio webhook (PUBLIC)
# ──────────────────────────────────────────────────────────────────────────

@router.get("/twilio-webhook")
async def twilio_webhook_health():
    return {"ok": True, "configured": bool(settings.TWILIO_AUTH_TOKEN)}


@router.post("/twilio-webhook")
async def twilio_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Inbound SMS from Twilio. PUBLIC — verified via HMAC signature."""
    form = await request.form()
    form_dict = {k: str(v) for k, v in form.items()}

    if settings.TWILIO_AUTH_TOKEN:
        from twilio.request_validator import RequestValidator

        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(str(request.url), form_dict, signature):
            raise HTTPException(status_code=403, detail="invalid signature")

    from_ = form_dict.get("From", "")
    to = form_dict.get("To", "")
    body = form_dict.get("Body", "")

    otp_match = OTP_REGEX.search(body)
    otp_code = otp_match.group(1) if otp_match else None

    user_id: uuid.UUID | None = None
    if to:
        cred_result = await db.execute(
            select(PortalCredential).where(PortalCredential.twilio_to_number == to).limit(1)
        )
        cred = cred_result.scalar_one_or_none()
        if cred:
            user_id = cred.user_id

    db.add(OtpInbox(
        user_id=user_id,
        from_number=from_[:20],
        to_number=to[:20],
        body=body,
        otp_code=otp_code,
    ))
    await db.commit()

    return Response(content="<Response/>", media_type="application/xml")
