from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.volume_bonus_payment import VolumeBonusPayment
from app.schemas.volume import VolumeCompareResponse, VolumeBonusResponse, VolumeBonusPaymentIn, VolumeBonusPaymentOut
from app.api.deps import get_paid_user as get_current_user
from app.services.parser_service import parse_excel
from app.services.volume_service import compare_volume, calculate_bonus

router = APIRouter()


@router.post("/upload-compare", response_model=VolumeCompareResponse)
async def upload_and_compare(
    file: UploadFile = File(...),
    password: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload volume report file, parse, and compare vs production & recruits."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="לא סופק קובץ")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls"):
        raise HTTPException(status_code=400, detail="רק קבצי xlsx/xls נתמכים")

    content = await file.read()

    try:
        result = parse_excel(content, file.filename, password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בפענוח הקובץ: {str(e)}")

    if result["format"] != "volume_report":
        raise HTTPException(status_code=400, detail="הקובץ אינו דוח היקפים — וודא שהקובץ מכיל עמודות תפוקה ורמת גורם")

    volume_data = result.get("volume_data", {})
    comparison = await compare_volume(db, user.id, volume_data)

    return VolumeCompareResponse(**comparison)


@router.post("/calculate-bonus", response_model=VolumeBonusResponse)
async def calculate_volume_bonus(
    file: UploadFile = File(...),
    password: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload volume report and calculate bonus per company using volume rates."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="לא סופק קובץ")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls"):
        raise HTTPException(status_code=400, detail="רק קבצי xlsx/xls נתמכים")

    content = await file.read()

    try:
        result = parse_excel(content, file.filename, password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בפענוח הקובץ: {str(e)}")

    if result["format"] != "volume_report":
        raise HTTPException(status_code=400, detail="הקובץ אינו דוח היקפים")

    volume_data = result.get("volume_data", {})
    bonus = await calculate_bonus(db, user.id, volume_data)

    return VolumeBonusResponse(**bonus)


@router.get("/bonus-payments")
async def list_bonus_payments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all volume bonus payment statuses for current user."""
    result = await db.execute(
        select(VolumeBonusPayment).where(VolumeBonusPayment.user_id == user.id)
    )
    payments = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "company_name": p.company_name,
            "year": p.year,
            "is_paid": p.is_paid,
            "paid_date": str(p.paid_date) if p.paid_date else None,
            "notes": p.notes,
        }
        for p in payments
    ]


@router.post("/bonus-payments")
async def upsert_bonus_payment(
    data: VolumeBonusPaymentIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create or update a bonus payment status for a company+year."""
    result = await db.execute(
        select(VolumeBonusPayment).where(
            VolumeBonusPayment.user_id == user.id,
            VolumeBonusPayment.company_name == data.company_name,
            VolumeBonusPayment.year == data.year,
        )
    )
    payment = result.scalar_one_or_none()

    paid_date_val = None
    if data.paid_date:
        try:
            paid_date_val = date.fromisoformat(data.paid_date)
        except ValueError:
            pass

    if payment:
        payment.is_paid = data.is_paid
        payment.paid_date = paid_date_val
        payment.notes = data.notes
    else:
        payment = VolumeBonusPayment(
            user_id=user.id,
            company_name=data.company_name,
            year=data.year,
            is_paid=data.is_paid,
            paid_date=paid_date_val,
            notes=data.notes,
        )
        db.add(payment)

    await db.commit()
    await db.refresh(payment)
    return {
        "id": str(payment.id),
        "company_name": payment.company_name,
        "year": payment.year,
        "is_paid": payment.is_paid,
        "paid_date": str(payment.paid_date) if payment.paid_date else None,
        "notes": payment.notes,
    }
