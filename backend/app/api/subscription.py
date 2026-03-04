from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.subscription import SignupRequest, SignupResponse, SubscriptionStatus
from app.services.subscription_service import create_signup, activate_subscription, get_subscription_status
from app.services.payment_service import verify_webhook

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
    data = await request.json()
    parsed = verify_webhook(data)
    if not parsed or not parsed.get("user_id"):
        raise HTTPException(status_code=400, detail="Invalid webhook data")

    user = await activate_subscription(
        db=db,
        user_id=parsed["user_id"],
        plan=parsed["plan"],
        cardcom_token=parsed.get("cardcom_token"),
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
