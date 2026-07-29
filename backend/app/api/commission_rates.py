import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.record import ClientRecord
from app.models.commission_rate import CommissionRate
from app.models.upload import FileUpload
from app.schemas.record import (
    CommissionRateIn,
    CommissionRateOut,
    RateCoverageOut,
    RateCoverageRow,
)
from app.api.deps import get_paid_user as get_current_user
from app.services.rate_select import explain_expected_commission
from app.utils.hebrew_mappings import DEFAULT_COMMISSION_RATES

router = APIRouter()


def _out(r: CommissionRate) -> CommissionRateOut:
    """Single serializer for a rate row. Was inlined four times, which is how
    `rate_kind` came to be written by the extractor, read by the matcher, and
    never sent to the browser."""
    return CommissionRateOut(
        id=str(r.id),
        company_name=r.company_name,
        product=r.product,
        rate=float(r.rate),
        rate_kind=r.rate_kind,
        rate_scope=r.rate_scope,
        payment_frequency=r.payment_frequency,
        paid_to=r.paid_to,
        company_email=r.company_email,
        effective_from=r.effective_from,
        effective_to=r.effective_to,
    )


@router.get("", response_model=list[CommissionRateOut])
async def list_rates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )
    return [_out(r) for r in result.scalars().all()]


@router.get("/coverage", response_model=RateCoverageOut)
async def rate_coverage(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """How much of the agent's ACTIVE production file the agreement shelf
    actually prices, and — for every company it doesn't — why.

    Exists because the expected-commission math fails by `continue`: a company
    whose name doesn't match, or whose records carry no premium, contributes ₪0
    and disappears with no error. The shelf shows percentages and counts and no
    money at all, so there was no surface on which an agent could notice that
    most of their portfolio was priced at nothing.
    """
    upload = (
        await db.execute(
            select(FileUpload)
            .where(FileUpload.user_id == user.id, FileUpload.is_production.is_(True))
            .order_by(FileUpload.uploaded_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not upload:
        return RateCoverageOut(has_production=False)

    rates = (
        await db.execute(
            select(CommissionRate).where(CommissionRate.user_id == user.id)
        )
    ).scalars().all()
    records = (
        await db.execute(
            select(
                ClientRecord.id_number,
                ClientRecord.receiving_company,
                ClientRecord.product,
                ClientRecord.product_type,
                ClientRecord.accumulation,
                ClientRecord.total_premium,
            ).where(ClientRecord.upload_id == upload.id)
        )
    ).all()

    total, _by_company, coverage = explain_expected_commission(records, list(rates))
    return RateCoverageOut(
        has_production=True,
        production_filename=upload.filename,
        total_records=sum(c["records"] for c in coverage),
        covered_records=sum(c["contributing"] for c in coverage),
        expected_total=total,
        rows=[RateCoverageRow(**c) for c in coverage],
    )


@router.post("/seed", response_model=list[CommissionRateOut])
async def seed_defaults(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seed the default commission rates from the rate table image."""
    # Check if user already has rates
    existing = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Commission rates already exist. Delete them first to re-seed.")

    rates = []
    for item in DEFAULT_COMMISSION_RATES:
        rate = CommissionRate(
            user_id=user.id,
            company_name=item["company_name"],
            product=item.get("product"),
            rate=item["rate"],
            payment_frequency=item["payment_frequency"],
            paid_to=item["paid_to"],
            company_email=item.get("company_email"),
        )
        db.add(rate)
        rates.append(rate)

    await db.commit()
    for r in rates:
        await db.refresh(r)

    return [_out(r) for r in rates]


@router.post("", response_model=CommissionRateOut)
async def create_rate(
    data: CommissionRateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rate = CommissionRate(
        user_id=user.id,
        company_name=data.company_name,
        product=data.product,
        rate=data.rate,
        payment_frequency=data.payment_frequency,
        paid_to=data.paid_to,
        company_email=data.company_email,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
    )
    if data.rate_kind:
        rate.rate_kind = data.rate_kind
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    return _out(rate)


@router.put("/{rate_id}", response_model=CommissionRateOut)
async def update_rate(
    rate_id: str,
    data: CommissionRateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CommissionRate).where(
            CommissionRate.id == uuid.UUID(rate_id),
            CommissionRate.user_id == user.id,
        )
    )
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    # Assign ONLY what the client actually sent. Assigning every field
    # unconditionally silently wiped the agreement's validity window: the
    # shelf's edit form has no date inputs, so `effective_from`/`effective_to`
    # arrived as their None defaults and editing a row's email cleared its
    # years — losing the window `commission_rate.py` documents as driving
    # sign-date matching.
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rate, field, value)
    await db.commit()
    await db.refresh(rate)

    return _out(rate)


@router.delete("/{rate_id}")
async def delete_rate(
    rate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CommissionRate).where(
            CommissionRate.id == uuid.UUID(rate_id),
            CommissionRate.user_id == user.id,
        )
    )
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    await db.delete(rate)
    await db.commit()
    return {"status": "deleted"}
