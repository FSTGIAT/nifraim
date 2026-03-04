import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.commission_rate import CommissionRate
from app.schemas.record import CommissionRateIn, CommissionRateOut
from app.api.deps import get_current_user
from app.utils.hebrew_mappings import DEFAULT_COMMISSION_RATES

router = APIRouter()


@router.get("", response_model=list[CommissionRateOut])
async def list_rates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )
    rates = result.scalars().all()
    return [
        CommissionRateOut(
            id=str(r.id),
            company_name=r.company_name,
            rate=float(r.rate),
            payment_frequency=r.payment_frequency,
            paid_to=r.paid_to,
            company_email=r.company_email,
        )
        for r in rates
    ]


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

    return [
        CommissionRateOut(
            id=str(r.id),
            company_name=r.company_name,
            rate=float(r.rate),
            payment_frequency=r.payment_frequency,
            paid_to=r.paid_to,
            company_email=r.company_email,
        )
        for r in rates
    ]


@router.post("", response_model=CommissionRateOut)
async def create_rate(
    data: CommissionRateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rate = CommissionRate(
        user_id=user.id,
        company_name=data.company_name,
        rate=data.rate,
        payment_frequency=data.payment_frequency,
        paid_to=data.paid_to,
        company_email=data.company_email,
    )
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    return CommissionRateOut(
        id=str(rate.id),
        company_name=rate.company_name,
        rate=float(rate.rate),
        payment_frequency=rate.payment_frequency,
        paid_to=rate.paid_to,
        company_email=rate.company_email,
    )


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

    rate.company_name = data.company_name
    rate.rate = data.rate
    rate.payment_frequency = data.payment_frequency
    rate.paid_to = data.paid_to
    rate.company_email = data.company_email
    await db.commit()
    await db.refresh(rate)

    return CommissionRateOut(
        id=str(rate.id),
        company_name=rate.company_name,
        rate=float(rate.rate),
        payment_frequency=rate.payment_frequency,
        paid_to=rate.paid_to,
        company_email=rate.company_email,
    )


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
