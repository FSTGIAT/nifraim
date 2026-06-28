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
import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.agent_twilio_number import AgentTwilioNumber
from app.models.otp_inbox import OtpInbox
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.portal_run_batch import PortalRunBatch
from app.models.sms_otp_template import SmsOtpTemplate
from app.models.user import User
from app.models.worker_heartbeat import WorkerHeartbeat
from app.schemas.portal_automation import (
    OtpInboxOut,
    OtpSubmitIn,
    PortalCredentialIn,
    PortalCredentialOut,
    PortalCredentialScheduleIn,
    PortalCredentialUpdate,
    PortalRunOut,
    RunStartOut,
    BatchStartOut,
    PortalRunBatchOut,
    TwilioNumberOut,
)
from app.services import twilio_provisioning
from app.services.portal_automation.companies import PORTAL_LABELS, REGISTRY
from app.services.portal_automation.runner import run_automation, run_phone_change
from app.services.portal_automation.batch_runner import run_batch
from app.utils.crypto import encrypt

logger = logging.getLogger(__name__)
router = APIRouter()


OTP_REGEX = re.compile(r"\b(\d{4,8})\b")
ACTIVE_RUN_STATUSES = {"pending", "running", "awaiting_otp", "downloading", "parsing"}
TERMINAL_RUN_STATUSES = {"success", "failed", "timeout"}
# A worker is "live" if it heartbeated within this window.
WORKER_LIVE_WINDOW_S = 90


async def _should_defer_to_worker(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Decide whether to ENQUEUE a run for the agent's local worker instead of
    executing it on Railway. True when the global WORKER_MODE override is set, OR
    — the normal path — when this user's local worker has a recent heartbeat.
    Auto-detection means the agent never flips a setting: installing + running the
    worker (it heartbeats) automatically routes their downloads to it; with no
    live worker, Railway runs them inline (pre-worker behavior)."""
    if settings.WORKER_MODE:
        return True
    row = (await db.execute(
        select(WorkerHeartbeat.last_seen).where(WorkerHeartbeat.user_id == user_id)
    )).scalar_one_or_none()
    if not row:
        return False
    return (datetime.utcnow() - row).total_seconds() <= WORKER_LIVE_WINDOW_S


def _cred_to_out(c: PortalCredential, recent: list[str] | None = None) -> PortalCredentialOut:
    return PortalCredentialOut(
        id=str(c.id),
        portal_kind=c.portal_kind,
        username=c.username,
        twilio_to_number=c.twilio_to_number,
        contact_phone_synced_to=c.contact_phone_synced_to,
        is_active=c.is_active,
        schedule_kind=c.schedule_kind,
        category_hint=c.category_hint,
        otp_method=getattr(c, "otp_method", "twilio") or "twilio",
        last_run_at=c.last_run_at,
        last_run_status=c.last_run_status,
        last_error=c.last_error,
        recent_run_statuses=recent or [],
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

IMPLEMENTED_PORTALS = {"phoenix", "phoenix_nifraim", "phoenix_nifraim_gemel", "phoenix_sfe", "migdal", "menora", "menora_nifraim", "clal", "clal_nifraim"}


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
    creds = result.scalars().all()

    # Window-function fetch of the last 7 statuses per credential. Index
    # ix_portal_runs_credential(credential_id, started_at) covers the partition.
    rn = func.row_number().over(
        partition_by=PortalRun.credential_id,
        order_by=PortalRun.started_at.desc(),
    ).label("rn")
    sub = (
        select(PortalRun.credential_id, PortalRun.status, rn)
        .where(PortalRun.user_id == user.id)
        .subquery()
    )
    recent_q = await db.execute(
        select(sub.c.credential_id, sub.c.status)
        .where(sub.c.rn <= 7)
    )
    recent_by_cred: dict[uuid.UUID, list[str]] = {}
    for cid, status in recent_q.all():
        recent_by_cred.setdefault(cid, []).append(status)

    return [_cred_to_out(c, recent_by_cred.get(c.id)) for c in creds]


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
        otp_method=payload.otp_method,
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

    # If the agent's local worker is live, leave the run "pending" for it to
    # claim and execute from an Israeli IP (no geo-block / no Bright Data POST
    # block). Otherwise Railway executes inline. Auto-detected — no manual flag.
    if not await _should_defer_to_worker(db, user.id):
        asyncio.create_task(run_automation(run.id))

    return RunStartOut(run_id=str(run.id))


ACTIVE_BATCH_STATUSES = {"pending", "running"}


@router.post("/batches/run", response_model=BatchStartOut)
async def run_all_portals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start a "run all portals" batch: every active credential runs
    sequentially, then the downloads are aggregated into one merged production
    file + one merged נפרעים file and the comparison runs automatically."""
    # Reject if a batch or any single run is already active for this user.
    active_batch = await db.execute(
        select(PortalRunBatch).where(
            PortalRunBatch.user_id == user.id,
            PortalRunBatch.status.in_(ACTIVE_BATCH_STATUSES),
        )
    )
    if active_batch.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="הורדה אוטומטית כבר פעילה")

    active_run = await db.execute(
        select(PortalRun).where(
            PortalRun.user_id == user.id,
            PortalRun.status.in_(ACTIVE_RUN_STATUSES),
        )
    )
    if active_run.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="קיימת הרצה פעילה — המתן לסיומה")

    active_creds = await db.execute(
        select(func.count(PortalCredential.id)).where(
            PortalCredential.user_id == user.id,
            PortalCredential.is_active.is_(True),
        )
    )
    if (active_creds.scalar() or 0) == 0:
        raise HTTPException(status_code=400, detail="אין חיבורי פורטל פעילים")

    batch = PortalRunBatch(
        user_id=user.id,
        status="pending",
        started_at=datetime.utcnow(),
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    # If the agent's local worker is live, leave the batch "pending" for it to
    # claim; otherwise execute inline on Railway. Auto-detected — no manual flag.
    if not await _should_defer_to_worker(db, user.id):
        asyncio.create_task(run_batch(batch.id))
    return BatchStartOut(batch_id=str(batch.id))


def _batch_to_out(batch: PortalRunBatch, runs: list[PortalRun]) -> PortalRunBatchOut:
    return PortalRunBatchOut(
        id=str(batch.id),
        status=batch.status,
        total=batch.total,
        succeeded=batch.succeeded,
        failed=batch.failed,
        current_run_id=str(batch.current_run_id) if batch.current_run_id else None,
        started_at=batch.started_at,
        finished_at=batch.finished_at,
        merged_upload_id=str(batch.merged_upload_id) if batch.merged_upload_id else None,
        merged_commission_upload_id=(
            str(batch.merged_commission_upload_id) if batch.merged_commission_upload_id else None
        ),
        period_month=batch.period_month,
        error_message=batch.error_message,
        runs=[_run_to_out(r) for r in runs],
    )


@router.get("/batches/latest", response_model=PortalRunBatchOut | None)
async def get_latest_batch(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The user's most recent "run all portals" batch, or null if they've never
    run one. Drives the new-user activation checklist (step 4 = first successful
    run). Declared before /batches/{batch_id} so "latest" isn't read as an id."""
    result = await db.execute(
        select(PortalRunBatch)
        .where(PortalRunBatch.user_id == user.id)
        .order_by(PortalRunBatch.started_at.desc())
        .limit(1)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        return None

    runs_q = await db.execute(
        select(PortalRun)
        .where(PortalRun.batch_id == batch.id)
        .order_by(PortalRun.started_at.asc())
    )
    return _batch_to_out(batch, list(runs_q.scalars().all()))


@router.get("/batches/{batch_id}", response_model=PortalRunBatchOut)
async def get_batch(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PortalRunBatch).where(
            PortalRunBatch.id == uuid.UUID(batch_id),
            PortalRunBatch.user_id == user.id,
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    runs_q = await db.execute(
        select(PortalRun)
        .where(PortalRun.batch_id == batch.id)
        .order_by(PortalRun.started_at.asc())
    )
    return _batch_to_out(batch, list(runs_q.scalars().all()))


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
            portal_kind=r.portal_kind,
            matched_company=r.matched_company,
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

    # Tag the company so the runner can route this code to the right portal.
    from app.services.otp_routing import match_otp_company
    portal_kind, matched_company = await match_otp_company(db, body, from_)

    db.add(OtpInbox(
        user_id=user_id,
        from_number=from_[:20],
        to_number=to[:20],
        body=body,
        otp_code=otp_code,
        portal_kind=portal_kind,
        matched_company=matched_company,
    ))
    await db.commit()

    return Response(content="<Response/>", media_type="application/xml")


# ──────────────────────────────────────────────────────────────────────────
# Phone-forward webhook (PUBLIC, token-auth) — see
# memory/portal_migdal_xhr_fallback.md for the architecture this enables.
# ──────────────────────────────────────────────────────────────────────────


class PhoneForwardIn(BaseModel):
    message: str = Field(..., max_length=2000)


def _build_phone_forward_url(token: str | None, request: Request | None = None) -> str | None:
    if not token:
        return None
    base = (settings.TWILIO_PUBLIC_WEBHOOK_BASE or "").rstrip("/")
    # Fall back to the inbound request's base URL when the env var hasn't been
    # configured to a public hostname (defaults to http://localhost:8000).
    if (not base or "localhost" in base) and request is not None:
        forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if forwarded_host:
            base = f"{forwarded_proto}://{forwarded_host}".rstrip("/")
    return f"{base}/api/portal-automation/phone-forward/{token}"


# IMPORTANT: literal routes MUST be registered before the {token} catch-all,
# otherwise FastAPI matches /phone-forward/test (etc.) as token="test" and
# returns the public-webhook's generic 200-OK instead of running the right handler.


@router.get("/phone-forward/me")
async def get_my_phone_forward(
    request: Request,
    user: User = Depends(get_current_user),
):
    return {
        "token": user.phone_forward_token,
        "url": _build_phone_forward_url(user.phone_forward_token, request),
    }


@router.get("/phone-forward/{token}/next-otp")
async def next_otp_for_external_driver(
    token: str,
    company: str | None = None,
    after: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Token-authed: return + CONSUME the newest unconsumed OTP for the token's
    user, optionally company-filtered. Lets an EXTERNAL process (the Windows
    Phoenix-terminal browser driver) get a HANDS-FREE OTP from `otp_inbox` — the
    same phone-forward chain the runner uses — instead of an operator typing it.
    `company` is a base portal_kind (e.g. `phoenix`) → matches that-company OR
    untagged codes, preferring the exact tag. `after` is an ISO timestamp to scope
    to codes received since the login submit. Returns {"otp": code|null}."""
    from sqlalchemy import or_, case as _case

    user = (await db.execute(
        select(User).where(User.phone_forward_token == token).limit(1)
    )).scalar_one_or_none()
    if not user:
        return {"otp": None}

    since = None
    if after:
        try:
            since = datetime.fromisoformat(after)
        except Exception:
            since = None
    base = (company or "").split("_")[0] or None

    stmt = select(OtpInbox).where(
        OtpInbox.user_id == user.id,
        OtpInbox.consumed_at.is_(None),
        OtpInbox.otp_code.is_not(None),
    )
    if since is not None:
        stmt = stmt.where(OtpInbox.received_at >= since)
    if base:
        stmt = stmt.where(
            or_(OtpInbox.portal_kind == base, OtpInbox.portal_kind.is_(None))
        ).order_by(
            _case((OtpInbox.portal_kind == base, 1), else_=0).desc(),
            OtpInbox.received_at.desc(),
        )
    else:
        stmt = stmt.order_by(OtpInbox.received_at.desc())

    row = (await db.execute(stmt.limit(1))).scalar_one_or_none()
    if not row:
        return {"otp": None}
    row.consumed_at = datetime.utcnow()
    await db.commit()
    return {"otp": row.otp_code, "company": row.matched_company}


@router.post("/phone-forward/token/regenerate")
async def regenerate_phone_forward_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user.phone_forward_token = secrets.token_urlsafe(32)
    await db.commit()
    return {
        "token": user.phone_forward_token,
        "url": _build_phone_forward_url(user.phone_forward_token, request),
    }


@router.post("/phone-forward/test")
async def test_phone_forward(
    payload: PhoneForwardIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Simulate an SMS arriving on the user's phone, without involving the
    phone. Inserts into otp_inbox identically to the public webhook so a
    pending run picks it up the same way."""
    body = (payload.message or "").strip()
    otp_match = OTP_REGEX.search(body)
    otp_code = otp_match.group(1) if otp_match else None

    from app.services.otp_routing import match_otp_company
    portal_kind, matched_company = await match_otp_company(db, body)

    db.add(OtpInbox(
        user_id=user.id,
        from_number="phone-forward-test",
        to_number="test",
        body=body[:500],
        otp_code=otp_code,
        portal_kind=portal_kind,
        matched_company=matched_company,
    ))
    await db.commit()
    return {"extracted_otp": otp_code, "portal_kind": portal_kind, "company": matched_company}


@router.get("/phone-forward/{token}/templates")
async def phone_forward_templates(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """SMS-OTP templates for the Android forwarder. PUBLIC — token-authenticated
    the same way as the webhook (the app already holds this token in its webhook
    URL). Returns the GLOBAL active templates so the app knows which SMS to pass.

    Unknown tokens get an empty list + 200 (don't leak token validity).
    """
    user_result = await db.execute(
        select(User).where(User.phone_forward_token == token).limit(1)
    )
    if user_result.scalar_one_or_none() is None:
        return {"templates": []}

    result = await db.execute(
        select(SmsOtpTemplate)
        .where(SmsOtpTemplate.active.is_(True))
        .order_by(SmsOtpTemplate.is_block, SmsOtpTemplate.company_name)
    )
    templates = [
        {"company_name": t.company_name, "pattern": t.pattern, "is_block": t.is_block}
        for t in result.scalars().all()
    ]
    return {"templates": templates}


@router.post("/phone-forward/{token}")
async def phone_forward_webhook(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Inbound SMS forwarded by the user's own phone (Android SMS Forwarder /
    iOS Shortcuts). PUBLIC — the token in the URL IS the auth credential.

    Accepts the SMS body in any reasonable shape so iOS Shortcuts / Android
    forwarder apps can be configured loosely:
        - JSON `{"message": "..."}` (recommended)
        - JSON with any of: message | body | text | content | sms
        - Plain text body (whole request body becomes the SMS body)
        - Form-encoded with same keys as JSON

    Unknown tokens get a 200 OK so an attacker can't enumerate by response code.
    """
    raw = await request.body()
    content_type = (request.headers.get("content-type") or "").lower()

    body_text = ""
    extracted_from = "raw"

    # 1. JSON
    if "application/json" in content_type or (raw and raw.lstrip().startswith(b"{")):
        try:
            import json as _json
            data = _json.loads(raw.decode("utf-8", "replace"))
            for key in ("message", "body", "text", "content", "sms"):
                if isinstance(data, dict) and key in data and data[key]:
                    body_text = str(data[key])
                    extracted_from = f"json.{key}"
                    break
            if not body_text and isinstance(data, dict) and data:
                # Fall back to concatenated values (unknown key shape)
                body_text = " ".join(str(v) for v in data.values() if v)
                extracted_from = "json.unknown_keys"
            elif not body_text and isinstance(data, str):
                body_text = data
                extracted_from = "json.string"
        except Exception as e:
            logger.warning("phone-forward: JSON parse failed: %s", e)

    # 2. Form-encoded
    if not body_text and "application/x-www-form-urlencoded" in content_type:
        try:
            form = await request.form()
            for key in ("message", "body", "text", "content", "sms", "Body"):
                if key in form and form[key]:
                    body_text = str(form[key])
                    extracted_from = f"form.{key}"
                    break
        except Exception as e:
            logger.warning("phone-forward: form parse failed: %s", e)

    # 3. Plain text — whole body is the SMS
    if not body_text and raw:
        body_text = raw.decode("utf-8", "replace").strip()
        extracted_from = "text/plain"

    body_text = body_text.strip()
    logger.info(
        "phone-forward: ct=%s len=%s extracted_from=%s preview=%r",
        content_type, len(raw), extracted_from, body_text[:80],
    )

    user_result = await db.execute(
        select(User).where(User.phone_forward_token == token).limit(1)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        logger.warning("phone-forward: unknown token %s...", token[:8])
        return {"status": "ok"}

    if not body_text:
        # Save anyway so the operator sees that the phone reached us — just no body parsed.
        db.add(OtpInbox(
            user_id=user.id,
            from_number="phone-forward",
            to_number=(user.phone or "personal")[:20],
            body=f"[empty body — content-type={content_type}, raw_len={len(raw)}]"[:500],
            otp_code=None,
        ))
        await db.commit()
        return {"status": "ok", "extracted": False, "reason": "empty body"}

    otp_match = OTP_REGEX.search(body_text)
    otp_code = otp_match.group(1) if otp_match else None

    # Tag the company from the SMS body (the forwarder strips the sender) so the
    # runner can route this code to the right portal. iPhone-proof: depends only
    # on the body text, not on any app-supplied metadata.
    from app.services.otp_routing import match_otp_company
    portal_kind, matched_company = await match_otp_company(db, body_text)

    db.add(OtpInbox(
        user_id=user.id,
        from_number="phone-forward",
        to_number=(user.phone or "personal")[:20],
        body=body_text[:500],
        otp_code=otp_code,
        portal_kind=portal_kind,
        matched_company=matched_company,
    ))
    await db.commit()
    return {"status": "ok", "extracted": bool(otp_code), "company": matched_company}


# ── Debug: serve portal-automation capture artifacts (screenshots/page dumps) ──
# Auth-gated, read-only, basename-sanitized. Temporary aid for diagnosing portal
# login failures (e.g. Harel OTP screen not rendering through the IL proxy).
@router.get("/_debug/screenshots")
async def list_debug_screenshots(user: User = Depends(get_current_user)):
    from app.services.portal_automation.runner import SCREENSHOT_ROOT
    if not SCREENSHOT_ROOT.exists():
        return {"root": str(SCREENSHOT_ROOT), "files": []}
    files = []
    for p in sorted(SCREENSHOT_ROOT.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            st = p.stat()
            files.append({"name": p.name, "size": st.st_size, "mtime": st.st_mtime})
    return {"root": str(SCREENSHOT_ROOT), "files": files}


@router.get("/_debug/screenshots/{name}")
async def get_debug_screenshot(name: str, user: User = Depends(get_current_user)):
    from pathlib import Path as _Path
    from fastapi.responses import FileResponse, PlainTextResponse
    from app.services.portal_automation.runner import SCREENSHOT_ROOT
    safe = _Path(name).name  # strip any path components
    if safe != name or not re.match(r"^[A-Za-z0-9._\-]+\.(png|txt|html)$", safe):
        raise HTTPException(status_code=400, detail="bad name")
    fp = SCREENSHOT_ROOT / safe
    if not fp.exists():
        raise HTTPException(status_code=404, detail="not found")
    if safe.endswith((".txt", ".html")):
        return PlainTextResponse(fp.read_text(errors="replace"))
    return FileResponse(str(fp))


# ── Local worker liveness (online/offline indicator for the web UI) ──
# The agent's local Windows worker writes its heartbeat straight to the DB; this
# read-only endpoint lets the site show whether that machine is on & ready.
WORKER_ONLINE_WINDOW_S = 90


@router.get("/worker/status")
async def worker_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (await db.execute(
        select(WorkerHeartbeat).where(WorkerHeartbeat.user_id == user.id)
    )).scalar_one_or_none()
    if not row or not row.last_seen:
        return {"online": False, "last_seen": None, "hostname": None, "current_job": None}
    age = (datetime.utcnow() - row.last_seen).total_seconds()
    return {
        "online": age <= WORKER_ONLINE_WINDOW_S,
        "last_seen": row.last_seen.isoformat(),
        "age_seconds": int(age),
        "hostname": row.hostname,
        "current_job": row.current_job,
    }


# ── Remote worker log sink (so support can "follow the log" server-side) ──
# Public, token-in-URL (phone_forward_token). The local worker + its installer
# POST diagnostics here; we echo them to the app log (visible in `railway logs`)
# even when the worker can't reach the DB. Never leaks whether a token is valid.
@router.post("/worker/log/{token}")
async def worker_log(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(
        select(User).where(User.phone_forward_token == token)
    )).scalar_one_or_none()
    body = (await request.body()).decode("utf-8", "replace")[:4000]
    logger.warning("WORKER-LOG [%s]: %s", user.email if user else "unknown-token", body)
    return {"status": "ok"}


# ── Self-contained worker code bundle (token-auth, no GitHub/git needed) ──
# Zips the worker's Python (under a backend/ prefix so paths mirror the repo).
@router.get("/worker/bundle/{token}")
async def worker_bundle(token: str, db: AsyncSession = Depends(get_db)):
    import io, zipfile
    from pathlib import Path as _P
    from fastapi.responses import Response

    user = (await db.execute(
        select(User).where(User.phone_forward_token == token)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="not found")

    backend = _P(__file__).resolve().parents[2]   # …/backend
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in (backend / "app").rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                z.write(p, "backend/" + str(p.relative_to(backend)).replace("\\", "/"))
        for rel in ("local_worker.py", "requirements.txt"):
            fp = backend / rel
            if fp.exists():
                z.write(fp, "backend/" + rel)
        wdir = backend / "scripts" / "windows"
        if wdir.exists():
            for p in wdir.rglob("*"):
                if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                    z.write(p, "backend/" + str(p.relative_to(backend)).replace("\\", "/"))
    buf.seek(0)
    return Response(buf.read(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="nifraim-worker.zip"'})


# ── Self-contained installer ──
# Download is a .BAT (double-click; immune to PowerShell execution policy, which
# hard-blocks unsigned downloaded .ps1). The .bat runs PowerShell with
# -ExecutionPolicy Bypass and pipes the PS installer (served at /installer-ps via
# token) straight into memory (irm|iex). The PS installer downloads the worker
# bundle, builds a venv, installs deps + Chromium, writes a BOM-free .env,
# registers the Scheduled Task, and REPORTS each step + errors to /worker/log.
def _worker_installer_ps(base: str, token: str, db_url: str, fernet: str, email: str) -> str:
    """PowerShell installer with a clean pastel WinForms progress window. The
    console is hidden (the .bat runs -WindowStyle Hidden); pip/Chromium output
    goes to a temp log, not the screen; the window auto-closes on success (no
    Enter). If WinForms can't load, the same install runs headless as a fallback."""
    tpl = r"""
$ErrorActionPreference = 'Stop'
$Base   = '__BASE__'
$Token  = '__TOKEN__'
$DbUrl  = '__DBURL__'
$Fernet = '__FERNET__'
$Email  = '__EMAIL__'
$Install = Join-Path $env:LOCALAPPDATA 'Nifraim'
$Log = Join-Path $env:TEMP 'nifraim_install.log'

$Work = {
  function Up($m, $p) {
    if ($sync) { $sync.status = $m; if ($p) { $sync.pct = $p } }
    try { Invoke-RestMethod -Uri "$Base/api/portal-automation/worker/log/$Token" -Method Post -Body ("installer: " + $m) -TimeoutSec 10 | Out-Null } catch {}
  }
  try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python 3.10+ required (python.org), then run again.' }
    New-Item -ItemType Directory -Force -Path $Install | Out-Null
    Up 'מוריד רכיבים' 15
    $zip = Join-Path $Install 'worker.zip'
    Invoke-WebRequest -Uri "$Base/api/portal-automation/worker/bundle/$Token" -OutFile $zip -TimeoutSec 180
    Expand-Archive -Path $zip -DestinationPath $Install -Force
    Up 'מתקין רכיבים (כמה דקות)' 40
    & python -m venv (Join-Path $Install 'venv') *>> $Log
    $py = Join-Path $Install 'venv\Scripts\python.exe'
    & $py -m pip install --upgrade pip *>> $Log
    & $py -m pip install -r (Join-Path $Install 'backend\requirements.txt') *>> $Log
    & $py -m playwright install chromium *>> $Log
    Up 'מגדיר' 80
    $lines = @(
      "DATABASE_URL=$DbUrl",
      "DATABASE_URL_SYNC=$($DbUrl -replace '\+asyncpg','')",
      "PORTAL_CRED_FERNET_KEY=$Fernet",
      "JWT_SECRET=local-worker",
      "WORKER_USER_EMAIL=$Email",
      "WORKER_LOG_BASE=$Base",
      "WORKER_LOG_TOKEN=$Token",
      "IL_RESIDENTIAL_PROXY="
    )
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines((Join-Path $Install '.env'), $lines, $enc)
    $worker = Join-Path $Install 'backend\local_worker.py'
    $startup = [Environment]::GetFolderPath('Startup')
    $vbsPath = Join-Path $startup 'NifraimWorker.vbs'
    $vbs = 'q = Chr(34)' + [Environment]::NewLine + 'CreateObject("WScript.Shell").Run q & "' + $py + '" & q & " " & q & "' + $worker + '" & q, 0, False'
    [System.IO.File]::WriteAllText($vbsPath, $vbs, $enc)
    Up 'מפעיל' 92
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*local_worker.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + $vbsPath + '"') -WindowStyle Hidden
    if ($sync) { $sync.pct = 100; $sync.done = $true }
    Up 'done' 100
  } catch {
    if ($sync) { $sync.error = $_.Exception.Message }
    Up ('FATAL: ' + $_.Exception.Message)
  }
}

try {
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  $sync = [hashtable]::Synchronized(@{ status = 'מתחילים'; pct = 5; done = $false; error = $null })

  $form = New-Object System.Windows.Forms.Form
  $form.Text = 'Nifraim'
  $form.ClientSize = New-Object System.Drawing.Size(460, 250)
  $form.StartPosition = 'CenterScreen'
  $form.FormBorderStyle = 'FixedSingle'
  $form.MaximizeBox = $false; $form.MinimizeBox = $false
  $form.BackColor = [System.Drawing.Color]::FromArgb(234, 247, 241)
  $form.RightToLeft = 'Yes'; $form.RightToLeftLayout = $true
  $form.Font = New-Object System.Drawing.Font('Segoe UI', 10)
  $form.TopMost = $true

  $title = New-Object System.Windows.Forms.Label
  $title.Text = 'Nifraim - התקנת הורדה אוטומטית'
  $title.Font = New-Object System.Drawing.Font('Segoe UI', 15, [System.Drawing.FontStyle]::Bold)
  $title.ForeColor = [System.Drawing.Color]::FromArgb(11, 59, 52)
  $title.AutoSize = $false; $title.TextAlign = 'MiddleCenter'; $title.SetBounds(20, 26, 420, 40)
  $form.Controls.Add($title)

  $sub = New-Object System.Windows.Forms.Label
  $sub.Text = 'מתקין את תוכנת ההורדה במחשב - רק רגע'
  $sub.ForeColor = [System.Drawing.Color]::FromArgb(17, 81, 74)
  $sub.AutoSize = $false; $sub.TextAlign = 'MiddleCenter'; $sub.SetBounds(20, 72, 420, 24)
  $form.Controls.Add($sub)

  $status = New-Object System.Windows.Forms.Label
  $status.Text = $sync.status
  $status.Font = New-Object System.Drawing.Font('Segoe UI', 12, [System.Drawing.FontStyle]::Bold)
  $status.ForeColor = [System.Drawing.Color]::FromArgb(4, 120, 87)
  $status.AutoSize = $false; $status.TextAlign = 'MiddleCenter'; $status.SetBounds(20, 130, 420, 30)
  $form.Controls.Add($status)

  $bar = New-Object System.Windows.Forms.ProgressBar
  $bar.Style = 'Marquee'; $bar.MarqueeAnimationSpeed = 28; $bar.SetBounds(40, 172, 380, 16)
  $form.Controls.Add($bar)

  $btn = New-Object System.Windows.Forms.Button
  $btn.Text = 'סגור'; $btn.SetBounds(180, 205, 100, 30); $btn.Visible = $false
  $btn.FlatStyle = 'Flat'; $btn.BackColor = [System.Drawing.Color]::White
  $btn.Add_Click({ $form.Close() })
  $form.Controls.Add($btn)

  $rs = [runspacefactory]::CreateRunspace(); $rs.Open()
  $rs.SessionStateProxy.SetVariable('sync', $sync)
  $rs.SessionStateProxy.SetVariable('Install', $Install)
  $rs.SessionStateProxy.SetVariable('Log', $Log)
  $rs.SessionStateProxy.SetVariable('Base', $Base)
  $rs.SessionStateProxy.SetVariable('Token', $Token)
  $rs.SessionStateProxy.SetVariable('DbUrl', $DbUrl)
  $rs.SessionStateProxy.SetVariable('Fernet', $Fernet)
  $rs.SessionStateProxy.SetVariable('Email', $Email)
  $psw = [powershell]::Create(); $psw.Runspace = $rs
  $null = $psw.AddScript($Work.ToString())
  $h = $psw.BeginInvoke()

  $timer = New-Object System.Windows.Forms.Timer
  $timer.Interval = 300
  $timer.Add_Tick({
    $status.Text = $sync.status
    if ($sync.error) {
      $timer.Stop(); $bar.Style = 'Continuous'; $bar.Value = 0
      $status.ForeColor = [System.Drawing.Color]::FromArgb(185, 28, 28)
      $status.Text = 'שגיאה: ' + $sync.error
      $btn.Visible = $true
    } elseif ($sync.done) {
      $timer.Stop(); $bar.Style = 'Continuous'; $bar.Value = 100
      $status.Text = 'הותקן! המחשב מחובר - חוזרים לאתר'
      $t2 = New-Object System.Windows.Forms.Timer
      $t2.Interval = 3500; $t2.Add_Tick({ $t2.Stop(); $form.Close() }); $t2.Start()
    }
  })
  $timer.Start()
  [void]$form.ShowDialog()
  try { $psw.EndInvoke($h) } catch {}
} catch {
  $sync = $null
  & $Work
}
"""
    return (tpl.replace("__BASE__", base).replace("__TOKEN__", token)
               .replace("__DBURL__", db_url).replace("__FERNET__", fernet)
               .replace("__EMAIL__", email))


@router.get("/worker/installer-ps/{token}")
async def worker_installer_ps(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """The PowerShell installer body, fetched by the .bat via irm|iex (token-auth,
    no JWT on the machine)."""
    from fastapi.responses import PlainTextResponse
    user = (await db.execute(
        select(User).where(User.phone_forward_token == token)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    base = str(request.base_url).rstrip("/").replace("http://", "https://", 1)
    ps = _worker_installer_ps(
        base, token,
        settings.WORKER_PUBLIC_DATABASE_URL or "<<WORKER_PUBLIC_DATABASE_URL not set>>",
        settings.PORTAL_CRED_FERNET_KEY or "",
        user.email,
    )
    return PlainTextResponse(ps, media_type="text/plain; charset=utf-8")


@router.get("/worker/installer")
async def worker_installer(request: Request, user: User = Depends(get_current_user)):
    """Download = a .BAT (double-clickable, immune to PS execution policy). It runs
    PowerShell with -ExecutionPolicy Bypass and pipes the PS installer into memory."""
    from fastapi.responses import PlainTextResponse
    if not user.phone_forward_token:
        raise HTTPException(status_code=400, detail="הפעל קודם 'העברת SMS אוטומטית' (טוקן טלפון חסר)")
    base = str(request.base_url).rstrip("/").replace("http://", "https://", 1)
    url = f"{base}/api/portal-automation/worker/installer-ps/{user.phone_forward_token}"
    bat = (
        "@echo off\r\n"
        f'start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "irm \'{url}\' | iex"\r\n'
    )
    return PlainTextResponse(
        bat,
        headers={"Content-Disposition": 'attachment; filename="nifraim-worker-setup.bat"'},
        media_type="application/octet-stream",
    )
