import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portal_link import CustomerPortalLink
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.services.auth_service import hash_password, verify_password


def generate_token() -> str:
    return secrets.token_urlsafe(48)


async def create_portal_link(
    db: AsyncSession,
    user_id: uuid.UUID,
    customer_id_number: str,
    customer_name: str,
    password: str,
    expires_days: int = 30,
    customer_email: str | None = None,
) -> CustomerPortalLink:
    token = generate_token()
    link = CustomerPortalLink(
        user_id=user_id,
        token=token,
        customer_id_number=customer_id_number,
        customer_name=customer_name,
        customer_email=customer_email,
        password_hash=hash_password(password),
        expires_at=datetime.utcnow() + timedelta(days=expires_days),
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def get_agent_links(db: AsyncSession, user_id: uuid.UUID) -> list[CustomerPortalLink]:
    result = await db.execute(
        select(CustomerPortalLink)
        .where(CustomerPortalLink.user_id == user_id)
        .order_by(CustomerPortalLink.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_link(db: AsyncSession, user_id: uuid.UUID, token: str) -> bool:
    result = await db.execute(
        select(CustomerPortalLink).where(
            CustomerPortalLink.token == token,
            CustomerPortalLink.user_id == user_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        return False
    link.is_active = False
    await db.commit()
    return True


async def verify_portal_access(db: AsyncSession, token: str, password: str) -> CustomerPortalLink | None:
    """Verify password for a portal link. Returns the link if valid, None otherwise."""
    result = await db.execute(
        select(CustomerPortalLink).where(CustomerPortalLink.token == token)
    )
    link = result.scalar_one_or_none()
    if not link:
        return None

    # Check active and not expired
    if not link.is_active or link.expires_at < datetime.utcnow():
        return None

    # Rate limiting: 5 failed attempts in 15 minutes
    if link.failed_attempts >= 5 and link.last_failed_at:
        lockout_until = link.last_failed_at + timedelta(minutes=15)
        if datetime.utcnow() < lockout_until:
            return None
        # Reset after lockout period
        link.failed_attempts = 0

    if not verify_password(password, link.password_hash):
        link.failed_attempts += 1
        link.last_failed_at = datetime.utcnow()
        await db.commit()
        return None

    # Success — reset failures, update last accessed
    link.failed_attempts = 0
    link.last_failed_at = None
    link.last_accessed_at = datetime.utcnow()
    await db.commit()
    return link


async def get_portal_dashboard(db: AsyncSession, user_id: uuid.UUID, id_number: str) -> dict | None:
    """Get dashboard data for a customer from the active production file."""
    # Find active production upload
    prod_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,
        )
    )
    prod_upload = prod_result.scalar_one_or_none()
    if not prod_upload:
        return None

    # Get customer records
    records_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.user_id == user_id,
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.id_number == id_number,
        )
    )
    records = list(records_result.scalars().all())
    if not records:
        return None

    # Build products list
    products = []
    for r in records:
        products.append({
            "product": r.product,
            "product_type": r.product_type,
            "receiving_company": r.receiving_company,
            "total_premium": float(r.total_premium) if r.total_premium else None,
            "accumulation": float(r.accumulation) if r.accumulation else None,
            "product_status": r.product_status,
            "sign_date": r.sign_date.isoformat() if r.sign_date else None,
            "fund_policy_number": r.fund_policy_number,
            "track": r.track,
        })

    # KPIs
    total_premium = sum(float(r.total_premium or 0) for r in records)
    total_accumulation = sum(float(r.accumulation or 0) for r in records)
    companies = set(r.receiving_company for r in records if r.receiving_company)

    # Company breakdown
    company_map: dict[str, dict] = {}
    for r in records:
        co = r.receiving_company or "אחר"
        if co not in company_map:
            company_map[co] = {"company": co, "premium": 0.0, "count": 0}
        company_map[co]["premium"] += float(r.total_premium or 0)
        company_map[co]["count"] += 1

    # Customer name from first record
    customer_name = ""
    for r in records:
        parts = [r.first_name or "", r.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        if name:
            customer_name = name
            break

    # Extract period from production filename (e.g. "דוח פרודוקציה דצמבר 25.xlsx")
    period_label = _extract_period(prod_upload.filename)

    return {
        "customer_name": customer_name or id_number,
        "id_number": id_number,
        "period": period_label,
        "products": products,
        "kpi": {
            "product_count": len(records),
            "total_premium": round(total_premium, 2),
            "total_accumulation": round(total_accumulation, 2),
            "company_count": len(companies),
        },
        "company_breakdown": sorted(company_map.values(), key=lambda x: x["premium"], reverse=True),
    }


def _extract_period(filename: str) -> str:
    """Extract Hebrew month + year from production filename."""
    import re
    months = [
        "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
        "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
    ]
    if not filename:
        return ""
    # Match Hebrew month name
    for month in months:
        if month in filename:
            # Look for year number (2 or 4 digits) near the month
            year_match = re.search(r'(\d{2,4})', filename)
            if year_match:
                year = year_match.group(1)
                if len(year) == 2:
                    year = "20" + year
                return f"{month} {year}"
            return month
    return ""
