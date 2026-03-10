import logging
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
from app.services.payment_service import create_payment_page, charge_token

logger = logging.getLogger(__name__)

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
        if existing.is_active:
            raise ValueError("Email already registered")
        # Inactive user from abandoned signup — clean up and allow retry
        await db.execute(
            select(Subscription).where(Subscription.user_id == existing.id)
        )
        from sqlalchemy import delete
        await db.execute(delete(Subscription).where(Subscription.user_id == existing.id))
        await db.execute(delete(User).where(User.id == existing.id))
        await db.flush()

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

    # Create Cardcom payment page (with token creation)
    payment_url, lp_code = await create_payment_page(
        amount=float(PLAN_PRICES[plan]),
        description=f"Nifraim - מנוי {'חודשי' if plan == 'monthly' else 'שנתי'}",
        user_email=email,
        user_name=full_name,
        user_id=str(user.id),
        plan=plan,
    )

    # Create pending subscription
    sub = Subscription(
        user_id=user.id,
        plan=plan,
        amount=float(PLAN_PRICES[plan]),
        status="pending",
        cardcom_low_profile_code=lp_code,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(user)

    return user, payment_url


async def activate_subscription(
    db: AsyncSession,
    user_id: str,
    plan: str,
    cardcom_token: str | None = None,
    token_exp_date: str | None = None,
    last4_digits: str | None = None,
    card_brand: str | None = None,
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
        sub.token_exp_date = token_exp_date
        sub.last4_digits = last4_digits
        sub.card_brand = card_brand
        sub.last_charge_at = now
        sub.next_charge_at = now + duration
        sub.retry_count = 0
        if amount:
            sub.amount = amount
    else:
        sub = Subscription(
            user_id=user.id,
            plan=plan,
            amount=amount or float(PLAN_PRICES.get(plan, 0)),
            status="active",
            cardcom_token=cardcom_token,
            token_exp_date=token_exp_date,
            last4_digits=last4_digits,
            card_brand=card_brand,
            started_at=now,
            expires_at=now + duration,
            last_charge_at=now,
            next_charge_at=now + duration,
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
        .where(Subscription.user_id == user.id, Subscription.status.in_(["active", "cancelled"]))
        .order_by(Subscription.expires_at.desc())
    )
    sub = result.scalar_one_or_none()

    if not sub:
        return {
            "is_active": user.is_active,
            "plan": None,
            "expires_at": None,
            "status": "none",
            "next_charge_at": None,
            "last4_digits": None,
            "card_brand": None,
            "is_recurring": False,
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
            "next_charge_at": None,
            "last4_digits": sub.last4_digits,
            "card_brand": sub.card_brand,
            "is_recurring": False,
        }

    return {
        "is_active": True,
        "plan": sub.plan,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "status": sub.status,
        "next_charge_at": sub.next_charge_at.isoformat() if sub.next_charge_at else None,
        "last4_digits": sub.last4_digits,
        "card_brand": sub.card_brand,
        "is_recurring": sub.status == "active" and sub.next_charge_at is not None,
    }


async def cancel_subscription(db: AsyncSession, user: User) -> dict:
    """Cancel auto-renewal. Access continues until expires_at."""
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.expires_at.desc())
    )
    sub = result.scalar_one_or_none()

    if not sub:
        return {"success": False, "message": "No active subscription found"}

    sub.status = "cancelled"
    sub.next_charge_at = None  # Stop renewals
    await db.commit()

    return {
        "success": True,
        "message": "Subscription cancelled. Access continues until expiry.",
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
    }


async def process_renewals(db: AsyncSession) -> dict:
    """Process all due recurring charges. Called by scheduler daily."""
    now = datetime.utcnow()
    stats = {"processed": 0, "success": 0, "failed": 0, "deactivated": 0}

    # Find active subscriptions due for renewal
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.status == "active",
            Subscription.next_charge_at <= now,
            Subscription.cardcom_token.isnot(None),
        )
    )
    subs = list(result.scalars().all())
    stats["processed"] = len(subs)

    for sub in subs:
        # Fetch user info for invoice generation
        user_result = await db.execute(select(User).where(User.id == sub.user_id))
        user = user_result.scalar_one_or_none()

        plan_label = "חודשי" if sub.plan == "monthly" else "שנתי"
        charge_result = await charge_token(
            token=sub.cardcom_token,
            amount=float(sub.amount),
            token_exp_date=sub.token_exp_date,
            customer_name=user.full_name if user else None,
            customer_email=user.email if user else None,
            description=f"Nifraim - חידוש מנוי {plan_label}",
        )

        if charge_result:
            # Success — extend subscription
            duration = PLAN_DURATIONS.get(sub.plan, timedelta(days=30))
            sub.expires_at = now + duration
            sub.next_charge_at = now + duration
            sub.last_charge_at = now
            sub.retry_count = 0
            stats["success"] += 1
            logger.info(f"Renewal success for user {sub.user_id}, next charge: {sub.next_charge_at}")
        else:
            # Failure — increment retry
            sub.retry_count = (sub.retry_count or 0) + 1
            stats["failed"] += 1

            if sub.retry_count >= 3:
                # Deactivate after 3 failures
                sub.status = "expired"
                sub.next_charge_at = None
                if user:
                    user.is_active = False
                stats["deactivated"] += 1
                logger.warning(f"Subscription deactivated for user {sub.user_id} after 3 failed charges")
            else:
                # Retry tomorrow
                sub.next_charge_at = now + timedelta(days=1)
                logger.warning(f"Renewal failed for user {sub.user_id}, retry {sub.retry_count}/3")

    await db.commit()
    logger.info(f"Renewal processing complete: {stats}")
    return stats


async def get_all_subscriptions(db: AsyncSession) -> list[Subscription]:
    """Admin: get all subscriptions."""
    result = await db.execute(select(Subscription).order_by(Subscription.created_at.desc()))
    return list(result.scalars().all())
