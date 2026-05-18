import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.models.subscription import Subscription
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.commission_comparison import CommissionComparison
from app.schemas.user import UserAdminOut, UserAdminUpdate

router = APIRouter()


@router.get("/users", response_model=list[UserAdminOut])
async def list_users(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        UserAdminOut(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            phone=u.phone,
            company_name=u.company_name,
            is_active=u.is_active,
            is_admin=u.is_admin,
            created_at=u.created_at.isoformat() if u.created_at else "",
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: str,
    body: UserAdminUpdate,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_admin is not None:
        user.is_admin = body.is_admin

    await db.commit()
    await db.refresh(user)

    return UserAdminOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        company_name=user.company_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.get("/subscriptions")
async def list_subscriptions(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Subscription).order_by(Subscription.created_at.desc()))
    subs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "user_id": str(s.user_id),
            "plan": s.plan,
            "amount": float(s.amount),
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in subs
    ]


@router.get("/diagnostic/commission-paths")
async def commission_path_diagnostic(
    target_email: str = Query(..., description="User to diagnose"),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Diagnostic for the 'AI quoted ₪37,352 / מור leading' bug.

    Returns the raw-DB commission total alongside the cached
    `commission_comparisons.summary_json.total_commission` per category, so
    we can confirm whether the AI was reading the cached per-category sum
    and reporting it as 'the period total'.

    Admin-only. Bring up via:
        GET /api/admin/diagnostic/commission-paths?target_email=admin@nifraim.co.il
    """
    user_q = await db.execute(select(User).where(User.email == target_email))
    target = user_q.scalar_one_or_none()
    if not target:
        raise HTTPException(404, f"User {target_email} not found")

    # Find production's period_month (for period-filtered totals)
    prod_q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == target.id,
            FileUpload.is_production.is_(True),
        )
    )
    prod = prod_q.scalar_one_or_none()
    prod_period = prod.period_month if prod else None

    # All commission uploads for this user
    comm_q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == target.id,
            FileUpload.file_category == "commission",
        )
    )
    comm_uploads = list(comm_q.scalars().all())

    # Period-filtered uploads
    period_uploads = [u for u in comm_uploads if u.period_month == prod_period] if prod_period else comm_uploads
    other_period_uploads = [u for u in comm_uploads if u.period_month and u.period_month != prod_period]
    no_period_uploads = [u for u in comm_uploads if u.period_month is None]

    async def _sum_paid(upload_ids: list[uuid.UUID]) -> dict:
        """Return per-company sum of commission_paid + grand total."""
        if not upload_ids:
            return {"total": 0.0, "by_company": []}
        rows = await db.execute(
            select(
                FileUpload.company_source,
                func.coalesce(func.sum(ClientRecord.commission_paid), 0).label("sum_paid"),
                func.count(func.distinct(ClientRecord.id_number)).label("clients"),
            )
            .join(ClientRecord, ClientRecord.upload_id == FileUpload.id)
            .where(FileUpload.id.in_(upload_ids))
            .group_by(FileUpload.company_source)
        )
        by_co = [
            {"company": r[0] or "(none)", "paid": float(r[1] or 0), "clients": int(r[2] or 0)}
            for r in rows.all()
        ]
        by_co.sort(key=lambda x: x["paid"], reverse=True)
        return {
            "total": round(sum(c["paid"] for c in by_co), 2),
            "by_company": by_co,
        }

    raw_all_periods = await _sum_paid([u.id for u in comm_uploads])
    period_filtered = await _sum_paid([u.id for u in period_uploads])

    # Cached commission_comparisons per category
    cached_q = await db.execute(
        select(CommissionComparison)
        .where(CommissionComparison.user_id == target.id)
        .order_by(CommissionComparison.computed_at.desc())
    )
    cached_rows = list(cached_q.scalars().all())
    seen_cat = set()
    cached_per_category: dict[str, dict] = {}
    for row in cached_rows:
        if row.category in seen_cat:
            continue
        seen_cat.add(row.category)
        summary = row.summary_json or {}
        cached_per_category[row.category] = {
            "total_commission": summary.get("total_commission"),
            "total_customers": summary.get("total_customers"),
            "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        }

    return {
        "user": target_email,
        "production_period_month": prod_period.isoformat() if prod_period else None,
        "raw_db_sum_all_periods": raw_all_periods,
        "period_filtered_sum": period_filtered,
        "uploads": {
            "total": len(comm_uploads),
            "matching_production_period": len(period_uploads),
            "other_period": len(other_period_uploads),
            "no_period_detected": len(no_period_uploads),
        },
        "commission_comparisons_cached_per_category": cached_per_category,
        "notes": [
            "raw_db_sum_all_periods sums commission_paid across ALL commission uploads — pre-fix behavior.",
            "period_filtered_sum sums only uploads whose period_month matches production — post-fix behavior.",
            "If cached_per_category contains an entry whose total_commission matches the AI's quoted figure, that's the AI's source.",
        ],
    }
