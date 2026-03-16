import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
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

    # Keep only latest previous upload with same filename (for monthly comparison)
    # Delete older duplicates but keep one for history
    old_uploads_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.filename == file.filename,
            FileUpload.file_category == file_category,
        ).order_by(desc(FileUpload.uploaded_at))
    )
    old_uploads = old_uploads_result.scalars().all()
    # Keep the first (latest) old upload, delete the rest
    for old in old_uploads[1:]:
        await db.delete(old)
    if old_uploads:
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
