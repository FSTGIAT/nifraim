import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.schemas.upload import ProductionFileInfo
from app.api.deps import get_current_user
from app.services.parser_service import parse_excel
from app.utils.sanitize import sanitize_record

router = APIRouter()


async def _get_production_upload(db: AsyncSession, user_id: uuid.UUID) -> FileUpload | None:
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,
        )
    )
    return result.scalar_one_or_none()


async def _get_companies_for_upload(db: AsyncSession, upload_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(ClientRecord.receiving_company)
        .where(
            ClientRecord.upload_id == upload_id,
            ClientRecord.receiving_company.isnot(None),
        )
        .distinct()
    )
    companies = [r[0] for r in result.all() if r[0] and r[0] not in ("nan", "None")]
    return sorted(companies)


@router.post("/upload", response_model=ProductionFileInfo)
async def upload_production(
    file: UploadFile = File(...),
    password: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload & persist production file, replacing previous."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="לא סופק קובץ")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls"):
        raise HTTPException(status_code=400, detail="רק קבצי xlsx/xls נתמכים")

    content = await file.read()

    try:
        result = parse_excel(content, file.filename, password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בפענוח הקובץ: {str(e)}")

    # Deactivate previous production file
    old_prod = await _get_production_upload(db, user.id)
    if old_prod:
        old_prod.is_production = False
        old_prod.file_category = "general"

    # Create new production upload
    upload = FileUpload(
        user_id=user.id,
        filename=file.filename,
        file_type=ext,
        company_source=result["company_source"],
        record_count=len(result["records"]),
        format_type=result["format"],
        is_production=True,
        file_category="production",
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

    await db.commit()
    await db.refresh(upload)

    companies = await _get_companies_for_upload(db, upload.id)

    return ProductionFileInfo(
        id=str(upload.id),
        filename=upload.filename,
        file_type=upload.file_type,
        company_source=upload.company_source,
        record_count=upload.record_count,
        uploaded_at=upload.uploaded_at,
        companies=companies,
    )


@router.get("/current", response_model=ProductionFileInfo | None)
async def get_current_production(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current production file info."""
    upload = await _get_production_upload(db, user.id)
    if not upload:
        return None

    companies = await _get_companies_for_upload(db, upload.id)

    return ProductionFileInfo(
        id=str(upload.id),
        filename=upload.filename,
        file_type=upload.file_type,
        company_source=upload.company_source,
        record_count=upload.record_count,
        uploaded_at=upload.uploaded_at,
        companies=companies,
    )


@router.delete("/current")
async def delete_current_production(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove current production file."""
    upload = await _get_production_upload(db, user.id)
    if not upload:
        raise HTTPException(status_code=404, detail="לא נמצא קובץ פרודוקציה פעיל")

    await db.delete(upload)
    await db.commit()
    return {"status": "deleted"}
