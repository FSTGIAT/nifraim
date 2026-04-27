"""Agency super-user service.

This is the ONLY file allowed to query across `user_id` boundaries. Every other
service is strictly per-agent. Functions here always require an `agency_id` and
restrict the fan-out to `User.agency_id == agency_id`.
"""
import logging
import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.agency import Agency
from app.models.agency_invite import AgencyInvite
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.production_summary import ProductionSummary
from app.models.volume_bonus_payment import VolumeBonusPayment
from app.models.commission_rate import CommissionRate
from app.models.company_contact import CompanyContact
from app.models.recruit import Recruit
from app.services.auth_service import hash_password
from app.services.email_service import _send_email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import settings

logger = logging.getLogger(__name__)

# A "lost money" record is one where the agency expected commission but didn't
# fully receive it. paid_mismatch is included only when actual < expected.
UNPAID_STATUSES = ("unpaid", "no_data", "paid_mismatch")


# ─── Member queries ─────────────────────────────────────────────────────────

async def list_agents(db: AsyncSession, agency_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User)
        .where(User.agency_id == agency_id, User.role == "agent")
        .order_by(User.full_name.asc())
    )
    return list(result.scalars().all())


async def _agent_ids(db: AsyncSession, agency_id: uuid.UUID) -> list[uuid.UUID]:
    """All user_ids whose data the agency super-user is allowed to read."""
    result = await db.execute(
        select(User.id).where(User.agency_id == agency_id)
    )
    return [row[0] for row in result.all()]


# ─── Headline overview ──────────────────────────────────────────────────────

async def agency_overview(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """Six headline KPIs the חשב עמלות sees on the agency dashboard."""
    agent_ids = await _agent_ids(db, agency_id)
    # Distinct count of *agents only* — excludes the super-user themselves so
    # the headline "X סוכנים" stays accurate when the super-user is an agency
    # member (which they always are).
    agents = await list_agents(db, agency_id)
    pure_agent_count = len(agents)
    if not agent_ids:
        return _empty_overview()

    # Active production uploads per agent (one per agent at most)
    prod_uploads_q = await db.execute(
        select(FileUpload.id, FileUpload.user_id, FileUpload.uploaded_at)
        .where(
            FileUpload.user_id.in_(agent_ids),
            FileUpload.is_production == True,
        )
    )
    prod_uploads = list(prod_uploads_q.all())
    prod_upload_ids = [row[0] for row in prod_uploads]
    last_upload_at = max((row[2] for row in prod_uploads), default=None)

    if not prod_upload_ids:
        return _empty_overview() | {"agent_count": pure_agent_count}

    # Premium + accumulation totals from the active production records.
    totals_row = (await db.execute(
        select(
            func.coalesce(func.sum(ClientRecord.total_premium), 0),
            func.coalesce(func.sum(ClientRecord.accumulation), 0),
            func.count(func.distinct(ClientRecord.id_number)),
        )
        .where(ClientRecord.upload_id.in_(prod_upload_ids))
    )).one()
    total_premium = float(totals_row[0] or 0)
    total_accumulation = float(totals_row[1] or 0)
    unique_clients = int(totals_row[2] or 0)

    # Lost money: expected commission − actual commission for any unpaid status,
    # summed across the entire agency.
    lost_row = (await db.execute(
        select(
            func.coalesce(
                func.sum(
                    func.coalesce(ClientRecord.expected_amount, 0)
                    - func.coalesce(ClientRecord.actual_amount, 0)
                ),
                0,
            ),
            func.count(),
        )
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
        )
    )).one()
    lost_amount = float(lost_row[0] or 0)
    lost_policy_count = int(lost_row[1] or 0)

    # Top losing company.
    top_lost_company_q = await db.execute(
        select(
            ClientRecord.receiving_company,
            func.coalesce(
                func.sum(
                    func.coalesce(ClientRecord.expected_amount, 0)
                    - func.coalesce(ClientRecord.actual_amount, 0)
                ),
                0,
            ).label("lost"),
        )
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
            ClientRecord.receiving_company.isnot(None),
        )
        .group_by(ClientRecord.receiving_company)
        .order_by(func.coalesce(func.sum(
            func.coalesce(ClientRecord.expected_amount, 0)
            - func.coalesce(ClientRecord.actual_amount, 0)
        ), 0).desc())
        .limit(1)
    )
    top_lost = top_lost_company_q.first()

    # Bonus pipeline this year — count of (agent, company) bonuses + how many paid.
    current_year = datetime.utcnow().year
    bonus_total = (await db.execute(
        select(func.count()).where(
            VolumeBonusPayment.user_id.in_(agent_ids),
            VolumeBonusPayment.year == current_year,
        )
    )).scalar_one()
    bonus_paid = (await db.execute(
        select(func.count()).where(
            VolumeBonusPayment.user_id.in_(agent_ids),
            VolumeBonusPayment.year == current_year,
            VolumeBonusPayment.is_paid == True,
        )
    )).scalar_one()

    return {
        "agent_count": pure_agent_count,
        "agents_with_data": sum(1 for _ in prod_upload_ids),
        "unique_clients": unique_clients,
        "total_premium": total_premium,
        "total_accumulation": total_accumulation,
        "lost_money_amount": lost_amount,
        "lost_money_policy_count": lost_policy_count,
        "top_lost_company": {
            "name": top_lost[0] if top_lost else None,
            "amount": float(top_lost[1]) if top_lost else 0.0,
        },
        "bonus_total_this_year": int(bonus_total or 0),
        "bonus_paid_this_year": int(bonus_paid or 0),
        "last_upload_at": last_upload_at.isoformat() if last_upload_at else None,
    }


def _empty_overview() -> dict:
    return {
        "agent_count": 0,
        "agents_with_data": 0,
        "unique_clients": 0,
        "total_premium": 0.0,
        "total_accumulation": 0.0,
        "lost_money_amount": 0.0,
        "lost_money_policy_count": 0,
        "top_lost_company": {"name": None, "amount": 0.0},
        "bonus_total_this_year": 0,
        "bonus_paid_this_year": 0,
        "last_upload_at": None,
    }


# ─── Agent leaderboard ──────────────────────────────────────────────────────

async def agent_leaderboard(db: AsyncSession, agency_id: uuid.UUID) -> list[dict]:
    """Per-agent rollup for the leaderboard table."""
    agents = await list_agents(db, agency_id)
    if not agents:
        return []
    agent_ids = [a.id for a in agents]

    # Active production per agent (one row per agent)
    prod_rows = (await db.execute(
        select(FileUpload.user_id, FileUpload.id, FileUpload.uploaded_at)
        .where(
            FileUpload.user_id.in_(agent_ids),
            FileUpload.is_production == True,
        )
    )).all()
    prod_by_user: dict[uuid.UUID, tuple[uuid.UUID, datetime]] = {
        row[0]: (row[1], row[2]) for row in prod_rows
    }
    prod_upload_ids = [v[0] for v in prod_by_user.values()]

    # Production totals per agent (premium / accumulation / clients)
    totals_by_user: dict[uuid.UUID, tuple[float, float, int]] = {}
    if prod_upload_ids:
        rows = (await db.execute(
            select(
                ClientRecord.user_id,
                func.coalesce(func.sum(ClientRecord.total_premium), 0),
                func.coalesce(func.sum(ClientRecord.accumulation), 0),
                func.count(func.distinct(ClientRecord.id_number)),
            )
            .where(ClientRecord.upload_id.in_(prod_upload_ids))
            .group_by(ClientRecord.user_id)
        )).all()
        totals_by_user = {
            row[0]: (float(row[1] or 0), float(row[2] or 0), int(row[3] or 0))
            for row in rows
        }

    # Lost money per agent (across ALL their uploads, not just production)
    lost_rows = (await db.execute(
        select(
            ClientRecord.user_id,
            func.coalesce(
                func.sum(
                    func.coalesce(ClientRecord.expected_amount, 0)
                    - func.coalesce(ClientRecord.actual_amount, 0)
                ),
                0,
            ),
            func.count(),
        )
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
        )
        .group_by(ClientRecord.user_id)
    )).all()
    lost_by_user: dict[uuid.UUID, tuple[float, int]] = {
        row[0]: (float(row[1] or 0), int(row[2] or 0)) for row in lost_rows
    }

    out: list[dict] = []
    for a in agents:
        prod = prod_by_user.get(a.id)
        premium, accumulation, clients = totals_by_user.get(a.id, (0.0, 0.0, 0))
        lost_amount, lost_count = lost_by_user.get(a.id, (0.0, 0))
        out.append({
            "user_id": str(a.id),
            "full_name": a.full_name or a.email,
            "email": a.email,
            "has_production": prod is not None,
            "last_upload_at": prod[1].isoformat() if prod else None,
            "total_premium": premium,
            "total_accumulation": accumulation,
            "unique_clients": clients,
            "lost_money_amount": lost_amount,
            "lost_money_policy_count": lost_count,
        })
    # Sort by lost-money-amount desc — the controller's natural reading order.
    out.sort(key=lambda r: r["lost_money_amount"], reverse=True)
    return out


# ─── Reconciliation report ──────────────────────────────────────────────────

async def unpaid_commission_by_company(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """Aggregated unpaid commission grouped by paying company, agency-wide."""
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"by_company": [], "top_policies": []}

    by_company_rows = (await db.execute(
        select(
            ClientRecord.receiving_company,
            ClientRecord.reconciliation_status,
            func.coalesce(
                func.sum(
                    func.coalesce(ClientRecord.expected_amount, 0)
                    - func.coalesce(ClientRecord.actual_amount, 0)
                ),
                0,
            ),
            func.count(),
        )
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
            ClientRecord.receiving_company.isnot(None),
        )
        .group_by(ClientRecord.receiving_company, ClientRecord.reconciliation_status)
    )).all()

    by_company: dict[str, dict] = {}
    for company, status, amount, count in by_company_rows:
        slot = by_company.setdefault(company, {"company": company, "amount": 0.0, "policies": 0, "by_status": {}})
        slot["amount"] += float(amount or 0)
        slot["policies"] += int(count or 0)
        slot["by_status"][status] = {"amount": float(amount or 0), "policies": int(count or 0)}
    by_company_list = sorted(by_company.values(), key=lambda r: r["amount"], reverse=True)

    return {
        "by_company": by_company_list,
        "top_policies": await top_lost_money(db, agency_id, limit=50),
    }


async def top_lost_money(db: AsyncSession, agency_id: uuid.UUID, limit: int = 50) -> list[dict]:
    """Highest-₪ unpaid policies across the entire agency, agent-attributed."""
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return []

    diff_expr = (
        func.coalesce(ClientRecord.expected_amount, 0)
        - func.coalesce(ClientRecord.actual_amount, 0)
    )
    rows = (await db.execute(
        select(
            ClientRecord.id,
            ClientRecord.user_id,
            ClientRecord.receiving_company,
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.product,
            ClientRecord.fund_policy_number,
            ClientRecord.expected_amount,
            ClientRecord.actual_amount,
            ClientRecord.reconciliation_status,
            diff_expr.label("diff"),
        )
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
        )
        .order_by(diff_expr.desc())
        .limit(limit)
    )).all()

    # Resolve agent display names (small N — agency size).
    user_rows = (await db.execute(
        select(User.id, User.full_name, User.email).where(User.id.in_(agent_ids))
    )).all()
    user_label = {row[0]: (row[1] or row[2]) for row in user_rows}

    out = []
    for row in rows:
        first = (row[4] or "").strip()
        last = (row[5] or "").strip()
        out.append({
            "record_id": str(row[0]),
            "agent_user_id": str(row[1]),
            "agent_name": user_label.get(row[1], ""),
            "company": row[2],
            "client_id_number": row[3],
            "client_name": (first + " " + last).strip() or None,
            "product": row[6],
            "policy_number": row[7],
            "expected_amount": float(row[8] or 0),
            "actual_amount": float(row[9] or 0),
            "lost_amount": float(row[11] or 0),
            "status": row[10],
        })
    return out


# ─── Bonus pipeline ─────────────────────────────────────────────────────────

async def missing_commission(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """Headline KPI for the חשב עמלות: missing commission this period vs previous.

    Returns:
      - this_month, last_month: { period_label, amount, policies, top_companies[] }
      - trend: monthly aggregate for the last ~12 months
      - delta_pct: % change month over month
    """
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return _empty_missing()

    # SQL "lost amount" per record = expected − actual (only for unpaid statuses)
    diff_expr = (
        func.coalesce(ClientRecord.expected_amount, 0)
        - func.coalesce(ClientRecord.actual_amount, 0)
    )
    period_expr = func.to_char(FileUpload.uploaded_at, "YYYY-MM").label("period")

    # Per-month rollup
    rows = (await db.execute(
        select(
            period_expr,
            func.coalesce(func.sum(diff_expr), 0),
            func.count(),
        )
        .select_from(ClientRecord)
        .join(FileUpload, ClientRecord.upload_id == FileUpload.id)
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
        )
        .group_by(period_expr)
        .order_by(period_expr)
    )).all()
    trend = [
        {"period": r[0], "amount": float(r[1] or 0), "policies": int(r[2] or 0)}
        for r in rows
        if r[0] is not None
    ]

    # Top companies for the latest 2 months
    async def top_companies_for(period: str | None) -> list[dict]:
        if not period:
            return []
        out = (await db.execute(
            select(
                ClientRecord.receiving_company,
                func.coalesce(func.sum(diff_expr), 0),
                func.count(),
            )
            .select_from(ClientRecord)
            .join(FileUpload, ClientRecord.upload_id == FileUpload.id)
            .where(
                ClientRecord.user_id.in_(agent_ids),
                ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
                ClientRecord.receiving_company.isnot(None),
                period_expr == period,
            )
            .group_by(ClientRecord.receiving_company)
            .order_by(func.coalesce(func.sum(diff_expr), 0).desc())
            .limit(3)
        )).all()
        return [
            {"company": r[0], "amount": float(r[1] or 0), "policies": int(r[2] or 0)}
            for r in out
        ]

    this_month = trend[-1] if len(trend) >= 1 else None
    last_month = trend[-2] if len(trend) >= 2 else None
    if this_month:
        this_month["top_companies"] = await top_companies_for(this_month["period"])
    if last_month:
        last_month["top_companies"] = await top_companies_for(last_month["period"])

    delta_pct = None
    if this_month and last_month and last_month["amount"] > 0:
        delta_pct = ((this_month["amount"] - last_month["amount"]) / last_month["amount"]) * 100

    return {
        "this_month": this_month,
        "last_month": last_month,
        "delta_pct": delta_pct,
        "trend": trend,
    }


def _empty_missing() -> dict:
    return {"this_month": None, "last_month": None, "delta_pct": None, "trend": []}


async def agent_detail(
    db: AsyncSession, agency_id: uuid.UUID, agent_id: uuid.UUID
) -> dict | None:
    """Full per-agent breakdown for the drill-in modal.

    Restricted to agents within `agency_id`. Returns None if not found / not
    a member. The caller is expected to be the agency super-user.
    """
    user_row = (await db.execute(
        select(User).where(User.id == agent_id, User.agency_id == agency_id)
    )).scalar_one_or_none()
    if not user_row:
        return None

    # Active production upload
    prod_q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == agent_id,
            FileUpload.is_production == True,
        )
    )
    prod = prod_q.scalar_one_or_none()
    prod_upload_id = prod.id if prod else None

    diff_expr = (
        func.coalesce(ClientRecord.expected_amount, 0)
        - func.coalesce(ClientRecord.actual_amount, 0)
    )

    # KPIs from the active production
    kpi = {"total_premium": 0.0, "total_accumulation": 0.0, "unique_clients": 0}
    if prod_upload_id:
        row = (await db.execute(
            select(
                func.coalesce(func.sum(ClientRecord.total_premium), 0),
                func.coalesce(func.sum(ClientRecord.accumulation), 0),
                func.count(func.distinct(ClientRecord.id_number)),
            ).where(ClientRecord.upload_id == prod_upload_id)
        )).one()
        kpi = {
            "total_premium": float(row[0] or 0),
            "total_accumulation": float(row[1] or 0),
            "unique_clients": int(row[2] or 0),
        }

    # Lost money for this agent
    lost_row = (await db.execute(
        select(
            func.coalesce(func.sum(diff_expr), 0),
            func.count(),
        ).where(
            ClientRecord.user_id == agent_id,
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
        )
    )).one()
    lost_amount = float(lost_row[0] or 0)
    lost_count = int(lost_row[1] or 0)

    # By company — premium AND lost money grouped (active production only for premium;
    # all records for lost-money since recon is across all uploads).
    by_company_premium: list[dict] = []
    if prod_upload_id:
        rows = (await db.execute(
            select(
                ClientRecord.receiving_company,
                func.coalesce(func.sum(ClientRecord.total_premium), 0),
                func.count(func.distinct(ClientRecord.id_number)),
            )
            .where(
                ClientRecord.upload_id == prod_upload_id,
                ClientRecord.receiving_company.isnot(None),
            )
            .group_by(ClientRecord.receiving_company)
            .order_by(func.coalesce(func.sum(ClientRecord.total_premium), 0).desc())
            .limit(8)
        )).all()
        by_company_premium = [
            {"company": r[0], "premium": float(r[1] or 0), "clients": int(r[2] or 0)}
            for r in rows
        ]

    by_company_lost: list[dict] = []
    rows = (await db.execute(
        select(
            ClientRecord.receiving_company,
            func.coalesce(func.sum(diff_expr), 0),
            func.count(),
        )
        .where(
            ClientRecord.user_id == agent_id,
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
            ClientRecord.receiving_company.isnot(None),
        )
        .group_by(ClientRecord.receiving_company)
        .order_by(func.coalesce(func.sum(diff_expr), 0).desc())
        .limit(8)
    )).all()
    by_company_lost = [
        {"company": r[0], "amount": float(r[1] or 0), "policies": int(r[2] or 0)}
        for r in rows
    ]

    # Reconciliation status distribution (donut)
    status_rows = (await db.execute(
        select(
            ClientRecord.reconciliation_status,
            func.count(),
            func.coalesce(func.sum(diff_expr), 0),
        )
        .where(ClientRecord.user_id == agent_id)
        .group_by(ClientRecord.reconciliation_status)
    )).all()
    status_distribution = [
        {"status": r[0] or "unknown", "count": int(r[1]), "amount": float(r[2] or 0)}
        for r in status_rows
    ]

    # Top 10 customers by premium (from active production)
    top_customers: list[dict] = []
    if prod_upload_id:
        rows = (await db.execute(
            select(
                ClientRecord.id_number,
                ClientRecord.first_name,
                ClientRecord.last_name,
                func.coalesce(func.sum(ClientRecord.total_premium), 0),
                func.coalesce(func.sum(ClientRecord.accumulation), 0),
                func.count(),
            )
            .where(
                ClientRecord.upload_id == prod_upload_id,
                ClientRecord.id_number.isnot(None),
            )
            .group_by(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name)
            .order_by(func.coalesce(func.sum(ClientRecord.total_premium), 0).desc())
            .limit(10)
        )).all()
        top_customers = [
            {
                "id_number": r[0],
                "name": ((r[1] or "") + " " + (r[2] or "")).strip() or None,
                "premium": float(r[3] or 0),
                "accumulation": float(r[4] or 0),
                "products": int(r[5] or 0),
            }
            for r in rows
        ]

    # Premium trend per period (this agent only)
    trend_rows = (await db.execute(
        select(
            ProductionSummary.period_label,
            func.coalesce(func.sum(ProductionSummary.total_premium), 0),
        )
        .where(ProductionSummary.user_id == agent_id)
        .group_by(ProductionSummary.period_label)
        .order_by(ProductionSummary.period_label.asc())
    )).all()
    premium_trend = [{"period": r[0], "amount": float(r[1] or 0)} for r in trend_rows]

    # Recent uploads (last 5)
    rec_q = (await db.execute(
        select(FileUpload)
        .where(FileUpload.user_id == agent_id)
        .order_by(FileUpload.uploaded_at.desc())
        .limit(5)
    )).scalars().all()
    recent_uploads = [
        {
            "id": str(u.id),
            "filename": u.filename,
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
            "record_count": u.record_count or 0,
            "is_production": bool(u.is_production),
            "company_source": u.company_source,
        }
        for u in rec_q
    ]

    # Bonus rows for this agent
    bonus_rows = (await db.execute(
        select(VolumeBonusPayment.company_name, VolumeBonusPayment.is_paid, VolumeBonusPayment.year)
        .where(VolumeBonusPayment.user_id == agent_id)
        .order_by(VolumeBonusPayment.year.desc())
    )).all()
    bonus = [
        {"company": r[0], "is_paid": bool(r[1]), "year": int(r[2])}
        for r in bonus_rows
    ]

    return {
        "user": {
            "id": str(user_row.id),
            "full_name": user_row.full_name or user_row.email,
            "email": user_row.email,
            "phone": user_row.phone,
        },
        "kpi": {
            **kpi,
            "lost_money_amount": lost_amount,
            "lost_money_policy_count": lost_count,
        },
        "by_company_premium": by_company_premium,
        "by_company_lost": by_company_lost,
        "status_distribution": status_distribution,
        "top_customers": top_customers,
        "premium_trend": premium_trend,
        "recent_uploads": recent_uploads,
        "bonus": bonus,
    }


# ─── Tab overviews (mirror the regular agent's workspace tabs, agency-aggregated) ───

async def production_overview(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """Aggregated production data for the agency `פרודוקציה` tab."""
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"kpi": _empty_prod_kpi(), "by_company": [], "top_clients": [], "by_agent": []}

    # Active production uploads per agent
    prod_rows = (await db.execute(
        select(FileUpload.id, FileUpload.user_id, FileUpload.uploaded_at)
        .where(FileUpload.user_id.in_(agent_ids), FileUpload.is_production == True)
    )).all()
    prod_upload_ids = [r[0] for r in prod_rows]

    if not prod_upload_ids:
        return {"kpi": _empty_prod_kpi() | {"agents_with_data": 0}, "by_company": [], "top_clients": [], "by_agent": []}

    # KPI row
    kpi_row = (await db.execute(
        select(
            func.coalesce(func.sum(ClientRecord.total_premium), 0),
            func.coalesce(func.sum(ClientRecord.accumulation), 0),
            func.count(func.distinct(ClientRecord.id_number)),
            func.count(),
        ).where(ClientRecord.upload_id.in_(prod_upload_ids))
    )).one()
    kpi = {
        "total_premium": float(kpi_row[0] or 0),
        "total_accumulation": float(kpi_row[1] or 0),
        "unique_clients": int(kpi_row[2] or 0),
        "total_records": int(kpi_row[3] or 0),
        "agents_with_data": len(prod_rows),
    }

    # By paying company
    co_rows = (await db.execute(
        select(
            ClientRecord.receiving_company,
            func.coalesce(func.sum(ClientRecord.total_premium), 0),
            func.coalesce(func.sum(ClientRecord.accumulation), 0),
            func.count(func.distinct(ClientRecord.id_number)),
            func.count(),
        )
        .where(ClientRecord.upload_id.in_(prod_upload_ids), ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(func.coalesce(func.sum(ClientRecord.total_premium), 0).desc())
        .limit(20)
    )).all()
    by_company = [
        {
            "company": r[0],
            "total_premium": float(r[1] or 0),
            "total_accumulation": float(r[2] or 0),
            "unique_clients": int(r[3] or 0),
            "records": int(r[4] or 0),
        }
        for r in co_rows
    ]

    # Top clients (across the whole agency)
    cli_rows = (await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.user_id,
            func.coalesce(func.sum(ClientRecord.total_premium), 0),
            func.coalesce(func.sum(ClientRecord.accumulation), 0),
            func.count(),
        )
        .where(ClientRecord.upload_id.in_(prod_upload_ids), ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name, ClientRecord.user_id)
        .order_by(func.coalesce(func.sum(ClientRecord.total_premium), 0).desc())
        .limit(15)
    )).all()
    user_label_map = await _user_label_map(db, [row[3] for row in cli_rows])
    top_clients = [
        {
            "id_number": r[0],
            "name": ((r[1] or "") + " " + (r[2] or "")).strip() or None,
            "agent_user_id": str(r[3]),
            "agent_name": user_label_map.get(r[3], ""),
            "total_premium": float(r[4] or 0),
            "total_accumulation": float(r[5] or 0),
            "products": int(r[6] or 0),
        }
        for r in cli_rows
    ]

    # Per-agent contribution
    agent_rows = (await db.execute(
        select(
            ClientRecord.user_id,
            func.coalesce(func.sum(ClientRecord.total_premium), 0),
            func.count(func.distinct(ClientRecord.id_number)),
        )
        .where(ClientRecord.upload_id.in_(prod_upload_ids))
        .group_by(ClientRecord.user_id)
        .order_by(func.coalesce(func.sum(ClientRecord.total_premium), 0).desc())
    )).all()
    agent_label_map = await _user_label_map(db, [row[0] for row in agent_rows])
    by_agent = [
        {
            "user_id": str(r[0]),
            "name": agent_label_map.get(r[0], ""),
            "total_premium": float(r[1] or 0),
            "unique_clients": int(r[2] or 0),
        }
        for r in agent_rows
    ]

    return {"kpi": kpi, "by_company": by_company, "top_clients": top_clients, "by_agent": by_agent}


def _empty_prod_kpi() -> dict:
    return {
        "total_premium": 0.0, "total_accumulation": 0.0,
        "unique_clients": 0, "total_records": 0, "agents_with_data": 0,
    }


async def comparison_overview(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """The headline tab — agency-wide השוואת נפרעים aggregation.

    Buckets follow the regular agent ComparisonDashboard:
      - matched_count       = records with reconciliation_status == 'paid_match'
      - unpaid_count        = records with reconciliation_status in (unpaid, paid_mismatch, no_data)
      - only_commission_count = records that exist only in a commission file (file_category='commission')
                                with id_numbers that don't appear in any production file for that agent
    """
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return _empty_comparison()

    diff_expr = (
        func.coalesce(ClientRecord.expected_amount, 0)
        - func.coalesce(ClientRecord.actual_amount, 0)
    )

    # Per-status totals across the agency
    status_rows = (await db.execute(
        select(
            ClientRecord.reconciliation_status,
            func.count(),
            func.coalesce(func.sum(diff_expr), 0),
            func.coalesce(func.sum(ClientRecord.total_premium), 0),
        )
        .where(ClientRecord.user_id.in_(agent_ids))
        .group_by(ClientRecord.reconciliation_status)
    )).all()

    matched_count = 0
    unpaid_count = 0
    total_unpaid_amount = 0.0
    total_premium = 0.0
    for status, count, diff_sum, prem_sum in status_rows:
        n = int(count or 0)
        d = float(diff_sum or 0)
        p = float(prem_sum or 0)
        total_premium += p
        if status == "paid_match":
            matched_count += n
        elif status in UNPAID_STATUSES:
            unpaid_count += n
            total_unpaid_amount += d

    # Per-company breakdown
    by_co_rows = (await db.execute(
        select(
            ClientRecord.receiving_company,
            ClientRecord.reconciliation_status,
            func.count(),
            func.coalesce(func.sum(diff_expr), 0),
        )
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.receiving_company.isnot(None),
        )
        .group_by(ClientRecord.receiving_company, ClientRecord.reconciliation_status)
    )).all()
    co_acc: dict[str, dict] = {}
    for company, status, count, diff_sum in by_co_rows:
        slot = co_acc.setdefault(company, {
            "company": company,
            "matched": 0, "unpaid": 0, "only_commission": 0,
            "unpaid_amount": 0.0,
        })
        n = int(count or 0)
        if status == "paid_match":
            slot["matched"] += n
        elif status in UNPAID_STATUSES:
            slot["unpaid"] += n
            slot["unpaid_amount"] += float(diff_sum or 0)
    by_company = sorted(co_acc.values(), key=lambda r: r["unpaid"], reverse=True)

    # Top unpaid customers across the agency
    cust_rows = (await db.execute(
        select(
            ClientRecord.id,
            ClientRecord.user_id,
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.receiving_company,
            ClientRecord.product,
            ClientRecord.fund_policy_number,
            ClientRecord.expected_amount,
            ClientRecord.actual_amount,
            ClientRecord.reconciliation_status,
            diff_expr,
        )
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
        )
        .order_by(diff_expr.desc())
        .limit(50)
    )).all()
    user_label_map = await _user_label_map(db, [row[1] for row in cust_rows])
    top_unpaid = [
        {
            "record_id": str(r[0]),
            "agent_user_id": str(r[1]),
            "agent_name": user_label_map.get(r[1], ""),
            "id_number": r[2],
            "name": ((r[3] or "") + " " + (r[4] or "")).strip() or None,
            "company": r[5],
            "product": r[6],
            "policy_number": r[7],
            "expected_amount": float(r[8] or 0),
            "actual_amount": float(r[9] or 0),
            "status": r[10],
            "unpaid_amount": float(r[11] or 0),
        }
        for r in cust_rows
    ]

    # Per-agent
    agent_rows = (await db.execute(
        select(
            ClientRecord.user_id,
            ClientRecord.reconciliation_status,
            func.count(),
            func.coalesce(func.sum(diff_expr), 0),
        )
        .where(ClientRecord.user_id.in_(agent_ids))
        .group_by(ClientRecord.user_id, ClientRecord.reconciliation_status)
    )).all()
    ag_acc: dict[uuid.UUID, dict] = {}
    for uid, status, count, diff_sum in agent_rows:
        slot = ag_acc.setdefault(uid, {
            "user_id": str(uid),
            "matched": 0, "unpaid": 0,
            "unpaid_amount": 0.0,
        })
        n = int(count or 0)
        if status == "paid_match":
            slot["matched"] += n
        elif status in UNPAID_STATUSES:
            slot["unpaid"] += n
            slot["unpaid_amount"] += float(diff_sum or 0)
    agent_label_map = await _user_label_map(db, list(ag_acc.keys()))
    by_agent = []
    for uid, slot in ag_acc.items():
        slot["name"] = agent_label_map.get(uid, "")
        by_agent.append(slot)
    by_agent.sort(key=lambda r: r["unpaid"], reverse=True)

    summary = {
        "matched_count": matched_count,
        "unpaid_count": unpaid_count,
        "only_commission_count": 0,  # placeholder — requires per-agent compare run, not available here
        "total_customers": matched_count + unpaid_count,
        "total_premium": total_premium,
        "total_unpaid_amount": total_unpaid_amount,
    }
    return {
        "summary": summary,
        "by_company": by_company,
        "top_unpaid_customers": top_unpaid,
        "by_agent": by_agent,
    }


def _empty_comparison() -> dict:
    return {
        "summary": {
            "matched_count": 0, "unpaid_count": 0, "only_commission_count": 0,
            "total_customers": 0, "total_premium": 0.0, "total_unpaid_amount": 0.0,
        },
        "by_company": [], "top_unpaid_customers": [], "by_agent": [],
    }


async def commission_rates_overview(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """Read-only summary of commission rates configured by all agency members."""
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"by_company": []}

    rows = (await db.execute(
        select(
            CommissionRate.company_name,
            CommissionRate.rate,
            CommissionRate.payment_frequency,
            CommissionRate.user_id,
        )
        .where(CommissionRate.user_id.in_(agent_ids))
    )).all()
    user_label_map = await _user_label_map(db, [r[3] for r in rows])

    co_acc: dict[str, dict] = {}
    for company, rate, freq, uid in rows:
        slot = co_acc.setdefault(company, {
            "company": company,
            "agent_count_with_rate": 0,
            "rates": [],
        })
        slot["agent_count_with_rate"] += 1
        slot["rates"].append({
            "agent_name": user_label_map.get(uid, ""),
            "rate": float(rate or 0),
            "payment_frequency": freq,
        })
    return {"by_company": sorted(co_acc.values(), key=lambda r: r["agent_count_with_rate"], reverse=True)}


async def company_emails_overview(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """Read-only list of company contact emails set by any member of the agency."""
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"by_company": []}

    rows = (await db.execute(
        select(
            CompanyContact.company_name,
            CompanyContact.email,
            CompanyContact.contact_name,
            CompanyContact.user_id,
        )
        .where(CompanyContact.user_id.in_(agent_ids))
    )).all()
    user_label_map = await _user_label_map(db, [r[3] for r in rows])

    co_acc: dict[str, dict] = {}
    for company, email, name, uid in rows:
        slot = co_acc.setdefault(company, {"company": company, "contacts": []})
        slot["contacts"].append({
            "email": email,
            "contact_name": name,
            "agent_name": user_label_map.get(uid, ""),
        })
    return {"by_company": sorted(co_acc.values(), key=lambda r: len(r["contacts"]), reverse=True)}


async def recruits_overview(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """Aggregated recruits across the agency."""
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"totals": {"total": 0, "by_category": {}}, "by_company": []}

    rows = (await db.execute(
        select(
            Recruit.company,
            Recruit.category,
            func.count(),
            func.coalesce(func.sum(Recruit.amount), 0),
        )
        .where(Recruit.user_id.in_(agent_ids))
        .group_by(Recruit.company, Recruit.category)
    )).all()
    total = 0
    by_cat: dict[str, int] = {}
    co_acc: dict[str, dict] = {}
    for company, category, count, amount in rows:
        n = int(count or 0)
        total += n
        cat = category or "financial"
        by_cat[cat] = by_cat.get(cat, 0) + n
        slot = co_acc.setdefault(company or "—", {
            "company": company or "—",
            "total": 0,
            "amount": 0.0,
        })
        slot["total"] += n
        slot["amount"] += float(amount or 0)
    by_company = sorted(co_acc.values(), key=lambda r: r["total"], reverse=True)
    return {
        "totals": {"total": total, "by_category": by_cat},
        "by_company": by_company,
    }


async def _user_label_map(db: AsyncSession, user_ids):
    """Resolve {user_id → display name} for a small set of agents."""
    ids = [uid for uid in (user_ids or []) if uid is not None]
    if not ids:
        return {}
    rows = (await db.execute(
        select(User.id, User.full_name, User.email).where(User.id.in_(ids))
    )).all()
    return {row[0]: (row[1] or row[2]) for row in rows}


# ─── Daily-workflow endpoints (chashav-עמלות real workflow) ─────────────────

# Default agency override — what fraction of gross commission the agency keeps.
# Used until per-agent overrides become a configurable column.
DEFAULT_OVERRIDE_PCT = 0.20


async def sub_agent_splits(
    db: AsyncSession, agency_id: uuid.UUID, override_pct: float = DEFAULT_OVERRIDE_PCT
) -> dict:
    """חישוב עמלות סוכני משנה: per-agent gross commission, agency override, net to agent.

    `gross` = sum of `actual_amount` across all the agent's commission records
              (i.e. what the insurance companies actually paid for that agent's book).
    `override` = `gross * override_pct` — what the agency takes off the top.
    `net` = `gross - override` — what flows to the end agent.
    """
    agents = await list_agents(db, agency_id)
    if not agents:
        return {"override_pct": override_pct, "rows": [], "totals": _empty_split()}

    rows = (await db.execute(
        select(
            ClientRecord.user_id,
            func.coalesce(func.sum(ClientRecord.actual_amount), 0),
            func.coalesce(func.sum(ClientRecord.expected_amount), 0),
        )
        .where(
            ClientRecord.user_id.in_([a.id for a in agents]),
            ClientRecord.actual_amount.isnot(None),
        )
        .group_by(ClientRecord.user_id)
    )).all()
    paid_by = {r[0]: float(r[1] or 0) for r in rows}
    expected_by = {r[0]: float(r[2] or 0) for r in rows}

    out = []
    totals = {"gross": 0.0, "override": 0.0, "net": 0.0, "expected": 0.0}
    for a in agents:
        gross = paid_by.get(a.id, 0.0)
        expected = expected_by.get(a.id, 0.0)
        override = round(gross * override_pct, 2)
        net = round(gross - override, 2)
        out.append({
            "user_id": str(a.id),
            "name": a.full_name or a.email,
            "gross": gross,
            "override": override,
            "net": net,
            "expected": expected,
        })
        totals["gross"] += gross
        totals["override"] += override
        totals["net"] += net
        totals["expected"] += expected
    out.sort(key=lambda r: r["gross"], reverse=True)
    return {"override_pct": override_pct, "rows": out, "totals": totals}


def _empty_split() -> dict:
    return {"gross": 0.0, "override": 0.0, "net": 0.0, "expected": 0.0}


async def storno_summary(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """סטורנו / ביטולים: cancelled policies aggregation per agent + per month.

    Uses `reconciliation_status == 'cancelled'`. Clawback amount per record =
    expected_amount (what the agency lost when the policy was cancelled).
    """
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"by_agent": [], "by_month": [], "totals": {"count": 0, "amount": 0.0}}

    period_expr = func.to_char(FileUpload.uploaded_at, "YYYY-MM").label("period")

    # Per agent
    agent_rows = (await db.execute(
        select(
            ClientRecord.user_id,
            func.count(),
            func.coalesce(func.sum(ClientRecord.expected_amount), 0),
        )
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status == "cancelled",
        )
        .group_by(ClientRecord.user_id)
    )).all()
    user_label = await _user_label_map(db, [r[0] for r in agent_rows])
    by_agent = [
        {
            "user_id": str(r[0]),
            "name": user_label.get(r[0], ""),
            "count": int(r[1]),
            "amount": float(r[2] or 0),
        }
        for r in agent_rows
    ]
    by_agent.sort(key=lambda r: r["amount"], reverse=True)

    # Trend per month
    month_rows = (await db.execute(
        select(
            period_expr,
            func.count(),
            func.coalesce(func.sum(ClientRecord.expected_amount), 0),
        )
        .select_from(ClientRecord)
        .join(FileUpload, ClientRecord.upload_id == FileUpload.id)
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status == "cancelled",
        )
        .group_by(period_expr)
        .order_by(period_expr)
    )).all()
    by_month = [
        {"period": r[0], "count": int(r[1]), "amount": float(r[2] or 0)}
        for r in month_rows if r[0] is not None
    ]

    totals = {
        "count": sum(r["count"] for r in by_agent),
        "amount": sum(r["amount"] for r in by_agent),
    }
    return {"by_agent": by_agent, "by_month": by_month, "totals": totals}


async def renewal_forecast(db: AsyncSession, agency_id: uuid.UUID, months_ahead: int = 6) -> dict:
    """תחזית renewals: project the next N months of recurring premium income.

    Naive but useful: use the latest production summary's `total_premium` for
    each agent as a monthly recurring proxy, multiply by the override+net split.
    Future: refine with policy-level renewal_date tracking.
    """
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"months_ahead": months_ahead, "history": [], "forecast": []}

    # Historical agency premium per period from production summaries
    rows = (await db.execute(
        select(
            ProductionSummary.period_label,
            func.coalesce(func.sum(ProductionSummary.total_premium), 0),
        )
        .where(ProductionSummary.user_id.in_(agent_ids))
        .group_by(ProductionSummary.period_label)
        .order_by(ProductionSummary.period_label.asc())
    )).all()
    history = [{"period": r[0], "amount": float(r[1] or 0)} for r in rows]

    # Forecast: average of last 3 historical points (or all if fewer)
    if not history:
        return {"months_ahead": months_ahead, "history": [], "forecast": []}
    recent = [h["amount"] for h in history[-3:]]
    baseline = sum(recent) / len(recent)
    growth = 1.0
    if len(history) >= 2:
        first, last = history[0]["amount"], history[-1]["amount"]
        if first > 0:
            growth = (last / first) ** (1 / max(1, len(history) - 1))
    growth = max(0.85, min(1.15, growth))  # clamp to sane range

    last_period = history[-1]["period"]  # "YYYY-MM"
    yr, mo = (int(p) for p in last_period.split("-"))
    forecast = []
    val = baseline
    for i in range(1, months_ahead + 1):
        mo += 1
        if mo > 12:
            mo = 1
            yr += 1
        val = val * growth
        # ±15% confidence band as proxy
        forecast.append({
            "period": f"{yr:04d}-{mo:02d}",
            "amount": round(val, 2),
            "low": round(val * 0.85, 2),
            "high": round(val * 1.15, 2),
        })
    return {
        "months_ahead": months_ahead,
        "growth_rate": round((growth - 1) * 100, 2),
        "history": history,
        "forecast": forecast,
    }


async def agent_payslip(
    db: AsyncSession, agency_id: uuid.UUID, agent_id: uuid.UUID,
    override_pct: float = DEFAULT_OVERRIDE_PCT,
) -> dict | None:
    """תלוש עמלות לסוכן: itemized monthly commission lines for one agent.

    Lines come from `ClientRecord.actual_amount` grouped by paying company.
    The slip totals: gross (sum of actual) → override deducted (configurable %)
    → net to agent. Includes recent storno (cancellations) as separate negative
    lines so the slip is "what we'd actually pay this month".
    """
    user_row = (await db.execute(
        select(User).where(User.id == agent_id, User.agency_id == agency_id)
    )).scalar_one_or_none()
    if not user_row:
        return None

    # Per-company totals (only paid records)
    co_rows = (await db.execute(
        select(
            ClientRecord.receiving_company,
            func.coalesce(func.sum(ClientRecord.actual_amount), 0),
            func.count(),
        )
        .where(
            ClientRecord.user_id == agent_id,
            ClientRecord.actual_amount.isnot(None),
            ClientRecord.actual_amount > 0,
            ClientRecord.receiving_company.isnot(None),
        )
        .group_by(ClientRecord.receiving_company)
        .order_by(func.coalesce(func.sum(ClientRecord.actual_amount), 0).desc())
    )).all()
    lines = [
        {"label": r[0], "amount": float(r[1] or 0), "policies": int(r[2] or 0), "kind": "income"}
        for r in co_rows
    ]
    gross = sum(l["amount"] for l in lines)

    # Storno (cancellation clawback) — negative
    storno_row = (await db.execute(
        select(
            func.coalesce(func.sum(ClientRecord.expected_amount), 0),
            func.count(),
        ).where(
            ClientRecord.user_id == agent_id,
            ClientRecord.reconciliation_status == "cancelled",
        )
    )).one()
    storno_amount = float(storno_row[0] or 0)
    storno_count = int(storno_row[1] or 0)
    if storno_count > 0:
        lines.append({"label": "סטורנו (ביטולים)", "amount": -storno_amount, "policies": storno_count, "kind": "deduction"})

    override_amount = round(gross * override_pct, 2)
    net = round(gross - override_amount - storno_amount, 2)

    return {
        "user": {
            "id": str(user_row.id),
            "name": user_row.full_name or user_row.email,
            "email": user_row.email,
        },
        "override_pct": override_pct,
        "lines": lines,
        "totals": {
            "gross": gross,
            "override": override_amount,
            "storno": storno_amount,
            "net": net,
        },
    }


async def exceptions_aging(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """חריגים בתורי טיפול: unpaid records grouped by aging bucket.

    Age = days since the file_uploads.uploaded_at for that record.
    Buckets: 0-30 / 31-60 / 61+. Per-company breakdown so the controller knows
    which insurance company to chase first.
    """
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"buckets": [], "by_company": [], "oldest": []}

    age_days = func.extract("day", func.now() - FileUpload.uploaded_at).label("age_days")

    rows = (await db.execute(
        select(
            ClientRecord.id,
            ClientRecord.user_id,
            ClientRecord.receiving_company,
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.expected_amount,
            ClientRecord.reconciliation_status,
            FileUpload.uploaded_at,
            age_days,
        )
        .select_from(ClientRecord)
        .join(FileUpload, ClientRecord.upload_id == FileUpload.id)
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.reconciliation_status.in_(UNPAID_STATUSES),
            ClientRecord.receiving_company.isnot(None),
        )
    )).all()

    bucket_acc = {"0-30": {"count": 0, "amount": 0.0}, "31-60": {"count": 0, "amount": 0.0}, "61+": {"count": 0, "amount": 0.0}}
    co_acc: dict[str, dict] = {}
    items = []
    for r in rows:
        age = int(r[9] or 0)
        amt = float(r[6] or 0)
        bucket = "0-30" if age <= 30 else ("31-60" if age <= 60 else "61+")
        bucket_acc[bucket]["count"] += 1
        bucket_acc[bucket]["amount"] += amt
        co = r[2]
        slot = co_acc.setdefault(co, {"company": co, "count": 0, "amount": 0.0, "oldest_age": 0})
        slot["count"] += 1
        slot["amount"] += amt
        if age > slot["oldest_age"]:
            slot["oldest_age"] = age
        items.append({
            "record_id": str(r[0]),
            "agent_user_id": str(r[1]),
            "company": co,
            "client_id_number": r[3],
            "client_name": ((r[4] or "") + " " + (r[5] or "")).strip() or None,
            "expected_amount": amt,
            "status": r[7],
            "uploaded_at": r[8].isoformat() if r[8] else None,
            "age_days": age,
        })

    # Resolve agent names for the oldest 20 items
    items.sort(key=lambda x: x["age_days"], reverse=True)
    oldest = items[:20]
    user_label = await _user_label_map(db, [uuid.UUID(o["agent_user_id"]) for o in oldest])
    for o in oldest:
        o["agent_name"] = user_label.get(uuid.UUID(o["agent_user_id"]), "")

    by_company = sorted(co_acc.values(), key=lambda r: r["amount"], reverse=True)[:10]
    buckets = [{"bucket": b, **v} for b, v in bucket_acc.items()]
    return {"buckets": buckets, "by_company": by_company, "oldest": oldest}


async def target_achievement(db: AsyncSession, agency_id: uuid.UUID) -> dict:
    """המגמה לפי חברה — חודש מול חודש קודם.

    For each top company, compare CURRENT-period premium vs PREVIOUS-period
    premium (sourced from per-period ProductionSummary aggregations across all
    agency members). Returns:
      - current_period / previous_period labels (for the gauge subtitle)
      - by_company: actual vs prev (target) + change_pct (signed)
      - top_performers: 5 agents by latest-period premium
    """
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"by_company": [], "top_performers": [], "current_period": None, "previous_period": None}

    # ── Identify current + previous periods from actual upload dates ──
    period_expr = func.to_char(FileUpload.uploaded_at, "YYYY-MM").label("period")
    period_rows = (await db.execute(
        select(
            period_expr,
            func.coalesce(func.sum(ClientRecord.total_premium), 0),
        )
        .select_from(ClientRecord)
        .join(FileUpload, ClientRecord.upload_id == FileUpload.id)
        .where(
            ClientRecord.user_id.in_(agent_ids),
            FileUpload.file_category == "production",
        )
        .group_by(period_expr)
        .order_by(period_expr.desc())
    )).all()
    if len(period_rows) < 1:
        return {"by_company": [], "top_performers": [], "current_period": None, "previous_period": None}

    current_period = period_rows[0][0]
    previous_period = period_rows[1][0] if len(period_rows) >= 2 else None

    # ── Per-company premium per period (same period_expr → consistent labels) ──
    co_rows = (await db.execute(
        select(
            ClientRecord.receiving_company,
            period_expr,
            func.coalesce(func.sum(ClientRecord.total_premium), 0),
        )
        .select_from(ClientRecord)
        .join(FileUpload, ClientRecord.upload_id == FileUpload.id)
        .where(
            ClientRecord.user_id.in_(agent_ids),
            ClientRecord.receiving_company.isnot(None),
            FileUpload.file_category == "production",
        )
        .group_by(ClientRecord.receiving_company, period_expr)
    )).all()

    by_co_period: dict[str, dict[str, float]] = {}
    for co, period, prem in co_rows:
        by_co_period.setdefault(co, {})[period] = float(prem or 0)

    # ── Build the by_company list: current vs previous, only for companies
    #    with non-zero current-period activity ──
    by_company = []
    for co, periods in by_co_period.items():
        actual = periods.get(current_period, 0)
        target = periods.get(previous_period, 0) if previous_period else 0
        if actual <= 0 and target <= 0:
            continue
        change_pct = round(((actual - target) / target * 100), 1) if target > 0 else (
            100.0 if actual > 0 else 0.0
        )
        # Display achievement as "% of last month": 100% = identical, >100 = grew
        achievement_pct = round((actual / target * 100), 1) if target > 0 else (
            100.0 if actual == 0 else 999.0  # new company → mark as "new"
        )
        by_company.append({
            "company": co,
            "actual": round(actual, 2),
            "target": round(target, 2),  # = previous period
            "achievement_pct": achievement_pct,
            "change_pct": change_pct,
            "is_new": target == 0 and actual > 0,
        })
    # Rank by current-period actual (most relevant first)
    by_company.sort(key=lambda r: r["actual"], reverse=True)
    by_company = by_company[:8]

    # ── Top performers — agents with highest current-period premium ──
    top_performers = []
    prod_upload_ids = (await db.execute(
        select(FileUpload.id).where(
            FileUpload.user_id.in_(agent_ids),
            FileUpload.is_production == True,
        )
    )).scalars().all()
    prod_upload_ids = list(prod_upload_ids)
    if prod_upload_ids:
        agent_rows = (await db.execute(
            select(
                ClientRecord.user_id,
                func.coalesce(func.sum(ClientRecord.total_premium), 0),
                func.count(func.distinct(ClientRecord.id_number)),
            )
            .where(ClientRecord.upload_id.in_(prod_upload_ids))
            .group_by(ClientRecord.user_id)
            .order_by(func.coalesce(func.sum(ClientRecord.total_premium), 0).desc())
            .limit(5)
        )).all()
        user_label = await _user_label_map(db, [r[0] for r in agent_rows])
        top_performers = [
            {
                "user_id": str(r[0]),
                "name": user_label.get(r[0], ""),
                "premium": float(r[1] or 0),
                "clients": int(r[2] or 0),
            }
            for r in agent_rows
        ]

    return {
        "by_company": by_company,
        "top_performers": top_performers,
        "current_period": current_period,
        "previous_period": previous_period,
    }


async def production_trend(db: AsyncSession, agency_id: uuid.UUID) -> list[dict]:
    """Month-over-month production totals across the entire agency.

    Aggregates `ProductionSummary` rows across all members of the agency,
    grouped by period_label (e.g. "2026-04"). Powers the headline chart on
    the super-user dashboard.
    """
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return []
    rows = (await db.execute(
        select(
            ProductionSummary.period_label,
            func.sum(ProductionSummary.total_premium),
            func.sum(ProductionSummary.total_accumulation),
            func.count(func.distinct(ProductionSummary.user_id)),
            func.min(ProductionSummary.upload_date),
        )
        .where(ProductionSummary.user_id.in_(agent_ids))
        .group_by(ProductionSummary.period_label)
        .order_by(ProductionSummary.period_label.asc())
    )).all()
    return [
        {
            "period": r[0],
            "total_premium": float(r[1] or 0),
            "total_accumulation": float(r[2] or 0),
            "agent_count": int(r[3] or 0),
            "first_upload": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


async def bonus_status_by_agent(
    db: AsyncSession, agency_id: uuid.UUID, year: int | None = None
) -> dict:
    if year is None:
        year = datetime.utcnow().year
    agent_ids = await _agent_ids(db, agency_id)
    if not agent_ids:
        return {"year": year, "rows": [], "totals": {"total": 0, "paid": 0}}

    rows = (await db.execute(
        select(
            VolumeBonusPayment.user_id,
            VolumeBonusPayment.company_name,
            VolumeBonusPayment.is_paid,
            VolumeBonusPayment.paid_date,
        )
        .where(
            VolumeBonusPayment.user_id.in_(agent_ids),
            VolumeBonusPayment.year == year,
        )
    )).all()

    user_rows = (await db.execute(
        select(User.id, User.full_name, User.email).where(User.id.in_(agent_ids))
    )).all()
    user_label = {row[0]: (row[1] or row[2]) for row in user_rows}

    out_rows = []
    paid = 0
    for user_id, company, is_paid, paid_date in rows:
        if is_paid:
            paid += 1
        out_rows.append({
            "agent_user_id": str(user_id),
            "agent_name": user_label.get(user_id, ""),
            "company": company,
            "is_paid": bool(is_paid),
            "paid_date": paid_date.isoformat() if paid_date else None,
        })

    return {
        "year": year,
        "rows": out_rows,
        "totals": {"total": len(rows), "paid": paid},
    }


# ─── Invites ────────────────────────────────────────────────────────────────

INVITE_DEFAULT_EXPIRY_DAYS = 14


async def create_invite(
    db: AsyncSession,
    agency: Agency,
    inviter: User,
    email: str,
    role: str = "agent",
) -> AgencyInvite:
    invite = AgencyInvite(
        agency_id=agency.id,
        email=email.lower().strip(),
        token=secrets.token_urlsafe(48),
        role=role,
        created_by_user_id=inviter.id,
        expires_at=datetime.utcnow() + timedelta(days=INVITE_DEFAULT_EXPIRY_DAYS),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


async def list_invites(db: AsyncSession, agency_id: uuid.UUID) -> list[AgencyInvite]:
    result = await db.execute(
        select(AgencyInvite)
        .where(AgencyInvite.agency_id == agency_id)
        .order_by(AgencyInvite.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_invite(db: AsyncSession, agency_id: uuid.UUID, invite_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(AgencyInvite).where(
            AgencyInvite.id == invite_id,
            AgencyInvite.agency_id == agency_id,
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        return False
    invite.revoked_at = datetime.utcnow()
    await db.commit()
    return True


async def lookup_invite(db: AsyncSession, token: str) -> AgencyInvite | None:
    result = await db.execute(select(AgencyInvite).where(AgencyInvite.token == token))
    invite = result.scalar_one_or_none()
    if not invite or invite.revoked_at or invite.accepted_at:
        return None
    if invite.expires_at < datetime.utcnow():
        return None
    return invite


async def accept_invite(db: AsyncSession, invite: AgencyInvite, user: User) -> User:
    """Bind an existing logged-in user to the invite's agency. Sets role too."""
    user.agency_id = invite.agency_id
    user.role = invite.role or "agent"
    invite.accepted_user_id = user.id
    invite.accepted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def send_invite_email(invite: AgencyInvite, agency: Agency, accept_url: str) -> bool:
    """Send the agency invite email. Reuses the SMTP path used by portal/reset emails."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP not configured — skipping invite email for %s", invite.email)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"הזמנה להצטרף ל-{agency.name} ב-Nifraim"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = invite.email

    html = f"""
    <div dir="rtl" style="font-family: 'Heebo', sans-serif; padding: 24px; max-width: 560px; margin: auto;">
      <h2 style="color:#0d3b66;">הוזמנת להצטרף לסוכנות {agency.name}</h2>
      <p>שלום,</p>
      <p>הסוכנות {agency.name} הזמינה אותך להצטרף ל-Nifraim — מערכת ניהול נפרעים ועמלות.</p>
      <p>לחצו על הקישור הבא כדי להצטרף לסוכנות:</p>
      <p style="margin: 24px 0;">
        <a href="{accept_url}" style="background:#f57c00; color:#fff; padding: 12px 24px;
           border-radius: 8px; text-decoration:none;">הצטרפות לסוכנות</a>
      </p>
      <p style="color:#666; font-size: 12px;">הקישור תקף ל-{INVITE_DEFAULT_EXPIRY_DAYS} ימים.</p>
    </div>
    """
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        await _send_email(msg)
        return True
    except Exception as e:
        logger.error("Failed to send agency invite email: %s", e)
        return False
