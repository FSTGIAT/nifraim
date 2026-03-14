import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.schemas.upload import ProductionFileInfo, ProductionAnalytics, ProductionCompareResponse
from app.api.deps import get_paid_user as get_current_user
from app.services.parser_service import parse_excel
from app.services.portal_service import create_snapshots_for_upload
from app.utils.sanitize import sanitize_record

router = APIRouter()


async def _create_snapshots_bg(user_id, upload_id):
    """Background task to create portal snapshots after production upload."""
    from app.database import async_session
    async with async_session() as db:
        await create_snapshots_for_upload(db, user_id, upload_id)


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
    background_tasks: BackgroundTasks,
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

    # Deactivate previous production file (keep file_category for history)
    old_prod = await _get_production_upload(db, user.id)
    if old_prod:
        old_prod.is_production = False

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

    # Create portal snapshots in background (non-blocking)
    background_tasks.add_task(_create_snapshots_bg, user.id, upload.id)

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


@router.get("/analytics", response_model=ProductionAnalytics | None)
async def get_production_analytics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Analytics for current production file."""
    upload = await _get_production_upload(db, user.id)
    if not upload:
        return None

    uid = upload.id
    base = select(ClientRecord).where(ClientRecord.upload_id == uid)

    # Totals
    totals = await db.execute(
        select(
            func.count().label("cnt"),
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("total_premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("total_accumulation"),
            func.count(func.distinct(ClientRecord.receiving_company)).label("companies_count"),
        ).where(ClientRecord.upload_id == uid)
    )
    t = totals.one()

    # Company breakdown
    company_q = await db.execute(
        select(
            ClientRecord.receiving_company,
            func.count().label("count"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
    )
    company_breakdown = [
        {"company": r[0], "count": r[1], "premium": float(r[2]), "accumulation": float(r[3])}
        for r in company_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Product type breakdown
    product_q = await db.execute(
        select(
            ClientRecord.product_type,
            func.count().label("count"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.product_type.isnot(None))
        .group_by(ClientRecord.product_type)
        .order_by(desc(func.count()))
    )
    product_type_breakdown = [
        {"product_type": r[0], "count": r[1], "premium": float(r[2])}
        for r in product_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Status breakdown
    status_q = await db.execute(
        select(
            ClientRecord.product_status,
            func.count().label("count"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.product_status.isnot(None))
        .group_by(ClientRecord.product_status)
        .order_by(desc(func.count()))
    )
    status_breakdown = [
        {"status": r[0], "count": r[1]}
        for r in status_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Top 10 clients by premium
    top_premium_q = await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.count().label("products"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.total_premium), 0)))
        .limit(10)
    )
    top_clients_premium = [
        {"id_number": r[0], "name": f"{r[1] or ''} {r[2] or ''}".strip(), "premium": float(r[3]), "products": r[4]}
        for r in top_premium_q.all()
    ]

    # Top 10 clients by accumulation
    top_accum_q = await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
            func.count().label("products"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
        .limit(10)
    )
    top_clients_accumulation = [
        {"id_number": r[0], "name": f"{r[1] or ''} {r[2] or ''}".strip(), "accumulation": float(r[3]), "products": r[4]}
        for r in top_accum_q.all()
    ]

    return ProductionAnalytics(
        total_records=t.cnt,
        unique_clients=t.unique_clients,
        total_premium=float(t.total_premium),
        total_accumulation=float(t.total_accumulation),
        companies_count=t.companies_count,
        company_breakdown=company_breakdown,
        product_type_breakdown=product_type_breakdown,
        status_breakdown=status_breakdown,
        top_clients_premium=top_clients_premium,
        top_clients_accumulation=top_clients_accumulation,
    )


@router.get("/history", response_model=list[ProductionFileInfo])
async def get_production_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List previous production files (non-active) for comparison."""
    result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "production",
            FileUpload.is_production == False,
        )
        .order_by(desc(FileUpload.uploaded_at))
        .limit(10)
    )
    uploads = result.scalars().all()
    out = []
    for u in uploads:
        companies = await _get_companies_for_upload(db, u.id)
        out.append(ProductionFileInfo(
            id=str(u.id),
            filename=u.filename,
            file_type=u.file_type,
            company_source=u.company_source,
            record_count=u.record_count,
            uploaded_at=u.uploaded_at,
            companies=companies,
        ))
    return out


class CompareRequest(BaseModel):
    current_upload_id: str
    previous_upload_id: str


@router.post("/compare", response_model=ProductionCompareResponse)
async def compare_productions(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare two production files: new/removed/changed clients."""
    current_id = uuid.UUID(req.current_upload_id)
    previous_id = uuid.UUID(req.previous_upload_id)

    # Fetch records for both uploads (scoped by user_id)
    async def _fetch_grouped(upload_id):
        result = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id == upload_id,
                ClientRecord.user_id == user.id,
            )
        )
        records = result.scalars().all()
        grouped = {}
        for r in records:
            if not r.id_number:
                continue
            if r.id_number not in grouped:
                grouped[r.id_number] = {
                    "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
                    "company": r.receiving_company or "",
                    "premium": 0.0,
                    "accumulation": 0.0,
                    "products_count": 0,
                    "statuses": [],
                }
            g = grouped[r.id_number]
            g["premium"] += float(r.total_premium or 0)
            g["accumulation"] += float(r.accumulation or 0)
            g["products_count"] += 1
            if r.product_status:
                g["statuses"].append(r.product_status)
        return grouped

    current = await _fetch_grouped(current_id)
    previous = await _fetch_grouped(previous_id)

    current_ids = set(current.keys())
    previous_ids = set(previous.keys())

    new_ids = current_ids - previous_ids
    removed_ids = previous_ids - current_ids
    common_ids = current_ids & previous_ids

    new_clients = []
    for cid in sorted(new_ids):
        c = current[cid]
        new_clients.append({"id_number": cid, "name": c["name"], "company": c["company"],
                            "premium": round(c["premium"], 2), "accumulation": round(c["accumulation"], 2),
                            "products_count": c["products_count"]})

    removed_clients = []
    for cid in sorted(removed_ids):
        p = previous[cid]
        removed_clients.append({"id_number": cid, "name": p["name"], "company": p["company"],
                                "premium": round(p["premium"], 2), "accumulation": round(p["accumulation"], 2),
                                "products_count": p["products_count"]})

    changed_clients = []
    unchanged_count = 0
    for cid in sorted(common_ids):
        c = current[cid]
        p = previous[cid]
        changes = []
        premium_diff = round(c["premium"] - p["premium"], 2)
        accum_diff = round(c["accumulation"] - p["accumulation"], 2)

        if abs(premium_diff) > 0.01:
            changes.append({"field": "פרמיה", "old_val": round(p["premium"], 2), "new_val": round(c["premium"], 2)})
        if abs(accum_diff) > 0.01:
            changes.append({"field": "צבירה", "old_val": round(p["accumulation"], 2), "new_val": round(c["accumulation"], 2)})
        if c["products_count"] != p["products_count"]:
            changes.append({"field": "מוצרים", "old_val": p["products_count"], "new_val": c["products_count"]})

        if changes:
            changed_clients.append({
                "id_number": cid, "name": c["name"], "company": c["company"],
                "changes": changes, "premium_diff": premium_diff, "accumulation_diff": accum_diff,
            })
        else:
            unchanged_count += 1

    summary = {
        "new_count": len(new_clients),
        "removed_count": len(removed_clients),
        "changed_count": len(changed_clients),
        "unchanged_count": unchanged_count,
        "total_current": len(current),
        "total_previous": len(previous),
    }

    return ProductionCompareResponse(
        summary=summary,
        new_clients=new_clients,
        removed_clients=removed_clients,
        changed_clients=changed_clients,
    )
