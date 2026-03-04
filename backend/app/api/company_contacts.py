import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.company_contact import CompanyContact
from app.schemas.company_contact import CompanyContactCreate, CompanyContactUpdate, CompanyContactOut
from app.api.deps import get_paid_user as get_current_user

router = APIRouter()

DEFAULT_COMPANY_CONTACTS = [
    {"company_name": "מור גמל", "email": "amalotgp@more.co.il"},
    {"company_name": "מור פנסיה", "email": "amalotpn@more.co.il"},
    {"company_name": "מיטב", "email": "agentcommission@meitav.co.il"},
    {"company_name": "ילין לפידות", "email": "ylcommissions@ylinlapidot.co.il"},
    {"company_name": "אנאליסט", "email": "commissions@analyst.co.il"},
]


@router.get("", response_model=list[CompanyContactOut])
async def list_company_contacts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CompanyContact)
        .where(CompanyContact.user_id == user.id)
        .order_by(CompanyContact.created_at.desc())
    )
    contacts = result.scalars().all()
    return [
        CompanyContactOut(
            id=str(c.id),
            company_name=c.company_name,
            email=c.email,
            contact_name=c.contact_name,
            notes=c.notes,
            created_at=c.created_at,
        )
        for c in contacts
    ]


@router.post("", response_model=CompanyContactOut)
async def create_company_contact(
    data: CompanyContactCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact = CompanyContact(
        user_id=user.id,
        company_name=data.company_name[:100],
        email=data.email[:255],
        contact_name=data.contact_name[:100] if data.contact_name else None,
        notes=data.notes[:500] if data.notes else None,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return CompanyContactOut(
        id=str(contact.id),
        company_name=contact.company_name,
        email=contact.email,
        contact_name=contact.contact_name,
        notes=contact.notes,
        created_at=contact.created_at,
    )


@router.put("/{contact_id}", response_model=CompanyContactOut)
async def update_company_contact(
    contact_id: str,
    data: CompanyContactUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CompanyContact).where(
            CompanyContact.id == uuid.UUID(contact_id),
            CompanyContact.user_id == user.id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="איש קשר לא נמצא")

    if data.company_name is not None:
        contact.company_name = data.company_name[:100]
    if data.email is not None:
        contact.email = data.email[:255]
    if data.contact_name is not None:
        contact.contact_name = data.contact_name[:100]
    if data.notes is not None:
        contact.notes = data.notes[:500]

    await db.commit()
    await db.refresh(contact)
    return CompanyContactOut(
        id=str(contact.id),
        company_name=contact.company_name,
        email=contact.email,
        contact_name=contact.contact_name,
        notes=contact.notes,
        created_at=contact.created_at,
    )


@router.delete("/{contact_id}")
async def delete_company_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CompanyContact).where(
            CompanyContact.id == uuid.UUID(contact_id),
            CompanyContact.user_id == user.id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="איש קשר לא נמצא")

    await db.delete(contact)
    await db.commit()
    return {"status": "deleted"}


@router.post("/seed", response_model=list[CompanyContactOut])
async def seed_company_contacts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seed default company contacts."""
    result = await db.execute(
        select(CompanyContact).where(CompanyContact.user_id == user.id)
    )
    existing = {c.company_name for c in result.scalars().all()}

    created = []
    for entry in DEFAULT_COMPANY_CONTACTS:
        if entry["company_name"] not in existing:
            contact = CompanyContact(
                user_id=user.id,
                company_name=entry["company_name"],
                email=entry["email"],
            )
            db.add(contact)
            created.append(contact)

    await db.commit()

    results = []
    for c in created:
        await db.refresh(c)
        results.append(CompanyContactOut(
            id=str(c.id),
            company_name=c.company_name,
            email=c.email,
            contact_name=c.contact_name,
            notes=c.notes,
            created_at=c.created_at,
        ))
    return results
