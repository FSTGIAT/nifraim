from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, AGENCY_ROLES
from app.models.upload import FileUpload
from app.models.recruit import Recruit
from app.models.production_summary import ProductionSummary
from app.models.commission_rate import CommissionRate
from app.models.volume_commission_rate import VolumeCommissionRate
from app.api.deps import get_paid_user
from app.schemas.ai import ChatRequest
from app.services.ai_service import stream_chat
from app.services import agency_service

router = APIRouter()


@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    # Only honour the agency persona if the user actually has an agency role.
    # Falls back silently to the agent persona otherwise — defence in depth so
    # an agent can't just pass `prompt_persona="agency_accountant"` to escape
    # their per-user data scoping.
    persona = req.prompt_persona
    agency_id = None
    if persona == "agency_accountant":
        if user.role in AGENCY_ROLES and user.agency_id:
            agency_id = user.agency_id
        else:
            persona = None

    return StreamingResponse(
        stream_chat(
            db,
            user.id,
            req.question,
            [m.model_dump() for m in req.history],
            view_context=req.view_context,
            prompt_persona=persona,
            agency_id=agency_id,
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


async def _knowledge_for_user(db: AsyncSession, user_id) -> dict:
    """Build the AI-library knowledge block for a single user.

    Same shape consumed by `AiLibraryTab.vue`: production[], commission[],
    myfile, rates. Used both for the regular `scope=agent` request and (loop)
    for each agency member when an agency super-user requests `scope=agency`.
    """
    # --- Production: active + all historical uploads ---
    prod_q = await db.execute(
        select(FileUpload)
        .where(FileUpload.user_id == user_id, FileUpload.file_category == "production")
        .order_by(desc(FileUpload.uploaded_at))
    )
    prod_uploads = prod_q.scalars().all()

    hist_q = await db.execute(
        select(ProductionSummary)
        .where(ProductionSummary.user_id == user_id)
        .order_by(desc(ProductionSummary.upload_date))
    )
    hist_summaries = {s.upload_id: s for s in hist_q.scalars().all()}

    # Dedupe production by filename — keep the most recent upload per filename,
    # but always preserve the active one. Re-uploading the same filename should
    # show as ONE entry in the library, not as duplicates.
    production_by_name: dict[str, dict] = {}
    for u in prod_uploads:  # already DESC by uploaded_at
        summary = hist_summaries.get(u.id)
        entry = {
            "id": str(u.id),
            "filename": u.filename,
            "is_active": bool(u.is_production),
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
            "record_count": u.record_count or 0,
            "unique_clients": summary.unique_clients if summary else None,
            "total_premium": float(summary.total_premium) if summary else None,
            "total_accumulation": float(summary.total_accumulation) if summary else None,
            "period_label": summary.period_label if summary else None,
        }
        key = (u.filename or '').strip().lower()
        # Always prefer the active upload; otherwise keep the first (most recent) seen.
        existing = production_by_name.get(key)
        if not existing or (entry["is_active"] and not existing["is_active"]):
            production_by_name[key] = entry
    production = sorted(production_by_name.values(), key=lambda r: r.get("uploaded_at") or "", reverse=True)

    # --- Commission files, grouped by company_source ---
    comm_q = await db.execute(
        select(FileUpload)
        .where(FileUpload.user_id == user_id, FileUpload.file_category == "commission")
        .order_by(desc(FileUpload.uploaded_at))
    )
    # Group by company, then dedupe within each group by filename — re-uploads
    # of the same file (same filename) collapse to a single entry showing the
    # latest upload. DB rows untouched (commission-diff pairing still has access
    # to the historical re-uploads); we just don't surface duplicates in the UI.
    commission_groups: dict[str, dict] = {}
    for u in comm_q.scalars().all():  # already DESC by uploaded_at
        company_key = u.company_source or u.filename or "חברה לא ידועה"
        g = commission_groups.setdefault(company_key, {"company": company_key, "files": [], "_seen_names": set()})
        name_key = (u.filename or '').strip().lower()
        if name_key in g["_seen_names"]:
            continue  # older same-name re-upload — skip
        g["_seen_names"].add(name_key)
        g["files"].append({
            "id": str(u.id),
            "filename": u.filename,
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
            "record_count": u.record_count or 0,
            "format_type": u.format_type,
        })
    # Strip the internal _seen_names helper before returning
    for g in commission_groups.values():
        g.pop("_seen_names", None)
    commission = sorted(commission_groups.values(), key=lambda g: g["company"])

    # --- Recruits / personal file ---
    recruit_count = (await db.execute(
        select(func.count(Recruit.id)).where(Recruit.user_id == user_id)
    )).scalar() or 0
    recruit_companies = (await db.execute(
        select(func.count(func.distinct(Recruit.company)))
        .where(Recruit.user_id == user_id, Recruit.company.isnot(None))
    )).scalar() or 0
    sign_min, sign_max = (await db.execute(
        select(func.min(Recruit.sign_date), func.max(Recruit.sign_date))
        .where(Recruit.user_id == user_id, Recruit.sign_date.isnot(None))
    )).one()
    by_category = [
        {"category": cat or "financial", "count": int(cnt)}
        for cat, cnt in (await db.execute(
            select(Recruit.category, func.count(Recruit.id))
            .where(Recruit.user_id == user_id)
            .group_by(Recruit.category)
        )).all()
    ]
    myfile = {
        "count": int(recruit_count),
        "companies": int(recruit_companies),
        "sign_date_min": sign_min.isoformat() if sign_min else None,
        "sign_date_max": sign_max.isoformat() if sign_max else None,
        "by_category": by_category,
    } if recruit_count else None

    # --- Commission rates (nifraim + volume) ---
    nifraim_total, nifraim_companies = (await db.execute(
        select(func.count(CommissionRate.id), func.count(func.distinct(CommissionRate.company_name)))
        .where(CommissionRate.user_id == user_id)
    )).one()
    volume_total, volume_companies = (await db.execute(
        select(func.count(VolumeCommissionRate.id), func.count(func.distinct(VolumeCommissionRate.company_name)))
        .where(VolumeCommissionRate.user_id == user_id)
    )).one()
    rates = {
        "nifraim": {"count": int(nifraim_total or 0), "companies": int(nifraim_companies or 0)},
        "volume":  {"count": int(volume_total or 0),  "companies": int(volume_companies or 0)},
    } if (nifraim_total or volume_total) else None

    return {"production": production, "commission": commission, "myfile": myfile, "rates": rates}


@router.get("/knowledge")
async def get_knowledge(
    scope: str = Query("agent", regex="^(agent|agency)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Return a comprehensive view of every data source the AI has access to.

    `scope=agent` (default) → user's own files only.
    `scope=agency` (super-user only) → user's own files PLUS an `agents:[]`
    array, one entry per agency member with the same shape, so the UI can
    render a "תיקיות סוכנים" section with one folder per agent.
    """
    own = await _knowledge_for_user(db, user.id)

    if scope != "agency":
        return own

    # Super-user only: also build per-agent folders
    if user.role not in AGENCY_ROLES or not user.agency_id:
        raise HTTPException(status_code=403, detail="Agency access required")

    members = (await db.execute(
        select(User)
        .where(User.agency_id == user.agency_id, User.id != user.id)
        .order_by(User.full_name.asc())
    )).scalars().all()

    agents = []
    for m in members:
        block = await _knowledge_for_user(db, m.id)
        agents.append({
            "user_id": str(m.id),
            "name": m.full_name or m.email,
            "email": m.email,
            "role": m.role,
            **block,
        })

    return {"scope": "agency", **own, "agents": agents}


