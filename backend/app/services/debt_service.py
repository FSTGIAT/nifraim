import uuid
import logging
from datetime import datetime

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.debt import Debt
from app.models.commission_rate import CommissionRate

logger = logging.getLogger(__name__)


def _calc_expected_commission(product: dict, rate: float, category: str) -> float:
    """Calculate expected commission for a product given its rate and category."""
    if category == "insurance":
        premium = float(product.get("premium") or product.get("total_premium") or 0)
        if premium > 0:
            return premium * rate * 100
    else:
        # Gemel/hishtalmut: accumulation * rate / 12
        accum = float(product.get("accumulation") or product.get("balance") or 0)
        if accum > 0:
            return accum * rate / 12
    return 0


def _find_rate(rates: list, company_name: str) -> float | None:
    """Find the commission rate for a given company name."""
    if not company_name or not rates:
        return None

    company_lower = company_name.lower()
    # Strip Hebrew ה prefix for matching
    company_stripped = company_lower.lstrip("ה")

    for r in rates:
        r_lower = r.company_name.lower()
        r_stripped = r_lower.lstrip("ה")
        if (company_lower in r_lower or r_lower in company_lower or
            company_stripped in r_stripped or r_stripped in company_stripped):
            return float(r.rate)
    return None


async def sync_debts(
    db: AsyncSession,
    user_id: uuid.UUID,
    comparison_result: dict,
    production_upload_id: uuid.UUID,
    commission_upload_id: uuid.UUID | None = None,
    category: str = "gemel_hishtalmut",
) -> int:
    """Sync debts from a comparison result into the debts table.

    - Creates new debts for only_production items
    - Resolves existing debts that are now matched
    Returns number of debts created/updated.
    """
    # Load commission rates
    rates_q = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user_id)
    )
    rates = rates_q.scalars().all()

    commission_companies = comparison_result.get("commission_company_sources") or []
    if not commission_companies:
        src = comparison_result.get("commission_company_source")
        if src:
            commission_companies = [src]

    customers = comparison_result.get("customers", [])
    created = 0
    resolved = 0

    for customer in customers:
        cid = customer.get("id_number")
        if not cid:
            continue

        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "—"

        if customer.get("match_status") == "only_production":
            # These are unpaid — create debt entries
            products = customer.get("production_products", [])
            for prod in products:
                prod_company = prod.get("company") or prod.get("company_full") or ""
                if not prod_company:
                    continue

                rate = _find_rate(rates, prod_company)
                expected = _calc_expected_commission(prod, rate, category) if rate else 0

                # Check if debt already exists
                existing = await db.execute(
                    select(Debt).where(
                        Debt.user_id == user_id,
                        Debt.customer_id_number == cid,
                        Debt.policy_number == (prod.get("policy_number") or prod.get("fund_policy_number")),
                        Debt.company_name == prod_company,
                        Debt.status == "open",
                    )
                )
                if existing.scalar_one_or_none():
                    continue  # Already tracked

                debt = Debt(
                    user_id=user_id,
                    company_name=prod_company,
                    category=category,
                    customer_id_number=cid,
                    customer_name=name,
                    product=prod.get("product") or prod.get("product_type") or "—",
                    policy_number=prod.get("policy_number") or prod.get("fund_policy_number"),
                    expected_amount=round(expected, 2),
                    premium=float(prod.get("premium") or prod.get("total_premium") or 0) or None,
                    accumulation=float(prod.get("accumulation") or 0) or None,
                    status="open",
                    production_upload_id=production_upload_id,
                    commission_upload_id=commission_upload_id,
                )
                db.add(debt)
                created += 1

        elif customer.get("match_status") == "matched":
            # Auto-resolve open debts for matched customers
            matched_policies = set()
            pm = customer.get("product_matches", {})
            for m in pm.get("matched", []):
                pn = m.get("production", {}).get("policy_number") or m.get("production", {}).get("fund_policy_number")
                if pn:
                    matched_policies.add(pn)

            if matched_policies:
                open_debts = await db.execute(
                    select(Debt).where(
                        Debt.user_id == user_id,
                        Debt.customer_id_number == cid,
                        Debt.status == "open",
                        Debt.policy_number.in_(matched_policies),
                    )
                )
                for d in open_debts.scalars().all():
                    d.status = "paid"
                    d.status_changed_at = datetime.utcnow()
                    resolved += 1

    await db.commit()
    logger.info(f"Debt sync: created={created}, resolved={resolved} for user {user_id}")
    return created


async def get_debts_summary(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Get aggregated debt summary."""
    # Total by status
    status_q = await db.execute(
        select(
            Debt.status,
            func.count().label("count"),
            func.coalesce(func.sum(Debt.expected_amount), 0).label("total"),
        )
        .where(Debt.user_id == user_id)
        .group_by(Debt.status)
    )
    status_rows = status_q.all()

    total_count = sum(r.count for r in status_rows)
    total_amount = sum(float(r.total) for r in status_rows)
    open_count = 0
    open_amount = 0
    paid_count = 0
    paid_amount = 0
    for r in status_rows:
        if r.status == "open":
            open_count = r.count
            open_amount = float(r.total)
        elif r.status == "paid":
            paid_count = r.count
            paid_amount = float(r.total)

    # By company
    company_q = await db.execute(
        select(
            Debt.company_name,
            Debt.category,
            func.count().label("count"),
            func.coalesce(func.sum(Debt.expected_amount), 0).label("total"),
        )
        .where(Debt.user_id == user_id, Debt.status == "open")
        .group_by(Debt.company_name, Debt.category)
        .order_by(func.coalesce(func.sum(Debt.expected_amount), 0).desc())
    )
    companies = [
        {
            "company": r.company_name,
            "category": r.category,
            "count": r.count,
            "total": float(r.total),
        }
        for r in company_q.all()
    ]

    unique_companies = len({c["company"] for c in companies})

    return {
        "total_count": total_count,
        "total_amount": round(total_amount, 2),
        "open_count": open_count,
        "open_amount": round(open_amount, 2),
        "paid_count": paid_count,
        "paid_amount": round(paid_amount, 2),
        "unique_companies": unique_companies,
        "companies": companies,
    }
