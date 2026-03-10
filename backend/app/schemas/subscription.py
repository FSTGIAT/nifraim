from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: str
    phone: str
    company_name: str | None = None
    plan: str  # monthly / yearly


class SignupResponse(BaseModel):
    payment_url: str | None = None
    user_id: str


class SubscriptionStatus(BaseModel):
    is_active: bool
    plan: str | None = None
    expires_at: str | None = None
    status: str | None = None
    next_charge_at: str | None = None
    last4_digits: str | None = None
    card_brand: str | None = None
    is_recurring: bool = False


class SubscriptionOut(BaseModel):
    id: str
    user_id: str
    plan: str
    amount: float
    status: str
    started_at: str | None
    expires_at: str | None
    next_charge_at: str | None = None
    last4_digits: str | None = None
    card_brand: str | None = None
    retry_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}
