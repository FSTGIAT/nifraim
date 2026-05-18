import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.schemas.upload import UploadOut
from app.api.deps import get_paid_user as get_current_user
from app.services.reconciliation_service import cross_reference_uploads
from app.services.upload_ingest import ingest_file_bytes, schedule_post_ingest

router = APIRouter()


def _has_file(u: FileUpload) -> bool:
    return bool(u.file_path) and os.path.exists(u.file_path)


_MIME_BY_EXT = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "pdf": "application/pdf",
    "csv": "text/csv",
}


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
        upload, _fmt = await ingest_file_bytes(
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

    # Fire downstream hooks. Production → snapshot + summary; commission →
    # auto-comparison against the active production. Manual commission uploads
    # used to skip this — agents had to navigate to the Comparison tab to see
    # results; this brings parity with the portal-automation runner.
    schedule_post_ingest(user.id, upload.id, upload.file_category)

    return UploadOut(
        id=str(upload.id),
        filename=upload.filename,
        file_type=upload.file_type,
        company_source=upload.company_source,
        record_count=upload.record_count,
        format_type=upload.format_type,
        file_category=upload.file_category,
        has_file=_has_file(upload),
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
            has_file=_has_file(u),
            uploaded_at=u.uploaded_at,
        )
        for u in uploads
    ]


@router.get("/{upload_id}/file")
async def download_upload_file(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stream the original uploaded/downloaded file back to the user.

    404 if the upload row is missing OR the on-disk file is gone (e.g. an
    older upload from before file_path was tracked, or a wiped volume).
    """
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.id == uuid.UUID(upload_id),
            FileUpload.user_id == user.id,
        )
    )
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if not upload.file_path or not os.path.exists(upload.file_path):
        raise HTTPException(status_code=404, detail="הקובץ המקורי לא זמין")
    media_type = _MIME_BY_EXT.get((upload.file_type or "").lower(), "application/octet-stream")
    return FileResponse(upload.file_path, media_type=media_type, filename=upload.filename)


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
