"""Shared parse + persist pipeline for Excel uploads.

Used by both the HTTP route (`POST /api/uploads`) and the portal automation
runner. Single source of truth for: detect format → call parse_excel → derive
file_category → replace-on-upload → bulk-insert ClientRecord rows → apply
commission rates → cross-reference uploads. Also keeps the original file on
disk under `/app/data/uploads/<user_id>/<upload_id>__<filename>` so the UI
can offer a download/preview affordance later.
"""

import asyncio
import logging
import os
import re
import uuid
from pathlib import Path

from sqlalchemy import select, or_, update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.debt import Debt
from app.models.production_summary import ProductionSummary
from app.models.portal_snapshot import PortalSnapshot
from app.services.parser_service import parse_excel
from app.services.reconciliation_service import (
    apply_commission_rates,
    apply_rate_deviation,
    cross_reference_uploads,
)
from app.utils.sanitize import sanitize_record


logger = logging.getLogger(__name__)

UPLOADS_ROOT = Path(os.environ.get("UPLOADS_STORAGE_DIR", "/app/data/uploads"))
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._\-֐-׿\(\) ]+")


def _sanitize_filename(name: str) -> str:
    cleaned = _FILENAME_SAFE.sub("_", (name or "").strip()) or "file"
    # Keep it short — the upload_id prefix already disambiguates
    return cleaned[:140]


def _save_upload_to_disk(user_id: uuid.UUID, upload_id: uuid.UUID, filename: str, content: bytes) -> str | None:
    """Write the raw file into the persistent uploads volume.

    Best-effort: returns the absolute path on success, None on failure (we
    log + continue — the parsed rows are the source of truth).
    """
    try:
        user_dir = UPLOADS_ROOT / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _sanitize_filename(filename)
        target = user_dir / f"{upload_id}__{safe_name}"
        target.write_bytes(content)
        return str(target)
    except OSError as e:
        logger.warning(f"Could not persist upload {upload_id}: {e}")
        return None


# Source-of-truth for format → category lives in parser_service. Importing it
# here keeps the two layers in sync (previous duplicate set in this file was
# missing `harel_savings_nifraim` — those uploads silently fell into "general"
# and never triggered the auto-comparison).
def _file_category_for_format(fmt: str) -> str:
    from app.services.parser_service import category_for_format
    cat = category_for_format(fmt)
    # The agent-facing buckets in this app are: production / commission /
    # recruits / general. Recruits + volume + unknown all surface as "general"
    # in FileUpload.file_category for now (the recruits UI uses its own model).
    if cat in ("production", "commission"):
        return cat
    return "general"


def _parse_zip_bundle(content: bytes, filename: str) -> dict:
    """Front-door for .zip uploads. Currently only the Migdal Mimshak format
    (DAT + MBT bundle) is recognised — produces production-format records.

    Returns a dict shaped like parser_service.parse_excel() output:
        { "format": str, "company_source": str, "records": list[dict] }

    For Mimshak: the parser builds a production-format xlsx in memory using
    the POC's xlsx_writer, then runs it through the existing parse_excel so
    full field decoding (status labels, summed coverage premiums, insurer
    normalisation, etc.) carries over from the manual-upload path.
    """
    from app.services.mimshak import is_mimshak_zip, parse_mimshak_zip
    from app.services.menora_legacy import (
        is_menora_legacy_zip,
        parse_menora_legacy_zip,
    )
    from app.services.menora_amalot import (
        is_menora_amalot_zip,
        parse_menora_amalot_zip,
    )

    if is_mimshak_zip(content):
        return parse_mimshak_zip(content)

    # Menora's כספות vault delivers production as an outer ZIP containing
    # inner files named `.ARJ` (actually ZIPs) holding CP1255 fixed-width
    # text (תקן 4-era). Different signature, same production-tab destination.
    if is_menora_legacy_zip(content):
        return parse_menora_legacy_zip(content)

    # The same vault delivers the נפרעים (commission) report as an outer ZIP
    # wrapping a single CP1255 CSV with the standard Menora commission columns.
    # Routes to format=menora → commission.
    if is_menora_amalot_zip(content):
        return parse_menora_amalot_zip(content)

    raise ValueError(
        "Unsupported ZIP bundle. Expected a Migdal Mimshak bundle "
        "(DAT + MBT files), a Menora legacy bundle (inner .ARJ ZIPs "
        "with P.TXT/G.TXT), or a Menora amalot/נפרעים CSV ZIP. "
        "Filename: " + filename
    )


async def ingest_file_bytes(
    db: AsyncSession,
    user_id: uuid.UUID,
    content: bytes,
    filename: str,
    password: str | None = None,
    commit: bool = True,
    make_active: bool = True,
    company_source_override: str | None = None,
) -> tuple[FileUpload, str]:
    """Parse the bytes (xlsx/xls/zip) and persist to the database.

    Returns (FileUpload, fmt). Callers pass `fmt` to `schedule_post_ingest()`
    to trigger the right downstream hooks (snapshot/summary for production,
    auto-compare for commission). `commit=False` lets the caller compose the
    ingest into a larger transaction.

    `make_active=False` holds a production upload WITHOUT flipping it to the
    active production file (or deactivating same-company actives). The "run all
    portals" batch uses this to ingest each per-company file, then aggregate
    them into ONE merged production upload that becomes the single active file.
    `company_source_override` forces FileUpload.company_source (e.g. "מאוחד"
    for the merged files), independent of what the parser detected.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Magic-byte override: portal automation plugins occasionally save a real
    # ZIP (e.g. Migdal Mimshak bundle from the Safes vault) under a misleading
    # `.xlsx` filename. Sniff the first 4 bytes — if it's a ZIP that the
    # Mimshak parser recognises, route to the ZIP path regardless of extension.
    if content[:4] == b"PK\x03\x04" and ext != "zip":
        from app.services.mimshak import is_mimshak_zip
        from app.services.menora_legacy import is_menora_legacy_zip
        from app.services.menora_amalot import is_menora_amalot_zip
        if (
            is_mimshak_zip(content)
            or is_menora_legacy_zip(content)
            or is_menora_amalot_zip(content)
        ):
            ext = "zip"

    # Same idea for a bare Mimshak holdings .DAT (Phoenix SFE כספת serves the
    # standardised XML envelope as a lone .DAT, sometimes under another name).
    # Sniff the head for the `<Mimshak>` root and route to the DAT path.
    if ext != "dat" and content[:6] in (b"<?xml ", b"<Mimsh"):
        from app.services.mimshak import is_mimshak_dat
        if is_mimshak_dat(content):
            ext = "dat"

    if ext == "zip":
        result = _parse_zip_bundle(content, filename)
    elif ext == "dat":
        from app.services.mimshak import parse_mimshak_dat
        result = parse_mimshak_dat(content, filename)
    elif ext in ("xlsx", "xls"):
        result = parse_excel(content, filename, password)
    else:
        raise ValueError(f"Unsupported file extension '{ext}' (expected xlsx/xls/zip/dat)")
    fmt = result["format"]
    file_category = _file_category_for_format(fmt)

    # Replace-on-upload: same user + filename + category → wipe prior rows so
    # comparisons always operate on the freshest data. Dependents (debts,
    # summaries, snapshots) reference file_uploads without ON DELETE CASCADE,
    # so we clear them explicitly first.
    old_uploads_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.filename == filename,
            FileUpload.file_category == file_category,
        )
    )
    old_uploads = old_uploads_result.scalars().all()
    if old_uploads:
        old_ids = [u.id for u in old_uploads]
        await db.execute(sql_delete(Debt).where(
            or_(
                Debt.commission_upload_id.in_(old_ids),
                Debt.production_upload_id.in_(old_ids),
            )
        ))
        await db.execute(sql_delete(ProductionSummary).where(
            ProductionSummary.upload_id.in_(old_ids)
        ))
        await db.execute(sql_delete(PortalSnapshot).where(
            PortalSnapshot.upload_id.in_(old_ids)
        ))
        # portal_runs.upload_id references file_uploads.id but the FK has
        # no ON DELETE rule — when the same filename is re-ingested by a
        # later run, the prior run's upload_id still points at the old row
        # and blocks the DELETE. NULL it out so the new ingest can proceed.
        # (The prior run's success log + downloaded_filename are preserved.)
        from app.models.portal_run import PortalRun
        from sqlalchemy import update as sql_update
        await db.execute(
            sql_update(PortalRun)
            .where(PortalRun.upload_id.in_(old_ids))
            .values(upload_id=None)
        )
        for old in old_uploads:
            await db.delete(old)
        await db.flush()

    from app.services.parser_service import detect_period_month
    from datetime import datetime as _dt
    # A parser may supply an authoritative period_month (e.g. Menora amalot CSV
    # reads "לתקופה : MM/YYYY" from the title); prefer it over filename/data-date
    # inference, which the embedded generation timestamp would otherwise fool.
    period = result.get("period_month") or detect_period_month(
        filename, result.get("records"), uploaded_at=_dt.utcnow()
    )

    upload = FileUpload(
        user_id=user_id,
        filename=filename,
        file_type=ext,
        company_source=company_source_override or result["company_source"],
        record_count=len(result["records"]),
        format_type=fmt,
        file_category=file_category,
        period_month=period,
    )
    db.add(upload)
    await db.flush()

    # Preserve the original bytes on disk so the UI can offer download/preview.
    # Best-effort — never blocks the ingest.
    saved_path = _save_upload_to_disk(user_id, upload.id, filename, content)
    if saved_path:
        upload.file_path = saved_path

    for rec_data in result["records"]:
        clean = sanitize_record(rec_data)
        record = ClientRecord(
            user_id=user_id,
            upload_id=upload.id,
            **{k: v for k, v in clean.items() if hasattr(ClientRecord, k)},
        )
        db.add(record)
    await db.flush()

    if fmt == "company_report":
        await apply_commission_rates(db, user_id, upload.id)

    # Percent-vs-percent deviation: works whenever the parser populates
    # reported_commission_pct (currently Menora; trivially extends as we
    # add the same "אחוז עמלה" mapping to other נפרעים parsers).
    await apply_rate_deviation(db, user_id, upload.id)

    await cross_reference_uploads(db, user_id)

    # Production uploads replace the prior active production FROM THE SAME
    # COMPANY only. Uploads from different companies (Migdal + Menora + ...)
    # for the same period all stay active simultaneously — together they
    # form the unified monthly production view. Within a single company the
    # latest upload still replaces prior ones.
    # make_active=False holds the upload non-active (batch path): the per-company
    # production files are aggregated into one merged upload that becomes active
    # at batch end, so flipping is_production here would double-count.
    if fmt == "production" and make_active:
        company = company_source_override or result.get("company_source")
        deactivate_q = update(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production.is_(True),
            FileUpload.id != upload.id,
        )
        if company:
            deactivate_q = deactivate_q.where(FileUpload.company_source == company)
        await db.execute(deactivate_q.values(is_production=False))
        upload.is_production = True

    if commit:
        await db.commit()
        await db.refresh(upload)

    return upload, fmt


# ── Post-ingest dispatcher ───────────────────────────────────────────────
# Shared by both the manual upload route and the portal-automation runner so
# every newly-ingested file gets the same downstream chain regardless of how
# it arrived.

async def _create_snapshots_bg(user_id: uuid.UUID, upload_id: uuid.UUID) -> None:
    from app.database import async_session
    from app.services.portal_service import create_snapshots_for_upload
    try:
        async with async_session() as db:
            await create_snapshots_for_upload(db, user_id, upload_id)
    except Exception as e:
        logger.warning("snapshot bg task failed (upload %s): %s", upload_id, e)


async def _compute_summary_bg(user_id: uuid.UUID, upload_id: uuid.UUID) -> None:
    from app.database import async_session
    from app.services.summary_service import compute_production_summary
    try:
        async with async_session() as db:
            await compute_production_summary(db, user_id, upload_id)
    except Exception as e:
        logger.warning("summary bg task failed (upload %s): %s", upload_id, e)


async def _auto_compare_after_commission_bg(user_id: uuid.UUID, commission_upload_id: uuid.UUID) -> None:
    """Best-effort comparison after a commission file lands. Mirrors what
    /api/comparison/compare-with-production does, but DB→memory only (no
    re-parse). Failure is logged + swallowed; the upload itself is fine."""
    from app.database import async_session
    from app.models.paying_company import PayingCompany
    from app.models.commission_comparison import CommissionComparison
    from app.services.comparison_service import compute_comparison

    try:
        async with async_session() as db:
            prod_q = await db.execute(
                select(FileUpload).where(
                    FileUpload.user_id == user_id,
                    FileUpload.is_production.is_(True),
                )
            )
            prod_upload = prod_q.scalar_one_or_none()
            if not prod_upload:
                return

            new_comm_q = await db.execute(
                select(FileUpload).where(FileUpload.id == commission_upload_id)
            )
            new_comm = new_comm_q.scalar_one_or_none()
            if not new_comm:
                return

            new_recs_q = await db.execute(
                select(ClientRecord).where(
                    ClientRecord.upload_id == new_comm.id,
                    ClientRecord.user_id == user_id,
                )
            )
            new_records = list(new_recs_q.scalars().all())
            if not new_records:
                return

            def _to_dict(r):
                return {
                    c.key: getattr(r, c.key)
                    for c in r.__table__.columns
                    if c.key not in ("id", "user_id", "upload_id")
                }

            new_dicts = [_to_dict(r) for r in new_records]

            all_comm_q = await db.execute(
                select(ClientRecord).where(
                    ClientRecord.user_id == user_id,
                    ClientRecord.upload_id != prod_upload.id,
                )
            )
            all_comm_records = [_to_dict(r) for r in all_comm_q.scalars().all()]
            if not all_comm_records:
                all_comm_records = new_dicts

            prod_q2 = await db.execute(
                select(ClientRecord).where(
                    ClientRecord.upload_id == prod_upload.id,
                    ClientRecord.user_id == user_id,
                )
            )
            prod_dicts = [_to_dict(r) for r in prod_q2.scalars().all()]
            if not prod_dicts:
                return

            paying_q = await db.execute(
                select(PayingCompany).where(PayingCompany.user_id == user_id)
            )
            paying_names = [p.company_name for p in paying_q.scalars().all()]

            comparison = compute_comparison(prod_dicts, all_comm_records, paying_names)

            comm_uploads_q = await db.execute(
                select(FileUpload).where(
                    FileUpload.user_id == user_id,
                    FileUpload.file_category == "commission",
                )
            )
            sources = sorted({
                u.company_source for u in comm_uploads_q.scalars().all() if u.company_source
            })
            comparison["commission_company_sources"] = sources
            comparison["commission_company_source"] = new_comm.company_source

            row = CommissionComparison(
                user_id=user_id,
                category=comparison.get("commission_category") or "unknown",
                production_upload_id=prod_upload.id,
                summary_json=comparison.get("summary") or {},
                result_json=comparison,
                commission_company_sources=sources,
            )
            db.add(row)
            await db.commit()
    except Exception as e:
        logger.warning("auto-compare bg task failed (upload %s): %s", commission_upload_id, e)


def schedule_post_ingest(
    user_id: uuid.UUID,
    upload_id: uuid.UUID,
    file_category: str,
) -> None:
    """Fire-and-forget downstream tasks based on file_category.

    Always async-task based (not BackgroundTasks) so it works identically from
    the manual upload route AND from the portal-automation runner (which has
    no request-scoped BackgroundTasks instance). The tasks each open their own
    DB session.
    """
    if file_category == "production":
        asyncio.create_task(_create_snapshots_bg(user_id, upload_id))
        asyncio.create_task(_compute_summary_bg(user_id, upload_id))
    elif file_category == "commission":
        asyncio.create_task(_auto_compare_after_commission_bg(user_id, upload_id))
