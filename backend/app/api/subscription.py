from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.subscription import SignupRequest, SignupResponse, SubscriptionStatus
from app.services.subscription_service import (
    create_signup, activate_subscription, get_subscription_status, cancel_subscription,
)
from app.services.payment_service import verify_webhook, is_cardcom_configured

router = APIRouter()


@router.post("/signup", response_model=SignupResponse)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, payment_url = await create_signup(
            db=db,
            email=req.email,
            full_name=req.full_name,
            phone=req.phone,
            company_name=req.company_name,
            plan=req.plan,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Dev mode: Cardcom not configured — auto-activate user
    if not payment_url and not is_cardcom_configured():
        await activate_subscription(
            db=db,
            user_id=str(user.id),
            plan=req.plan,
            last4_digits="0000",
            card_brand="Demo",
        )
        return SignupResponse(user_id=str(user.id), demo_mode=True)

    if not payment_url:
        raise HTTPException(status_code=502, detail="Payment service unavailable")

    return SignupResponse(payment_url=payment_url, user_id=str(user.id))


@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    parsed = verify_webhook(data)
    if not parsed or not parsed.get("user_id"):
        raise HTTPException(status_code=400, detail="Invalid webhook data")

    user = await activate_subscription(
        db=db,
        user_id=parsed["user_id"],
        plan=parsed["plan"],
        cardcom_token=parsed.get("cardcom_token"),
        token_exp_date=parsed.get("token_exp_date"),
        last4_digits=parsed.get("last4_digits"),
        card_brand=parsed.get("card_brand"),
        amount=parsed.get("amount"),
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "ok"}


@router.get("/success")
async def payment_success():
    return {"status": "ok", "message": "Payment successful"}


@router.get("/status", response_model=SubscriptionStatus)
async def subscription_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_subscription_status(db, user)
    return SubscriptionStatus(**result)


@router.post("/cancel")
async def cancel(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await cancel_subscription(db, user)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/renew", response_model=SignupResponse)
async def renew(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-subscribe after expiry/cancellation — creates a new payment page."""
    from app.models.subscription import Subscription
    from app.services.payment_service import create_payment_page
    from app.services.subscription_service import PLAN_PRICES, PLAN_DURATIONS
    from sqlalchemy import select
    from decimal import Decimal

    # Get the last subscription to determine plan
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    )
    last_sub = result.scalar_one_or_none()
    plan = last_sub.plan if last_sub else "monthly"

    # Create new pending subscription
    sub = Subscription(
        user_id=user.id,
        plan=plan,
        amount=float(PLAN_PRICES.get(plan, Decimal("295.00"))),
        status="pending",
    )
    db.add(sub)
    await db.commit()

    # Dev mode: Cardcom not configured — auto-activate
    if not is_cardcom_configured():
        sub.status = "active"
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        duration = PLAN_DURATIONS.get(plan, timedelta(days=30))
        sub.started_at = now
        sub.expires_at = now + duration
        sub.next_charge_at = now + duration
        sub.last_charge_at = now
        sub.last4_digits = "0000"
        sub.card_brand = "Demo"
        user.is_active = True
        await db.commit()
        return SignupResponse(user_id=str(user.id), demo_mode=True)

    # Create payment page
    payment_url, lp_code = await create_payment_page(
        amount=float(PLAN_PRICES.get(plan, Decimal("295.00"))),
        description=f"Nifraim - חידוש מנוי {'חודשי' if plan == 'monthly' else 'שנתי'}",
        user_email=user.email,
        user_id=str(user.id),
        plan=plan,
    )

    if lp_code:
        sub.cardcom_low_profile_code = lp_code
        await db.commit()

    if not payment_url:
        raise HTTPException(status_code=502, detail="Payment service unavailable")

    return SignupResponse(payment_url=payment_url, user_id=str(user.id))
