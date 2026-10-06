"""לקוח חדש (walk-in) — a customer the agent adds by hand before any production file has them.
Their phone joins the Nifraim App's customer list: calls with them upload on their own, including
the recordings of the last 3 hours (the app re-checks what it skipped when the list grows)."""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user as get_current_user
from app.database import get_db
from app.models.user import User
from app.models.walkin_customer import WalkinCustomer
from app.services.calls.ingest import phone_display, phone_key

router = APIRouter()
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


class WalkinIn(BaseModel):
    id_number: str
    first_name: str
    last_name: str | None = None
    phone: str
    email: str | None = None


def _clean(data: WalkinIn) -> dict:
    idn = re.sub(r"\D", "", data.id_number or "").lstrip("0")
    if not 5 <= len(idn) <= 9:
        raise HTTPException(400, "ת.ז לא תקינה")
    if not phone_key(data.phone):
        raise HTTPException(400, "מספר טלפון לא תקין")
    first = (data.first_name or "").strip()
    if not first:
        raise HTTPException(400, "חסר שם פרטי")
    email = (data.email or "").strip() or None
    if email and not EMAIL_RE.match(email):
        raise HTTPException(400, "כתובת מייל לא תקינה")
    return {"id_number": idn, "first_name": first[:80], "last_name": ((data.last_name or "").strip() or None),
            "phone": phone_display(data.phone) or data.phone.strip(), "email": email}


def _out(w: WalkinCustomer) -> dict:
    return {"id": str(w.id), "id_number": w.id_number, "first_name": w.first_name, "last_name": w.last_name or "",
            "name": " ".join(x for x in (w.first_name, w.last_name) if x), "phone": w.phone, "email": w.email or "",
            "created_at": w.created_at.isoformat() + "Z" if w.created_at else None}


@router.get("")
async def list_walkins(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(WalkinCustomer).where(WalkinCustomer.user_id == user.id)
                             .order_by(WalkinCustomer.created_at.desc()))).scalars().all()
    return [_out(w) for w in rows]


@router.post("")
async def add_walkin(data: WalkinIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vals = _clean(data)
    dup = (await db.execute(select(WalkinCustomer).where(WalkinCustomer.user_id == user.id,
                                                          WalkinCustomer.id_number == vals["id_number"]))).scalar_one_or_none()
    if dup:
        for k, v in vals.items():
            setattr(dup, k, v)
        w = dup
    else:
        w = WalkinCustomer(user_id=user.id, **vals)
        db.add(w)
    await db.commit()
    await db.refresh(w)
    return _out(w)


@router.put("/{walkin_id}")
async def update_walkin(walkin_id: str, data: WalkinIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    w = await _own(db, user, walkin_id)
    for k, v in _clean(data).items():
        setattr(w, k, v)
    await db.commit()
    await db.refresh(w)
    return _out(w)


@router.delete("/{walkin_id}")
async def delete_walkin(walkin_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.delete(await _own(db, user, walkin_id))
    await db.commit()
    return {"ok": True}


async def _own(db, user, walkin_id: str) -> WalkinCustomer:
    try:
        wid = uuid.UUID(walkin_id)
    except ValueError:
        raise HTTPException(404, "לא נמצא")
    w = await db.get(WalkinCustomer, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "לא נמצא")
    return w
