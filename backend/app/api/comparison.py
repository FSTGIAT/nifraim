import logging
import uuid

from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.paying_company import PayingCompany
from app.api.deps import get_paid_user as get_current_user
from sqlalchemy import and_

from app.services.parser_service import parse_excel
from app.services.comparison_service import compute_comparison
from app.schemas.comparison import ComparisonResponse, PaymentStatusUpdate
from app.utils.sanitize import sanitize_record

router = APIRouter()


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
        prod_result = parse_excel(prod_content, production_file.filename, production_password)
    except Exception as e:
        raise HTTPException(400, f"שגיאה בפענוח קובץ פרודוקציה: {str(e)}")

    try:
        comm_result = parse_excel(comm_content, commission_file.filename, commission_password)
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
    )
    comm_upload = FileUpload(
        user_id=user.id,
        filename=commission_file.filename,
        file_type=comm_ext,
        company_source=comm_result["company_source"],
        record_count=len(comm_result["records"]),
        format_type=comm_result["format"],
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
    return comparison


@router.post("/compute", response_model=ComparisonResponse)
async def compute_from_uploads(
    production_upload_id: str = Form(...),
    commission_upload_id: str = Form(...),
    category: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compute comparison from two existing uploads."""
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
    return comparison


@router.post("/compare-with-production", response_model=ComparisonResponse)
async def compare_with_production(
    commission_files: List[UploadFile] = File(...),
    commission_password: str = Form(default=None),
    category: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload one or more commission files and compare against stored production file."""
    # Find active production upload
    prod_upload_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == True,
        )
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
            comm_result = parse_excel(comm_content, commission_file.filename, commission_password)
        except Exception as e:
            raise HTTPException(400, f"שגיאה בפענוח {commission_file.filename}: {str(e)}")

        # Debug: log parse results
        ids_with_val = [r.get("id_number") for r in comm_result["records"] if r.get("id_number")]
        logger.warning(
            "PARSE DEBUG: file=%s format=%s company=%s total_records=%d records_with_id=%d sample_ids=%s",
            commission_file.filename, comm_result["format"], comm_result.get("company_source"),
            len(comm_result["records"]), len(ids_with_val), ids_with_val[:3]
        )

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

    # Load production records from DB
    prod_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.user_id == user.id,
        )
    )
    prod_records = prod_result.scalars().all()

    def record_to_dict(r):
        return {c.key: getattr(r, c.key) for c in r.__table__.columns if c.key not in ("id", "user_id", "upload_id")}

    prod_dicts = [record_to_dict(r) for r in prod_records]

    # Load paying companies for this user
    paying_result = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user.id)
    )
    paying_names = [p.company_name for p in paying_result.scalars().all()]

    # Debug: log production and commission stats
    prod_ids_with_val = [r.get("id_number") for r in prod_dicts if r.get("id_number")]
    comm_ids_with_val = [r.get("id_number") for r in all_commission_records if r.get("id_number")]
    logger.warning(
        "COMPARISON DEBUG: prod_records=%d prod_with_id=%d comm_records=%d comm_with_id=%d category=%s",
        len(prod_dicts), len(prod_ids_with_val), len(all_commission_records), len(comm_ids_with_val), category
    )

    # Compute comparison with ALL commission records merged
    comparison = compute_comparison(prod_dicts, all_commission_records, paying_names, category_override=category)
    logger.warning("COMPARISON RESULT: %s", comparison["summary"])
    comparison["commission_company_source"] = company_sources[0] if len(company_sources) == 1 else None
    comparison["commission_company_sources"] = sorted(set(company_sources))
    return comparison


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
