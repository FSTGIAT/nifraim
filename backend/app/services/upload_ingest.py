"""Shared parse + persist pipeline for Excel uploads.

Used by both the HTTP route (`POST /api/uploads`) and the portal automation
runner. Single source of truth for: detect format → call parse_excel → derive
file_category → replace-on-upload → bulk-insert ClientRecord rows → apply
commission rates → cross-reference uploads.
"""

import uuid

from sqlalchemy import select, or_, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.debt import Debt
from app.models.production_summary import ProductionSummary
from app.models.portal_snapshot import PortalSnapshot
from app.services.parser_service import parse_excel
from app.services.reconciliation_service import apply_commission_rates, cross_reference_uploads
from app.utils.sanitize import sanitize_record


_COMMISSION_FORMATS = {
    "agent_tracking", "company_report", "nifraim",
    "hachshara_nifraim", "menora", "altshuler",
    "clal_life_nifraim", "clal_health_nifraim", "migdal_nifraim",
    "ayalon_nifraim", "harel_nifraim", "phoenix_insurance_nifraim",
}


def _file_category_for_format(fmt: str) -> str:
    if fmt == "production":
        return "production"
    if fmt in _COMMISSION_FORMATS:
        return "commission"
    return "general"


async def ingest_file_bytes(
    db: AsyncSession,
    user_id: uuid.UUID,
    content: bytes,
    filename: str,
    password: str | None = None,
    commit: bool = True,
) -> FileUpload:
    """Parse the Excel bytes and persist to the database.

    Returns the inserted FileUpload row. Caller may set commit=False to compose
    the ingest into a larger transaction (the runner does this so the FileUpload
    insert and the PortalRun.upload_id update commit atomically).
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("xlsx", "xls"):
        raise ValueError(f"Only xlsx/xls files supported (got '{ext}')")

    result = parse_excel(content, filename, password)
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
        for old in old_uploads:
            await db.delete(old)
        await db.flush()

    upload = FileUpload(
        user_id=user_id,
        filename=filename,
        file_type=ext,
        company_source=result["company_source"],
        record_count=len(result["records"]),
        format_type=fmt,
        file_category=file_category,
    )
    db.add(upload)
    await db.flush()

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

    await cross_reference_uploads(db, user_id)

    if commit:
        await db.commit()
        await db.refresh(upload)

    return upload
