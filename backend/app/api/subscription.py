from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.subscription import SignupRequest, SignupResponse, SubscriptionStatus
from app.services.subscription_service import (
    create_signup, activate_subscription, get_subscription_status, cancel_subscription,
)
from app.services.payment_service import verify_webhook, get_lp_result

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

    if not payment_url:
        raise HTTPException(status_code=502, detail="Payment service unavailable")

    return SignupResponse(payment_url=payment_url, user_id=str(user.id))


@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Cardcom webhook after payment.
    Cardcom sends LowProfileCode — we call GetLpResult to get full payment details."""
    import logging
    logger = logging.getLogger(__name__)

    # Cardcom may send as JSON or form data
    content_type = request.headers.get("content-type", "")
    if "json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    logger.info(f"Cardcom webhook received: {data}")
    parsed = verify_webhook(data)
    if not parsed or not parsed.get("user_id"):
        raise HTTPException(status_code=400, detail="Invalid webhook data")

    # If we have a LowProfileCode, call GetLpResult for full details (token, card info)
    lp_code = parsed.get("low_profile_code")
    if lp_code:
        lp_result = await get_lp_result(lp_code)
        if lp_result:
            # Merge GetLpResult data (more reliable than webhook payload)
            parsed["cardcom_token"] = lp_result.get("token") or parsed.get("cardcom_token")
            parsed["token_exp_date"] = lp_result.get("token_exp_date") or parsed.get("token_exp_date")
            parsed["last4_digits"] = lp_result.get("last4_digits") or parsed.get("last4_digits")
            parsed["card_brand"] = lp_result.get("card_brand") or parsed.get("card_brand")
            parsed["amount"] = lp_result.get("amount") or parsed.get("amount")

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

    # Create payment page
    payment_url, lp_code = await create_payment_page(
        amount=float(PLAN_PRICES.get(plan, Decimal("295.00"))),
        description=f"Nifraim - חידוש מנוי {'חודשי' if plan == 'monthly' else 'שנתי'}",
        user_email=user.email,
        user_name=user.full_name,
        user_id=str(user.id),
        plan=plan,
    )

    if lp_code:
        sub.cardcom_low_profile_code = lp_code
        await db.commit()

    if not payment_url:
        raise HTTPException(status_code=502, detail="Payment service unavailable")

    return SignupResponse(payment_url=payment_url, user_id=str(user.id))
