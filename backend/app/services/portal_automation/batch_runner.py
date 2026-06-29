"""Orchestrates a "run all portals" batch.

Runs every active credential SEQUENTIALLY (concurrent OTP would race on the
shared inbox), holding each downloaded production/commission file non-active.
After every site has run, aggregates:

  • all production records → ONE merged production xlsx (active production file)
  • all נפרעים records     → ONE merged commission xlsx (single commission file)

then runs the per-category comparison (גמל + ביטוח) against the merged
production and fires the production snapshot/summary hooks. Partial failures
(one portal down) don't abort the batch.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import Counter
from datetime import datetime, date

from sqlalchemy import select, update

from app.database import async_session
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.portal_run_batch import PortalRunBatch

logger = logging.getLogger(__name__)

# Reuse the single-run hard timeout per credential.
from app.services.portal_automation.runner import (
    _run_inner,
    _set_status,
    RUN_HARD_TIMEOUT_S,
    OtpTimeout,
)

_HE_MONTHS = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל", 5: "מאי", 6: "יוני",
    7: "יולי", 8: "אוגוסט", 9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
}


def _month_label(period: date | None) -> str:
    if not period:
        return ""
    return f"{_HE_MONTHS.get(period.month, '')} {period.year % 100:02d}".strip()


def _record_to_dict(r) -> dict:
    return {
        c.key: getattr(r, c.key)
        for c in r.__table__.columns
        if c.key not in ("id", "user_id", "upload_id")
    }


def _jsonable(obj):
    """Coerce a comparison-result tree into JSON-safe primitives. asyncpg's
    JSONB encoder can't serialise Decimal/date/UUID (DB columns are Numeric →
    Decimal), so walk the tree once. Mirrors comparison.py's helper."""
    from decimal import Decimal
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return obj


async def _delete_uploads(db, upload_ids: list[uuid.UUID]) -> None:
    """Delete held per-company uploads after their data has been folded into a
    merged file. Cascade removes their ClientRecord rows; NULL any
    portal_runs.upload_id first (that FK has no ON DELETE rule)."""
    if not upload_ids:
        return
    from sqlalchemy import update as sql_update, delete as sql_delete
    from app.models.upload import FileUpload
    await db.execute(
        sql_update(PortalRun).where(PortalRun.upload_id.in_(upload_ids)).values(upload_id=None)
    )
    # ORM delete per row so the records cascade fires.
    rows = (await db.execute(select(FileUpload).where(FileUpload.id.in_(upload_ids)))).scalars().all()
    for u in rows:
        await db.delete(u)
    await db.flush()


async def _run_worker_only_portal(db, run, cred):
    """Dispatch a non-Playwright portal (phoenix_terminal) to its native Windows
    orchestrator subprocess. Returns (success, upload_id). Failure-tolerant — a
    crash here marks only this child failed; the rest of the batch continues."""
    import subprocess, sys, os
    from pathlib import Path
    from app.services.portal_automation.companies import WORKER_ONLY_PORTALS
    rel = WORKER_ONLY_PORTALS.get(cred.portal_kind)
    script = Path(__file__).resolve().parents[3] / rel if rel else None
    if not script or not script.exists():
        await _set_status(db, run, status="failed", error="orchestrator not found", finished=True)
        return False, None
    env = {**os.environ, "PHOENIX_MBT_WAIT_S": os.environ.get("PHOENIX_MBT_WAIT_S", "150")}
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, lambda: subprocess.run(
            [sys.executable, str(script), str(run.id)], timeout=330, env=env))
    except Exception as e:
        logger.exception("worker-only portal %s failed", cred.portal_kind)
        await _set_status(db, run, status="failed", error=str(e)[:300], finished=True)
        return False, None
    await db.refresh(run)
    return (run.status == "success", run.upload_id)


async def run_batch(batch_id: uuid.UUID) -> None:
    """Top-level entry point. Owns its own DB session and never raises."""
    async with async_session() as db:
        batch_q = await db.execute(select(PortalRunBatch).where(PortalRunBatch.id == batch_id))
        batch = batch_q.scalar_one_or_none()
        if batch is None:
            logger.error("PortalRunBatch %s not found", batch_id)
            return

        try:
            await _run_batch_inner(db, batch)
        except Exception as e:
            logger.exception("Batch %s failed", batch_id)
            batch.status = "failed"
            batch.error_message = str(e)[:500]
            batch.finished_at = datetime.utcnow()
            await db.commit()


async def _run_batch_inner(db, batch: PortalRunBatch) -> None:
    from app.models.upload import FileUpload
    from app.models.record import ClientRecord

    user_id = batch.user_id

    from app.services.portal_automation.companies import REGISTRY, WORKER_ONLY_PORTALS

    creds_q = await db.execute(
        select(PortalCredential)
        .where(PortalCredential.user_id == user_id, PortalCredential.is_active.is_(True))
        .order_by(PortalCredential.portal_kind)
    )
    all_creds = list(creds_q.scalars().all())

    # Only run credentials whose portal is (a) implemented (registered) and
    # (b) batch-eligible. Skips junk creds (unknown portal_kind, e.g. a leftover
    # "test_production") and dead-end / folded portals (phoenix terminal,
    # phoenix_nifraim_gemel) so the batch doesn't burn an OTP on a guaranteed
    # failure. Single manual runs are unaffected.
    creds: list[PortalCredential] = []
    skipped: list[str] = []
    for c in all_creds:
        if c.portal_kind in WORKER_ONLY_PORTALS:
            # WORKER_ONLY portals (phoenix_terminal) drive a native Windows
            # green-screen via SendInput and need an ELEVATED worker. In a normal
            # batch they reliably fail ("login script exit 1"), so skip them here
            # to honour the "don't burn a slot on a guaranteed failure" intent
            # above — they remain available as explicit single manual runs.
            skipped.append(c.portal_kind)
            continue
        plugin_cls = REGISTRY.get(c.portal_kind)
        if plugin_cls is None or not getattr(plugin_cls, "include_in_batch", True):
            skipped.append(c.portal_kind)
        else:
            creds.append(c)
    if skipped:
        logger.info("Batch %s: skipping non-batch portals: %s", batch.id, skipped)

    batch.total = len(creds)
    batch.status = "running"
    await db.commit()

    prod_upload_ids: list[uuid.UUID] = []
    comm_upload_ids: list[uuid.UUID] = []
    prod_periods: list[date] = []

    # ── 1. Run every credential sequentially ─────────────────────────────
    for cred in creds:
        run = PortalRun(
            user_id=user_id,
            credential_id=cred.id,
            status="pending",
            started_at=datetime.utcnow(),
            batch_id=batch.id,
        )
        db.add(run)
        await db.flush()
        batch.current_run_id = run.id
        await db.commit()

        if cred.portal_kind in WORKER_ONLY_PORTALS:
            ok, up = await _run_worker_only_portal(db, run, cred)
            if ok and up:
                prod_upload_ids.append(up)
                batch.succeeded += 1
                cred.last_run_status = "success"; cred.last_error = None
            else:
                batch.failed += 1
                cred.last_run_status = "failed"
            cred.last_run_at = datetime.utcnow()
            await db.commit()
            continue

        try:
            ingested = await asyncio.wait_for(
                _run_inner(db, run, make_active=False, defer_post_ingest=True),
                timeout=RUN_HARD_TIMEOUT_S,
            )
            cred.last_run_status = "success"
            cred.last_error = None
            batch.succeeded += 1
            for upload_id, file_category, _company in (ingested or []):
                if file_category == "production":
                    prod_upload_ids.append(upload_id)
                elif file_category == "commission":
                    comm_upload_ids.append(upload_id)
        except OtpTimeout as e:
            await _set_status(db, run, status="failed", error=str(e), finished=True)
            cred.last_run_status = "failed"
            cred.last_error = str(e)
            batch.failed += 1
        except asyncio.TimeoutError:
            await _set_status(db, run, status="timeout",
                              error=f"Run exceeded {RUN_HARD_TIMEOUT_S}s", finished=True)
            cred.last_run_status = "timeout"
            cred.last_error = f"Run exceeded {RUN_HARD_TIMEOUT_S}s"
            batch.failed += 1
        except Exception as e:
            logger.exception("Batch child run %s failed", run.id)
            # _run_inner may have left the run un-finalized; mark it failed.
            await _set_status(db, run, status="failed", error=str(e), finished=True)
            cred.last_run_status = "failed"
            cred.last_error = str(e)
            batch.failed += 1
        finally:
            cred.last_run_at = datetime.utcnow()
            await db.commit()

    batch.current_run_id = None
    await db.commit()

    # Resolve held upload period months (for naming + batch.period_month).
    if prod_upload_ids:
        periods_q = await db.execute(
            select(FileUpload.period_month).where(FileUpload.id.in_(prod_upload_ids))
        )
        prod_periods = [p for (p,) in periods_q.all() if p]
    batch_period = Counter(prod_periods).most_common(1)[0][0] if prod_periods else None
    batch.period_month = batch_period
    month_label = _month_label(batch_period)

    # ── 2. Merge production → ONE active upload ───────────────────────────
    merged_prod_upload = None
    if prod_upload_ids:
        from app.services.portal_automation.aggregate import build_unified_workbook_bytes
        from app.services.upload_ingest import ingest_file_bytes

        prod_recs_q = await db.execute(
            select(ClientRecord).where(ClientRecord.upload_id.in_(prod_upload_ids))
        )
        prod_records = [_record_to_dict(r) for r in prod_recs_q.scalars().all()]
        if prod_records:
            xlsx_bytes = build_unified_workbook_bytes(prod_records)
            fname = f"פרודוקציה מאוחד {month_label}.xlsx".replace("  ", " ").strip()
            merged_prod_upload, _ = await ingest_file_bytes(
                db, user_id=user_id, content=xlsx_bytes, filename=fname,
                commit=False, make_active=True, company_source_override="מאוחד",
            )
            batch.merged_upload_id = merged_prod_upload.id
            # The merged "מאוחד" file supersedes every other active production
            # (a prior single-run active from before the batch must go inactive).
            await db.execute(
                update(FileUpload)
                .where(
                    FileUpload.user_id == user_id,
                    FileUpload.is_production.is_(True),
                    FileUpload.id != merged_prod_upload.id,
                )
                .values(is_production=False)
            )
            # Held per-company production data now lives in the merged file —
            # delete the held uploads so stray records can't be miscounted by
            # the generic comparison path (which treats every non-active-
            # production record as commission).
            await _delete_uploads(db, prod_upload_ids)
            await db.commit()

            # Invariant: exactly one active production upload remains.
            active_q = await db.execute(
                select(FileUpload.id).where(
                    FileUpload.user_id == user_id,
                    FileUpload.is_production.is_(True),
                )
            )
            active_ids = [i for (i,) in active_q.all()]
            if active_ids != [merged_prod_upload.id]:
                logger.error(
                    "Batch %s: expected 1 active production (%s), found %s",
                    batch.id, merged_prod_upload.id, active_ids,
                )

    # ── 3. Merge נפרעים → ONE commission upload ───────────────────────────
    merged_comm_upload = None
    if comm_upload_ids:
        from app.services.portal_automation.aggregate import build_unified_nifraim_bytes
        from app.services.upload_ingest import ingest_file_bytes

        comm_recs_q = await db.execute(
            select(ClientRecord).where(ClientRecord.upload_id.in_(comm_upload_ids))
        )
        comm_records = [_record_to_dict(r) for r in comm_recs_q.scalars().all()]
        if comm_records:
            nif_bytes = build_unified_nifraim_bytes(comm_records, period_label=month_label)
            fname = f"נפרעים מאוחד {month_label}.xlsx".replace("  ", " ").strip()
            merged_comm_upload, _ = await ingest_file_bytes(
                db, user_id=user_id, content=nif_bytes, filename=fname,
                commit=False, make_active=True, company_source_override="מאוחד",
            )
            batch.merged_commission_upload_id = merged_comm_upload.id
            # Delete the held per-company commission uploads so the merged file
            # is the single canonical commission source (no double-count, no
            # stray per-company rows in the comparison company list).
            held_comm = [cid for cid in comm_upload_ids if cid != merged_comm_upload.id]
            await _delete_uploads(db, held_comm)
            await db.commit()

    # ── 4. Per-category comparison (גמל + ביטוח) ──────────────────────────
    if merged_comm_upload is not None:
        await _compare_merged(db, user_id, merged_comm_upload.id)

    # ── 5. Production snapshot/summary hooks ──────────────────────────────
    if merged_prod_upload is not None:
        from app.services.upload_ingest import schedule_post_ingest
        try:
            schedule_post_ingest(user_id, merged_prod_upload.id, "production")
        except Exception as e:
            logger.warning("Batch %s: production post-ingest failed: %s", batch.id, e)

    # ── 6. Finalize status ────────────────────────────────────────────────
    if batch.failed == 0:
        batch.status = "success"
    elif batch.succeeded == 0:
        batch.status = "failed"
    else:
        batch.status = "partial"
    batch.finished_at = datetime.utcnow()
    await db.commit()


async def _compare_merged(db, user_id: uuid.UUID, merged_comm_upload_id: uuid.UUID) -> None:
    """Run the comparison once per category against the active production and
    persist a CommissionComparison row per category (so both tabs populate)."""
    from app.models.upload import FileUpload
    from app.models.record import ClientRecord
    from app.models.paying_company import PayingCompany
    from app.models.commission_comparison import CommissionComparison
    from app.services.comparison_service import compute_comparison
    from app.services.portal_automation.aggregate import (
        commission_category_token,
        NIFRAIM_CATEGORY_GEMEL,
    )

    prod_q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production.is_(True),
        )
    )
    prod_upload = prod_q.scalar_one_or_none()
    if not prod_upload:
        return

    prod_recs_q = await db.execute(
        select(ClientRecord).where(ClientRecord.upload_id == prod_upload.id)
    )
    prod_dicts = [_record_to_dict(r) for r in prod_recs_q.scalars().all()]
    if not prod_dicts:
        return

    comm_recs_q = await db.execute(
        select(ClientRecord).where(ClientRecord.upload_id == merged_comm_upload_id)
    )
    comm_dicts = [_record_to_dict(r) for r in comm_recs_q.scalars().all()]
    if not comm_dicts:
        return

    paying_q = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user_id)
    )
    paying_names = [p.company_name for p in paying_q.scalars().all()]

    # Split commission records by category token; pass only the matching
    # category's records to each comparison so cross-category rows don't leak.
    by_cat = {"gemel_hishtalmut": [], "insurance": []}
    for rec in comm_dicts:
        if commission_category_token(rec) == NIFRAIM_CATEGORY_GEMEL:
            by_cat["gemel_hishtalmut"].append(rec)
        else:
            by_cat["insurance"].append(rec)

    for category, recs in by_cat.items():
        if not recs:
            continue
        try:
            comparison = compute_comparison(
                prod_dicts, recs, paying_names, category_override=category
            )
            sources = sorted({
                r.get("receiving_company") for r in recs if r.get("receiving_company")
            })
            comparison["commission_company_sources"] = sources
            comparison["commission_company_source"] = sources[0] if len(sources) == 1 else None
            if prod_upload.period_month is not None:
                comparison["period_month"] = prod_upload.period_month.isoformat()

            row = CommissionComparison(
                user_id=user_id,
                category=category,
                production_upload_id=prod_upload.id,
                summary_json=_jsonable(comparison.get("summary") or {}),
                result_json=_jsonable(comparison),
                commission_company_sources=_jsonable(sources),
            )
            db.add(row)
            await db.commit()

            # Sync the debts table (drives the insights dashboard + the
            # company-summary "gap" column), mirroring compare_with_production.
            try:
                from app.services.debt_service import sync_debts
                await sync_debts(
                    db, user_id, comparison,
                    production_upload_id=prod_upload.id,
                    commission_upload_id=merged_comm_upload_id,
                    category=category,
                )
                await db.commit()
            except Exception as de:
                logger.warning("Batch debt sync (%s) failed: %s", category, de)
                await db.rollback()
        except Exception as e:
            logger.warning("Batch compare (%s) failed: %s", category, e)
            await db.rollback()
