import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class PortalLinkCreate(BaseModel):
    customer_id_number: str
    customer_name: str
    customer_email: str | None = None
    password: str
    expires_days: int = 30
    # Setup wizard choices (services/portal_view.normalize_settings). Omitted →
    # NULL → the customer sees everything, as before the wizard.
    settings: dict | None = None


class PortalSettingsUpdate(BaseModel):
    settings: dict


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
    settings: dict | None = None

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
    total_premium: float | None      # None = the agent chose to hide it
    total_accumulation: float | None
    company_count: int


class PortalCompanyBreakdown(BaseModel):
    company: str
    premium: float | None
    accumulation: float | None
    count: int


class PortalOfferPublic(BaseModel):
    service_key: str
    title: str
    url: str


class PortalAgentCard(BaseModel):
    name: str | None = None
    phone: str | None = None
    company_name: str | None = None


class PortalDashboardData(BaseModel):
    customer_name: str
    id_number: str
    period: str = ""
    products: list[PortalProduct]
    kpi: PortalKPI
    company_breakdown: list[PortalCompanyBreakdown]
    recent_changes: dict | None = None
    settings: dict | None = None
    offers: list[PortalOfferPublic] = []
    agent: PortalAgentCard | None = None


# --- Agent offers (setup wizard step 3) ---

class AgentOfferIn(BaseModel):
    service_key: str
    title: str | None = None
    url: str = Field(..., max_length=1000)
    is_active: bool = True


class AgentOfferOut(BaseModel):
    service_key: str
    title: str
    url: str
    is_active: bool
    clicks: int = 0


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
