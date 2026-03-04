import uuid

from sqlalchemy import select, func, or_, and_, case, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record import ClientRecord
from app.models.commission_rate import CommissionRate


async def get_records_page(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
    search: str | None = None,
    company: str | None = None,
    status: str | None = None,
    product: str | None = None,
    upload_id: str | None = None,
    sort_by: str = "last_name",
    sort_dir: str = "asc",
) -> dict:
    query = select(ClientRecord).where(ClientRecord.user_id == user_id)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                ClientRecord.first_name.ilike(pattern),
                ClientRecord.last_name.ilike(pattern),
                ClientRecord.id_number.ilike(pattern),
            )
        )
    if company:
        query = query.where(ClientRecord.receiving_company.ilike(f"%{company}%"))
    if status:
        query = query.where(ClientRecord.reconciliation_status == status)
    if product:
        query = query.where(ClientRecord.product.ilike(f"%{product}%"))
    if upload_id:
        query = query.where(ClientRecord.upload_id == uuid.UUID(upload_id))

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sort
    sort_col = getattr(ClientRecord, sort_by, ClientRecord.last_name)
    if sort_dir == "desc":
        sort_col = sort_col.desc()
    query = query.order_by(sort_col)

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


async def get_status_summary(db: AsyncSession, user_id: uuid.UUID, upload_id: str | None = None) -> dict:
    base = select(ClientRecord).where(ClientRecord.user_id == user_id)
    if upload_id:
        base = base.where(ClientRecord.upload_id == uuid.UUID(upload_id))

    # Status counts
    status_q = (
        select(ClientRecord.reconciliation_status, func.count())
        .where(ClientRecord.user_id == user_id)
        .group_by(ClientRecord.reconciliation_status)
    )
    if upload_id:
        status_q = status_q.where(ClientRecord.upload_id == uuid.UUID(upload_id))

    result = await db.execute(status_q)
    counts = {row[0]: row[1] for row in result.all()}

    # Totals
    totals_q = (
        select(
            func.coalesce(func.sum(ClientRecord.expected_amount), 0),
            func.coalesce(func.sum(ClientRecord.actual_amount), 0),
            func.coalesce(func.sum(ClientRecord.amount_difference), 0),
        )
        .where(ClientRecord.user_id == user_id)
    )
    if upload_id:
        totals_q = totals_q.where(ClientRecord.upload_id == uuid.UUID(upload_id))

    totals = (await db.execute(totals_q)).one()

    total_records = sum(counts.values())

    return {
        "paid_match": counts.get("paid_match", 0),
        "paid_mismatch": counts.get("paid_mismatch", 0),
        "unpaid": counts.get("unpaid", 0),
        "cancelled": counts.get("cancelled", 0),
        "no_data": counts.get("no_data", 0),
        "matched": counts.get("matched", 0),
        "missing_from_report": counts.get("missing_from_report", 0),
        "extra_in_report": counts.get("extra_in_report", 0),
        "total": total_records,
        "total_expected": float(totals[0]),
        "total_actual": float(totals[1]),
        "total_difference": float(totals[2]),
    }


async def get_client_records(db: AsyncSession, user_id: uuid.UUID, id_number: str) -> list:
    query = (
        select(ClientRecord)
        .where(and_(ClientRecord.user_id == user_id, ClientRecord.id_number == id_number))
        .order_by(ClientRecord.sign_date.desc().nullslast())
    )
    result = await db.execute(query)
    return result.scalars().all()


STATUS_LABELS = {
    "paid_match": "שולם - תואם",
    "paid_mismatch": "שולם - חריגה",
    "unpaid": "לא שולם",
    "cancelled": "בוטל",
    "no_data": "אין נתונים",
    "matched": "נמצא בשני הקבצים",
    "missing_from_report": "חסר בדוח חברה",
    "extra_in_report": "חסר בקובץ סוכן",
}


async def get_analytics(db: AsyncSession, user_id: uuid.UUID, upload_id: str | None = None) -> dict:
    base_filter = [ClientRecord.user_id == user_id]
    if upload_id:
        base_filter.append(ClientRecord.upload_id == uuid.UUID(upload_id))

    # Unified amount expressions that work for both file formats:
    # Agent tracking: expected_amount / actual_amount / amount_difference
    # Company report: balance / commission_paid (no expected/actual)
    amt_main = func.coalesce(ClientRecord.expected_amount, ClientRecord.balance)
    amt_secondary = func.coalesce(ClientRecord.actual_amount, ClientRecord.commission_paid)
    amt_diff = func.coalesce(
        ClientRecord.amount_difference,
        ClientRecord.commission_paid - ClientRecord.commission_expected,
    )

    # 1. Status distribution
    status_q = (
        select(
            ClientRecord.reconciliation_status,
            func.count().label("cnt"),
            func.coalesce(func.sum(amt_main), 0).label("total_amt"),
        )
        .where(*base_filter)
        .group_by(ClientRecord.reconciliation_status)
    )
    status_rows = (await db.execute(status_q)).all()
    status_distribution = [
        {
            "status": row[0] or "no_data",
            "status_label": STATUS_LABELS.get(row[0] or "no_data", row[0] or "אין נתונים"),
            "count": row[1],
            "total_amount": float(row[2]),
        }
        for row in status_rows
    ]

    # 2. Company breakdown
    company_q = (
        select(
            ClientRecord.receiving_company,
            func.count().label("cnt"),
            func.coalesce(func.sum(amt_main), 0),
            func.coalesce(func.sum(amt_secondary), 0),
            func.coalesce(func.sum(amt_diff), 0),
        )
        .where(*base_filter)
        .where(ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(func.count().desc())
        .limit(15)
    )
    company_rows = (await db.execute(company_q)).all()
    company_breakdown = [
        {
            "company": row[0],
            "count": row[1],
            "total_expected": float(row[2]),
            "total_actual": float(row[3]),
            "difference": float(row[4]),
        }
        for row in company_rows
    ]

    # 3. Product breakdown — top 10 by total amount
    product_q = (
        select(
            ClientRecord.product,
            func.count().label("cnt"),
            func.coalesce(func.sum(amt_main), 0).label("total_amt"),
        )
        .where(*base_filter)
        .where(ClientRecord.product.isnot(None))
        .group_by(ClientRecord.product)
        .order_by(func.coalesce(func.sum(amt_main), 0).desc())
        .limit(10)
    )
    product_rows = (await db.execute(product_q)).all()
    product_breakdown = [
        {
            "product": row[0],
            "count": row[1],
            "total_amount": float(row[2]),
        }
        for row in product_rows
    ]

    # 4. Top records — biggest balances/amounts (works for both formats)
    # For agent tracking: show biggest amount_difference
    # For company reports: show biggest balance
    mismatch_q = (
        select(
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.id_number,
            amt_main.label("expected"),
            amt_secondary.label("actual"),
            amt_main.label("sort_val"),
        )
        .where(*base_filter)
        .where(amt_main.isnot(None))
        .order_by(amt_main.desc())
        .limit(10)
    )
    mismatch_rows = (await db.execute(mismatch_q)).all()
    top_mismatches = [
        {
            "first_name": row[0],
            "last_name": row[1],
            "id_number": row[2],
            "expected": float(row[3]) if row[3] is not None else None,
            "actual": float(row[4]) if row[4] is not None else None,
            "difference": float(row[3] - row[4]) if row[3] is not None and row[4] is not None else 0,
        }
        for row in mismatch_rows
    ]

    return {
        "status_distribution": status_distribution,
        "company_breakdown": company_breakdown,
        "product_breakdown": product_breakdown,
        "top_mismatches": top_mismatches,
    }


async def cross_reference_uploads(db: AsyncSession, user_id: uuid.UUID):
    """Cross-reference records between agent tracking and company report files.

    Agent tracking records have expected_amount (non-null).
    Company report records have balance (non-null).
    Matching is done by id_number (ת.ז).
    """
    # 1. Get distinct id_numbers from agent tracking records (have expected_amount)
    agent_q = (
        select(ClientRecord.id_number)
        .where(
            and_(
                ClientRecord.user_id == user_id,
                ClientRecord.expected_amount.isnot(None),
                ClientRecord.id_number.isnot(None),
                ClientRecord.id_number != "",
            )
        )
        .distinct()
    )
    agent_result = await db.execute(agent_q)
    agent_ids = {row[0] for row in agent_result.all()}

    # 2. Get distinct id_numbers from company report records (have balance)
    company_q = (
        select(ClientRecord.id_number)
        .where(
            and_(
                ClientRecord.user_id == user_id,
                ClientRecord.balance.isnot(None),
                ClientRecord.id_number.isnot(None),
                ClientRecord.id_number != "",
            )
        )
        .distinct()
    )
    company_result = await db.execute(company_q)
    company_ids = {row[0] for row in company_result.all()}

    # If only one file type exists, no cross-reference possible
    if not agent_ids or not company_ids:
        return

    # 3. Compute sets
    matched_ids = agent_ids & company_ids
    only_agent_ids = agent_ids - company_ids
    only_company_ids = company_ids - agent_ids

    # 4. Bulk update statuses (skip cancelled records)
    if matched_ids:
        matched_list = list(matched_ids)
        # Agent records that matched
        await db.execute(
            update(ClientRecord)
            .where(
                and_(
                    ClientRecord.user_id == user_id,
                    ClientRecord.expected_amount.isnot(None),
                    ClientRecord.id_number.in_(matched_list),
                    ClientRecord.reconciliation_status != "cancelled",
                )
            )
            .values(reconciliation_status="matched")
        )
        # Company records that matched
        await db.execute(
            update(ClientRecord)
            .where(
                and_(
                    ClientRecord.user_id == user_id,
                    ClientRecord.balance.isnot(None),
                    ClientRecord.id_number.in_(matched_list),
                    ClientRecord.reconciliation_status != "cancelled",
                )
            )
            .values(reconciliation_status="matched")
        )

    if only_agent_ids:
        await db.execute(
            update(ClientRecord)
            .where(
                and_(
                    ClientRecord.user_id == user_id,
                    ClientRecord.expected_amount.isnot(None),
                    ClientRecord.id_number.in_(list(only_agent_ids)),
                    ClientRecord.reconciliation_status != "cancelled",
                )
            )
            .values(reconciliation_status="missing_from_report")
        )

    if only_company_ids:
        await db.execute(
            update(ClientRecord)
            .where(
                and_(
                    ClientRecord.user_id == user_id,
                    ClientRecord.balance.isnot(None),
                    ClientRecord.id_number.in_(list(only_company_ids)),
                    ClientRecord.reconciliation_status != "cancelled",
                )
            )
            .values(reconciliation_status="extra_in_report")
        )

    # 5. For matched agent records: copy commission totals from company records
    if matched_ids:
        # Get aggregated commission data per id_number from company records
        commission_q = (
            select(
                ClientRecord.id_number,
                func.sum(ClientRecord.balance),
                func.sum(ClientRecord.commission_paid),
            )
            .where(
                and_(
                    ClientRecord.user_id == user_id,
                    ClientRecord.balance.isnot(None),
                    ClientRecord.id_number.in_(list(matched_ids)),
                )
            )
            .group_by(ClientRecord.id_number)
        )
        comm_result = await db.execute(commission_q)
        commission_data = {row[0]: (row[1], row[2]) for row in comm_result.all()}

        # Update matched agent records with commission info and determine paid status
        agent_records_q = (
            select(ClientRecord)
            .where(
                and_(
                    ClientRecord.user_id == user_id,
                    ClientRecord.expected_amount.isnot(None),
                    ClientRecord.id_number.in_(list(matched_ids)),
                    ClientRecord.reconciliation_status != "cancelled",
                )
            )
        )
        agent_records_result = await db.execute(agent_records_q)
        for record in agent_records_result.scalars().all():
            comm = commission_data.get(record.id_number)
            if comm:
                total_balance, total_paid = comm
                if total_paid is not None:
                    record.commission_paid = float(total_paid)
                if total_balance is not None:
                    record.balance = float(total_balance)
                # Determine paid match/mismatch
                if record.expected_amount is not None and total_paid is not None:
                    if abs(float(record.expected_amount) - float(total_paid)) < 1.0:
                        record.reconciliation_status = "paid_match"
                    else:
                        record.reconciliation_status = "paid_mismatch"

    await db.flush()


async def apply_commission_rates(db: AsyncSession, user_id: uuid.UUID, upload_id: uuid.UUID):
    """Apply commission rates from the rate table to company report records."""
    # Get all commission rates for this user
    rates_q = select(CommissionRate).where(CommissionRate.user_id == user_id)
    rates_result = await db.execute(rates_q)
    rates = {r.company_name: float(r.rate) for r in rates_result.scalars().all()}

    if not rates:
        return

    # Get records from this upload that have a balance but no commission_expected
    records_q = (
        select(ClientRecord)
        .where(
            and_(
                ClientRecord.upload_id == upload_id,
                ClientRecord.balance.isnot(None),
            )
        )
    )
    result = await db.execute(records_q)
    records = result.scalars().all()

    for record in records:
        # Try to match company by partial name
        matched_rate = None
        company = record.receiving_company or ""
        for rate_company, rate_val in rates.items():
            if rate_company in company or company in rate_company:
                matched_rate = rate_val
                break

        if matched_rate and record.balance:
            record.commission_expected = float(record.balance) * matched_rate
            # Re-determine status
            if record.commission_paid is not None:
                if abs(float(record.commission_paid) - record.commission_expected) < 1.0:
                    record.reconciliation_status = "paid_match"
                else:
                    record.reconciliation_status = "paid_mismatch"

    await db.flush()
