import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class PortalLinkCreate(BaseModel):
    customer_id_number: str
    customer_name: str
    customer_email: str | None = None
    password: str
    expires_days: int = 30


class PortalLinkOut(BaseModel):
    id: uuid.UUID
    token: str
    customer_id_number: str
    customer_name: str
    customer_email: str | None
    is_active: bool
    expires_at: datetime
    created_at: datetime
    last_accessed_at: datetime | None

    model_config = {"from_attributes": True}


class PortalAccessRequest(BaseModel):
    password: str


class PortalAccessResponse(BaseModel):
    session_token: str
    customer_name: str
    expires_at: datetime


class PortalProduct(BaseModel):
    product: str | None
    product_type: str | None
    receiving_company: str | None
    total_premium: float | None
    accumulation: float | None
    product_status: str | None
    sign_date: str | None
    fund_policy_number: str | None
    track: str | None


class PortalKPI(BaseModel):
    product_count: int
    total_premium: float
    total_accumulation: float
    company_count: int


class PortalCompanyBreakdown(BaseModel):
    company: str
    premium: float
    accumulation: float
    count: int


class PortalDashboardData(BaseModel):
    customer_name: str
    id_number: str
    period: str = ""
    products: list[PortalProduct]
    kpi: PortalKPI
    company_breakdown: list[PortalCompanyBreakdown]
    recent_changes: dict | None = None


# --- Snapshot schemas ---

class PortalSnapshotOut(BaseModel):
    snapshot_date: datetime
    period_label: str
    kpi: dict
    has_changes: bool
    changes_json: dict | None = None

    model_config = {"from_attributes": True}


class PortalHistoryResponse(BaseModel):
    snapshots: list[PortalSnapshotOut]


# --- AI Chat schemas ---

class PortalChatMessage(BaseModel):
    role: str
    content: str


class PortalChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=300)
    history: list[PortalChatMessage] = []
