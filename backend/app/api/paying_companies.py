import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.paying_company import PayingCompany
from app.schemas.paying_company import PayingCompanyCreate, PayingCompanyOut
from app.api.deps import get_current_user

router = APIRouter()

DEFAULT_PAYING_COMPANIES = ["מור", "מיטב", "ילין", "לפידות", "אנאליסט"]


@router.get("", response_model=list[PayingCompanyOut])
async def list_paying_companies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PayingCompany)
        .where(PayingCompany.user_id == user.id)
        .order_by(PayingCompany.created_at.desc())
    )
    companies = result.scalars().all()
    return [
        PayingCompanyOut(
            id=str(c.id),
            company_name=c.company_name,
            created_at=c.created_at,
        )
        for c in companies
    ]


@router.post("", response_model=PayingCompanyOut)
async def create_paying_company(
    data: PayingCompanyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = PayingCompany(
        user_id=user.id,
        company_name=data.company_name[:100],
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return PayingCompanyOut(
        id=str(company.id),
        company_name=company.company_name,
        created_at=company.created_at,
    )


@router.delete("/{company_id}")
async def delete_paying_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PayingCompany).where(
            PayingCompany.id == uuid.UUID(company_id),
            PayingCompany.user_id == user.id,
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="חברה משלמת לא נמצאה")

    await db.delete(company)
    await db.commit()
    return {"status": "deleted"}


@router.post("/seed", response_model=list[PayingCompanyOut])
async def seed_paying_companies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seed default paying companies (מור, מיטב, ילין, לפידות, אנאליסט)."""
    # Check existing
    result = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user.id)
    )
    existing = {c.company_name for c in result.scalars().all()}

    created = []
    for name in DEFAULT_PAYING_COMPANIES:
        if name not in existing:
            company = PayingCompany(
                user_id=user.id,
                company_name=name,
            )
            db.add(company)
            created.append(company)

    await db.commit()

    results = []
    for c in created:
        await db.refresh(c)
        results.append(PayingCompanyOut(
            id=str(c.id),
            company_name=c.company_name,
            created_at=c.created_at,
        ))
    return results
