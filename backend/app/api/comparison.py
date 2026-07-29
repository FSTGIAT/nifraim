import logging
import uuid
from datetime import date, datetime
from decimal import Decimal

from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

logger = logging.getLogger(__name__)
from sqlalchemy import select, desc, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.paying_company import PayingCompany
from app.models.debt import Debt
from app.models.commission_comparison import CommissionComparison
from app.api.deps import get_paid_user as get_current_user
from sqlalchemy import and_

from app.services.parser_service import parse_excel, CategoryMismatchError
from app.services.comparison_service import compute_comparison
from app.schemas.comparison import ComparisonResponse, PaymentStatusUpdate
from app.utils.sanitize import sanitize_record

router = APIRouter()


def _jsonable(obj):
    """Recursively coerce a comparison-result tree into JSON-safe primitives.

    asyncpg's JSONB encoder doesn't know how to serialise Decimal / date /
    datetime / UUID, so a comparison result coming straight out of the
    SQLAlchemy column values blows up with "Object of type Decimal is not
    JSON serializable" at INSERT time. Walk the dict/list tree once and
    convert the offending types to JSON primitives. Floats lose precision
    vs Decimal but the comparison table is for display, not accounting.
    """
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return obj


async def _persist_comparison(
    db: AsyncSession,
    user_id: uuid.UUID,
    comparison: dict,
    *,
    production_upload_id: uuid.UUID | None,
) -> None:
    """Save the result of a `compute_comparison` call so the Comparison tab
    can rehydrate it on next load. Best-effort — never raises.
    """
    try:
        category = comparison.get("commission_category") or "unknown"
        summary = comparison.get("summary") or {}
        sources = comparison.get("commission_company_sources") or (
            [comparison.get("commission_company_source")]
            if comparison.get("commission_company_source")
            else []
        )
        row = CommissionComparison(
            user_id=user_id,
            category=category,
            production_upload_id=production_upload_id,
            summary_json=_jsonable(summary),
            result_json=_jsonable(comparison),
            commission_company_sources=_jsonable(sources),
        )
        db.add(row)
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to persist commission comparison: {e}")
        try:
            await db.rollback()
        except Exception:
            pass


@router.post("/dual-upload", response_model=ComparisonResponse)
async def dual_upload(
    production_file: UploadFile = File(...),
    commission_file: UploadFile = File(...),
    production_password: str = Form(default=None),
    commission_password: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload two files and compare them."""
    # Validate file extensions
    for f, label in [(production_file, "פרודוקציה"), (commission_file, "נפרעים")]:
        if not f.filename:
            raise HTTPException(400, f"לא סופק קובץ {label}")
        ext = f.filename.rsplit(".", 1)[-1].lower()
        if ext not in ("xlsx", "xls"):
            raise HTTPException(400, f"קובץ {label}: רק xlsx/xls נתמך")

    # Read both files
    prod_content = await production_file.read()
    comm_content = await commission_file.read()

    # Parse both files
    try:
        prod_result = parse_excel(
            prod_content, production_file.filename, production_password,
            expected_category="production",
        )
    except CategoryMismatchError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"שגיאה בפענוח קובץ פרודוקציה: {str(e)}")

    try:
        comm_result = parse_excel(
            comm_content, commission_file.filename, commission_password,
            expected_category="commission",
        )
    except CategoryMismatchError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"שגיאה בפענוח דוח נפרעים: {str(e)}")

    # Create FileUpload records for both
    prod_ext = production_file.filename.rsplit(".", 1)[-1].lower()
    comm_ext = commission_file.filename.rsplit(".", 1)[-1].lower()

    prod_upload = FileUpload(
        user_id=user.id,
        filename=production_file.filename,
        file_type=prod_ext,
        company_source=prod_result["company_source"],
        record_count=len(prod_result["records"]),
        format_type=prod_result["format"],
        file_category="production",
    )
    comm_upload = FileUpload(
        user_id=user.id,
        filename=commission_file.filename,
        file_type=comm_ext,
        company_source=comm_result["company_source"],
        record_count=len(comm_result["records"]),
        format_type=comm_result["format"],
        file_category="commission",
    )
    db.add(prod_upload)
    db.add(comm_upload)
    await db.flush()

    # Insert records into DB
    for rec_data in prod_result["records"]:
        clean = sanitize_record(rec_data)
        record = ClientRecord(
            user_id=user.id,
            upload_id=prod_upload.id,
            **{k: v for k, v in clean.items() if hasattr(ClientRecord, k)},
        )
        db.add(record)

    for rec_data in comm_result["records"]:
        clean = sanitize_record(rec_data)
        record = ClientRecord(
            user_id=user.id,
            upload_id=comm_upload.id,
            **{k: v for k, v in clean.items() if hasattr(ClientRecord, k)},
        )
        db.add(record)

    await db.commit()

    # Load paying companies for this user
    paying_result = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user.id)
    )
    paying_names = [p.company_name for p in paying_result.scalars().all()]

    # Compute comparison on the fly
    comparison = compute_comparison(prod_result["records"], comm_result["records"], paying_names)
    comparison["commission_company_source"] = comm_result.get("company_source")
    await _persist_comparison(db, user.id, comparison, production_upload_id=prod_upload.id)
    return comparison


@router.post("/compute", response_model=ComparisonResponse)
async def compute_from_uploads(
    production_upload_id: str = Form(...),
    commission_upload_id: str = Form(...),
    category: str = Form(default=None),
    persist: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compute comparison from two existing uploads.

    With ``persist=false`` the result is returned but NOT saved as the
    latest comparison — used for ephemeral single-file inspection so it
    never clobbers the merged all-companies picture.
    """
    # Load production records
    prod_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == uuid.UUID(production_upload_id),
            ClientRecord.user_id == user.id,
        )
    )
    prod_records = prod_result.scalars().all()

    # Load commission records
    comm_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == uuid.UUID(commission_upload_id),
            ClientRecord.user_id == user.id,
        )
    )
    comm_records = comm_result.scalars().all()

    if not prod_records:
        raise HTTPException(404, "לא נמצאו רשומות בקובץ הפרודוקציה")
    if not comm_records:
        raise HTTPException(404, "לא נמצאו רשומות בדוח הנפרעים")

    # Convert ORM objects to dicts
    def record_to_dict(r):
        return {c.key: getattr(r, c.key) for c in r.__table__.columns if c.key not in ("id", "user_id", "upload_id")}

    prod_dicts = [record_to_dict(r) for r in prod_records]
    comm_dicts = [record_to_dict(r) for r in comm_records]

    # Load paying companies for this user
    paying_result = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user.id)
    )
    paying_names = [p.company_name for p in paying_result.scalars().all()]

    # Get commission upload company source
    comm_upload_result = await db.execute(
        select(FileUpload).where(FileUpload.id == uuid.UUID(commission_upload_id))
    )
    comm_upload = comm_upload_result.scalar_one_or_none()

    comparison = compute_comparison(prod_dicts, comm_dicts, paying_names, category_override=category)
    comparison["commission_company_source"] = comm_upload.company_source if comm_upload else None
    if persist:
        await _persist_comparison(db, user.id, comparison, production_upload_id=uuid.UUID(production_upload_id))
    return comparison


@router.post("/compare-with-production", response_model=ComparisonResponse)
async def compare_with_production(
    commission_files: List[UploadFile] = File(...),
    commission_password: str = Form(default=None),
    category: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload one or more commission files, then recompute the merged
    all-companies comparison (latest file per company) against production."""
    # Fail fast when there's no active production. Production is NOT a
    # singleton (multiple per-company uploads coexist as is_production=True),
    # so LIMIT 1 — scalar_one_or_none() raised MultipleResultsFound here.
    prod_upload_result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == True,
        )
        .order_by(desc(FileUpload.uploaded_at))
        .limit(1)
    )
    prod_upload = prod_upload_result.scalar_one_or_none()
    if not prod_upload:
        raise HTTPException(404, "לא נמצא קובץ פרודוקציה פעיל. יש להעלות קובץ פרודוקציה קודם.")

    all_commission_records = []
    company_sources = []

    for commission_file in commission_files:
        # Validate each file
        if not commission_file.filename:
            continue
        ext = commission_file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ("xlsx", "xls"):
            raise HTTPException(400, f"קובץ {commission_file.filename}: רק xlsx/xls נתמך")

        # Parse commission file
        comm_content = await commission_file.read()
        try:
            comm_result = parse_excel(
                comm_content, commission_file.filename, commission_password,
                expected_category="commission",
            )
        except CategoryMismatchError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(400, f"שגיאה בפענוח {commission_file.filename}: {str(e)}")

        # Debug: log parse results
        ids_with_val = [r.get("id_number") for r in comm_result["records"] if r.get("id_number")]
        print(f"PARSE DEBUG: file={commission_file.filename} format={comm_result['format']} company={comm_result.get('company_source')} total_records={len(comm_result['records'])} records_with_id={len(ids_with_val)} sample_ids={ids_with_val[:3]}", flush=True)

        # Keep only latest previous upload with same filename (for monthly comparison)
        old_uploads_result = await db.execute(
            select(FileUpload).where(
                FileUpload.user_id == user.id,
                FileUpload.filename == commission_file.filename,
                FileUpload.file_category == "commission",
            ).order_by(desc(FileUpload.uploaded_at))
        )
        old_uploads = old_uploads_result.scalars().all()
        to_delete = old_uploads[1:]
        if to_delete:
            # debts.commission_upload_id has no ON DELETE rule — null out references
            # before deleting old uploads to avoid FK violation.
            delete_ids = [u.id for u in to_delete]
            await db.execute(
                update(Debt)
                .where(Debt.commission_upload_id.in_(delete_ids))
                .values(commission_upload_id=None)
            )
            for old in to_delete:
                await db.delete(old)
            await db.flush()

        # Save commission upload to DB
        comm_upload = FileUpload(
            user_id=user.id,
            filename=commission_file.filename,
            file_type=ext,
            company_source=comm_result["company_source"],
            record_count=len(comm_result["records"]),
            format_type=comm_result["format"],
            file_category="commission",
        )
        db.add(comm_upload)
        await db.flush()

        for rec_data in comm_result["records"]:
            clean = sanitize_record(rec_data)
            record = ClientRecord(
                user_id=user.id,
                upload_id=comm_upload.id,
                **{k: v for k, v in clean.items() if hasattr(ClientRecord, k)},
            )
            db.add(record)

        all_commission_records.extend(comm_result["records"])
        if comm_result.get("company_source"):
            company_sources.append(comm_result["company_source"])

    await db.commit()

    if not all_commission_records:
        raise HTTPException(400, "לא נמצאו רשומות בקבצי הנפרעים")

    # Recompute the merged all-companies picture (latest source per company
    # across ALL stored uploads — not just this request's files). The
    # orchestrator computes + persists + debt-syncs one comparison per
    # category, exactly like the batch flow.
    from app.services.comparison_orchestrator import compute_merged_comparison
    merged = await compute_merged_comparison(db, user.id)
    if merged["skip_reason"] == "no_production":
        raise HTTPException(404, "לא נמצא קובץ פרודוקציה פעיל. יש להעלות קובץ פרודוקציה קודם.")
    comparison = merged.get("comparison")
    if not comparison:
        raise HTTPException(400, "ההשוואה לא הופקה — לא נמצאו רשומות נפרעים תואמות")

    # One merged comparison covering every company and both גמל and ביטוח.
    # This used to majority-vote the uploaded records into a single category
    # and return only that half — which mislabelled the minority half of a
    # merged נפרעים file and hid the rest of the agent's picture.
    return comparison


@router.post("/refresh")
async def refresh_merged_comparison(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Recompute + persist the merged all-companies comparison on demand
    (latest source per company across all stored uploads)."""
    from app.services.comparison_orchestrator import compute_merged_comparison

    merged = await compute_merged_comparison(db, user.id)
    return {
        "persisted": merged["persisted"],
        "skip_reason": merged["skip_reason"],
    }


@router.get("/insights")
async def comparison_insights(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Always-on insights for the Comparison tab.

    Combines:
        current — live aggregates from the `debts` table
        previous — same shape from the row before the latest commission_comparisons,
                   so the dashboard can show MoM deltas the moment a 2nd
                   comparison runs
        trend — up to 6 most-recent comparison summaries, feeding the
                per-card sparklines

    `category` is accepted for URL compatibility and IGNORED — the comparison
    is no longer split into גמל/ביטוח, so scoping these aggregates to one of
    them would report half the agent's debts as if it were all of them.
    """
    # Live debts summary — all categories
    debts_q = await db.execute(
        select(
            Debt.status,
            func.count().label("count"),
            func.coalesce(func.sum(Debt.expected_amount), 0).label("total"),
            func.count(func.distinct(Debt.customer_id_number)).label("customers"),
            func.count(func.distinct(Debt.company_name)).label("companies"),
        )
        .where(Debt.user_id == user.id)
        .group_by(Debt.status)
    )
    by_status: dict[str, dict] = {}
    for r in debts_q.all():
        by_status[r.status] = {
            "count": int(r.count or 0),
            "amount": float(r.total or 0),
            "customers": int(r.customers or 0),
            "companies": int(r.companies or 0),
        }
    open_ = by_status.get("open", {"count": 0, "amount": 0, "customers": 0, "companies": 0})
    paid_ = by_status.get("paid", {"count": 0, "amount": 0, "customers": 0, "companies": 0})

    distinct_q = await db.execute(
        select(
            func.count(func.distinct(Debt.customer_id_number)).label("debt_customers"),
            func.count(func.distinct(Debt.company_name)).label("debt_companies"),
        )
        .where(Debt.user_id == user.id, Debt.status == "open")
    )
    distincts = distinct_q.one()

    current = {
        "open_count":     open_["count"],
        "open_amount":    open_["amount"],
        "paid_count":     paid_["count"],
        "paid_amount":    paid_["amount"],
        "debt_customers": int(distincts.debt_customers or 0),
        "debt_companies": int(distincts.debt_companies or 0),
    }

    # Per-company breakdown for the chart (top 8 by amount).
    # `since` = earliest debt creation per company → drives "מאז" pill + age in UI.
    companies_q = await db.execute(
        select(
            Debt.company_name,
            func.count().label("count"),
            func.coalesce(func.sum(Debt.expected_amount), 0).label("amount"),
            func.count(func.distinct(Debt.customer_id_number)).label("customers"),
            func.min(Debt.created_at).label("since"),
        )
        .where(Debt.user_id == user.id, Debt.status == "open")
        .group_by(Debt.company_name)
        .order_by(func.coalesce(func.sum(Debt.expected_amount), 0).desc())
        .limit(8)
    )
    companies = [
        {
            "company": r.company_name,
            "count": int(r.count or 0),
            "amount": float(r.amount or 0),
            "customers": int(r.customers or 0),
            "since": r.since.isoformat() if r.since else None,
        }
        for r in companies_q.all()
    ]
    current["companies"] = companies

    # Per-customer breakdown for the 2nd chart (top 8 by amount)
    customers_q = await db.execute(
        select(
            Debt.customer_id_number,
            Debt.customer_name,
            func.count().label("count"),
            func.coalesce(func.sum(Debt.expected_amount), 0).label("amount"),
            func.count(func.distinct(Debt.company_name)).label("companies"),
            func.min(Debt.created_at).label("since"),
        )
        .where(Debt.user_id == user.id, Debt.status == "open")
        .group_by(Debt.customer_id_number, Debt.customer_name)
        .order_by(func.coalesce(func.sum(Debt.expected_amount), 0).desc())
        .limit(8)
    )
    customers = [
        {
            "id_number": r.customer_id_number,
            "name": r.customer_name or r.customer_id_number,
            "count": int(r.count or 0),
            "amount": float(r.amount or 0),
            "companies": int(r.companies or 0),
            "since": r.since.isoformat() if r.since else None,
        }
        for r in customers_q.all()
    ]
    current["top_customers"] = customers

    # Trend + previous from persisted comparisons. Not filtered by category:
    # new rows are written under the single MERGED_CATEGORY label, and old
    # per-category rows are still valid history for the same portfolio.
    history_q = await db.execute(
        select(CommissionComparison)
        .where(CommissionComparison.user_id == user.id)
        .order_by(desc(CommissionComparison.computed_at))
        .limit(6)
    )
    rows = list(history_q.scalars().all())
    trend = []
    for row in reversed(rows):
        s = row.summary_json or {}
        trend.append({
            "computed_at":     row.computed_at.isoformat() if row.computed_at else None,
            "open_count":      int(s.get("only_in_production") or 0),
            "open_amount":     float(s.get("total_premium") or 0),
            "matched":         int(s.get("matched") or 0),
            "total_customers": int(s.get("total_customers") or 0),
        })

    previous = None
    if len(rows) >= 2:
        s2 = rows[1].summary_json or {}
        previous = {
            "open_count":     int(s2.get("only_in_production") or 0),
            "open_amount":    float(s2.get("total_premium") or 0),
            "matched":        int(s2.get("matched") or 0),
            "total_customers": int(s2.get("total_customers") or 0),
        }

    return {
        "category": category,
        "current": current,
        "previous": previous,
        "trend": trend,
        "has_any_history": len(rows) > 0,
    }


@router.get("/latest")
async def latest_comparison(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the most-recent persisted comparison for this user, or null.

    Lets the Comparison tab rehydrate its dashboard on page reload (and pick
    up results from scheduled portal automation runs the user wasn't watching).

    `category` is accepted for URL compatibility and IGNORED. Filtering by it
    would strand every agent whose newest comparison is a merged one, and
    return a stale half-picture from the old per-category rows instead.
    """
    result = await db.execute(
        select(CommissionComparison)
        .where(CommissionComparison.user_id == user.id)
        .order_by(desc(CommissionComparison.computed_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"result": None, "computed_at": None}
    return {
        "result": row.result_json,
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
    }


@router.get("/company-summary")
async def company_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cross-company reconciliation overview spanning BOTH categories.

    One row per company: produced / matched / unpaid / received / expected /
    gap. Sources are the SAME ones the dashboards use — produced & received
    come from the persisted comparison result_json; the gap (unpaid expected)
    comes from the canonical `debts` table — so the overview can't drift from
    the per-company drill-down.
    """
    from app.utils.company_norm import normalize_company

    def _key(name):
        return normalize_company(name) or (name or "")

    # company → aggregates
    agg: dict[str, dict] = {}

    def _bucket(name):
        k = _key(name)
        if k not in agg:
            agg[k] = {
                "company": name or k,
                "produced": 0, "matched": 0, "unpaid": 0,
                "received": 0.0, "gap": 0.0,
            }
        return agg[k]

    # produced + received from the latest comparison. This used to loop the two
    # categories and merge their newest rows; one merged comparison now covers
    # both, and summing a merged row with a stale per-category one would
    # double-count every company they share.
    row_q = await db.execute(
        select(CommissionComparison)
        .where(CommissionComparison.user_id == user.id)
        .order_by(desc(CommissionComparison.computed_at))
        .limit(1)
    )
    row = row_q.scalar_one_or_none()
    if row and row.result_json:
        for cust in row.result_json.get("customers", []):
            for p in cust.get("production_products", []) or []:
                b = _bucket(p.get("company") or p.get("company_full"))
                b["produced"] += 1
            for p in cust.get("commission_products", []) or []:
                b = _bucket(p.get("company"))
                b["received"] += float(p.get("commission") or 0)

    # unpaid count + gap (expected unpaid) from the canonical debts table
    debts_q = await db.execute(
        select(
            Debt.company_name,
            func.count().label("count"),
            func.coalesce(func.sum(Debt.expected_amount), 0).label("gap"),
        )
        .where(Debt.user_id == user.id, Debt.status == "open")
        .group_by(Debt.company_name)
    )
    for r in debts_q.all():
        b = _bucket(r.company_name)
        b["unpaid"] += int(r.count or 0)
        b["gap"] += float(r.gap or 0)

    companies = []
    totals = {"produced": 0, "matched": 0, "unpaid": 0, "received": 0.0, "expected": 0.0, "gap": 0.0}
    for b in agg.values():
        b["matched"] = max(b["produced"] - b["unpaid"], 0)
        b["expected"] = round(b["received"] + b["gap"], 2)
        b["received"] = round(b["received"], 2)
        b["gap"] = round(b["gap"], 2)
        companies.append(b)
        for k in ("produced", "matched", "unpaid", "received", "expected", "gap"):
            totals[k] += b[k]

    companies.sort(key=lambda x: x["gap"], reverse=True)
    totals["received"] = round(totals["received"], 2)
    totals["expected"] = round(totals["expected"], 2)
    totals["gap"] = round(totals["gap"], 2)
    return {"companies": companies, "totals": totals}


@router.patch("/mark-paid")
async def mark_paid(
    data: PaymentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Toggle payment status for a product identified by id_number + policy_number."""
    result = await db.execute(
        select(ClientRecord).where(
            and_(
                ClientRecord.user_id == user.id,
                ClientRecord.id_number == data.id_number,
                ClientRecord.fund_policy_number == data.policy_number,
            )
        )
    )
    records = result.scalars().all()
    if not records:
        raise HTTPException(404, "רשומה לא נמצאה")

    new_status = "paid_match" if data.paid else "unpaid"
    for record in records:
        record.reconciliation_status = new_status

    await db.commit()
    return {"status": new_status, "count": len(records)}
