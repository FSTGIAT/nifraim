import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import delete, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.recruit import Recruit
from app.schemas.recruit import (
    RecruitCreate, RecruitOut, RecruitMatchResult, RecruitComparisonResponse,
    RecruitFileProduct, RecruitFileClient, RecruitUploadResponse,
)
from app.services.parser_service import parse_excel
from app.services.comparison_service import _normalize_id, _extract_policy_core
from app.api.deps import get_current_user

router = APIRouter()


def _safe_float(val):
    """Convert to float, return None for NaN/Inf/invalid."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


@router.get("", response_model=list[RecruitOut])
async def list_recruits(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Recruit).where(Recruit.user_id == user.id)
    if category:
        q = q.where(Recruit.category == category)
    result = await db.execute(q.order_by(Recruit.created_at.desc()))
    recruits = result.scalars().all()
    return [
        RecruitOut(
            id=str(r.id),
            id_number=r.id_number,
            first_name=r.first_name,
            last_name=r.last_name,
            company=r.company,
            product=r.product,
            amount=_safe_float(r.amount),
            customer_status=r.customer_status,
            sign_date=r.sign_date,
            created_at=r.created_at,
        )
        for r in recruits
    ]


@router.post("", response_model=RecruitOut)
async def create_recruit(
    data: RecruitCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    recruit = Recruit(
        user_id=user.id,
        id_number=data.id_number[:20],
        first_name=data.first_name[:100],
        last_name=data.last_name[:100],
        company=data.company[:100] if data.company else None,
        product=data.product[:100] if data.product else None,
        amount=data.amount,
        sign_date=data.sign_date,
    )
    db.add(recruit)
    await db.commit()
    await db.refresh(recruit)
    return RecruitOut(
        id=str(recruit.id),
        id_number=recruit.id_number,
        first_name=recruit.first_name,
        last_name=recruit.last_name,
        company=recruit.company,
        product=recruit.product,
        amount=float(recruit.amount) if recruit.amount is not None else None,
        sign_date=recruit.sign_date,
        created_at=recruit.created_at,
    )


@router.post("/bulk", response_model=list[RecruitOut])
async def create_bulk_recruits(
    data: list[RecruitCreate],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    created = []
    for item in data:
        recruit = Recruit(
            user_id=user.id,
            id_number=item.id_number[:20],
            first_name=item.first_name[:100],
            last_name=item.last_name[:100],
            company=item.company[:100] if item.company else None,
            product=item.product[:100] if item.product else None,
            amount=item.amount,
            sign_date=item.sign_date,
        )
        db.add(recruit)
        created.append(recruit)

    await db.commit()

    results = []
    for r in created:
        await db.refresh(r)
        results.append(RecruitOut(
            id=str(r.id),
            id_number=r.id_number,
            first_name=r.first_name,
            last_name=r.last_name,
            company=r.company,
            product=r.product,
            amount=_safe_float(r.amount),
            sign_date=r.sign_date,
            created_at=r.created_at,
        ))
    return results


@router.post("/upload")
async def upload_recruits(
    file: UploadFile = File(...),
    password: str = Form(default=None),
    category: str = Form(default="financial"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload an Excel file and bulk-create recruits from parsed rows."""
    if not file.filename:
        raise HTTPException(400, "לא סופק קובץ")
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls"):
        raise HTTPException(400, "רק xlsx/xls נתמך")

    content = await file.read()
    try:
        parsed = parse_excel(content, file.filename, password)
    except Exception as e:
        raise HTTPException(400, f"שגיאה בפענוח הקובץ: {str(e)}")

    records = parsed["records"]

    # If parser returned unknown format, try direct pandas with flexible column mapping
    if parsed.get("format") == "unknown" or not records:
        try:
            import pandas as pd
            from io import BytesIO
            df = pd.read_excel(BytesIO(content))
            # Normalize column names: strip whitespace/newlines
            col_map = {}
            for c in df.columns:
                clean = str(c).replace('\n', ' ').replace('\r', ' ').strip()
                col_map[c] = clean
            df.rename(columns=col_map, inplace=True)
            cols = df.columns.tolist()

            # Find columns by partial match
            def _find_col(*keywords):
                # Prefer exact start match, then contains
                for kw in keywords:
                    for c in cols:
                        if c.startswith(kw) or c == kw:
                            return c
                for kw in keywords:
                    for c in cols:
                        if kw in c and len(c) < len(kw) + 15:
                            return c
                return None

            id_col = _find_col('ת.ז', 'תעודת זהות', 'מספר זהות')
            fname_col = _find_col('שם פרטי')
            lname_col = _find_col('שם משפחה')
            company_col = _find_col('חברה')
            product_col = _find_col('מוצר', 'סוג ביטוח')
            amount_col = _find_col('פרמיה חודשית', 'פרמיה מוערכת', 'פרמיה')
            policy_col = _find_col('מספר פוליסה')
            # Specific date keywords only — plain 'תאריך' would hit תאריך לידה etc.
            sign_date_col = _find_col('תאריך חתימה', 'תאריך הצטרפות', 'תאריך התחלה', 'תאריך הסכם', 'תאריך התחלת', 'תאריך תחילת')

            if id_col:
                records = []
                for _, row in df.iterrows():
                    rec = {"id_number": row.get(id_col)}
                    if fname_col: rec["first_name"] = row.get(fname_col)
                    if lname_col: rec["last_name"] = row.get(lname_col)
                    if company_col: rec["receiving_company"] = row.get(company_col)
                    if product_col: rec["product"] = row.get(product_col)
                    if amount_col: rec["total_premium"] = row.get(amount_col)
                    if policy_col: rec["fund_policy_number"] = row.get(policy_col)
                    if sign_date_col: rec["sign_date"] = row.get(sign_date_col)
                    records.append(rec)
        except Exception:
            pass

    if not records:
        raise HTTPException(400, "לא נמצאו רשומות בקובץ")

    # Parse sign_date once per record so we can pick the row with the LATEST date during dedup.
    # A customer may appear multiple times (one row per product signed across different months) —
    # we want the latest sign so April updates a Feb-only record for the same person.
    def _parse_sign_date(raw):
        if raw is None or str(raw).strip() in ("", "nan", "NaT", "None"):
            return None
        try:
            import pandas as pd
            ts = pd.to_datetime(raw, errors="coerce", dayfirst=True)
            if ts is not None and not pd.isna(ts):
                return ts.date()
        except Exception:
            pass
        return None

    # Group by id_number, pick record with the latest sign_date (or first if none have dates)
    best_by_id = {}
    for rec in records:
        id_number = str(rec.get("id_number") or "").strip()
        if id_number.endswith(".0"):
            id_number = id_number[:-2]
        if not id_number:
            continue
        sd = _parse_sign_date(rec.get("sign_date"))
        existing = best_by_id.get(id_number)
        if existing is None:
            best_by_id[id_number] = (rec, sd)
        else:
            _, existing_sd = existing
            if sd is not None and (existing_sd is None or sd > existing_sd):
                best_by_id[id_number] = (rec, sd)

    to_insert = []
    for id_number, (rec, parsed_sign_date) in best_by_id.items():

        first_name = str(rec.get("first_name") or "").strip()
        last_name = str(rec.get("last_name") or "").strip()
        if not first_name and not last_name:
            full = str(rec.get("full_name") or "").strip()
            if full:
                parts = full.split(None, 1)
                first_name = parts[0] if parts else ""
                last_name = parts[1] if len(parts) > 1 else ""
        if not first_name:
            first_name = "—"

        company = str(rec.get("receiving_company") or "").strip() or None
        product = str(rec.get("product") or rec.get("fund_type") or "").strip() or None
        raw_amount = rec.get("expected_amount") or rec.get("actual_amount") or rec.get("total_premium")
        try:
            amount = float(str(raw_amount).replace(',', '').replace('?', '').replace('₪', '').strip()) if raw_amount is not None else None
            if amount is not None and (amount != amount or amount == float('inf')):  # NaN/Inf check
                amount = None
        except (ValueError, TypeError):
            amount = None

        to_insert.append(Recruit(
            user_id=user.id,
            id_number=id_number[:20],
            first_name=first_name[:100],
            last_name=(last_name or "—")[:100],
            company=company[:100] if company else None,
            product=product[:100] if product else None,
            amount=amount,
            sign_date=parsed_sign_date,
            category=category,
        ))

    if not to_insert:
        raise HTTPException(400, "לא נמצאו רשומות תקינות בקובץ")

    # Delete existing recruits for this user+category before inserting
    await db.execute(delete(Recruit).where(Recruit.user_id == user.id, Recruit.category == category))

    # Batch insert without refreshing each row (saves memory + time)
    db.add_all(to_insert)
    await db.commit()

    return {"status": "ok", "count": len(to_insert), "format": parsed.get("format", "unknown")}


@router.patch("/{recruit_id}/status")
async def update_recruit_status(
    recruit_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Recruit).where(
            Recruit.id == uuid.UUID(recruit_id),
            Recruit.user_id == user.id,
        )
    )
    recruit = result.scalar_one_or_none()
    if not recruit:
        raise HTTPException(status_code=404, detail="מגויס לא נמצא")

    status = body.get("status", "")
    recruit.customer_status = status[:50] if status else None
    await db.commit()
    return {"status": "ok"}


@router.put("/{recruit_id}", response_model=RecruitOut)
async def update_recruit(
    recruit_id: str,
    data: RecruitCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Recruit).where(
            Recruit.id == uuid.UUID(recruit_id),
            Recruit.user_id == user.id,
        )
    )
    recruit = result.scalar_one_or_none()
    if not recruit:
        raise HTTPException(status_code=404, detail="מגויס לא נמצא")

    recruit.id_number = data.id_number[:20]
    recruit.first_name = data.first_name[:100]
    recruit.last_name = data.last_name[:100]
    recruit.company = data.company[:100] if data.company else None
    recruit.product = data.product[:100] if data.product else None
    recruit.amount = data.amount
    recruit.sign_date = data.sign_date

    await db.commit()
    await db.refresh(recruit)
    return RecruitOut(
        id=str(recruit.id),
        id_number=recruit.id_number,
        first_name=recruit.first_name,
        last_name=recruit.last_name,
        company=recruit.company,
        product=recruit.product,
        amount=float(recruit.amount) if recruit.amount is not None else None,
        sign_date=recruit.sign_date,
        created_at=recruit.created_at,
    )


@router.delete("/{recruit_id}")
async def delete_recruit(
    recruit_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Recruit).where(
            Recruit.id == uuid.UUID(recruit_id),
            Recruit.user_id == user.id,
        )
    )
    recruit = result.scalar_one_or_none()
    if not recruit:
        raise HTTPException(status_code=404, detail="מגויס לא נמצא")

    await db.delete(recruit)
    await db.commit()
    return {"status": "deleted"}


@router.post("/upload-compare", response_model=RecruitUploadResponse)
async def upload_and_compare(
    file: UploadFile = File(...),
    password: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload an agent tracking Excel file and compare against production."""
    if not file.filename:
        raise HTTPException(400, "לא סופק קובץ")
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls"):
        raise HTTPException(400, "רק xlsx/xls נתמך")

    content = await file.read()
    try:
        parsed = parse_excel(content, file.filename, password)
    except Exception as e:
        raise HTTPException(400, f"שגיאה בפענוח הקובץ: {str(e)}")

    recruit_records = parsed["records"]
    if not recruit_records:
        raise HTTPException(400, "לא נמצאו רשומות בקובץ")

    # Load production records
    prod_upload_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == True,
        )
    )
    prod_upload = prod_upload_result.scalar_one_or_none()
    if not prod_upload:
        raise HTTPException(404, "לא נמצא קובץ פרודוקציה פעיל. יש להעלות קובץ פרודוקציה קודם.")

    prod_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.user_id == user.id,
        )
    )
    prod_records = prod_result.scalars().all()

    # Group production by normalized id
    prod_by_id = {}
    for r in prod_records:
        if r.id_number:
            key = _normalize_id(r.id_number)
            prod_by_id.setdefault(key, []).append(r)

    # Group recruit records by normalized id
    recruit_by_id = {}
    for rec in recruit_records:
        id_num = rec.get("id_number")
        if not id_num:
            continue
        key = _normalize_id(str(id_num))
        recruit_by_id.setdefault(key, []).append(rec)

    companies_set = set()
    results = []
    total_found = 0
    total_client_only = 0
    total_not_found = 0
    total_products = 0

    for norm_id, recs in recruit_by_id.items():
        prod_recs = prod_by_id.get(norm_id, [])
        first = recs[0]
        first_name = first.get("first_name")
        last_name = first.get("last_name")

        products = []
        found_count = 0

        for rec in recs:
            total_products += 1
            company = rec.get("receiving_company") or ""
            if company:
                companies_set.add(company)

            policy = str(rec.get("fund_policy_number") or "")
            recruit_core = _extract_policy_core(policy) if policy else None

            status = "not_found"
            if prod_recs:
                # Client exists in production — check product match
                matched = False
                if recruit_core:
                    for pr in prod_recs:
                        prod_policy = str(pr.fund_policy_number or "")
                        prod_core = _extract_policy_core(prod_policy)
                        if prod_core and recruit_core and prod_core == recruit_core:
                            matched = True
                            break
                if matched:
                    status = "found"
                    found_count += 1
                else:
                    status = "client_only"
            # else: not_found (no client in production)

            sign_date_val = rec.get("sign_date")
            products.append(RecruitFileProduct(
                product=rec.get("product") or rec.get("fund_type") or None,
                company=company or None,
                policy_number=policy or None,
                expected_amount=rec.get("expected_amount"),
                actual_amount=rec.get("actual_amount"),
                sign_date=str(sign_date_val) if sign_date_val else None,
                is_active=rec.get("product_status"),
                track=rec.get("track"),
                management_fee=rec.get("management_fee"),
                status=status,
            ))

        # Determine client-level status
        if not prod_recs:
            match_status = "not_found"
            total_not_found += len(recs)
        elif found_count == len(products):
            match_status = "full_match"
            total_found += found_count
        elif found_count > 0:
            match_status = "partial_match"
            total_found += found_count
            total_client_only += len(products) - found_count
        else:
            match_status = "client_only"
            total_client_only += len(products)

        results.append(RecruitFileClient(
            id_number=norm_id,
            first_name=first_name,
            last_name=last_name,
            products=products,
            found_count=found_count,
            total_count=len(products),
            match_status=match_status,
        ))

    # Sort: not_found first, then client_only, partial, full
    status_order = {"not_found": 0, "client_only": 1, "partial_match": 2, "full_match": 3}
    results.sort(key=lambda c: status_order.get(c.match_status, 1))

    return RecruitUploadResponse(
        total_clients=len(results),
        total_products=total_products,
        found=total_found,
        client_only=total_client_only,
        not_found=total_not_found,
        companies=sorted(companies_set),
        results=results,
    )


@router.post("/compare", response_model=RecruitComparisonResponse)
async def compare_recruits(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare recruits against the active production file."""
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

    # Load production records grouped by id_number
    prod_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.user_id == user.id,
        )
    )
    prod_records = prod_result.scalars().all()

    prod_by_id = {}
    for r in prod_records:
        if r.id_number:
            prod_by_id.setdefault(_normalize_id(r.id_number), []).append(r)

    # Load recruits and group by normalized id_number (one entry per client)
    q = select(Recruit).where(Recruit.user_id == user.id)
    if category:
        q = q.where(Recruit.category == category)
    recruits_result = await db.execute(q.order_by(Recruit.created_at.desc()))
    recruits = recruits_result.scalars().all()

    # Group recruits by normalized id_number
    recruits_by_id = {}
    for recruit in recruits:
        key = _normalize_id(recruit.id_number)
        if key not in recruits_by_id:
            recruits_by_id[key] = recruit  # Keep first (most recent) for name/details

    results = []
    found_count = 0

    for norm_id, recruit in recruits_by_id.items():
        prod_recs = prod_by_id.get(norm_id, [])
        found = len(prod_recs) > 0

        if found:
            found_count += 1

        production_products = []
        total_premium = 0.0
        for r in prod_recs:
            premium = _safe_float(r.total_premium) or 0
            total_premium += premium
            production_products.append({
                "product": r.product or "",
                "product_type": r.product_type or "",
                "company": r.receiving_company or "",
                "premium": premium,
                "status": r.product_status or "",
            })

        results.append(RecruitMatchResult(
            recruit_id=str(recruit.id),
            id_number=recruit.id_number,
            first_name=recruit.first_name,
            last_name=recruit.last_name,
            company=recruit.company,
            product=recruit.product,
            amount=_safe_float(recruit.amount),
            customer_status=recruit.customer_status,
            found_in_production=found,
            production_products=production_products,
            production_premium=round(total_premium, 2),
        ))

    # Sort: not found first, then found
    results.sort(key=lambda r: (r.found_in_production, r.last_name or ""))

    # ── Compute summary stats ──
    total_premium_found = sum(r.production_premium for r in results if r.found_in_production)
    estimated_missing_premium = sum(
        r.amount for r in results if not r.found_in_production and r.amount
    )

    # Company breakdown
    company_stats = {}
    for r in results:
        comp = r.company or "לא ידוע"
        if comp not in company_stats:
            company_stats[comp] = {"company": comp, "found": 0, "not_found": 0, "premium": 0}
        if r.found_in_production:
            company_stats[comp]["found"] += 1
            company_stats[comp]["premium"] += r.production_premium
        else:
            company_stats[comp]["not_found"] += 1
    company_breakdown = sorted(company_stats.values(), key=lambda x: x["found"] + x["not_found"], reverse=True)

    # Status breakdown from production products
    status_counts = {}
    total_found_products = 0
    for r in results:
        if r.found_in_production:
            for p in r.production_products:
                total_found_products += 1
                st = p.get("status", "") or ""
                if "פעיל" in st or "active" in st.lower():
                    label = "פעיל"
                elif "מוקפא" in st or "frozen" in st.lower():
                    label = "מוקפא"
                elif "מבוטל" in st or "cancel" in st.lower():
                    label = "מבוטל"
                else:
                    label = st or "אחר"
                status_counts[label] = status_counts.get(label, 0) + 1

    active_count = status_counts.get("פעיל", 0)
    active_product_rate = (active_count / total_found_products * 100) if total_found_products > 0 else 0

    return RecruitComparisonResponse(
        total=len(recruits_by_id),
        found=found_count,
        not_found=len(recruits_by_id) - found_count,
        results=results,
        total_premium_found=round(total_premium_found, 2),
        estimated_missing_premium=round(estimated_missing_premium, 2),
        company_breakdown=company_breakdown,
        status_breakdown=status_counts,
        active_product_rate=round(active_product_rate, 1),
    )


@router.post("/compare-commission", response_model=RecruitComparisonResponse)
async def compare_recruits_commission(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    company: str | None = None,
    category: str | None = None,
):
    """Compare recruits against commission (נפרעים) files. Optional query: ?company=הפניקס"""
    filter_company = company

    # Find commission uploads, deduplicate by company_source (keep latest per company)
    comm_uploads_result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "commission",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    all_comm_uploads = comm_uploads_result.scalars().all()
    if not all_comm_uploads:
        raise HTTPException(404, "לא נמצאו קבצי נפרעים. יש להעלות קבצי נפרעים קודם.")

    # Keep only latest upload per company (by company_source, fallback to filename)
    seen_companies = set()
    all_company_names = set()  # For response tags (always full list)
    comm_uploads = []
    for u in all_comm_uploads:
        key = u.company_source or u.filename
        if key not in seen_companies:
            seen_companies.add(key)
            all_company_names.add(key)
            # If filtering by company, only include matching uploads
            if filter_company:
                if filter_company in key or key in filter_company:
                    comm_uploads.append(u)
            else:
                comm_uploads.append(u)

    if filter_company and not comm_uploads:
        raise HTTPException(404, f"לא נמצא קובץ נפרעים עבור {filter_company}")

    # Load all commission records grouped by normalized id
    # Deduplicate per client per company to avoid double-counting
    comm_by_id = {}  # norm_id -> { company -> best_record }
    for upload in comm_uploads:
        company_src = upload.company_source or upload.filename
        result = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id == upload.id,
                ClientRecord.user_id == user.id,
            )
        )
        for r in result.scalars().all():
            if r.id_number:
                norm = _normalize_id(r.id_number)
                if norm not in comm_by_id:
                    comm_by_id[norm] = {}
                # Keep all records per company (a client can have multiple products)
                comm_by_id[norm].setdefault(company_src, []).append(r)

    # Load recruits and group by normalized id_number
    q = select(Recruit).where(Recruit.user_id == user.id)
    if category:
        q = q.where(Recruit.category == category)
    recruits_result = await db.execute(q.order_by(Recruit.created_at.desc()))
    recruits = recruits_result.scalars().all()

    recruits_by_id = {}
    for recruit in recruits:
        # If filtering by company, only include recruits from that company
        if filter_company and recruit.company:
            if filter_company not in recruit.company and recruit.company not in filter_company:
                continue
        key = _normalize_id(recruit.id_number)
        if key not in recruits_by_id:
            recruits_by_id[key] = recruit

    results = []
    found_count = 0

    for norm_id, recruit in recruits_by_id.items():
        client_companies = comm_by_id.get(norm_id, {})
        # Flatten all records across companies
        comm_recs = []
        for recs in client_companies.values():
            comm_recs.extend(recs)
        found = len(comm_recs) > 0

        if found:
            found_count += 1

        commission_products = []
        total_commission = 0.0
        for r in comm_recs:
            commission = _safe_float(r.commission_before_fee) or 0
            premium = _safe_float(r.total_premium) or 0
            total_commission += commission or premium
            commission_products.append({
                "product": r.product or r.product_type or "",
                "product_type": r.product_type or "",
                "company": r.receiving_company or "",
                "premium": premium,
                "commission": commission,
                "status": r.product_status or "",
            })

        results.append(RecruitMatchResult(
            recruit_id=str(recruit.id),
            id_number=recruit.id_number,
            first_name=recruit.first_name,
            last_name=recruit.last_name,
            company=recruit.company,
            product=recruit.product,
            amount=_safe_float(recruit.amount),
            customer_status=recruit.customer_status,
            found_in_production=found,
            production_products=commission_products,
            production_premium=round(total_commission, 2),
        ))

    # Sort: not found first, then by commission company match, then by name
    comm_company_names = set(u.company_source or "" for u in comm_uploads if u.company_source)

    def _has_comm_company(r):
        if not r.company:
            return 1
        for cc in comm_company_names:
            if cc in r.company or r.company in cc:
                return 0
        return 1

    results.sort(key=lambda r: (r.found_in_production, _has_comm_company(r), r.last_name or ""))

    # Summary stats (commission comparison)
    total_premium_found = sum(r.production_premium for r in results if r.found_in_production)
    estimated_missing_premium = sum(
        r.amount for r in results if not r.found_in_production and r.amount
    )

    # Company breakdown
    company_stats = {}
    for r in results:
        comp = r.company or "לא ידוע"
        if comp not in company_stats:
            company_stats[comp] = {"company": comp, "found": 0, "not_found": 0, "premium": 0}
        if r.found_in_production:
            company_stats[comp]["found"] += 1
            company_stats[comp]["premium"] += r.production_premium
        else:
            company_stats[comp]["not_found"] += 1
    company_breakdown = sorted(company_stats.values(), key=lambda x: x["found"] + x["not_found"], reverse=True)

    # Status breakdown
    status_counts = {}
    total_found_products = 0
    for r in results:
        if r.found_in_production:
            for p in r.production_products:
                total_found_products += 1
                st = p.get("status", "") or ""
                if "פעיל" in st or "active" in st.lower():
                    label = "פעיל"
                elif "מוקפא" in st or "frozen" in st.lower():
                    label = "מוקפא"
                elif "מבוטל" in st or "cancel" in st.lower():
                    label = "מבוטל"
                else:
                    label = st or "אחר"
                status_counts[label] = status_counts.get(label, 0) + 1

    active_count = status_counts.get("פעיל", 0)
    active_product_rate = (active_count / total_found_products * 100) if total_found_products > 0 else 0

    commission_file_names = sorted(all_company_names)

    print(f"RECRUIT-COMM DEBUG: filter={filter_company} uploads={len(comm_uploads)} recruits={len(recruits_by_id)} found={found_count} not_found={len(recruits_by_id)-found_count} companies={commission_file_names}", flush=True)

    return RecruitComparisonResponse(
        total=len(recruits_by_id),
        found=found_count,
        not_found=len(recruits_by_id) - found_count,
        results=results,
        total_premium_found=round(total_premium_found, 2),
        estimated_missing_premium=round(estimated_missing_premium, 2),
        company_breakdown=company_breakdown,
        status_breakdown=status_counts,
        active_product_rate=round(active_product_rate, 1),
        commission_files=commission_file_names,
    )
