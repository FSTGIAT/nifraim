"""Orchestration — the brain of the clearinghouse flow.

Public functions (everything else is module-internal):
    create_inquiry(...)       — agent-initiated, status=pending
    submit_inquiry(...)       — background task, status=pending → submitted
    poll_and_ingest(...)      — scheduler/manual, walks the inbox
    expire_stale_inquiries(...) — scheduler, flips timed-out rows
    get_enriched_picture(...)  — read-only, shaped like portal dashboard
    reconcile_to_client_records(...) — matches holdings to production rows

All functions are async + strictly user_id-scoped (multi-tenancy).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.pension_inquiry import PensionInquiry, ALLOWED_TRANSITIONS
from app.models.pension_holding import PensionHolding
from app.models.pension_audit import PensionRawPayload
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.services.maslaka import adapter, audit
from app.services.maslaka.transport import get_transport, VaultFile
from app.utils.crypto import encrypt_bytes
from app.utils.sanitize import sanitize_record

logger = logging.getLogger(__name__)

MASLAKA_KEY = "MASLAKA_ENCRYPTION_KEY"


# ─── Inquiry creation + submission ─────────────────────────────────────────
async def create_inquiry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    customer_id_number: str,
    customer_name: str | None = None,
) -> PensionInquiry:
    """Create a `pending` inquiry row. Does NOT send anything to the vault —
    that's `submit_inquiry` (run in a background task). Splitting create/submit
    lets the API return immediately with a row the client can poll."""
    normalized = (customer_id_number or "").lstrip("0") or "0"
    inquiry = PensionInquiry(
        user_id=user_id,
        customer_id_number=normalized,
        customer_name=customer_name,
        status="pending",
        interface_code="events_v007",
        request_reference=uuid.uuid4().hex,
        expires_at=datetime.utcnow() + timedelta(days=settings.MASLAKA_INQUIRY_TIMEOUT_DAYS),
    )
    db.add(inquiry)
    await db.flush()
    await audit.log_event(
        db, user_id=user_id, inquiry_id=inquiry.id,
        customer_id_number=normalized, event_type="inquiry_created",
        from_status=None, to_status="pending", actor="agent",
    )
    await db.commit()
    return inquiry


async def submit_inquiry(db: AsyncSession, inquiry_id: uuid.UUID) -> None:
    """Build the outbound XML, encrypt+store it, drop it in the vault outbox,
    flip status to `submitted`. Idempotent: if the row is no longer `pending`
    we no-op (background tasks may race the user clicking submit twice)."""
    inquiry = await db.get(PensionInquiry, inquiry_id)
    if inquiry is None:
        logger.warning("maslaka.submit_inquiry: missing inquiry %s", inquiry_id)
        return
    if inquiry.status != "pending":
        logger.info("maslaka.submit_inquiry: %s already in %s — skip", inquiry_id, inquiry.status)
        return

    try:
        xml_bytes, ref = adapter.build_events_request(
            inquiry.customer_id_number,
            request_reference=inquiry.request_reference,
        )
        # Stash the encrypted outbound payload before we transport — if the
        # transport fails we still have the audit trail.
        await _store_raw_payload(
            db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
            direction="outbound", interface_code="events_v007",
            source_filename=f"events_v007_{ref}.xml",
            plaintext=xml_bytes,
        )

        transport = get_transport()
        filename = f"events_v007_{ref}.xml"
        await transport.send(filename, xml_bytes)

        # Advance status now that the transport succeeded.
        await _advance_status(
            db, inquiry, to_status="submitted", actor="system",
            event_type="submitted", detail=f"vault file: {filename}",
        )
        inquiry.vault_outbound_filename = filename
        inquiry.submitted_at = datetime.utcnow()
        await db.commit()
        logger.info("maslaka.submit_inquiry: %s → submitted (vault file %s)", inquiry.id, filename)
    except Exception as e:
        logger.exception("maslaka.submit_inquiry: failed for %s", inquiry_id)
        inquiry.error_code = "transport_error"
        inquiry.error_detail = str(e)[:500]
        await _advance_status(
            db, inquiry, to_status="failed", actor="system",
            event_type="transport_error", detail=str(e)[:500],
        )
        await db.commit()


# ─── Poll + ingest ─────────────────────────────────────────────────────────
async def poll_and_ingest(db: AsyncSession, *, user_id: uuid.UUID | None = None) -> dict:
    """Walk the vault inbox, route each file to feedback/holdings ingest,
    archive on success. Returns stats for the scheduler/health endpoint.

    `user_id=None` means "system poll across all tenants" (the scheduler
    path). User-initiated /poll passes the requester's id so they only
    process files matching their own inquiries (this happens naturally
    since `request_reference` is unique per inquiry).
    """
    transport = get_transport()
    files = await transport.list_inbox()
    stats = {
        "scanned": len(files),
        "feedback_ingested": 0,
        "holdings_ingested": 0,
        "unknown": 0,
        "errors": 0,
    }
    if not files:
        return stats

    for vf in files:
        try:
            await _ingest_one(db, transport, vf, user_id=user_id, stats=stats)
        except Exception as e:
            stats["errors"] += 1
            logger.exception("maslaka.poll: error ingesting %s", vf.name)
            await audit.log_event(
                db, user_id=user_id or uuid.UUID(int=0),
                event_type="ingest_error", actor="system",
                detail=f"{vf.name}: {str(e)[:400]}",
            )

    await db.commit()
    return stats


async def _ingest_one(
    db: AsyncSession,
    transport,
    vf: VaultFile,
    *,
    user_id: uuid.UUID | None,
    stats: dict,
) -> None:
    payload = await transport.fetch(vf.name)
    kind = adapter.classify_inbound(payload)

    if kind == "feedback":
        await _ingest_feedback(db, payload, source_filename=vf.name, scope_user_id=user_id)
        stats["feedback_ingested"] += 1
        await transport.archive(vf.name)
    elif kind == "holdings":
        await _ingest_holdings(db, payload, source_filename=vf.name, scope_user_id=user_id)
        stats["holdings_ingested"] += 1
        await transport.archive(vf.name)
    else:
        stats["unknown"] += 1
        logger.warning("maslaka.poll: unknown XML type, leaving in inbox: %s", vf.name)


async def _ingest_feedback(
    db: AsyncSession,
    payload: bytes,
    *,
    source_filename: str,
    scope_user_id: uuid.UUID | None,
) -> None:
    fb = adapter.parse_feedback(payload)
    inquiry = await _find_inquiry_by_reference(db, fb.request_reference, scope_user_id=scope_user_id)
    if inquiry is None:
        logger.warning(
            "maslaka.feedback: no inquiry for ref=%s (file=%s) — leaving unprocessed",
            fb.request_reference, source_filename,
        )
        return

    await _store_raw_payload(
        db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
        direction="inbound", interface_code="feedback_v009",
        source_filename=source_filename, plaintext=payload,
    )

    if fb.is_ack:
        inquiry.providers_expected = fb.providers_expected
        inquiry.acknowledged_at = datetime.utcnow()
        await _advance_status(
            db, inquiry, to_status="acknowledged", actor="system",
            event_type="ack_received",
            detail=f"providers_expected={fb.providers_expected}",
        )
    else:
        inquiry.error_code = fb.error_code or "defect"
        inquiry.error_detail = (fb.error_detail or "")[:500]
        await _advance_status(
            db, inquiry, to_status="failed", actor="system",
            event_type="defect_received",
            detail=f"{fb.error_code}: {fb.error_detail}",
        )


async def _ingest_holdings(
    db: AsyncSession,
    payload: bytes,
    *,
    source_filename: str,
    scope_user_id: uuid.UUID | None,
) -> None:
    ref, items = adapter.parse_holdings(payload)
    inquiry = await _find_inquiry_by_reference(db, ref, scope_user_id=scope_user_id)
    if inquiry is None:
        logger.warning(
            "maslaka.holdings: no inquiry for ref=%s (file=%s) — leaving unprocessed",
            ref, source_filename,
        )
        return

    raw = await _store_raw_payload(
        db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
        direction="inbound", interface_code="holdings_v009",
        source_filename=source_filename, plaintext=payload,
    )

    inserted = 0
    for it in items:
        row_data = sanitize_record(it.to_dict())
        h = PensionHolding(
            user_id=inquiry.user_id,
            inquiry_id=inquiry.id,
            raw_payload_id=raw.id,
            match_status="clearinghouse_only",  # reconciled below
            **row_data,
        )
        db.add(h)
        inserted += 1

    await db.flush()

    # Reconcile against active production ClientRecords.
    matched = await reconcile_to_client_records(db, inquiry=inquiry)

    inquiry.providers_received += 1
    await audit.log_event(
        db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
        customer_id_number=inquiry.customer_id_number,
        event_type="holdings_ingested", actor="system",
        detail=f"inserted={inserted} matched={matched} file={source_filename}",
    )

    expected = inquiry.providers_expected or 1
    if inquiry.providers_received >= expected:
        inquiry.completed_at = datetime.utcnow()
        await _advance_status(
            db, inquiry, to_status="complete", actor="system",
            event_type="status_changed",
            detail=f"received {inquiry.providers_received}/{expected}",
        )
    else:
        # Multi-file responses — record intermediate progress.
        await _advance_status(
            db, inquiry, to_status="partial", actor="system",
            event_type="status_changed",
            detail=f"received {inquiry.providers_received}/{expected}",
        )


# ─── Reconciliation ────────────────────────────────────────────────────────
async def reconcile_to_client_records(db: AsyncSession, *, inquiry: PensionInquiry) -> int:
    """Match this inquiry's holdings against the user's active production
    ClientRecords. Mirrors the id-matching idiom from `portal_service.py:119-132`
    (`or_()` with leading-zero variants + `func.ltrim`). Returns the number of
    holdings that flipped to `matched`."""
    prod_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == inquiry.user_id,
            FileUpload.is_production == True,  # noqa: E712
        )
    )
    prod_upload = prod_result.scalar_one_or_none()
    if prod_upload is None:
        return 0

    id_stripped = inquiry.customer_id_number  # already normalized in create_inquiry
    id_raw = id_stripped  # we don't have a non-normalized variant — fine, ltrim handles it

    prod_rows = (await db.execute(
        select(ClientRecord).where(
            ClientRecord.user_id == inquiry.user_id,
            ClientRecord.upload_id == prod_upload.id,
            or_(
                ClientRecord.id_number == id_raw,
                ClientRecord.id_number == id_stripped,
                func.ltrim(ClientRecord.id_number, "0") == id_stripped,
            ),
        )
    )).scalars().all()

    if not prod_rows:
        return 0

    # Build a {fund_policy_number: ClientRecord} index for the production side.
    prod_by_policy: dict[str, ClientRecord] = {}
    for r in prod_rows:
        key = (r.fund_policy_number or "").strip().lstrip("0") or (r.fund_policy_number or "")
        if key:
            prod_by_policy.setdefault(key, r)

    holdings_rows = (await db.execute(
        select(PensionHolding).where(PensionHolding.inquiry_id == inquiry.id)
    )).scalars().all()

    matched = 0
    for h in holdings_rows:
        key = (h.fund_policy_number or "").strip().lstrip("0") or (h.fund_policy_number or "")
        if key and key in prod_by_policy:
            h.matched_client_record_id = prod_by_policy[key].id
            h.match_status = "matched"
            matched += 1
    await db.flush()
    return matched


# ─── Expiry sweep ──────────────────────────────────────────────────────────
async def expire_stale_inquiries(db: AsyncSession) -> int:
    """Flip inquiries past their `expires_at` to `expired` (or `complete` if
    partial data exists — don't lose what we have). Returns count flipped."""
    now = datetime.utcnow()
    candidates = (await db.execute(
        select(PensionInquiry).where(
            PensionInquiry.expires_at.isnot(None),
            PensionInquiry.expires_at < now,
            PensionInquiry.status.in_({"pending", "submitted", "acknowledged", "partial"}),
        )
    )).scalars().all()

    flipped = 0
    for inq in candidates:
        # If we received at least one holdings file, treat it as complete
        # rather than throwing the partial picture away.
        final = "complete" if (inq.providers_received or 0) > 0 else "expired"
        await _advance_status(
            db, inq, to_status=final, actor="system",
            event_type="status_changed",
            detail=f"auto-expired: received {inq.providers_received}/{inq.providers_expected or '?'}",
        )
        if final == "complete":
            inq.completed_at = now
        flipped += 1

    if flipped:
        await db.commit()
    return flipped


# ─── Read-only assembler ───────────────────────────────────────────────────
async def get_enriched_picture(
    db: AsyncSession, *, user_id: uuid.UUID, id_number: str,
) -> dict | None:
    """Return holdings + KPIs for one customer, shaped like
    `portal_service.get_portal_dashboard()` so portal chart components can
    be reused once a frontend is added."""
    normalized = (id_number or "").lstrip("0") or "0"
    holdings = (await db.execute(
        select(PensionHolding).where(
            PensionHolding.user_id == user_id,
            PensionHolding.customer_id_number == normalized,
        )
    )).scalars().all()
    if not holdings:
        return None

    products = [_holding_to_product(h) for h in holdings]
    total_premium = sum(float(h.total_premium or 0) for h in holdings)
    total_accumulation = sum(float(h.accumulation or 0) for h in holdings)

    company_map: dict[str, dict] = defaultdict(
        lambda: {"company": "", "premium": 0.0, "accumulation": 0.0, "count": 0}
    )
    for h in holdings:
        co = h.receiving_company or h.provider_code or "אחר"
        slot = company_map[co]
        slot["company"] = co
        slot["premium"] += float(h.total_premium or 0)
        slot["accumulation"] += float(h.accumulation or 0)
        slot["count"] += 1

    companies = {h.receiving_company for h in holdings if h.receiving_company}

    last_inquiry = (await db.execute(
        select(PensionInquiry)
        .where(
            PensionInquiry.user_id == user_id,
            PensionInquiry.customer_id_number == normalized,
        )
        .order_by(PensionInquiry.created_at.desc())
    )).scalars().first()

    return {
        "customer_name": last_inquiry.customer_name if last_inquiry else None,
        "id_number": normalized,
        "products": products,
        "kpi": {
            "product_count": len(holdings),
            "total_premium": round(total_premium, 2),
            "total_accumulation": round(total_accumulation, 2),
            "company_count": len(companies),
        },
        "company_breakdown": sorted(
            company_map.values(), key=lambda x: x["accumulation"], reverse=True,
        ),
        "last_inquiry": {
            "id": str(last_inquiry.id),
            "status": last_inquiry.status,
            "completed_at": last_inquiry.completed_at.isoformat() if last_inquiry.completed_at else None,
        } if last_inquiry else None,
    }


def _holding_to_product(h: PensionHolding) -> dict:
    return {
        "product": h.product,
        "product_type": h.product_type,
        "receiving_company": h.receiving_company,
        "provider_code": h.provider_code,
        "total_premium": float(h.total_premium) if h.total_premium else None,
        "accumulation": float(h.accumulation) if h.accumulation else None,
        "expected_pension": float(h.expected_pension) if h.expected_pension else None,
        "management_fee_deposit": float(h.management_fee_deposit) if h.management_fee_deposit else None,
        "management_fee_balance": float(h.management_fee_balance) if h.management_fee_balance else None,
        "fund_policy_number": h.fund_policy_number,
        "track": h.track,
        "status_date": h.status_date.isoformat() if h.status_date else None,
        "match_status": h.match_status,
        "insurance_coverage": _maybe_json(h.insurance_coverage),
    }


def _maybe_json(raw: str | None):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw  # leave as-is if it wasn't JSON


# ─── Internal: state machine + payload storage ─────────────────────────────
async def _advance_status(
    db: AsyncSession,
    inquiry: PensionInquiry,
    *,
    to_status: str,
    actor: str,
    event_type: str,
    detail: str | None = None,
) -> None:
    """Validate transition against ALLOWED_TRANSITIONS, mutate the inquiry,
    write the audit row. No commit — caller batches."""
    prev = inquiry.status
    allowed = ALLOWED_TRANSITIONS.get(prev, set())
    if to_status not in allowed and to_status != prev:
        logger.warning(
            "maslaka.advance_status: invalid %s → %s on inquiry %s (allowed: %s) — forcing anyway",
            prev, to_status, inquiry.id, sorted(allowed),
        )
        # Don't silently swallow — record the violation in the audit log too.
        await audit.log_event(
            db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
            customer_id_number=inquiry.customer_id_number,
            event_type="invalid_transition", actor=actor,
            from_status=prev, to_status=to_status,
            detail=f"forced: {detail or ''}",
        )
    inquiry.status = to_status
    await audit.log_event(
        db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
        customer_id_number=inquiry.customer_id_number,
        event_type=event_type, actor=actor,
        from_status=prev, to_status=to_status,
        detail=detail,
    )


async def _store_raw_payload(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    inquiry_id: uuid.UUID,
    direction: str,
    interface_code: str | None,
    source_filename: str,
    plaintext: bytes,
) -> PensionRawPayload:
    ciphertext = encrypt_bytes(plaintext, key_env=MASLAKA_KEY)
    row = PensionRawPayload(
        user_id=user_id,
        inquiry_id=inquiry_id,
        direction=direction,
        interface_code=interface_code,
        source_filename=source_filename,
        ciphertext=ciphertext,
        byte_size=len(plaintext),
    )
    db.add(row)
    await db.flush()
    return row


async def _find_inquiry_by_reference(
    db: AsyncSession,
    request_reference: str,
    *,
    scope_user_id: uuid.UUID | None,
) -> PensionInquiry | None:
    if not request_reference:
        return None
    q = select(PensionInquiry).where(PensionInquiry.request_reference == request_reference)
    if scope_user_id is not None:
        q = q.where(PensionInquiry.user_id == scope_user_id)
    return (await db.execute(q)).scalar_one_or_none()


# ─── Retention purge (called by daily scheduler job) ──────────────────────
async def purge_old_payloads(db: AsyncSession) -> int:
    """Null `ciphertext` on `pension_raw_payloads` older than retention. Keep
    the audit + sizing trail; just drop the bulk encrypted blobs."""
    cutoff = datetime.utcnow() - timedelta(days=settings.MASLAKA_RETENTION_DAYS)
    result = await db.execute(
        update(PensionRawPayload)
        .where(
            PensionRawPayload.created_at < cutoff,
            PensionRawPayload.purged == False,  # noqa: E712
        )
        .values(ciphertext=None, purged=True)
    )
    await db.commit()
    return result.rowcount or 0
