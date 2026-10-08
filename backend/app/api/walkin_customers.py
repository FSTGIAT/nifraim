"""לקוח חדש (walk-in) — a customer the agent adds by hand before any production file has them.
Their phone joins the Nifraim App's customer list: calls with them upload on their own, including
the recordings of the last 3 hours (the app re-checks what it skipped when the list grows)."""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
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


async def _in_book(db: AsyncSession, user: User, id_number: str | None, phone: str | None) -> dict:
    """Who in this month's production book already has this ת.ז or phone.

    A person already in the book is already a customer: their calls upload on their own, so adding
    them again changes nothing on the phone (2026-10-07: kiko added סרגיי שנקמן, whose number was
    already in the book for 4 family members, and expected the 3-hour re-check to run — it can't,
    the app's list didn't grow)."""
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord

    idn = re.sub(r"\D", "", id_number or "").lstrip("0")
    key = phone_key(phone)
    if not (len(idn) >= 5 or key):
        return {"id": None, "phone": []}
    ids = await _get_production_upload_ids(db, user.id)
    if not ids:
        return {"id": None, "phone": []}
    conds = []
    if len(idn) >= 5:
        conds.append(ClientRecord.id_number.in_([idn, idn.zfill(9)]))
    if key:
        conds.append(ClientRecord.client_phone.is_not(None))
    rows = (await db.execute(
        select(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name, ClientRecord.client_phone)
        .where(ClientRecord.user_id == user.id, ClientRecord.upload_id.in_(ids), or_(*conds))
        .distinct()
    )).all()
    by_id, by_phone = None, {}
    for rid, first, last, ph in rows:
        rid = (str(rid or "").strip().lstrip("0")) or None
        name = " ".join(x for x in ((first or "").strip(), (last or "").strip()) if x) or "ללא שם"
        if rid and rid == idn and not by_id:
            by_id = name
        if key and phone_key(ph) == key and rid:
            by_phone.setdefault(rid, name)
    return {"id": by_id, "phone": sorted(set(by_phone.values()))}


@router.get("/check")
async def check_walkin(id_number: str = "", phone: str = "",
                       user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """For the form, while typing: is this person / number already in the book?"""
    return await _in_book(db, user, id_number, phone)


@router.get("")
async def list_walkins(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(WalkinCustomer).where(WalkinCustomer.user_id == user.id)
                             .order_by(WalkinCustomer.created_at.desc()))).scalars().all()
    return [_out(w) for w in rows]


@router.post("")
async def add_walkin(data: WalkinIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vals = _clean(data)
    known = await _in_book(db, user, vals["id_number"], vals["phone"])
    if known["id"]:
        raise HTTPException(409, f"{known['id']} כבר לקוח בתיק — שיחות איתו עולות לבד, אין צורך להוסיף.")
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
