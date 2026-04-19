import re
import uuid
import logging
from datetime import datetime

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.production_summary import ProductionSummary

logger = logging.getLogger(__name__)

# Hebrew month names for filename parsing
HEBREW_MONTHS = {
    "ינואר": "01", "פברואר": "02", "מרץ": "03", "מרס": "03",
    "אפריל": "04", "מאי": "05", "יוני": "06",
    "יולי": "07", "אוגוסט": "08", "ספטמבר": "09",
    "אוקטובר": "10", "נובמבר": "11", "דצמבר": "12",
}


def _extract_period_label(filename: str, uploaded_at: datetime) -> str:
    """Extract period label like '2026-03' from filename or fallback to upload date."""
    name = filename.lower().replace(".xlsx", "").replace(".xls", "")

    # Try YYYY-MM or MM-YYYY patterns
    m = re.search(r"(\d{4})[_\-\s.](\d{1,2})", name)
    if m:
        year, month = m.group(1), m.group(2).zfill(2)
        if 1 <= int(month) <= 12:
            return f"{year}-{month}"

    m = re.search(r"(\d{1,2})[_\-\s.](\d{4})", name)
    if m:
        month, year = m.group(1).zfill(2), m.group(2)
        if 1 <= int(month) <= 12:
            return f"{year}-{month}"

    # Try Hebrew month names
    for heb, num in HEBREW_MONTHS.items():
        if heb in name:
            # Look for a year nearby
            y = re.search(r"(\d{2,4})", name)
            if y:
                year = y.group(1)
                if len(year) == 2:
                    year = "20" + year
                return f"{year}-{num}"

    # Fallback to upload date
    return uploaded_at.strftime("%Y-%m")


async def compute_production_summary(
    db: AsyncSession, user_id: uuid.UUID, upload_id: uuid.UUID
) -> ProductionSummary | None:
    """Compute and persist a production summary for the given upload."""
    # Check if summary already exists
    existing = await db.execute(
        select(ProductionSummary).where(ProductionSummary.upload_id == upload_id)
    )
    if existing.scalar_one_or_none():
        return None

    # Get upload metadata
    upload_result = await db.execute(
        select(FileUpload).where(FileUpload.id == upload_id)
    )
    upload = upload_result.scalar_one_or_none()
    if not upload:
        return None

    uid = upload_id

    # Totals
    totals = await db.execute(
        select(
            func.count().label("cnt"),
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("total_premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("total_accumulation"),
        ).where(ClientRecord.upload_id == uid)
    )
    t = totals.one()

    # Company breakdown
    company_q = await db.execute(
        select(
            ClientRecord.receiving_company,
            func.count().label("products"),
            func.count(func.distinct(ClientRecord.id_number)).label("clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
    )
    companies = [
        {
            "company": r[0], "products": r[1], "clients": r[2],
            "premium": float(r[3]), "accumulation": float(r[4]),
        }
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
    product_types = [
        {"product_type": r[0], "count": r[1], "premium": float(r[2])}
        for r in product_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Top 5 clients by accumulation
    top_q = await db.execute(
        select(
            ClientRecord.id_number,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
        .limit(5)
    )
    top_clients = [
        {
            "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
            "id_number": r.id_number,
            "premium": float(r.premium),
            "accumulation": float(r.accumulation),
        }
        for r in top_q.all() if float(r.accumulation) > 0
    ]

    # Compute month-over-month changes
    changes = await _compute_changes(db, user_id, upload_id, t)

    period_label = _extract_period_label(upload.filename, upload.uploaded_at)

    summary = ProductionSummary(
        user_id=user_id,
        upload_id=upload_id,
        period_label=period_label,
        upload_date=upload.uploaded_at,
        total_records=t.cnt,
        unique_clients=t.unique_clients,
        total_premium=float(t.total_premium),
        total_accumulation=float(t.total_accumulation),
        companies_json=companies,
        product_types_json=product_types,
        top_clients_json=top_clients,
        changes_json=changes,
    )
    db.add(summary)
    await db.commit()
    await db.refresh(summary)

    logger.info(f"Created production summary for upload {upload_id}, period {period_label}")
    return summary


async def _compute_changes(
    db: AsyncSession, user_id: uuid.UUID, current_upload_id: uuid.UUID, current_totals
) -> dict | None:
    """Compute changes vs the previous production summary."""
    # Find the previous summary
    prev_result = await db.execute(
        select(ProductionSummary)
        .where(
            ProductionSummary.user_id == user_id,
            ProductionSummary.upload_id != current_upload_id,
        )
        .order_by(desc(ProductionSummary.upload_date))
        .limit(1)
    )
    prev = prev_result.scalar_one_or_none()
    if not prev:
        return None

    premium_diff = float(current_totals.total_premium) - float(prev.total_premium)
    accum_diff = float(current_totals.total_accumulation) - float(prev.total_accumulation)
    client_diff = int(current_totals.unique_clients) - int(prev.unique_clients)

    # Compute new/removed clients by comparing id_numbers
    current_ids_q = await db.execute(
        select(func.distinct(ClientRecord.id_number))
        .where(ClientRecord.upload_id == current_upload_id, ClientRecord.id_number.isnot(None))
    )
    current_ids = {r[0] for r in current_ids_q.all()}

    prev_ids_q = await db.execute(
        select(func.distinct(ClientRecord.id_number))
        .where(ClientRecord.upload_id == prev.upload_id, ClientRecord.id_number.isnot(None))
    )
    prev_ids = {r[0] for r in prev_ids_q.all()}

    new_ids = current_ids - prev_ids
    removed_ids = prev_ids - current_ids

    prev_premium_pct = (premium_diff / float(prev.total_premium) * 100) if float(prev.total_premium) > 0 else 0

    return {
        "new_clients": len(new_ids),
        "removed_clients": len(removed_ids),
        "client_diff": client_diff,
        "premium_diff": round(premium_diff, 2),
        "premium_diff_pct": round(prev_premium_pct, 1),
        "accumulation_diff": round(accum_diff, 2),
    }
