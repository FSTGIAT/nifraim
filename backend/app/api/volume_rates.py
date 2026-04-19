import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.volume_commission_rate import VolumeCommissionRate
from app.schemas.volume import VolumeCommissionRateIn, VolumeCommissionRateOut
from app.api.deps import get_paid_user as get_current_user
from app.services.parser_service import parse_volume_rates
from app.utils.hebrew_mappings import DEFAULT_VOLUME_RATES

router = APIRouter()


def _rate_to_out(r: VolumeCommissionRate) -> VolumeCommissionRateOut:
    return VolumeCommissionRateOut(
        id=str(r.id),
        company_name=r.company_name,
        nifraim_rate=float(r.nifraim_rate) if r.nifraim_rate is not None else None,
        volume_rate_per_million=float(r.volume_rate_per_million) if r.volume_rate_per_million is not None else None,
        pension_accumulation=float(r.pension_accumulation) if r.pension_accumulation is not None else None,
        changed_percent=float(r.changed_percent) if r.changed_percent is not None else None,
        conversion_to_annuity=float(r.conversion_to_annuity) if r.conversion_to_annuity is not None else None,
        payment_frequency=r.payment_frequency,
        paid_to=r.paid_to,
        notes=r.notes,
    )


@router.get("", response_model=list[VolumeCommissionRateOut])
async def list_rates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VolumeCommissionRate).where(VolumeCommissionRate.user_id == user.id)
    )
    return [_rate_to_out(r) for r in result.scalars().all()]


@router.post("/seed", response_model=list[VolumeCommissionRateOut])
async def seed_defaults(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seed the default volume commission rates."""
    existing = await db.execute(
        select(VolumeCommissionRate).where(VolumeCommissionRate.user_id == user.id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Volume rates already exist. Delete them first to re-seed.")

    rates = []
    for item in DEFAULT_VOLUME_RATES:
        rate = VolumeCommissionRate(
            user_id=user.id,
            company_name=item["company_name"],
            nifraim_rate=item.get("nifraim_rate"),
            volume_rate_per_million=item.get("volume_rate_per_million"),
            pension_accumulation=item.get("pension_accumulation"),
            changed_percent=item.get("changed_percent"),
            conversion_to_annuity=item.get("conversion_to_annuity"),
            payment_frequency=item.get("payment_frequency"),
            paid_to=item.get("paid_to"),
            notes=item.get("notes"),
        )
        db.add(rate)
        rates.append(rate)

    await db.commit()
    for r in rates:
        await db.refresh(r)

    return [_rate_to_out(r) for r in rates]


@router.post("", response_model=VolumeCommissionRateOut)
async def create_rate(
    data: VolumeCommissionRateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rate = VolumeCommissionRate(
        user_id=user.id,
        company_name=data.company_name,
        nifraim_rate=data.nifraim_rate,
        volume_rate_per_million=data.volume_rate_per_million,
        pension_accumulation=data.pension_accumulation,
        changed_percent=data.changed_percent,
        conversion_to_annuity=data.conversion_to_annuity,
        payment_frequency=data.payment_frequency,
        paid_to=data.paid_to,
        notes=data.notes,
    )
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    return _rate_to_out(rate)


@router.put("/{rate_id}", response_model=VolumeCommissionRateOut)
async def update_rate(
    rate_id: str,
    data: VolumeCommissionRateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VolumeCommissionRate).where(
            VolumeCommissionRate.id == uuid.UUID(rate_id),
            VolumeCommissionRate.user_id == user.id,
        )
    )
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    rate.company_name = data.company_name
    rate.nifraim_rate = data.nifraim_rate
    rate.volume_rate_per_million = data.volume_rate_per_million
    rate.pension_accumulation = data.pension_accumulation
    rate.changed_percent = data.changed_percent
    rate.conversion_to_annuity = data.conversion_to_annuity
    rate.payment_frequency = data.payment_frequency
    rate.paid_to = data.paid_to
    rate.notes = data.notes
    await db.commit()
    await db.refresh(rate)
    return _rate_to_out(rate)


@router.delete("/{rate_id}")
async def delete_rate(
    rate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VolumeCommissionRate).where(
            VolumeCommissionRate.id == uuid.UUID(rate_id),
            VolumeCommissionRate.user_id == user.id,
        )
    )
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    await db.delete(rate)
    await db.commit()
    return {"status": "deleted"}


@router.post("/upload", response_model=list[VolumeCommissionRateOut])
async def upload_rates(
    file: UploadFile = File(...),
    password: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Parse Excel file and bulk insert volume commission rates."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="לא סופק קובץ")

    content = await file.read()
    try:
        parsed_rates = parse_volume_rates(content, file.filename, password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בפענוח הקובץ: {str(e)}")

    if not parsed_rates:
        raise HTTPException(status_code=400, detail="לא נמצאו שורות בקובץ")

    # Delete existing rates for this user
    existing = await db.execute(
        select(VolumeCommissionRate).where(VolumeCommissionRate.user_id == user.id)
    )
    for r in existing.scalars().all():
        await db.delete(r)

    rates = []
    for item in parsed_rates:
        rate = VolumeCommissionRate(
            user_id=user.id,
            company_name=item.get("company_name", ""),
            nifraim_rate=item.get("nifraim_rate"),
            volume_rate_per_million=item.get("volume_rate_per_million"),
            pension_accumulation=item.get("pension_accumulation"),
            changed_percent=item.get("changed_percent"),
            conversion_to_annuity=item.get("conversion_to_annuity"),
            payment_frequency=item.get("payment_frequency"),
            paid_to=item.get("paid_to"),
            notes=item.get("notes"),
        )
        db.add(rate)
        rates.append(rate)

    await db.commit()
    for r in rates:
        await db.refresh(r)

    return [_rate_to_out(r) for r in rates]
