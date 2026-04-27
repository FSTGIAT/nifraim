import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, AGENCY_ROLES
from app.models.agency import Agency
from app.models.portal_link import CustomerPortalLink
from app.services.auth_service import decode_token, decode_token_full, decode_portal_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_paid_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription required")
    return user


async def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def get_agency_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Agency]:
    """Resolve a JWT bearing an agency role and return (user, agency).

    Rejects portal tokens (handled inside decode_token_full) and any token whose
    `role` claim is not in AGENCY_ROLES. Also re-checks the role against the DB
    so a revoked role takes effect immediately even before the JWT expires.
    """
    payload = decode_token_full(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_result = await db.execute(select(User).where(User.id == uuid.UUID(sub)))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.role not in AGENCY_ROLES or not user.agency_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agency access required")
    agency_result = await db.execute(select(Agency).where(Agency.id == user.agency_id))
    agency = agency_result.scalar_one_or_none()
    if not agency:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agency not found")
    return user, agency


async def get_impersonation_target(
    agent_id: uuid.UUID,
    agency_user: tuple[User, Agency] = Depends(get_agency_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Agency, User]:
    """Validate that the agency user can impersonate the given agent.

    Returns (super_user, agency, target_agent). Used by the impersonation mint
    endpoint; not by the impersonation session itself (those use get_current_user).
    """
    super_user, agency = agency_user
    target_result = await db.execute(select(User).where(User.id == agent_id))
    target = target_result.scalar_one_or_none()
    if not target or target.agency_id != agency.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not in your agency")
    return super_user, agency, target


async def get_portal_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CustomerPortalLink:
    """Validate a portal JWT and return the associated portal link."""
    payload = decode_portal_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid portal session")
    portal_token = payload.get("sub")
    result = await db.execute(
        select(CustomerPortalLink).where(CustomerPortalLink.token == portal_token)
    )
    link = result.scalar_one_or_none()
    if not link or not link.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Portal link expired or revoked")
    from datetime import datetime
    if link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Portal link expired")
    return link
