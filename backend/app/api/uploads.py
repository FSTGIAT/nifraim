import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.schemas.upload import UploadOut
from app.api.deps import get_paid_user as get_current_user
from app.services.reconciliation_service import cross_reference_uploads
from app.services.upload_ingest import ingest_file_bytes

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

    content = await file.read()

    try:
        upload = await ingest_file_bytes(
            db,
            user_id=user.id,
            content=content,
            filename=file.filename,
            password=password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

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
