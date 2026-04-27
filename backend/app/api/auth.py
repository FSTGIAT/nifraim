import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.agency import Agency
from app.schemas.user import (
    UserRegister, UserLogin, Token, UserOut, AgencySummary,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.services.auth_service import hash_password, verify_password, create_access_token, decode_token_full
from app.services.email_service import send_reset_password_email
from app.api.deps import get_current_user, security

router = APIRouter()


@router.post("/register", response_model=Token)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), role=user.role, agency_id=str(user.agency_id) if user.agency_id else None)
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(user.id), role=user.role, agency_id=str(user.agency_id) if user.agency_id else None)
    return Token(access_token=token)


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="האימייל לא נמצא במערכת")

    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    await db.commit()

    try:
        await send_reset_password_email(user.email, user.full_name or "", token)
    except Exception as e:
        import logging
        logging.error(f"Failed to send reset email: {e}")
        raise HTTPException(status_code=500, detail=f"שגיאה בשליחת האימייל: {e}")

    return {"message": "קישור לאיפוס סיסמה נשלח לאימייל שלך"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            User.password_reset_token == data.token,
            User.password_reset_expires > datetime.utcnow(),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="קישור לא תקין או שפג תוקפו")

    user.hashed_password = hash_password(data.password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.commit()

    return {"message": "הסיסמה שונתה בהצלחה"}


@router.get("/me", response_model=UserOut)
async def me(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    agency_summary: AgencySummary | None = None
    if user.agency_id:
        result = await db.execute(select(Agency).where(Agency.id == user.agency_id))
        agency = result.scalar_one_or_none()
        if agency:
            agency_summary = AgencySummary(id=str(agency.id), name=agency.name, slug=agency.slug)

    payload = decode_token_full(credentials.credentials) or {}
    impersonating = bool(payload.get("impersonator"))

    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        is_admin=user.is_admin,
        role=user.role,
        agency=agency_summary,
        impersonating=impersonating,
    )
