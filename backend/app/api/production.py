import hashlib
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
from app.services.comparison_service import _classify_product_type, _GEMEL_KEYWORDS, _INSURANCE_KEYWORDS
from app.utils.sanitize import sanitize_record

router = APIRouter()


async def _create_snapshots_bg(user_id, upload_id):
    """Background task to create portal snapshots after production upload."""
    from app.database import async_session
    async with async_session() as db:
        await create_snapshots_for_upload(db, user_id, upload_id)


async def _compute_summary_bg(user_id, upload_id):
    """Background task to compute production summary after upload."""
    from app.database import async_session
    from app.services.summary_service import compute_production_summary
    async with async_session() as db:
        await compute_production_summary(db, user_id, upload_id)


def _compute_data_fingerprint(records: list[dict]) -> str:
    """Compute an MD5 fingerprint from parsed record data to detect duplicates."""
    rows = sorted(
        (
            r.get("id_number") or "",
            str(r.get("total_premium") or 0),
            str(r.get("accumulation") or 0),
            r.get("receiving_company") or "",
        )
        for r in records
    )
    return hashlib.md5(str(rows).encode()).hexdigest()


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

    # Check if new file has different data than current production
    old_prod = await _get_production_upload(db, user.id)
    if old_prod:
        # Build a fingerprint from the new parsed data
        new_fingerprint = _compute_data_fingerprint(result["records"])
        # Build fingerprint from existing records
        old_records_q = await db.execute(
            select(
                ClientRecord.id_number,
                ClientRecord.total_premium,
                ClientRecord.accumulation,
                ClientRecord.receiving_company,
            )
            .where(ClientRecord.upload_id == old_prod.id)
            .order_by(ClientRecord.id_number)
        )
        old_rows = old_records_q.all()
        old_fingerprint = hashlib.md5(
            str(sorted(
                (r[0] or "", str(r[1] or 0), str(r[2] or 0), r[3] or "")
                for r in old_rows
            )).encode()
        ).hexdigest()

        if new_fingerprint == old_fingerprint:
            raise HTTPException(
                status_code=400,
                detail="הקובץ מכיל נתונים זהים לקובץ הפרודוקציה הנוכחי — לא בוצע שינוי"
            )

        # Deactivate previous production file (keep file_category for history)
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

    # Create portal snapshots and production summary in background (non-blocking)
    background_tasks.add_task(_create_snapshots_bg, user.id, upload.id)
    background_tasks.add_task(_compute_summary_bg, user.id, upload.id)

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
    from app.models.portal_snapshot import PortalSnapshot
    from app.models.debt import Debt
    from app.models.production_summary import ProductionSummary

    upload = await _get_production_upload(db, user.id)
    if not upload:
        raise HTTPException(status_code=404, detail="לא נמצא קובץ פרודוקציה פעיל")

    # Delete related rows first to satisfy FK constraints.
    # debts.production_upload_id is NOT NULL → delete those debt rows.
    # debts.commission_upload_id is nullable but may also point at this upload → handled too.
    from sqlalchemy import delete as sql_delete, update as sql_update
    await db.execute(
        sql_delete(PortalSnapshot).where(PortalSnapshot.upload_id == upload.id)
    )
    await db.execute(
        sql_delete(ProductionSummary).where(ProductionSummary.upload_id == upload.id)
    )
    await db.execute(
        sql_delete(ClientRecord).where(ClientRecord.upload_id == upload.id)
    )
    await db.execute(
        sql_delete(Debt).where(Debt.production_upload_id == upload.id)
    )
    await db.execute(
        sql_update(Debt)
        .where(Debt.commission_upload_id == upload.id)
        .values(commission_upload_id=None)
    )

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
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
    )
    company_breakdown = [
        {"company": r[0], "count": r[1], "unique_clients": r[2], "premium": float(r[3]), "accumulation": float(r[4])}
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


@router.get("/clients")
async def get_production_clients(
    sort: str = "premium",
    search: str = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all clients from the active production file, grouped by id_number."""
    upload = await _get_production_upload(db, user.id)
    if not upload:
        return []

    order_col = func.coalesce(func.sum(ClientRecord.accumulation), 0) if sort == "accumulation" else func.coalesce(func.sum(ClientRecord.total_premium), 0)

    filters = [ClientRecord.upload_id == upload.id, ClientRecord.id_number.isnot(None)]
    if search:
        search = search.strip()
        filters.append(
            (ClientRecord.id_number.contains(search)) |
            (ClientRecord.first_name.ilike(f"%{search}%")) |
            (ClientRecord.last_name.ilike(f"%{search}%"))
        )

    q = await db.execute(
        select(
            ClientRecord.id_number,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.min(ClientRecord.receiving_company).label("company"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
            func.count().label("products"),
        )
        .where(*filters)
        .group_by(ClientRecord.id_number)
        .order_by(desc(order_col))
        .limit(50)
    )
    return [
        {
            "id_number": r.id_number,
            "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
            "company": r.company,
            "premium": float(r.premium),
            "accumulation": float(r.accumulation),
            "products": r.products,
        }
        for r in q.all()
    ]


@router.get("/clients/{id_number}")
async def get_client_detail(
    id_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all products for a specific client from the active production file."""
    upload = await _get_production_upload(db, user.id)
    if not upload:
        raise HTTPException(status_code=404, detail="אין קובץ פרודוקציה פעיל")

    result = await db.execute(
        select(ClientRecord)
        .where(
            ClientRecord.upload_id == upload.id,
            ClientRecord.id_number == id_number.lstrip('0'),
        )
    )
    records = result.scalars().all()
    if not records:
        raise HTTPException(status_code=404, detail="לקוח לא נמצא")

    name = f"{records[0].first_name or ''} {records[0].last_name or ''}".strip()
    products = []
    for r in records:
        products.append({
            "product": r.product or r.product_type or "—",
            "company": r.receiving_company or "—",
            "premium": float(r.total_premium or 0),
            "accumulation": float(r.accumulation or 0),
            "status": r.product_status or "—",
            "policy_number": r.fund_policy_number or "—",
        })

    return {
        "id_number": id_number,
        "name": name,
        "products": products,
        "total_premium": sum(p["premium"] for p in products),
        "total_accumulation": sum(p["accumulation"] for p in products),
    }


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


async def _build_commission_lookups(db: AsyncSession, user_id: uuid.UUID, dividing_date):
    """Build current vs previous {id_number: total_commission} grouped BY COMPANY.

    Pairing strategy (dividing_date kept for API compat but not used — batch
    upload timestamps made date-based splits unreliable):

    For each distinct company_source (fallback: filename):
      - current  = the latest upload
      - previous = the most recent upload with a DIFFERENT filename
                   (= a different period). If all uploads share the same filename
                   (re-uploads/corrections of the same period), fall back to the
                   second-latest of those.

    Returns:
        current_comm: {id_number: total}
        previous_comm: {id_number: total}
        has_data: bool
        has_previous: bool — at least one company has a prior-period pairing
        current_comm_detail: {id_number: [{company, commission}, ...]}
        covered_categories: set of product categories covered
    """
    all_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == False,
            FileUpload.file_category == "commission",
        ).order_by(desc(FileUpload.uploaded_at))
    )
    all_uploads = all_result.scalars().all()

    # Pair commission files BY COMPANY (not filename, not upload date).
    # For each company: current = latest upload; previous = the next-most-recent
    # upload with a DIFFERENT filename (= different period). If all uploads share
    # the same filename (re-uploads/corrections of the same period), previous
    # falls back to the second-latest of those.
    #
    # Rationale: users upload one commission file per company per month, with
    # period-specific filenames like "מור עמלות פברואר 26" vs "12_2025_נפרעים מור".
    # Date-based splits don't work because batch-uploads share timestamps, and
    # filename-based matching never triggers across periods.
    from collections import defaultdict

    upload_meta = {}  # upload_id → {company, filename}
    by_company = defaultdict(list)  # company_source → [uploads desc by date]
    for u in all_uploads:
        company_key = u.company_source or u.filename
        upload_meta[u.id] = {"company": company_key, "filename": u.filename}
        by_company[company_key].append(u)

    current_upload_ids = []
    previous_upload_ids = []
    for company, uploads in by_company.items():
        if not uploads:
            continue
        current_upload_ids.append(uploads[0].id)
        if len(uploads) < 2:
            continue
        # Prefer a different-filename upload (different period) as "previous"
        chosen = None
        for prev_u in uploads[1:]:
            if prev_u.filename != uploads[0].filename:
                chosen = prev_u
                break
        # All re-uploads of the same filename → use second-latest (correction diff)
        if chosen is None:
            chosen = uploads[1]
        previous_upload_ids.append(chosen.id)

    has_previous = len(previous_upload_ids) > 0
    all_needed_ids = list(set(current_upload_ids + previous_upload_ids))

    has_data = len(all_needed_ids) > 0

    # Fetch records for all needed uploads in one query
    # records_by_upload: {upload_id: {id_number: commission_sum}}
    records_by_upload = {}
    covered_categories = set()  # which product categories have commission data
    if all_needed_ids:
        result = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id.in_(all_needed_ids),
                ClientRecord.user_id == user_id,
            )
        )
        for r in result.scalars().all():
            if not r.id_number:
                continue
            # Detect which categories are covered by commission files
            product = (r.fund_type or r.product or "").lower()
            if product:
                if any(kw in product for kw in _GEMEL_KEYWORDS):
                    covered_categories.add("gemel_hishtalmut")
                if any(kw in product for kw in _INSURANCE_KEYWORDS):
                    covered_categories.add("insurance")
            comm_val = None
            for field_name in ("commission_paid", "commission_before_fee", "commission_expected", "actual_amount"):
                v = getattr(r, field_name, None)
                if v is not None:
                    try:
                        comm_val = float(v)
                    except (ValueError, TypeError):
                        continue
                    break
            if comm_val is not None and comm_val != 0:
                if r.upload_id not in records_by_upload:
                    records_by_upload[r.upload_id] = {}
                rec = records_by_upload[r.upload_id]
                rec[r.id_number] = round(rec.get(r.id_number, 0.0) + comm_val, 2)

    # Aggregate across uploads for each period
    def _aggregate(upload_ids):
        combined = {}
        for uid in upload_ids:
            for id_num, val in records_by_upload.get(uid, {}).items():
                combined[id_num] = combined.get(id_num, 0.0) + val
        return combined

    current_comm = _aggregate(current_upload_ids)
    previous_comm = _aggregate(previous_upload_ids)

    # Per-company detail for current period: {id_number: [{company, commission}, ...]}
    current_comm_detail = {}
    for uid in current_upload_ids:
        company = upload_meta.get(uid, {}).get("company", "?")
        for id_num, val in records_by_upload.get(uid, {}).items():
            if id_num not in current_comm_detail:
                current_comm_detail[id_num] = []
            current_comm_detail[id_num].append({
                "company": company,
                "commission": round(val, 2),
            })

    return current_comm, previous_comm, has_data, has_previous, current_comm_detail, covered_categories


@router.post("/compare", response_model=ProductionCompareResponse)
async def compare_productions(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare two production files: new/removed/changed clients."""
    current_id = uuid.UUID(req.current_upload_id)
    previous_id = uuid.UUID(req.previous_upload_id)

    # Fetch upload metadata for file names/dates
    current_upload = await db.execute(
        select(FileUpload).where(FileUpload.id == current_id, FileUpload.user_id == user.id)
    )
    current_file = current_upload.scalar_one_or_none()
    previous_upload = await db.execute(
        select(FileUpload).where(FileUpload.id == previous_id, FileUpload.user_id == user.id)
    )
    previous_file = previous_upload.scalar_one_or_none()

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
                    "product_types": [],
                    "statuses": [],
                    "categories": set(),
                }
            g = grouped[r.id_number]
            g["premium"] += float(r.total_premium or 0)
            g["accumulation"] += float(r.accumulation or 0)
            g["products_count"] += 1
            if r.product_status:
                g["statuses"].append(r.product_status)
            if r.product_type:
                g["product_types"].append(r.product_type)
            cat = _classify_product_type(r.product_type)
            if cat:
                g["categories"].add(cat)
        return grouped

    current = await _fetch_grouped(current_id)
    previous = await _fetch_grouped(previous_id)

    # ── Commission lookup: split by previous production upload date ──
    # For each filename: current = latest overall, previous = latest before prev date
    # Files not re-uploaded → same data both sides → diff = 0 (honest)
    prev_date = previous_file.uploaded_at if previous_file else None
    current_comm, previous_comm, has_commission_data, has_previous_commission, current_comm_detail, covered_categories = await _build_commission_lookups(
        db, user.id, prev_date
    )

    current_ids = set(current.keys())
    previous_ids = set(previous.keys())

    new_ids = current_ids - previous_ids
    removed_ids = previous_ids - current_ids
    common_ids = current_ids & previous_ids

    def _comm_fields(cid):
        curr = round(current_comm.get(cid, 0.0), 2)
        detail = current_comm_detail.get(cid, [])
        if has_previous_commission:
            prev = round(previous_comm.get(cid, 0.0), 2)
            return {
                "commission": curr,
                "commission_prev": prev,
                "commission_diff": round(curr - prev, 2),
                "commission_details": detail,
            }
        # No previous commission data — don't fake a diff
        return {
            "commission": curr,
            "commission_prev": None,
            "commission_diff": None,
            "commission_details": detail,
        }

    new_clients = []
    for cid in sorted(new_ids):
        c = current[cid]
        new_clients.append({"id_number": cid, "name": c["name"], "company": c["company"],
                            "premium": round(c["premium"], 2), "accumulation": round(c["accumulation"], 2),
                            "products_count": c["products_count"],
                            "product_types": list(set(c["product_types"])),
                            **_comm_fields(cid)})

    removed_clients = []
    for cid in sorted(removed_ids):
        p = previous[cid]
        removed_clients.append({"id_number": cid, "name": p["name"], "company": p["company"],
                                "premium": round(p["premium"], 2), "accumulation": round(p["accumulation"], 2),
                                "products_count": p["products_count"],
                                "product_types": list(set(p["product_types"])),
                                **_comm_fields(cid)})

    changed_clients = []
    unchanged_clients = []
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
                "premium": round(c["premium"], 2), "accumulation": round(c["accumulation"], 2),
                "products_count": c["products_count"],
                "changes": changes, "premium_diff": premium_diff, "accumulation_diff": accum_diff,
                **_comm_fields(cid),
            })
        else:
            unchanged_clients.append({
                "id_number": cid, "name": c["name"], "company": c["company"],
                "premium": round(c["premium"], 2), "accumulation": round(c["accumulation"], 2),
                "products_count": c["products_count"],
                **_comm_fields(cid),
            })

    # Positive/negative split for premium and accumulation diffs
    premium_positive = sum(1 for c in changed_clients if c["premium_diff"] > 0.01)
    premium_negative = sum(1 for c in changed_clients if c["premium_diff"] < -0.01)
    accum_positive = sum(1 for c in changed_clients if c["accumulation_diff"] > 0.01)
    accum_negative = sum(1 for c in changed_clients if c["accumulation_diff"] < -0.01)

    # Commission totals — scoped to production clients only (not all commission file clients)
    commission_total = round(sum(current_comm.get(cid, 0) for cid in current_ids), 2)
    if has_previous_commission:
        commission_prev_total = round(sum(previous_comm.get(cid, 0) for cid in previous_ids), 2)
        commission_diff_total = round(commission_total - commission_prev_total, 2)
    else:
        commission_prev_total = None
        commission_diff_total = None

    # Commission diff counts across ALL current production clients
    all_clients_with_data = new_clients + removed_clients + changed_clients + unchanged_clients
    commission_diff_positive = sum(1 for c in all_clients_with_data if (c.get("commission_diff") or 0) > 0.01)
    commission_diff_negative = sum(1 for c in all_clients_with_data if (c.get("commission_diff") or 0) < -0.01)

    # Count clients with/without commission from current commission data
    # Only count "ללא עמלה" for clients whose product category is covered by uploaded commission files
    commission_positive_count = sum(1 for cid in current_ids if current_comm.get(cid, 0) > 0)
    commission_zero_count = 0
    for cid in current_ids:
        if current_comm.get(cid, 0) == 0:
            client_cats = current[cid].get("categories", set())
            # Count as "ללא עמלה" only if any of client's categories has commission data
            if client_cats & covered_categories:
                commission_zero_count += 1
            elif not client_cats and covered_categories:
                # Unknown category but we have some commission data — count conservatively
                commission_zero_count += 1

    # Commission breakdown by company (scoped to production clients)
    company_totals = {}  # company → {total, clients}
    for cid in current_ids:
        for entry in current_comm_detail.get(cid, []):
            co = entry["company"]
            if co not in company_totals:
                company_totals[co] = {"total": 0.0, "clients": set()}
            company_totals[co]["total"] += entry["commission"]
            if entry["commission"] != 0:
                company_totals[co]["clients"].add(cid)
    commission_by_company = sorted([
        {"company": co, "total": round(data["total"], 2), "clients_count": len(data["clients"])}
        for co, data in company_totals.items()
        if data["total"] != 0
    ], key=lambda x: -abs(x["total"]))

    summary = {
        "new_count": len(new_clients),
        "removed_count": len(removed_clients),
        "changed_count": len(changed_clients),
        "unchanged_count": len(unchanged_clients),
        "total_current": len(current),
        "total_previous": len(previous),
        "has_commission_data": has_commission_data,
        "has_previous_commission": has_previous_commission,
        "commission_total": round(commission_total, 2),
        "commission_prev_total": round(commission_prev_total, 2) if commission_prev_total is not None else None,
        "commission_diff_total": commission_diff_total,
        "commission_diff_positive": commission_diff_positive,
        "commission_diff_negative": commission_diff_negative,
        "commission_positive_count": commission_positive_count,
        "commission_zero_count": commission_zero_count,
        "commission_by_company": commission_by_company,
        "premium_positive": premium_positive,
        "premium_negative": premium_negative,
        "accum_positive": accum_positive,
        "accum_negative": accum_negative,
        "current_filename": current_file.filename if current_file else "",
        "current_date": current_file.uploaded_at.isoformat() if current_file else "",
        "previous_filename": previous_file.filename if previous_file else "",
        "previous_date": previous_file.uploaded_at.isoformat() if previous_file else "",
    }

    return ProductionCompareResponse(
        summary=summary,
        new_clients=new_clients,
        removed_clients=removed_clients,
        changed_clients=changed_clients,
        unchanged_clients=unchanged_clients,
    )


# Commission format types (for backfilling file_category)
COMMISSION_FORMATS = {
    "agent_tracking", "company_report", "nifraim",
    "hachshara_nifraim", "menora", "altshuler",
    "clal_life_nifraim", "clal_health_nifraim", "migdal_nifraim",
    "ayalon_nifraim", "harel_nifraim", "phoenix_insurance_nifraim",
}


@router.post("/backfill-categories")
async def backfill_file_categories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One-time backfill: set file_category on existing uploads based on format_type."""
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.file_category.in_((None, "general")),
        )
    )
    uploads = result.scalars().all()
    updated = 0
    for u in uploads:
        if u.format_type == "production":
            u.file_category = "production"
            updated += 1
        elif u.format_type in COMMISSION_FORMATS:
            u.file_category = "commission"
            updated += 1
    await db.commit()
    return {"updated": updated, "total_checked": len(uploads)}


@router.post("/backfill-summaries")
async def backfill_summaries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One-time backfill: compute production summaries for all historical uploads."""
    from app.services.summary_service import compute_production_summary

    result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "production",
        )
        .order_by(FileUpload.uploaded_at)
    )
    uploads = result.scalars().all()
    created = 0
    for u in uploads:
        summary = await compute_production_summary(db, user.id, u.id)
        if summary:
            created += 1
    return {"created": created, "total_uploads": len(uploads)}
