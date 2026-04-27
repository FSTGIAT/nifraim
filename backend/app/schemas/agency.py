from datetime import datetime

from pydantic import BaseModel, EmailStr


class AgencyOut(BaseModel):
    id: str
    name: str
    slug: str

    model_config = {"from_attributes": True}


class AgencyOverviewOut(BaseModel):
    agent_count: int
    agents_with_data: int
    unique_clients: int
    total_premium: float
    total_accumulation: float
    lost_money_amount: float
    lost_money_policy_count: int
    top_lost_company: dict
    bonus_total_this_year: int
    bonus_paid_this_year: int
    last_upload_at: str | None


class AgentLeaderboardRow(BaseModel):
    user_id: str
    full_name: str
    email: str
    has_production: bool
    last_upload_at: str | None
    total_premium: float
    total_accumulation: float
    unique_clients: int
    lost_money_amount: float
    lost_money_policy_count: int


class ImpersonationToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    target_user_id: str
    target_name: str
    expires_in_minutes: int = 15


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = "agent"


class InviteOut(BaseModel):
    id: str
    email: str
    role: str
    accepted_at: datetime | None
    revoked_at: datetime | None
    expires_at: datetime
    created_at: datetime
    accept_url: str | None = None

    model_config = {"from_attributes": True}


class InviteAccept(BaseModel):
    token: str
