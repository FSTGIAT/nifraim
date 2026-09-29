import uuid
from datetime import datetime, timedelta

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
from app.models.worker_heartbeat import WorkerHeartbeat
from app.schemas.user import UserAdminOut, UserAdminUpdate, UserAdminCreate, AgentStatusOut
from app.services.auth_service import hash_password
from app.services.username_service import generate_unique_username

router = APIRouter()

# A worker is "online" if it heartbeated within this window. Mirrors
# WORKER_LIVE_WINDOW_S in app/api/portal_automation.py (the source of truth).
WORKER_LIVE_WINDOW_S = 90


@router.get("/users", response_model=list[UserAdminOut])
async def list_users(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [_user_admin_out(u) for u in users]


def _user_admin_out(u: User) -> UserAdminOut:
    return UserAdminOut(
        id=str(u.id),
        email=u.email,
        full_name=u.full_name,
        phone=u.phone,
        company_name=u.company_name,
        is_active=u.is_active,
        is_admin=u.is_admin,
        created_at=u.created_at.isoformat() if u.created_at else "",
        is_test_user=bool(getattr(u, "is_test_user", False)),
    )


def _sim_offset_for(today_value) -> int | None:
    """Seconds between the real clock and a TEST user's chosen "today" (same
    time of day, Israel time). None when no date was given."""
    if not today_value:
        return None
    from datetime import date as _date
    from zoneinfo import ZoneInfo

    from app.services.cycle_service import utc_now

    try:
        d = _date.fromisoformat(str(today_value))
    except ValueError as e:
        raise HTTPException(status_code=400, detail="תאריך 'היום' לא תקין") from e
    now_il = utc_now().astimezone(ZoneInfo("Asia/Jerusalem"))
    target = now_il.replace(year=d.year, month=d.month, day=d.day)
    return int((target - now_il).total_seconds()) or None


@router.post("/users", response_model=UserAdminOut, status_code=201)
async def create_user(
    body: UserAdminCreate,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    email = body.email.lower()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # `username` is NOT NULL — admin-created accounts don't choose one, so derive
    # it from the email. The user can rename via PATCH /api/auth/me/username.
    created_at = None
    signup_value = body.signup_date or body.sim_today
    if body.signup_date and body.sim_today and body.signup_date > body.sim_today:
        raise HTTPException(status_code=400, detail="תאריך ההרשמה אחרי 'היום' של המשתמש")
    if signup_value:
        from datetime import date as _date
        from zoneinfo import ZoneInfo
        try:
            d = _date.fromisoformat(signup_value)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="תאריך הרשמה לא תקין") from e
        created_at = (datetime(d.year, d.month, d.day, 12, 0, tzinfo=ZoneInfo("Asia/Jerusalem"))
                      .astimezone(ZoneInfo("UTC")).replace(tzinfo=None))

    user = User(
        email=email,
        username=await generate_unique_username(db, email),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        phone=body.phone,
        company_name=body.company_name,
        is_active=True,  # admin-created accounts are active immediately
        is_admin=body.is_admin,
        **({"created_at": created_at} if created_at else {}),
        sim_clock_offset_s=_sim_offset_for(body.sim_today),
        # A simulated "today" only makes sense on a test account.
        is_test_user=bool(body.is_test_user or body.sim_today) and not body.is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return _user_admin_out(user)


@router.post("/test-users", response_model=UserAdminOut, status_code=201)
async def create_test_user(
    body: dict,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """A user "as if" they signed up on a chosen date — to see how the app
    shows the cycle and מסלקה dates to a new agent (first cycle, locked
    Production tab, שיוך deadline → the 15th production arrives).

    Optional שיוך state (`maslaka_status`: not_started | submitted | approved,
    with its own dates). A test link NEVER carries an agent ID or the
    auto-production consent, so approval opens no real subscription at the
    מסלקה (orchestration.ensure_monthly_subscriptions requires both).
    """
    from datetime import date as _date
    from zoneinfo import ZoneInfo

    from app.models.maslaka_agent_link import (
        APPROVED, NOT_STARTED, SUBMITTED, MaslakaAgentLink,
    )

    il = ZoneInfo("Asia/Jerusalem")

    def at_noon_utc(value, field: str) -> datetime:
        try:
            d = _date.fromisoformat(str(value))
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"{field}: תאריך לא תקין") from e
        # Noon Israel time, stored naive-UTC like every created_at in the app.
        return (datetime(d.year, d.month, d.day, 12, 0, tzinfo=il)
                .astimezone(ZoneInfo("UTC")).replace(tzinfo=None))

    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    # Same validator as /auth/login — an address login rejects (e.g. *.local)
    # would make an account nobody can sign into.
    from pydantic import EmailStr, TypeAdapter, ValidationError
    try:
        TypeAdapter(EmailStr).validate_python(email)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail="אימייל לא תקין (לא ניתן להתחבר איתו)") from e
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="סיסמה של 4 תווים לפחות")
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="האימייל כבר רשום")

    sim_offset = _sim_offset_for(body.get("sim_today"))
    sim_today_utc = (at_noon_utc(body.get("sim_today"), "היום המדומה")
                     if body.get("sim_today") else None)
    signup_at = at_noon_utc(body.get("signup_date") or body.get("sim_today"), "תאריך הרשמה")
    if sim_today_utc and signup_at > sim_today_utc:
        raise HTTPException(status_code=400, detail="תאריך ההרשמה אחרי 'היום' של המשתמש")
    status = str(body.get("maslaka_status") or NOT_STARTED)
    if status not in (NOT_STARTED, SUBMITTED, APPROVED):
        raise HTTPException(status_code=400, detail="מצב שיוך לא תקין")
    submitted_at = approved_at = None
    if status in (SUBMITTED, APPROVED):
        submitted_at = at_noon_utc(body.get("maslaka_submitted_date"), "תאריך הגשת שיוך")
        if submitted_at < signup_at:
            raise HTTPException(status_code=400, detail="הגשת השיוך לפני ההרשמה")
    if status == APPROVED:
        approved_at = at_noon_utc(body.get("maslaka_approved_date"), "תאריך אישור שיוך")
        if approved_at < submitted_at:
            raise HTTPException(status_code=400, detail="אישור השיוך לפני ההגשה")
    for when in (submitted_at, approved_at):
        if sim_today_utc and when and when > sim_today_utc:
            raise HTTPException(status_code=400, detail="תאריך שיוך אחרי 'היום' של המשתמש")

    user = User(
        email=email,
        username=await generate_unique_username(db, email),
        hashed_password=hash_password(password),
        full_name=str(body.get("full_name") or "").strip() or "משתמש בדיקה",
        is_active=True,
        is_admin=False,
        created_at=signup_at,
        sim_clock_offset_s=sim_offset,
        is_test_user=True,
    )
    db.add(user)
    await db.flush()
    if status != NOT_STARTED:
        db.add(MaslakaAgentLink(
            user_id=user.id,
            status=status,
            agent_name=user.full_name,
            submitted_at=submitted_at,
            approved_at=approved_at,
            decided_via="admin" if status == APPROVED else None,
            auto_production=False,
        ))
    await db.commit()
    await db.refresh(user)
    return _user_admin_out(user)


@router.delete("/users/{user_id}")
async def delete_test_user(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a TEST user and all their data. Refuses anyone not marked
    `is_test_user`, any admin, and the caller — a real agent's account and
    data are never deletable from here."""
    from app.services.test_user_purge import purge_user

    try:
        uid = uuid.UUID(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="מזהה לא תקין") from e
    user = await db.get(User, uid)
    if user is None:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")
    if not user.is_test_user or user.is_admin or user.id == admin.id:
        raise HTTPException(status_code=403, detail="אפשר למחוק רק משתמשי בדיקה")
    email = user.email
    try:
        counts = await purge_user(db, uid)
        await db.commit()
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"המחיקה נכשלה: {e}") from e
    return {"deleted": email, "rows": counts}


@router.get("/agents-status", response_model=list[AgentStatusOut])
async def agents_status(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Every agent + whether their local worker is currently connected."""
    result = await db.execute(
        select(User, WorkerHeartbeat)
        .outerjoin(WorkerHeartbeat, WorkerHeartbeat.user_id == User.id)
        .order_by(User.created_at.desc())
    )
    now = datetime.utcnow()
    out: list[AgentStatusOut] = []
    for user, hb in result.all():
        online = hb is not None and (now - hb.last_seen).total_seconds() <= WORKER_LIVE_WINDOW_S
        out.append(
            AgentStatusOut(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                company_name=user.company_name,
                is_active=user.is_active,
                worker_online=online,
                last_seen=hb.last_seen.isoformat() if hb and hb.last_seen else None,
                hostname=hb.hostname if hb else None,
                current_job=hb.current_job if hb else None,
            )
        )
    return out


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
    if body.is_test_user is not None:
        if body.is_test_user and user.is_admin:
            raise HTTPException(status_code=400, detail="אדמין לא יכול להיות משתמש בדיקה")
        user.is_test_user = body.is_test_user

    await db.commit()
    await db.refresh(user)

    return _user_admin_out(user)


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


@router.get("/operations")
async def operations(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin operations dashboard: monthly cycle per worker, worker liveness,
    Mail Agent, מסלקה link + downloads, agreement requests — every agent."""
    from app.services.admin_operations import operations_overview
    return await operations_overview(db)

