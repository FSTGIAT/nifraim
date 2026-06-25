"""Pension clearinghouse (המסלקה הפנסיונית) HTTP surface.

All routes are auth-gated via `get_paid_user` (same dep used by uploads).
Strict `user.id` scoping — a customer-id passed in a URL only resolves
against records owned by the requesting user; missing → 404.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user as get_current_user
from app.database import async_session, get_db
from app.models.pension_audit import PensionAuditLog
from app.models.pension_holding import PensionHolding
from app.models.pension_inquiry import PensionInquiry
from app.models.user import User
from app.schemas.maslaka import (
    AuditEntryOut,
    EnrichedPictureOut,
    InquiryCreateRequest,
    InquiryDetailOut,
    InquiryOut,
    PollStatsOut,
)
from app.services.maslaka import orchestration

router = APIRouter()


# ─── Inquiry creation ──────────────────────────────────────────────────────
@router.post("/inquiry", response_model=InquiryOut)
async def create_inquiry_endpoint(
    payload: InquiryCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a pending inquiry and enqueue the actual vault send to a
    background task — same pattern as `api/production.py:82-89,174-176`."""
    inquiry = await orchestration.create_inquiry(
        db,
        user_id=user.id,
        customer_id_number=payload.customer_id_number,
        customer_name=payload.customer_name,
    )
    background_tasks.add_task(_submit_bg, inquiry.id)
    return _serialize_inquiry(inquiry)


async def _submit_bg(inquiry_id: uuid.UUID) -> None:
    """Run the vault submit on a fresh DB session — same trick as the
    portal-snapshot background helper in production.py uses."""
    async with async_session() as db:
        await orchestration.submit_inquiry(db, inquiry_id)


# ─── Inquiry listing + detail ──────────────────────────────────────────────
@router.get("/inquiries", response_model=list[InquiryOut])
async def list_inquiries(
    status: str | None = Query(default=None),
    customer_id_number: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(PensionInquiry).where(PensionInquiry.user_id == user.id)
    if status:
        q = q.where(PensionInquiry.status == status)
    if customer_id_number:
        normalized = customer_id_number.lstrip("0") or "0"
        q = q.where(PensionInquiry.customer_id_number == normalized)
    q = q.order_by(desc(PensionInquiry.created_at)).limit(200)
    rows = (await db.execute(q)).scalars().all()
    return [_serialize_inquiry(r) for r in rows]


@router.get("/inquiry/{inquiry_id}", response_model=InquiryDetailOut)
async def inquiry_detail(
    inquiry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inquiry = await db.get(PensionInquiry, inquiry_id)
    if inquiry is None or inquiry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    audit_rows = (await db.execute(
        select(PensionAuditLog)
        .where(PensionAuditLog.inquiry_id == inquiry.id)
        .order_by(PensionAuditLog.created_at.asc())
    )).scalars().all()
    holdings_count = (await db.execute(
        select(func.count()).select_from(PensionHolding).where(PensionHolding.inquiry_id == inquiry.id)
    )).scalar_one()

    base = _serialize_inquiry(inquiry)
    return InquiryDetailOut(
        **base.model_dump(),
        audit=[
            AuditEntryOut(
                event_type=a.event_type,
                from_status=a.from_status,
                to_status=a.to_status,
                actor=a.actor,
                detail=a.detail,
                created_at=a.created_at,
            ) for a in audit_rows
        ],
        holdings_count=holdings_count,
    )


# ─── Enriched per-customer view ────────────────────────────────────────────
@router.get("/customer/{id_number}", response_model=EnrichedPictureOut)
async def enriched_picture(
    id_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    picture = await orchestration.get_enriched_picture(db, user_id=user.id, id_number=id_number)
    if picture is None:
        raise HTTPException(status_code=404, detail="No clearinghouse holdings for this customer")
    return picture


# ─── Manual poll (for dev / on-demand refresh) ─────────────────────────────
@router.post("/poll", response_model=PollStatsOut)
async def manual_poll(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """User-scoped poll — only matches inbox files whose request_reference
    belongs to one of this user's inquiries. Safe to call repeatedly; the
    scheduler runs the same code system-wide on a timer."""
    stats = await orchestration.poll_and_ingest(db, user_id=user.id)
    return stats


# ─── Internal: serializer ──────────────────────────────────────────────────
def _serialize_inquiry(inq: PensionInquiry) -> InquiryOut:
    return InquiryOut(
        id=str(inq.id),
        user_id=str(inq.user_id),
        customer_id_number=inq.customer_id_number,
        customer_name=inq.customer_name,
        status=inq.status,
        interface_code=inq.interface_code,
        request_reference=inq.request_reference,
        vault_outbound_filename=inq.vault_outbound_filename,
        submitted_at=inq.submitted_at,
        acknowledged_at=inq.acknowledged_at,
        completed_at=inq.completed_at,
        expires_at=inq.expires_at,
        error_code=inq.error_code,
        error_detail=inq.error_detail,
        providers_expected=inq.providers_expected,
        providers_received=inq.providers_received,
        created_at=inq.created_at,
    )
