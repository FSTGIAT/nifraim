"""Orchestration — the brain of the clearinghouse flow.

Public functions (everything else is module-internal):
    create_inquiry(...)       — agent-initiated, status=pending
    submit_inquiry(...)       — Gateway claim loop, status=pending → submitted
    claim_and_submit_one(...) — FOR UPDATE SKIP LOCKED claim of one pending row
    submit_pending_inquiries(...) — bounded drain of the pending queue
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
from app.models.maslaka_agent_link import MaslakaAgentLink, APPROVED as LINK_APPROVED
from app.models.pension_holding import PensionHolding
from app.models.pension_audit import PensionRawPayload
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.services.maslaka import adapter, audit
from app.services.maslaka.events import (
    ACTION_CODES, build_events_request, build_file_number, environment,
    maslaka_now,
    MaslakaIdentityNotConfigured,
)
from app.services.maslaka.filenames import build_filename
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
    action_code: str | None = None,
    target_yatzran_id: str | None = None,
    information_date: str | None = None,
) -> PensionInquiry:
    """Create a `pending` inquiry row. Does NOT send anything to the vault —
    that's `submit_inquiry` (run in a background task). Splitting create/submit
    lets the API return immediately with a row the client can poll.

    For a production report (2000/2100) `customer_id_number` is the AGENT's own
    ID and `target_yatzran_id` the body asked — see events.build_events_request."""
    action_code = action_code or DEFAULT_ACTION_CODE
    if action_code not in ACTION_CODES:
        raise ValueError(f"unknown action code {action_code!r}")
    normalized = (customer_id_number or "").lstrip("0") or "0"
    inquiry = PensionInquiry(
        user_id=user_id,
        customer_id_number=normalized,
        customer_name=customer_name,
        status="pending",
        interface_code=f"events_v007:{action_code}",
        target_yatzran_id=target_yatzran_id,
        information_date=information_date,
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


# ─── Daily file sequence (EEEE in the נספח ו' filename) ─────────────────────
# The 4-digit sequence resets at the start of each business day and must be
# unique per sender per day: two files a second apart with the same sequence
# get IDENTICAL names, and the Transporter uploads one and silently drops the
# rest. `submit_pending_inquiries` drains up to 20 rows per tick, so this is a
# real collision, not a theoretical one.
#
# An advisory lock (not a counter table) because this repo currently has three
# alembic heads — allocating without a schema change is the smaller risk. The
# lock is transaction-scoped, so it releases on the commit inside submit_inquiry.
# Gaps are fine: Swiftness's own samples jump 6501 → 6535 → 6555.
DEFAULT_ACTION_CODE = "9100"


class AssociationNotApproved(RuntimeError):
    """The requesting user's שיוך לבית תוכנה is not approved by the מסלקה."""   # טרום ייעוץ, one-off. No UI picker yet.


async def _allocate_daily_sequence(db: AsyncSession, *, sender_id: str, when: datetime) -> int:
    day_start = datetime(when.year, when.month, when.day)
    key = f"maslaka_seq:{sender_id}:{day_start.date().isoformat()}"
    await db.execute(select(func.pg_advisory_xact_lock(func.hashtext(key))))
    used = (await db.execute(
        select(func.count(PensionInquiry.id)).where(
            PensionInquiry.submitted_at >= day_start,
            PensionInquiry.vault_outbound_filename.is_not(None),
        )
    )).scalar_one()
    return int(used) + 1


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
        # The real ממשק אירועים v007 builder + the נספח ו' filename grammar.
        # Until 2026-09-10 this path used a stub that produced
        # `events_v007_<hex>.xml`, which is not a legal name in that grammar at
        # all — the מסלקה identifies a file by its NAME before it parses any
        # XML, so every request the app sent on its own would have been
        # discarded without content-level feedback.
        sender_id = settings.MASLAKA_AGENT_ID or ""
        # Israel local, explicitly — see events.maslaka_now(). The filename
        # stamp, TAARICH-BITZUA and the allocator's business-day window all use
        # this one clock; the "business day" the sequence resets on is an
        # ISRAELI day, not a UTC one.
        now = maslaka_now()
        env_code, file_type = environment()
        sequence = await _allocate_daily_sequence(db, sender_id=sender_id, when=now)

        # `rpartition` on a colon-less value returns the WHOLE string, so rows
        # created before the action code was recorded (interface_code =
        # "events_v007") would otherwise pass "events_v007" as an action code
        # and fail as a generic transport_error. Validate against the table.
        _parsed = (inquiry.interface_code or "").rpartition(":")[2]
        action_code = _parsed if _parsed in ACTION_CODES else DEFAULT_ACTION_CODE

        # The worker is the last host before a regulator, so it re-checks the
        # agent's association itself rather than trusting that the API did.
        # A feature flag is not an authorisation, and neither is a row that
        # merely reached this queue.
        link = (await db.execute(
            select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == inquiry.user_id)
        )).scalar_one_or_none()
        if link is None or link.status != LINK_APPROVED or not link.agent_id_number:
            raise AssociationNotApproved(
                f"user {inquiry.user_id} has no APPROVED שיוך לבית תוכנה "
                f"(status={getattr(link, 'status', None)!r}) — refusing to send on their behalf"
            )

        req = build_events_request(
            action_code=action_code,
            customer_id_number=inquiry.customer_id_number,
            customer_first_name=(inquiry.customer_name or "").split(" ")[0],
            customer_last_name=" ".join((inquiry.customer_name or "").split(" ")[1:]),
            sequence=sequence,
            when=now,
            environment_code=env_code,
            file_number=build_file_number(sender_id=sender_id, sequence=sequence, when=now),
            acting_agent_id=link.agent_id_number,
            acting_agent_name=link.agent_name,
            yatzran_id=inquiry.target_yatzran_id,
            information_date=inquiry.information_date,
        )
        xml_bytes = req.xml
        filename = build_filename(
            direction="001",              # בעל רישיון → מסלקה
            sender_id=sender_id,
            service="EVENTS",
            version="007",
            sequence=sequence,
            product_family="000",         # only אחזקות/טרום-ייעוץ files name a family
            file_type=file_type,          # same call as env_code — they cannot disagree
            when=now,                     # the SAME instant as TAARICH-BITZUA / MISPAR-HAKOVETZ
        )

        # Stash the encrypted outbound payload before we transport — if the
        # transport fails we still have the audit trail.
        await _store_raw_payload(
            db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
            direction="outbound", interface_code="events_v007",
            source_filename=filename,
            plaintext=xml_bytes,
        )

        transport = get_transport()
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
    except AssociationNotApproved as e:
        logger.error("maslaka.submit_inquiry: %s — %s", inquiry_id, e)
        inquiry.error_code = "association_not_approved"
        inquiry.error_detail = str(e)[:500]
        await _advance_status(
            db, inquiry, to_status="failed", actor="system",
            event_type="association_not_approved", detail=str(e)[:500],
        )
        await db.commit()
    except MaslakaIdentityNotConfigured as e:
        # Not a transport problem — the deployment has no clearinghouse identity.
        # Label it as itself so the operator fixes the env instead of chasing SFTP.
        logger.error("maslaka.submit_inquiry: %s — identity not configured", inquiry_id)
        inquiry.error_code = "identity_not_configured"
        inquiry.error_detail = str(e)[:500]
        await _advance_status(
            db, inquiry, to_status="failed", actor="system",
            event_type="identity_not_configured", detail=str(e)[:500],
        )
        await db.commit()
    except Exception as e:
        logger.exception("maslaka.submit_inquiry: failed for %s", inquiry_id)
        inquiry.error_code = "transport_error"
        inquiry.error_detail = str(e)[:500]
        await _advance_status(
            db, inquiry, to_status="failed", actor="system",
            event_type="transport_error", detail=str(e)[:500],
        )
        await db.commit()


# ─── The agent's bodies, and automatic monthly production ──────────────────
async def agent_bodies(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """Every body a production report can be asked from, with how many of the
    agent's own customers sit there (from their records) and whether a monthly
    subscription (2100) is already open."""
    from app.services.maslaka.code_tables import PROVIDER_CODE_TO_COMPANY, provider_code_for_company

    counts: dict[str, int] = {}
    rows = (await db.execute(
        select(ClientRecord.receiving_company,
               func.count(func.distinct(func.ltrim(ClientRecord.id_number, "0"))))
        .where(ClientRecord.user_id == user_id)
        .group_by(ClientRecord.receiving_company)
    )).all()
    for company, n in rows:
        code = provider_code_for_company(company)
        if code:
            counts[code] = counts.get(code, 0) + int(n or 0)

    monthly = set((await db.execute(
        select(PensionInquiry.target_yatzran_id).where(
            PensionInquiry.user_id == user_id,
            PensionInquiry.interface_code == "events_v007:2100",
            PensionInquiry.status.notin_(("failed", "expired")),
        )
    )).scalars().all())

    out = [
        {"id": code, "name": name, "clients": counts.get(code, 0), "monthly": code in monthly}
        for code, name in PROVIDER_CODE_TO_COMPANY.items()
    ]
    out.sort(key=lambda b: (-b["clients"], b["name"]))
    return out


async def ensure_monthly_subscriptions(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Open a monthly production subscription (2100) with every body the agent
    has customers at and is not yet subscribed to. Runs ONLY for an approved
    agent who consented (`auto_production`). Returns how many were created —
    as `pending` rows; the Gateway sends them."""
    from app.models.maslaka_agent_link import MaslakaAgentLink
    from app.services.maslaka.code_tables import label_for_provider

    link = (await db.execute(
        select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == user_id)
    )).scalar_one_or_none()
    if link is None or link.status != LINK_APPROVED or not link.auto_production or not link.agent_id_number:
        return 0
    created = 0
    for b in await agent_bodies(db, user_id):
        if b["clients"] > 0 and not b["monthly"]:
            await create_inquiry(
                db, user_id=user_id, customer_id_number=link.agent_id_number,
                customer_name=label_for_provider(b["id"]), action_code="2100",
                target_yatzran_id=b["id"],
            )
            created += 1
    if created:
        logger.info("maslaka.auto_production: user %s — opened %d monthly subscription(s)", user_id, created)
    return created


async def ensure_all_monthly_subscriptions(db: AsyncSession) -> int:
    """Daily sweep: every consenting approved agent gets subscriptions for any
    body that has appeared in their records since."""
    from app.models.maslaka_agent_link import MaslakaAgentLink
    users = (await db.execute(select(MaslakaAgentLink.user_id).where(
        MaslakaAgentLink.status == LINK_APPROVED,
        MaslakaAgentLink.auto_production == True,  # noqa: E712
    ))).scalars().all()
    total = 0
    for uid in users:
        total += await ensure_monthly_subscriptions(db, uid)
    return total


# ─── When should the answer arrive? ────────────────────────────────────────
# Straight from Swiftness's published rules, so the agent is never left staring
# at "נשלח" with no idea whether silence is normal:
#   * 9100/9101 (all / one body, טרום ייעוץ): משוב א' within 3 hours; the savers
#     Q&A: since 22.5.2022 the full "all products" answer is expected within
#     3–4 hours of sending (legal ceiling: 3 business days, V9M.pdf).
#   * 2000 one-off production report: "המענה יתקבל עד ל-15 בחודש העוקב להגשת
#     הבקשה" (clalei_prod_1.pdf §13.1); 2100 monthly — the same 15th, monthly.
_FAST_INFO_CODES = {"9100", "9101"}
_PRODUCTION_CODES = {"2000", "2100"}
_OPEN_STATUSES = {"submitted", "acknowledged", "partial"}


def expected_answer_by(inquiry: PensionInquiry) -> tuple[datetime | None, str | None]:
    """(due time as tz-aware UTC, short basis) — or (None, None) when not applicable."""
    from zoneinfo import ZoneInfo
    if inquiry.status not in _OPEN_STATUSES or not inquiry.submitted_at:
        return None, None
    code = (inquiry.interface_code or "").rpartition(":")[2]
    utc = ZoneInfo("UTC")
    sent = inquiry.submitted_at.replace(tzinfo=utc)       # stored naive UTC
    if code in _FAST_INFO_CODES:
        return sent + timedelta(hours=4), "info_hours"
    if code in _PRODUCTION_CODES:
        il = ZoneInfo("Asia/Jerusalem")
        local = sent.astimezone(il)
        y, m = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
        due = datetime(y, m, 15, 23, 59, tzinfo=il)
        return due.astimezone(utc), "production_15th"
    return None, None


# ─── Poll + ingest ─────────────────────────────────────────────────────────
async def claim_and_submit_one(db: AsyncSession) -> uuid.UUID | None:
    """Claim the oldest `pending` inquiry and run its vault send. Returns the id
    submitted, or None when the queue is empty.

    `SELECT ... FOR UPDATE SKIP LOCKED` rather than the status-CAS that
    `local_worker._claim_pending_run` uses. The difference is how long the claim
    lives: a PortalRun claim outlives its transaction by minutes of Playwright, so
    it needs a durable `running` marker in a column. A maslaka send is seconds and
    sits entirely inside one transaction, so a row lock is enough — and a crash
    releases it automatically, which is why there is no stale-claim reaper here.

    A status CAS would also be actively *wrong*: flipping to `submitted` before the
    send means a crash mid-send loses the request while the row claims success. The
    status must advance only after `transport.send()` returns, which is exactly
    what `submit_inquiry` already does.

    ONE row at a time, deliberately: `submit_inquiry` commits internally, which
    would release a multi-row lock early and hand the rest to a concurrent claimer
    mid-flight.
    """
    inquiry_id = (await db.execute(
        select(PensionInquiry.id)
        .where(PensionInquiry.status == "pending")
        .order_by(PensionInquiry.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )).scalar_one_or_none()
    if inquiry_id is None:
        return None
    await submit_inquiry(db, inquiry_id)      # commits, releasing the row lock
    return inquiry_id


async def submit_pending_inquiries(db: AsyncSession, *, max_per_tick: int = 20) -> int:
    """Drain the pending queue, bounded. Returns how many were submitted.

    Bounded so one tick can never monopolise the loop: with a large backlog the
    worker still returns to poll the inbox instead of spending the whole cycle
    sending. `submit_inquiry` never raises — it records `failed` on the row — so a
    single poisoned inquiry cannot stall the drain.
    """
    submitted = 0
    for _ in range(max_per_tick):
        if await claim_and_submit_one(db) is None:
            break
        submitted += 1
    return submitted


async def poll_and_ingest(db: AsyncSession, *, user_id: uuid.UUID | None = None) -> dict:
    """Walk the vault inbox, route each file to feedback/holdings ingest,
    archive on success. Returns stats for the scheduler/health endpoint.

    `user_id=None` means "system poll across all tenants" (the scheduler
    path). User-initiated /poll passes the requester's id so they only
    process files matching their own inquiries (this happens naturally
    since `request_reference` is unique per inquiry).
    """
    await backfill_mislaka_numbers(db)
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
                db, user_id=user_id,
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
        # Archive ONLY when every customer in the file was routed. An unmatched
        # data file used to be archived anyway — i.e. silently dropped from the
        # inbox. It stays put now, and the next poll retries it (e.g. after the
        # receipt carrying its GUID has been ingested).
        if await _ingest_holdings(db, payload, source_filename=vf.name, scope_user_id=user_id):
            stats["holdings_ingested"] += 1
            await transport.archive(vf.name)
        else:
            stats["unknown"] += 1
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
    # The מסלקה correlates by echoing the FILENAME it is answering
    # (`SHEM-HAKOVETZ`), not by any reference of ours — `request_reference`
    # never appears on the wire. Try the filename first and keep the reference
    # lookup for the legacy stub fixtures.
    inquiry = None
    if fb.acked_filename:
        inquiry = await _find_inquiry_by_outbound_filename(
            db, fb.acked_filename, scope_user_id=scope_user_id)
    if inquiry is None and fb.request_reference:
        inquiry = await _find_inquiry_by_reference(
            db, fb.request_reference, scope_user_id=scope_user_id)
    if inquiry is None:
        logger.warning(
            "maslaka.feedback: no inquiry for acked=%s ref=%s (file=%s) — leaving unprocessed",
            fb.acked_filename, fb.request_reference, source_filename,
        )
        return

    await _store_raw_payload(
        db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
        direction="inbound", interface_code="feedback_v009",
        source_filename=source_filename, plaintext=payload,
    )

    # MISPAR-MISLAKA: the GUID the מסלקה gave this request. Every insurer's data
    # file carries it — without it, an answer cannot find its request.
    if fb.mislaka_number and not inquiry.mislaka_number:
        inquiry.mislaka_number = fb.mislaka_number

    if fb.sug_mashov == "2":
        # משוב ב' is an INSURER's content answer (e.g. "no such member") — it
        # counts as that body having answered, and is never a failure of the
        # whole request (other bodies may still return data).
        inquiry.providers_received = (inquiry.providers_received or 0) + 1
        await audit.log_event(
            db, user_id=inquiry.user_id, inquiry_id=inquiry.id,
            customer_id_number=inquiry.customer_id_number,
            event_type="content_feedback", actor="system",
            detail=f"משוב ב': {fb.error_code or 'ok'} {fb.error_detail or ''}"[:500],
        )
        return

    if fb.is_ack:
        # SUG-MASHOV 1 = משוב א', a technical receipt: "well-formed, accepted".
        # It is NOT the answer — the data arrives later as משוב ב' or holdings.
        # Advancing past `acknowledged` here would report success on an inquiry
        # that has returned no data at all.
        if fb.providers_expected is not None:
            inquiry.providers_expected = fb.providers_expected
        inquiry.acknowledged_at = datetime.utcnow()
        await _advance_status(
            db, inquiry, to_status="acknowledged", actor="system",
            event_type="ack_received",
            detail=f"sug_mashov={fb.sug_mashov} providers_expected={fb.providers_expected}",
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
) -> bool:
    """Ingest a REAL holdings / CONSLT answer. Returns True when every customer
    in it was routed to a request (the caller archives only then).

    Parsing is `services/mimshak` — the parser proven on Swiftness's CONSLT
    samples and on Migdal/Clal (tests/test_maslaka_conslt_parse.py). The old
    `adapter.parse_holdings` read tags our stub invented and found nothing.

    Routing, per customer (`adapter.holdings_index`):
      1. MISPAR-MISLAKA → the request whose receipt carried that GUID;
      2. else the authorised agent (PerutMeyupeKoach) → that agent's approved
         link → their open request for this customer (9100) or this body
         (2000/2100).
    """
    from app.models.maslaka_agent_link import MaslakaAgentLink
    from app.services.mimshak import parse_mimshak_dat
    from app.services.maslaka.code_tables import label_for_provider

    index = adapter.holdings_index(payload)
    records = parse_mimshak_dat(payload, source_filename).get("records", [])
    if not records:
        logger.warning("maslaka.holdings: %s parsed to 0 records — leaving in inbox", source_filename)
        return False

    guids = {v["guid"] for v in index.values() if v.get("guid")}
    by_guid: dict[str, PensionInquiry] = {}
    if guids:
        q = select(PensionInquiry).where(PensionInquiry.mislaka_number.in_(guids))
        if scope_user_id is not None:
            q = q.where(PensionInquiry.user_id == scope_user_id)
        for inq in (await db.execute(q)).scalars().all():
            by_guid[inq.mislaka_number] = inq

    open_statuses = ("submitted", "acknowledged", "partial")

    # The file header's recipient (NetuneiGoremNimaan) — for a production file
    # this is the מפיץ it is addressed to.
    header_nimaan = (adapter.header_recipient_id(payload) or "").lstrip("0") or None

    async def unique(q) -> PensionInquiry | None:
        if scope_user_id is not None:
            q = q.where(PensionInquiry.user_id == scope_user_id)
        rows = (await db.execute(q.limit(2))).scalars().all()
        return rows[0] if len(rows) == 1 else None     # 0 or ambiguous → never guess

    async def by_customer(cust: str) -> PensionInquiry | None:
        # 9100/9101 answer: the customer's ID identifies the request when exactly
        # one open information request exists for that ID. Measured 2026-09-25:
        # our PROD receipts are FILE-level (RAMAT-MASHOV=1) and carry NO
        # MISPAR-MISLAKA, so the GUID route never fires for our own requests.
        return await unique(select(PensionInquiry).where(
            PensionInquiry.customer_id_number == cust,
            PensionInquiry.interface_code.in_(("events_v007:9100", "events_v007:9101")),
            PensionInquiry.status.in_(open_statuses),
        ))

    async def by_body(keys: dict) -> PensionInquiry | None:
        # Production answer (2000/2100): the body's ח.פ, narrowed to the agent
        # the header addresses when that is one of our approved agents; else the
        # single open production request to that body. Two agents asking the same
        # body with no header match → ambiguous → left in the inbox.
        yat = keys.get("yatzran")
        if not yat:
            return None
        q = select(PensionInquiry).where(
            PensionInquiry.target_yatzran_id == yat,
            PensionInquiry.interface_code.in_(("events_v007:2000", "events_v007:2100")),
            PensionInquiry.status.in_(open_statuses),
        )
        if header_nimaan:
            link_users = (await db.execute(select(MaslakaAgentLink.user_id).where(
                MaslakaAgentLink.status == LINK_APPROVED,
                func.ltrim(MaslakaAgentLink.agent_id_number, "0") == header_nimaan,
            ))).scalars().all()
            if len(link_users) == 1:
                hit = (await db.execute(q.where(PensionInquiry.user_id == link_users[0])
                                         .order_by(PensionInquiry.interface_code.desc(),
                                                   PensionInquiry.created_at.desc()))).scalars().first()
                if hit is not None:
                    return hit
        users = set((await db.execute(select(PensionInquiry.user_id).where(
            PensionInquiry.target_yatzran_id == yat,
            PensionInquiry.interface_code.in_(("events_v007:2000", "events_v007:2100")),
            PensionInquiry.status.in_(open_statuses),
        ))).scalars().all())
        if len(users) != 1:
            return None
        # prefer the monthly subscription (it stays open), else the newest one-off
        return (await db.execute(q.order_by(PensionInquiry.interface_code.desc(),
                                            PensionInquiry.created_at.desc()))).scalars().first()

    async def by_agent(cust: str, keys: dict) -> PensionInquiry | None:
        agent = keys.get("agent_id")
        if not agent:
            return None
        links = (await db.execute(select(MaslakaAgentLink).where(
            MaslakaAgentLink.status == LINK_APPROVED,
            func.ltrim(MaslakaAgentLink.agent_id_number, "0") == agent,
        ))).scalars().all()
        if len(links) != 1:
            return None                      # none, or ambiguous — never guess
        uid = links[0].user_id
        if scope_user_id is not None and uid != scope_user_id:
            return None
        base = select(PensionInquiry).where(
            PensionInquiry.user_id == uid, PensionInquiry.status.in_(open_statuses),
        ).order_by(PensionInquiry.created_at.desc())
        hit = (await db.execute(base.where(PensionInquiry.customer_id_number == cust))).scalars().first()
        if hit is None and keys.get("yatzran"):
            hit = (await db.execute(base.where(
                PensionInquiry.target_yatzran_id == keys["yatzran"],
                PensionInquiry.interface_code.in_(("events_v007:2000", "events_v007:2100")),
            ))).scalars().first()
        return hit

    routed: dict[uuid.UUID, tuple[PensionInquiry, list[dict]]] = {}
    unrouted: set[str] = set()
    for rec in records:
        cust = str(rec.get("id_number") or "").lstrip("0")
        if not cust:
            continue
        keys = index.get(cust, {})
        inq = (by_guid.get(keys.get("guid") or "")
               or await by_agent(cust, keys)
               or await by_customer(cust)
               or await by_body(keys))
        if inq is None:
            unrouted.add(cust)
            continue
        routed.setdefault(inq.id, (inq, []))[1].append(rec | {"_yatzran": keys.get("yatzran")})

    if unrouted:
        logger.warning(
            "maslaka.holdings: %s — %d customer(s) not routable yet (guid/agent unknown): %s — leaving in inbox",
            source_filename, len(unrouted), sorted(unrouted)[:5],
        )
        # Nothing has been written for this file yet (routing happens before any
        # insert), so there is nothing to undo — and a rollback here would also
        # discard receipts ingested earlier in the same poll.
        return False

    for inq, recs in routed.values():
        raw = await _store_raw_payload(
            db, user_id=inq.user_id, inquiry_id=inq.id,
            direction="inbound", interface_code="holdings_v009",
            source_filename=source_filename, plaintext=payload,
        )
        for rec in recs:
            yat = rec.get("_yatzran")
            db.add(PensionHolding(
                user_id=inq.user_id,
                inquiry_id=inq.id,
                raw_payload_id=raw.id,
                match_status="clearinghouse_only",
                **sanitize_record({
                "customer_id_number": str(rec.get("id_number") or "").lstrip("0"),
                "receiving_company": rec.get("receiving_company") or label_for_provider(yat),
                "provider_code": yat,
                "product": rec.get("product"),
                "product_type": rec.get("product_type"),
                "fund_policy_number": rec.get("fund_policy_number"),
                "accumulation": rec.get("accumulation"),
                "total_premium": rec.get("total_premium"),
                })))
        await db.flush()
        matched = await reconcile_to_client_records(db, inquiry=inq)

        inq.providers_received = (inq.providers_received or 0) + 1
        await audit.log_event(
            db, user_id=inq.user_id, inquiry_id=inq.id,
            customer_id_number=inq.customer_id_number,
            event_type="holdings_ingested", actor="system",
            detail=f"{source_filename}: {len(recs)} product(s), {matched} matched to production",
        )
        # A monthly subscription (2100) stays open: a new file comes every month.
        if inq.interface_code == "events_v007:2100":
            if inq.status != "partial":
                await _advance_status(db, inq, to_status="partial", actor="system",
                                      event_type="holdings_received", detail=source_filename)
            continue
        # A 9100 goes to EVERY body, and each answers in its own file — so with
        # no known count, one file means "partial", never "complete". The expiry
        # sweep turns a partial request complete once its window closes.
        expected = inq.providers_expected
        if expected and inq.providers_received >= expected:
            inq.completed_at = datetime.utcnow()
            await _advance_status(db, inq, to_status="complete", actor="system",
                                  event_type="holdings_received",
                                  detail=f"received {inq.providers_received}/{expected}")
        elif inq.status != "partial":
            await _advance_status(db, inq, to_status="partial", actor="system",
                                  event_type="holdings_received",
                                  detail=f"received {inq.providers_received}/{expected}")
    return True


# ─── GUID backfill ─────────────────────────────────────────────────────────
async def backfill_mislaka_numbers(db: AsyncSession) -> int:
    """Recover MISPAR-MISLAKA for requests whose receipt was ingested before
    the GUID was kept (everything before 2026-09-25 afternoon). The receipts
    are stored encrypted; decrypting needs MASLAKA_ENCRYPTION_KEY, which only
    the Gateway holds — so this runs there, at the start of every poll."""
    from app.utils.crypto import decrypt_bytes
    rows = (await db.execute(
        select(PensionInquiry.id, PensionRawPayload.ciphertext)
        .join(PensionRawPayload, PensionRawPayload.inquiry_id == PensionInquiry.id)
        .where(
            PensionInquiry.mislaka_number.is_(None),
            PensionInquiry.vault_outbound_filename.is_not(None),
            PensionRawPayload.direction == "inbound",
            PensionRawPayload.interface_code == "feedback_v009",
        )
    )).all()
    found = 0
    for inq_id, ciphertext in rows:
        try:
            guid = adapter.parse_feedback(decrypt_bytes(ciphertext, key_env=MASLAKA_KEY)).mislaka_number
        except Exception:
            continue
        if guid:
            inq = await db.get(PensionInquiry, inq_id)
            if inq and not inq.mislaka_number:
                inq.mislaka_number = guid
                found += 1
    if found:
        await db.commit()
        logger.info("maslaka.backfill: recovered MISPAR-MISLAKA for %d request(s)", found)
    return found


async def reconcile_to_client_records(db: AsyncSession, *, inquiry: PensionInquiry) -> int:
    """Match this inquiry's holdings against the user's active production
    ClientRecords, by EACH holding's own customer + policy number.

    Keyed per holding, not by `inquiry.customer_id_number`: for a production
    request (2000/2100) that is the AGENT's own ID, and would match nothing.
    And across every active production upload — companies coexist as separate
    active uploads, so `scalar_one_or_none()` here used to raise."""
    holdings_rows = (await db.execute(
        select(PensionHolding).where(PensionHolding.inquiry_id == inquiry.id)
    )).scalars().all()
    ids = {(h.customer_id_number or "").lstrip("0") for h in holdings_rows} - {""}
    if not ids:
        return 0

    upload_ids = (await db.execute(
        select(FileUpload.id).where(
            FileUpload.user_id == inquiry.user_id,
            FileUpload.is_production == True,  # noqa: E712
        )
    )).scalars().all()
    if not upload_ids:
        return 0

    prod_rows = (await db.execute(
        select(ClientRecord).where(
            ClientRecord.user_id == inquiry.user_id,
            ClientRecord.upload_id.in_(upload_ids),
            func.ltrim(ClientRecord.id_number, "0").in_(ids),
        )
    )).scalars().all()

    def pkey(v):
        v = (v or "").strip()
        return v.lstrip("0") or v

    prod_by = {}
    for r in prod_rows:
        k = pkey(r.fund_policy_number)
        if k:
            prod_by.setdefault(((r.id_number or "").lstrip("0"), k), r)

    matched = 0
    for h in holdings_rows:
        r = prod_by.get(((h.customer_id_number or "").lstrip("0"), pkey(h.fund_policy_number)))
        if r is not None:
            h.matched_client_record_id = r.id
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
        # Production reports keep their own clock. A monthly subscription (2100)
        # never expires; a one-off (2000) is due by the 15th of the next month,
        # so a flat 7-day timeout would expire it two weeks before its answer.
        code = (inq.interface_code or "").rpartition(":")[2]
        if code == "2100":
            continue
        if code == "2000":
            due, _ = expected_answer_by(inq)
            if due is not None and now < due.replace(tzinfo=None) + timedelta(days=7):
                continue
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

    # The name comes from a CUSTOMER request (9100/9101) or the agent's own
    # records — never from a production request, whose name field is the insurer.
    name = (last_inquiry.customer_name
            if last_inquiry and (last_inquiry.interface_code or "").endswith((":9100", ":9101"))
            else None)
    if not name:
        rec = (await db.execute(
            select(ClientRecord.first_name, ClientRecord.last_name).where(
                ClientRecord.user_id == user_id,
                func.ltrim(ClientRecord.id_number, "0") == normalized,
            ).limit(1)
        )).first()
        if rec:
            name = " ".join(x for x in (rec[0], rec[1]) if x) or None
    as_of = max((h.created_at for h in holdings if getattr(h, "created_at", None)), default=None)

    return {
        "customer_name": name,
        "as_of": as_of.isoformat() if as_of else None,
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


async def _find_inquiry_by_outbound_filename(
    db: AsyncSession,
    filename: str,
    *,
    scope_user_id: uuid.UUID | None,
) -> PensionInquiry | None:
    """Match a feedback file back to the request it answers, by the filename the
    מסלקה echoes in `SHEM-HAKOVETZ`. `vault_outbound_filename` is what we
    recorded when the worker transported it, so the two are the same string."""
    if not filename:
        return None
    q = select(PensionInquiry).where(PensionInquiry.vault_outbound_filename == filename.strip())
    if scope_user_id is not None:
        q = q.where(PensionInquiry.user_id == scope_user_id)
    return (await db.execute(q)).scalars().first()


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
