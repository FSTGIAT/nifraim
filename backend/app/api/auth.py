import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserRegister, UserLogin, Token, UserOut, UsernameUpdate, AvatarUpdate,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.services.email_service import send_reset_password_email, FRONTEND_URL
from app.services.username_service import normalize_username, is_valid_username
from app.api.deps import get_current_user

router = APIRouter()


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        username=user.username,
        avatar_seed=user.avatar_seed,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        is_admin=user.is_admin,
    )


@router.post("/register", response_model=Token)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    username = normalize_username(data.username)
    if not is_valid_username(username):
        raise HTTPException(status_code=422, detail="שם משתמש לא תקין")

    taken = await db.execute(select(User.id).where(User.username == username))
    if taken.first():
        raise HTTPException(status_code=409, detail="שם המשתמש תפוס")

    user = User(
        email=data.email,
        username=username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Two concurrent signups can both pass the check above; the unique index
        # is the real guard.
        await db.rollback()
        raise HTTPException(status_code=409, detail="שם המשתמש תפוס")
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.patch("/me/username", response_model=UserOut)
async def change_username(
    data: UsernameUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename your handle.

    This is the escape hatch for users whose handle was auto-derived from their
    email local-part by the backfill migration.
    """
    username = normalize_username(data.username)
    if not is_valid_username(username):
        raise HTTPException(status_code=422, detail="שם משתמש לא תקין")

    if username != user.username:
        taken = await db.execute(select(User.id).where(User.username == username))
        if taken.first():
            raise HTTPException(status_code=409, detail="שם המשתמש תפוס")
        user.username = username
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="שם המשתמש תפוס")

    return _user_out(user)


@router.patch("/me/avatar", response_model=UserOut)
async def change_avatar(
    data: AvatarUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pick the seed for your generated avatar (chosen from the chat settings)."""
    user.avatar_seed = data.avatar_seed.strip()[:64]
    await db.commit()
    return _user_out(user)


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(user.id))
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
        # Email delivery failed (e.g. SMTP 535 auth rejected). The reset token is
        # already committed above, so recovery is still possible — surface the
        # ready-to-use reset link in the server log so the operator can hand it to
        # the user manually while the mailbox credentials are being fixed.
        reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
        logging.error(f"Failed to send reset email to {user.email}: {e}")
        logging.warning(f"PASSWORD RESET LINK (deliver manually) for {user.email}: {reset_url}")
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
async def me(user: User = Depends(get_current_user)):
    return _user_out(user)
