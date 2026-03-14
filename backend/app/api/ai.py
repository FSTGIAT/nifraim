from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.recruit import Recruit
from app.api.deps import get_paid_user
from app.schemas.ai import ChatRequest
from app.services.ai_service import stream_chat

router = APIRouter()


@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    return StreamingResponse(
        stream_chat(db, user.id, req.question, [m.model_dump() for m in req.history]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sources")
async def get_sources(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Return the data sources the AI has access to."""
    sources = []

    # Production file
    prod = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == True,
        )
    )
    prod_upload = prod.scalar_one_or_none()
    if prod_upload:
        sources.append({"type": "production", "label": "פרודוקציה", "filename": prod_upload.filename})

    # Commission files (deduplicated by filename)
    comm_q = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "commission",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    seen = set()
    for u in comm_q.scalars().all():
        if u.filename not in seen:
            seen.add(u.filename)
            label = u.company_source or u.filename
            sources.append({"type": "commission", "label": label, "filename": u.filename, "upload_id": str(u.id)})
        if len(seen) >= 5:
            break

    # My File (recruits)
    recruits_count = await db.execute(
        select(Recruit.id).where(Recruit.user_id == user.id).limit(1)
    )
    if recruits_count.scalar_one_or_none() is not None:
        sources.append({"type": "myfile", "label": "קובץ אישי"})

    return {"sources": sources}
