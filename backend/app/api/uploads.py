import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, desc, or_, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.debt import Debt
from app.models.production_summary import ProductionSummary
from app.models.portal_snapshot import PortalSnapshot
from app.schemas.upload import UploadOut
from app.api.deps import get_paid_user as get_current_user
from app.services.parser_service import parse_excel
from app.services.reconciliation_service import apply_commission_rates, cross_reference_uploads
from app.utils.sanitize import sanitize_record

router = APIRouter()


@router.post("", response_model=UploadOut)
async def upload_file(
    file: UploadFile = File(...),
    password: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls"):
        raise HTTPException(status_code=400, detail="Only xlsx/xls files supported")

    content = await file.read()

    try:
        result = parse_excel(content, file.filename, password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Determine file category from format type
    fmt = result["format"]
    if fmt == "production":
        file_category = "production"
    elif fmt in (
        "agent_tracking", "company_report", "nifraim",
        "hachshara_nifraim", "menora", "altshuler",
        "clal_life_nifraim", "clal_health_nifraim", "migdal_nifraim",
        "ayalon_nifraim", "harel_nifraim", "phoenix_insurance_nifraim",
    ):
        file_category = "commission"
    else:
        file_category = "general"

    # True replace-on-upload: delete every old upload with the same filename
    # for this user+category. Commission-period pairing works by company_source
    # (not filename), so no reason to keep an older copy of the same filename.
    #
    # Four tables reference file_uploads.id WITHOUT ON DELETE CASCADE — we must
    # clear them first or the delete raises a FK violation:
    #   - client_records.upload_id        (ORM cascade handles this)
    #   - debts.commission_upload_id      ← explicit
    #   - debts.production_upload_id      ← explicit
    #   - production_summaries.upload_id  ← explicit (unique constraint)
    #   - portal_snapshots.upload_id      ← explicit (snapshot becomes stale)
    #
    # Dependents are derived data that will be regenerated next time the
    # relevant query runs (debts on demand, summaries on production upload,
    # snapshots when the portal is viewed).
    old_uploads_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.filename == file.filename,
            FileUpload.file_category == file_category,
        )
    )
    old_uploads = old_uploads_result.scalars().all()
    if old_uploads:
        old_ids = [u.id for u in old_uploads]
        # Drop every dependent row referencing any of the old uploads
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
        # Now safe to delete the FileUpload rows (client_records cascade via ORM)
        for old in old_uploads:
            await db.delete(old)
        await db.flush()

    upload = FileUpload(
        user_id=user.id,
        filename=file.filename,
        file_type=ext,
        company_source=result["company_source"],
        record_count=len(result["records"]),
        format_type=result["format"],
        file_category=file_category,
    )
    db.add(upload)
    await db.flush()

    # Bulk insert records
    for rec_data in result["records"]:
        clean = sanitize_record(rec_data)
        record = ClientRecord(
            user_id=user.id,
            upload_id=upload.id,
            **{k: v for k, v in clean.items() if hasattr(ClientRecord, k)},
        )
        db.add(record)

    await db.flush()

    # Apply commission rates for company reports
    if result["format"] == "company_report":
        await apply_commission_rates(db, user.id, upload.id)

    # Cross-reference between agent tracking and company report
    await cross_reference_uploads(db, user.id)

    await db.commit()
    await db.refresh(upload)

    return UploadOut(
        id=str(upload.id),
        filename=upload.filename,
        file_type=upload.file_type,
        company_source=upload.company_source,
        record_count=upload.record_count,
        uploaded_at=upload.uploaded_at,
    )


@router.get("", response_model=list[UploadOut])
async def list_uploads(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileUpload)
        .where(FileUpload.user_id == user.id)
        .order_by(FileUpload.uploaded_at.desc())
    )
    uploads = result.scalars().all()
    return [
        UploadOut(
            id=str(u.id),
            filename=u.filename,
            file_type=u.file_type,
            company_source=u.company_source,
            record_count=u.record_count,
            format_type=u.format_type,
            file_category=u.file_category,
            uploaded_at=u.uploaded_at,
        )
        for u in uploads
    ]


@router.delete("/{upload_id}")
async def delete_upload(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.id == uuid.UUID(upload_id),
            FileUpload.user_id == user.id,
        )
    )
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    await db.delete(upload)
    await db.flush()

    # Recompute cross-reference statuses after removing records
    await cross_reference_uploads(db, user.id)

    await db.commit()
    return {"status": "deleted"}
