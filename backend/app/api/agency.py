import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.agency import Agency
from app.api.deps import get_agency_user, get_current_user, get_impersonation_target
from app.schemas.agency import (
    AgencyOut, AgencyOverviewOut, AgentLeaderboardRow,
    ImpersonationToken, InviteCreate, InviteOut, InviteAccept,
)
from app.services import agency_service
from app.services.auth_service import create_impersonation_token

router = APIRouter()


# ─── Read-only super-user views ─────────────────────────────────────────────

@router.get("/me", response_model=AgencyOut)
async def my_agency(agency_user: tuple[User, Agency] = Depends(get_agency_user)):
    _, agency = agency_user
    return AgencyOut(id=str(agency.id), name=agency.name, slug=agency.slug)


@router.get("/overview", response_model=AgencyOverviewOut)
async def overview(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.agency_overview(db, agency.id)


@router.get("/agents", response_model=list[AgentLeaderboardRow])
async def agents(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.agent_leaderboard(db, agency.id)


@router.get("/reconciliation")
async def reconciliation(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.unpaid_commission_by_company(db, agency.id)


@router.get("/bonus")
async def bonus(
    year: int | None = None,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.bonus_status_by_agent(db, agency.id, year)


@router.get("/trends")
async def trends(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return {"production": await agency_service.production_trend(db, agency.id)}


@router.get("/agents/{agent_id}/detail")
async def agent_detail(
    agent_id: uuid.UUID,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    detail = await agency_service.agent_detail(db, agency.id, agent_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Agent not found in your agency")
    return detail


@router.get("/production")
async def production(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.production_overview(db, agency.id)


@router.get("/comparison")
async def comparison(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.comparison_overview(db, agency.id)


@router.get("/commission-rates")
async def commission_rates(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.commission_rates_overview(db, agency.id)


@router.get("/company-emails")
async def company_emails(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.company_emails_overview(db, agency.id)


@router.get("/recruits")
async def recruits(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.recruits_overview(db, agency.id)


@router.get("/sub-agent-splits")
async def sub_agent_splits(
    override_pct: float | None = None,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    pct = override_pct if override_pct is not None else 0.20
    return await agency_service.sub_agent_splits(db, agency.id, override_pct=pct)


@router.get("/storno")
async def storno(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.storno_summary(db, agency.id)


@router.get("/renewal-forecast")
async def renewal_forecast(
    months_ahead: int = 6,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.renewal_forecast(db, agency.id, months_ahead=months_ahead)


@router.get("/agent-payslip/{agent_id}")
async def agent_payslip(
    agent_id: uuid.UUID,
    override_pct: float | None = None,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    pct = override_pct if override_pct is not None else 0.20
    slip = await agency_service.agent_payslip(db, agency.id, agent_id, override_pct=pct)
    if not slip:
        raise HTTPException(status_code=404, detail="Agent not found in your agency")
    return slip


@router.get("/exceptions-aging")
async def exceptions_aging(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.exceptions_aging(db, agency.id)


@router.get("/target-achievement")
async def target_achievement(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.target_achievement(db, agency.id)


@router.get("/missing-commission")
async def missing_commission(
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    return await agency_service.missing_commission(db, agency.id)


# ─── Impersonation ──────────────────────────────────────────────────────────

@router.post("/impersonate/{agent_id}", response_model=ImpersonationToken)
async def impersonate(
    agent_id: uuid.UUID,
    deps: tuple[User, Agency, User] = Depends(get_impersonation_target),
):
    super_user, agency, target = deps
    token = create_impersonation_token(
        target_user_id=str(target.id),
        parent_user_id=str(super_user.id),
        parent_role=super_user.role,
        agency_id=str(agency.id),
    )
    return ImpersonationToken(
        access_token=token,
        target_user_id=str(target.id),
        target_name=target.full_name or target.email,
    )


# ─── Invites ────────────────────────────────────────────────────────────────

def _accept_url(request: Request, token: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/agency/join/{token}"


@router.post("/invites", response_model=InviteOut)
async def create_invite(
    body: InviteCreate,
    request: Request,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    super_user, agency = agency_user
    if super_user.role != "agency_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only agency_admin may invite")
    invite = await agency_service.create_invite(db, agency, super_user, body.email, body.role)
    accept_url = _accept_url(request, invite.token)
    await agency_service.send_invite_email(invite, agency, accept_url)
    return InviteOut(
        id=str(invite.id),
        email=invite.email,
        role=invite.role,
        accepted_at=invite.accepted_at,
        revoked_at=invite.revoked_at,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        accept_url=accept_url,
    )


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(
    request: Request,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    invites = await agency_service.list_invites(db, agency.id)
    return [
        InviteOut(
            id=str(i.id),
            email=i.email,
            role=i.role,
            accepted_at=i.accepted_at,
            revoked_at=i.revoked_at,
            expires_at=i.expires_at,
            created_at=i.created_at,
            accept_url=_accept_url(request, i.token),
        )
        for i in invites
    ]


@router.delete("/invites/{invite_id}")
async def revoke_invite(
    invite_id: uuid.UUID,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
):
    _, agency = agency_user
    ok = await agency_service.revoke_invite(db, agency.id, invite_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Invite not found")
    return {"ok": True}


@router.get("/invites/lookup/{token}")
async def lookup_invite(token: str, db: AsyncSession = Depends(get_db)):
    """Public — used by the frontend join page to show the agency name before login."""
    invite = await agency_service.lookup_invite(db, token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite invalid or expired")
    from sqlalchemy import select
    agency = (await db.execute(select(Agency).where(Agency.id == invite.agency_id))).scalar_one()
    return {
        "agency": {"id": str(agency.id), "name": agency.name, "slug": agency.slug},
        "email": invite.email,
        "role": invite.role,
        "expires_at": invite.expires_at.isoformat(),
    }


@router.post("/invites/accept")
async def accept_invite(
    body: InviteAccept,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logged-in user binds themselves to an agency via the invite token."""
    invite = await agency_service.lookup_invite(db, body.token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite invalid or expired")
    if invite.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="Invite was issued to a different email")
    await agency_service.accept_invite(db, invite, user)
    return {"ok": True, "agency_id": str(invite.agency_id), "role": user.role}
