import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.deps import get_paid_user
from app.services import unpaid_tracker_service

router = APIRouter()


class DismissCustomerBody(BaseModel):
    company: str
    customer_id: str


class DismissCompanyBody(BaseModel):
    company: str


class RestoreBody(BaseModel):
    company: str
    customer_id: str | None = None


@router.get("/by-company")
async def by_company(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Latest unpaid snapshot per company for the current user.

    Returns one row per company — what the monitor card renders inline.
    Each row includes a 5-customer preview so the row can show counts and
    a sparkline without a second roundtrip.
    """
    rows = await unpaid_tracker_service.current_by_company(db, user.id)
    return {"rows": rows}


@router.get("/trend")
async def trend(
    company: str | None = Query(default=None),
    months: int = Query(default=12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Per-period unpaid counts/amounts for the line chart.

    Shape: `[{period, company, count, amount}, ...]` — frontend pivots
    into ApexCharts series (one series per company).
    """
    rows = await unpaid_tracker_service.trend(db, user.id, company=company, months=months)
    return {"rows": rows}


@router.get("/{snapshot_id}/customers")
async def get_customers(
    snapshot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Drill-in: full unpaid customer list for one snapshot."""
    customers = await unpaid_tracker_service.get_customers(db, user.id, snapshot_id)
    if customers is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"customers": customers}


@router.post("/dismiss-customer")
async def dismiss_customer(
    body: DismissCustomerBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Hide a single customer from the unpaid monitor (per-company)."""
    ok = await unpaid_tracker_service.dismiss_customer(
        db, user.id, body.company, body.customer_id,
    )
    return {"ok": ok}


@router.post("/dismiss-company")
async def dismiss_company(
    body: DismissCompanyBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Hide every currently-visible unpaid customer for one company."""
    n = await unpaid_tracker_service.dismiss_company(db, user.id, body.company)
    return {"ok": True, "dismissed": n}


@router.post("/restore")
async def restore(
    body: RestoreBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Undo dismissals. Pass customer_id to restore one, omit it to restore the whole company."""
    n = await unpaid_tracker_service.restore_customer(
        db, user.id, body.company, body.customer_id,
    )
    return {"ok": True, "restored": n}


@router.post("/{snapshot_id}/send-email")
async def send_email(
    snapshot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Build XLSX of unpaid customers and email it to the company contact.

    Requires a CompanyContact row for (user, company_name). Returns 404
    with code=no_contact when the user hasn't configured an email yet —
    UI maps that to the 'אין מייל מוגדר' prompt.
    """
    try:
        return await unpaid_tracker_service.send_company_email(db, user.id, snapshot_id)
    except ValueError as e:
        code = str(e)
        if code == "no_contact":
            raise HTTPException(
                status_code=404,
                detail={"code": "no_contact", "message": "אין מייל מוגדר לחברה זו — הוסף בלשונית אימיילים לחברות"},
            )
        if code == "not_found":
            raise HTTPException(status_code=404, detail="Snapshot not found")
        raise
