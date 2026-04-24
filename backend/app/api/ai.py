from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.recruit import Recruit
from app.models.production_summary import ProductionSummary
from app.models.commission_rate import CommissionRate
from app.models.volume_commission_rate import VolumeCommissionRate
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
        stream_chat(
            db,
            user.id,
            req.question,
            [m.model_dump() for m in req.history],
            view_context=req.view_context,
        ),
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


@router.get("/knowledge")
async def get_knowledge(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Return a comprehensive view of every data source the AI has access to.

    Powers the ספריית AI tab so users can see *exactly* what the assistant knows.
    """
    # --- Production: active + all historical uploads ---
    prod_q = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "production",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    prod_uploads = prod_q.scalars().all()

    # Historical summaries (for month labels + totals)
    hist_q = await db.execute(
        select(ProductionSummary)
        .where(ProductionSummary.user_id == user.id)
        .order_by(desc(ProductionSummary.upload_date))
    )
    hist_summaries = {s.upload_id: s for s in hist_q.scalars().all()}

    production = []
    for u in prod_uploads:
        summary = hist_summaries.get(u.id)
        production.append({
            "id": str(u.id),
            "filename": u.filename,
            "is_active": bool(u.is_production),
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
            "record_count": u.record_count or 0,
            "unique_clients": summary.unique_clients if summary else None,
            "total_premium": float(summary.total_premium) if summary else None,
            "total_accumulation": float(summary.total_accumulation) if summary else None,
            "period_label": summary.period_label if summary else None,
        })

    # --- Commission files, grouped by company_source (or filename fallback) ---
    comm_q = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "commission",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    commission_rows = comm_q.scalars().all()
    commission_groups: dict[str, dict] = {}
    for u in commission_rows:
        key = u.company_source or u.filename or "חברה לא ידועה"
        g = commission_groups.setdefault(key, {"company": key, "files": []})
        g["files"].append({
            "id": str(u.id),
            "filename": u.filename,
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
            "record_count": u.record_count or 0,
            "format_type": u.format_type,
        })
    commission = sorted(commission_groups.values(), key=lambda g: g["company"])

    # --- My File (recruits) ---
    recruit_count_q = await db.execute(
        select(func.count(Recruit.id)).where(Recruit.user_id == user.id)
    )
    recruit_count = recruit_count_q.scalar() or 0

    recruit_company_q = await db.execute(
        select(func.count(func.distinct(Recruit.company))).where(
            Recruit.user_id == user.id,
            Recruit.company.isnot(None),
        )
    )
    recruit_companies = recruit_company_q.scalar() or 0

    recruit_date_q = await db.execute(
        select(func.min(Recruit.sign_date), func.max(Recruit.sign_date)).where(
            Recruit.user_id == user.id,
            Recruit.sign_date.isnot(None),
        )
    )
    sign_min, sign_max = recruit_date_q.one()

    # Breakdown by category (financial / insurance) — each category is replaced
    # on upload, so this makes the combined total understandable at a glance.
    recruit_cat_q = await db.execute(
        select(Recruit.category, func.count(Recruit.id))
        .where(Recruit.user_id == user.id)
        .group_by(Recruit.category)
    )
    by_category = [
        {"category": cat or "financial", "count": int(cnt)}
        for cat, cnt in recruit_cat_q.all()
    ]

    myfile = {
        "count": recruit_count,
        "companies": recruit_companies,
        "sign_date_min": sign_min.isoformat() if sign_min else None,
        "sign_date_max": sign_max.isoformat() if sign_max else None,
        "by_category": by_category,
    } if recruit_count else None

    # --- Commission rates (nifraim + volume) — both tables use `company_name` ---
    nifraim_q = await db.execute(
        select(func.count(CommissionRate.id), func.count(func.distinct(CommissionRate.company_name)))
        .where(CommissionRate.user_id == user.id)
    )
    nifraim_total, nifraim_companies = nifraim_q.one()

    volume_q = await db.execute(
        select(func.count(VolumeCommissionRate.id), func.count(func.distinct(VolumeCommissionRate.company_name)))
        .where(VolumeCommissionRate.user_id == user.id)
    )
    volume_total, volume_companies = volume_q.one()

    rates = {
        "nifraim": {"count": int(nifraim_total or 0), "companies": int(nifraim_companies or 0)},
        "volume":  {"count": int(volume_total or 0),  "companies": int(volume_companies or 0)},
    } if (nifraim_total or volume_total) else None

    return {
        "production": production,
        "commission": commission,
        "myfile": myfile,
        "rates": rates,
    }
