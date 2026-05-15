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
    # Get all commission rates for this user — collapse to company-level by
    # keeping the row without a `product` (the legacy "default" rate). This
    # function predates per-product rates and is only used by older formats;
    # the new percent-vs-percent path is `apply_rate_deviation`.
    rates_q = select(CommissionRate).where(
        CommissionRate.user_id == user_id,
        CommissionRate.product.is_(None),
    )
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


# Tolerance for percent-to-percent comparison (in absolute percentage points).
# Real agreements quote rates to one decimal place (e.g. 19.2%, 0.32%). For
# high rates (life/health/risk: 15–30%) anything under 0.1pp is rounding
# noise. For low rates (gemel/financial: 0.2–0.5%) 0.1pp is huge — 31% in
# relative terms — so we tighten to 0.05pp. Otherwise a 0.32% → 0.24%
# underpayment (8/100 of a point, but a 25% cut in real money) would slip
# past as a "match".
_RATE_TOLERANCE_PP_HIGH = 0.1
_RATE_TOLERANCE_PP_LOW = 0.05
_LOW_RATE_THRESHOLD_PCT = 2.0


def _tolerance_for(rate_pct: float) -> float:
    return _RATE_TOLERANCE_PP_LOW if rate_pct < _LOW_RATE_THRESHOLD_PCT else _RATE_TOLERANCE_PP_HIGH


def _norm(s: str | None) -> str:
    """Lowercase + strip leading definite article + strip whitespace —
    used so 'הכשרה' matches 'הכשרה ביטוח' and lookups don't fail on casing
    or company-name suffix differences between agreement and report."""
    if not s:
        return ""
    return s.strip().lstrip("ה").lower()


def _significant_tokens(s: str) -> set[str]:
    """Tokenize a product name into significant words (length >= 3),
    stripping punctuation and quote marks. Used for fuzzy matching between
    agreement-side product names ('מוצרי ריסק') and report-side ones
    ('ריסק פרט'): the common token 'ריסק' makes the pair a match."""
    if not s:
        return set()
    cleaned = (
        s.replace('"', " ").replace("'", " ").replace("-", " ")
         .replace("/", " ").replace("(", " ").replace(")", " ")
    )
    return {t for t in cleaned.split() if len(t) >= 3}


def _product_match(report_prod: str, agreement_prod: str) -> bool:
    """Decide whether a report product name refers to the same product as
    an agreement product name. Loose by design — agreement and report use
    different vocabularies for the same product."""
    if not report_prod or not agreement_prod:
        return False
    if report_prod == agreement_prod:
        return True
    if report_prod in agreement_prod or agreement_prod in report_prod:
        return True
    return bool(_significant_tokens(report_prod) & _significant_tokens(agreement_prod))


def _candidate_covers(cand: dict, policy_date) -> bool:
    """Does this rate's validity window contain the policy's sign date?
    A NULL bound is treated as open-ended on that side, so a rate with only
    effective_from set still covers everything from that date onward."""
    if policy_date is None:
        return False
    ef = cand.get("from")
    et = cand.get("to")
    if ef is not None and policy_date < ef:
        return False
    if et is not None and policy_date > et:
        return False
    return True


def _pick_best(candidates: list[dict], reported_pct: float, policy_date) -> float | None:
    """Year-aware candidate picker.

    1. Prefer candidates whose validity window contains the policy sign
       date — that's the rate the agent actually agreed to for THAT policy.
    2. Among those, prefer the one with the most recent effective_from
       (newer revision wins ties).
    3. If no window matches (e.g. policy older than any uploaded agreement,
       or the policy has no sign_date), fall back to the candidate closest
       to the reported pct — old behaviour, preserves prior test results.
    """
    if not candidates:
        return None
    if policy_date is not None:
        in_window = [c for c in candidates if _candidate_covers(c, policy_date)]
        if in_window:
            # Latest effective_from wins; NULL from sorts first (least specific).
            in_window.sort(key=lambda c: (c.get("from") or _ZERO_DATE), reverse=True)
            return in_window[0]["pct"]
    # No year context (or no covering rate) — fall back to nearest match.
    return min(candidates, key=lambda c: abs(c["pct"] - reported_pct))["pct"]


_ZERO_DATE = __import__("datetime").date.min


async def apply_rate_deviation(db: AsyncSession, user_id: uuid.UUID, upload_id: uuid.UUID):
    """Compare each record's reported_commission_pct (from the company's
    נפרעים report) against the agreement's per-product rate, and tag the
    record's reconciliation_status accordingly.

    Driven by the QA spec: "צריך להתאים את אחוזי הנפרעים בהסכם לעמודה
    שנקראת אחוז עמלה בדוח נפרעים — המערכת תזהה סטייה בעמלה."

    Status outcomes for a record with reported_commission_pct set:
    - paid_match    — agreement found and |reported - agreement| < tolerance
    - paid_mismatch — agreement found and delta >= tolerance (real deviation
                      OR an old-year policy still paid at last year's rate)
    - no_data       — no agreement on file for (company, product)

    Year-aware: when the agreement carries validity dates and the policy has
    a sign_date, we prefer the rate whose window contains that date. Without
    this, a 2018 policy paid at the 2018 rate would silently match the 2025
    agreement (wrong) or look like a deviation against the wrong year.
    """
    # by_company: {co_key -> {prod_key -> [candidate, ...]}}
    # company_default: {co_key -> [candidate, ...]}   (rows with product=NULL)
    # Each candidate is {"pct": float, "from": date|None, "to": date|None}.
    rates_q = select(CommissionRate).where(CommissionRate.user_id == user_id)
    rates_all = (await db.execute(rates_q)).scalars().all()

    by_company: dict[str, dict[str, list[dict]]] = {}
    company_default: dict[str, list[dict]] = {}
    for r in rates_all:
        co_key = _norm(r.company_name)
        cand = {
            "pct": float(r.rate) * 100.0,
            "from": r.effective_from,
            "to": r.effective_to,
        }
        if r.product:
            by_company.setdefault(co_key, {}).setdefault(_norm(r.product), []).append(cand)
        else:
            company_default.setdefault(co_key, []).append(cand)

    records_q = (
        select(ClientRecord)
        .where(
            and_(
                ClientRecord.upload_id == upload_id,
                ClientRecord.reported_commission_pct.isnot(None),
            )
        )
    )
    records = (await db.execute(records_q)).scalars().all()

    for record in records:
        co = _norm(record.receiving_company)
        prod = _norm(record.product)
        policy_date = record.sign_date
        if not co:
            continue

        reported = float(record.reported_commission_pct)
        agreement_pct: float | None = None

        # Tier 1: matching company + product (exact or token-fuzzy).
        if prod:
            candidates: list[dict] = []
            for r_co_key, products in by_company.items():
                if not (co in r_co_key or r_co_key in co):
                    continue
                if prod in products:
                    candidates.extend(products[prod])
                for r_prod_key, r_cands in products.items():
                    if r_prod_key and r_prod_key != prod and _product_match(prod, r_prod_key):
                        candidates.extend(r_cands)
            if candidates:
                agreement_pct = _pick_best(candidates, reported, policy_date)

        # Tier 2: company-level default rate (product IS NULL).
        if agreement_pct is None:
            for r_co_key, defaults in company_default.items():
                if co in r_co_key or r_co_key in co:
                    agreement_pct = _pick_best(defaults, reported, policy_date)
                    if agreement_pct is not None:
                        break

        # Tier 3: any rate the company has on file. Bias toward HIGHEST so
        # underpayments surface, per QA spec "alert if paid less".
        if agreement_pct is None:
            company_rates: list[dict] = []
            for r_co_key, products in by_company.items():
                if co in r_co_key or r_co_key in co:
                    for cs in products.values():
                        company_rates.extend(cs)
            for r_co_key, defaults in company_default.items():
                if co in r_co_key or r_co_key in co:
                    company_rates.extend(defaults)
            if company_rates:
                # Window match first, then fall back to max rate.
                in_window = [c for c in company_rates if _candidate_covers(c, policy_date)]
                pool = in_window or company_rates
                agreement_pct = max(c["pct"] for c in pool)

        if agreement_pct is None:
            record.reconciliation_status = "no_data"
            continue

        # Tolerance scales by the AGREEMENT rate (the expected value), not the
        # reported one — otherwise a near-zero reported value would always
        # match under the tighter low-rate tolerance.
        if abs(reported - agreement_pct) < _tolerance_for(agreement_pct):
            record.reconciliation_status = "paid_match"
        else:
            record.reconciliation_status = "paid_mismatch"

    await db.flush()
