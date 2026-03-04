from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.record import RecordOut, RecordPage, StatusSummary, AnalyticsResponse
from app.api.deps import get_current_user
from app.services.reconciliation_service import get_records_page, get_status_summary, get_client_records, get_analytics

router = APIRouter()


def record_to_out(r) -> RecordOut:
    return RecordOut(
        id=str(r.id),
        upload_id=str(r.upload_id),
        id_number=r.id_number,
        first_name=r.first_name,
        last_name=r.last_name,
        sign_date=r.sign_date,
        product=r.product,
        receiving_company=r.receiving_company,
        expected_amount=float(r.expected_amount) if r.expected_amount is not None else None,
        actual_amount=float(r.actual_amount) if r.actual_amount is not None else None,
        amount_difference=float(r.amount_difference) if r.amount_difference is not None else None,
        balance=float(r.balance) if r.balance is not None else None,
        commission_paid=float(r.commission_paid) if r.commission_paid is not None else None,
        commission_expected=float(r.commission_expected) if r.commission_expected is not None else None,
        reconciliation_status=r.reconciliation_status,
        management_fee=float(r.management_fee) if r.management_fee is not None else None,
        fund_policy_number=r.fund_policy_number,
        employment_status=r.employment_status,
        is_active=r.is_active,
        track=r.track,
        agent_number=r.agent_number,
        general_notes=r.general_notes,
    )


@router.get("", response_model=RecordPage)
async def list_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = None,
    company: str | None = None,
    status: str | None = None,
    product: str | None = None,
    upload_id: str | None = None,
    sort_by: str = "last_name",
    sort_dir: str = "asc",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await get_records_page(
        db, user.id, page, per_page, search, company, status, product, upload_id, sort_by, sort_dir
    )
    return RecordPage(
        items=[record_to_out(r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        pages=result["pages"],
    )


@router.get("/summary", response_model=StatusSummary)
async def summary(
    upload_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_status_summary(db, user.id, upload_id)


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(
    upload_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_analytics(db, user.id, upload_id)


@router.get("/client/{id_number}", response_model=list[RecordOut])
async def client_detail(
    id_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    records = await get_client_records(db, user.id, id_number)
    return [record_to_out(r) for r in records]
