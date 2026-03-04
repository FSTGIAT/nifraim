import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.recruit import Recruit
from app.schemas.recruit import RecruitCreate, RecruitOut, RecruitMatchResult, RecruitComparisonResponse
from app.api.deps import get_paid_user as get_current_user

router = APIRouter()


@router.get("", response_model=list[RecruitOut])
async def list_recruits(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Recruit)
        .where(Recruit.user_id == user.id)
        .order_by(Recruit.created_at.desc())
    )
    recruits = result.scalars().all()
    return [
        RecruitOut(
            id=str(r.id),
            id_number=r.id_number,
            first_name=r.first_name,
            last_name=r.last_name,
            company=r.company,
            product=r.product,
            amount=float(r.amount) if r.amount is not None else None,
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
            amount=float(r.amount) if r.amount is not None else None,
            created_at=r.created_at,
        ))
    return results


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


@router.post("/compare", response_model=RecruitComparisonResponse)
async def compare_recruits(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare all recruits against the active production file."""
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
            prod_by_id.setdefault(r.id_number, []).append(r)

    # Load recruits
    recruits_result = await db.execute(
        select(Recruit)
        .where(Recruit.user_id == user.id)
        .order_by(Recruit.created_at.desc())
    )
    recruits = recruits_result.scalars().all()

    results = []
    found_count = 0

    for recruit in recruits:
        prod_recs = prod_by_id.get(recruit.id_number, [])
        found = len(prod_recs) > 0

        if found:
            found_count += 1

        production_products = []
        total_premium = 0.0
        for r in prod_recs:
            premium = float(r.total_premium) if r.total_premium is not None else 0
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
            amount=float(recruit.amount) if recruit.amount is not None else None,
            found_in_production=found,
            production_products=production_products,
            production_premium=total_premium,
        ))

    return RecruitComparisonResponse(
        total=len(recruits),
        found=found_count,
        not_found=len(recruits) - found_count,
        results=results,
    )
