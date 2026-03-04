import secrets
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.subscription import Subscription
from app.services.auth_service import hash_password
from app.services.sms_service import send_password_sms
from app.services.payment_service import create_payment_page

PLAN_PRICES = {
    "monthly": Decimal("295.00"),
    "yearly": Decimal("3245.00"),
}

PLAN_DURATIONS = {
    "monthly": timedelta(days=30),
    "yearly": timedelta(days=365),
}


async def create_signup(
    db: AsyncSession,
    email: str,
    full_name: str,
    phone: str,
    company_name: str | None,
    plan: str,
) -> tuple[User, str | None]:
    """Create user (inactive) and initiate Cardcom payment. Returns (user, payment_url)."""
    if plan not in PLAN_PRICES:
        raise ValueError(f"Invalid plan: {plan}")

    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("Email already registered")

    # Create user with temporary password (will be replaced after payment)
    temp_password = secrets.token_urlsafe(16)
    user = User(
        email=email,
        full_name=full_name,
        phone=phone,
        company_name=company_name,
        hashed_password=hash_password(temp_password),
        is_active=False,
    )
    db.add(user)
    await db.flush()

    # Create pending subscription
    sub = Subscription(
        user_id=user.id,
        plan=plan,
        amount=float(PLAN_PRICES[plan]),
        status="pending",
    )
    db.add(sub)
    await db.commit()
    await db.refresh(user)

    # Create Cardcom payment page
    payment_url = await create_payment_page(
        amount=float(PLAN_PRICES[plan]),
        description=f"Nifraim - מנוי {'חודשי' if plan == 'monthly' else 'שנתי'}",
        user_email=email,
        user_id=str(user.id),
        plan=plan,
    )

    return user, payment_url


async def activate_subscription(
    db: AsyncSession,
    user_id: str,
    plan: str,
    cardcom_token: str | None = None,
    amount: float | None = None,
) -> User | None:
    """Activate user subscription after successful payment. Generates and sends password via SMS."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        return None

    now = datetime.utcnow()
    duration = PLAN_DURATIONS.get(plan, timedelta(days=30))

    # Update or create subscription
    sub_result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == "pending")
        .order_by(Subscription.created_at.desc())
    )
    sub = sub_result.scalar_one_or_none()

    if sub:
        sub.status = "active"
        sub.started_at = now
        sub.expires_at = now + duration
        sub.cardcom_token = cardcom_token
        if amount:
            sub.amount = amount
    else:
        sub = Subscription(
            user_id=user.id,
            plan=plan,
            amount=amount or float(PLAN_PRICES.get(plan, 0)),
            status="active",
            cardcom_token=cardcom_token,
            started_at=now,
            expires_at=now + duration,
        )
        db.add(sub)

    # Generate real password and send via SMS
    password = secrets.token_urlsafe(8)
    user.hashed_password = hash_password(password)
    user.is_active = True

    await db.commit()

    # Send password via SMS
    if user.phone:
        await send_password_sms(user.phone, password)

    return user


async def get_subscription_status(db: AsyncSession, user: User) -> dict:
    """Get current subscription status for a user."""
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.expires_at.desc())
    )
    sub = result.scalar_one_or_none()

    if not sub:
        return {
            "is_active": user.is_active,
            "plan": None,
            "expires_at": None,
            "status": "none",
        }

    # Check expiration
    now = datetime.utcnow()
    if sub.expires_at and sub.expires_at < now:
        sub.status = "expired"
        user.is_active = False
        await db.commit()
        return {
            "is_active": False,
            "plan": sub.plan,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "status": "expired",
        }

    return {
        "is_active": True,
        "plan": sub.plan,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "status": "active",
    }


async def get_all_subscriptions(db: AsyncSession) -> list[Subscription]:
    """Admin: get all subscriptions."""
    result = await db.execute(select(Subscription).order_by(Subscription.created_at.desc()))
    return list(result.scalars().all())
