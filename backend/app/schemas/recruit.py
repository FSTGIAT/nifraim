from datetime import date, datetime
from pydantic import BaseModel


class RecruitCreate(BaseModel):
    id_number: str
    first_name: str
    last_name: str
    company: str | None = None
    product: str | None = None
    amount: float | None = None
    sign_date: date | None = None


class RecruitOut(BaseModel):
    id: str
    id_number: str
    first_name: str
    last_name: str
    company: str | None = None
    product: str | None = None
    amount: float | None = None
    customer_status: str | None = None
    sign_date: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecruitMatchResult(BaseModel):
    recruit_id: str
    id_number: str
    first_name: str
    last_name: str
    company: str | None = None
    product: str | None = None
    amount: float | None = None
    customer_status: str | None = None
    found_in_production: bool = False
    production_products: list[dict] = []
    production_premium: float = 0


class RecruitComparisonResponse(BaseModel):
    total: int = 0
    found: int = 0
    not_found: int = 0
    results: list[RecruitMatchResult] = []
    total_premium_found: float = 0
    estimated_missing_premium: float = 0
    company_breakdown: list[dict] = []
    status_breakdown: dict = {}
    active_product_rate: float = 0
    commission_files: list[str] = []


# ── File upload + production comparison schemas ──

class RecruitFileProduct(BaseModel):
    product: str | None = None
    company: str | None = None
    policy_number: str | None = None
    expected_amount: float | None = None
    actual_amount: float | None = None
    sign_date: str | None = None
    is_active: str | None = None
    track: str | None = None
    management_fee: float | None = None
    status: str  # "found" | "client_only" | "not_found"


class RecruitFileClient(BaseModel):
    id_number: str
    first_name: str | None = None
    last_name: str | None = None
    products: list[RecruitFileProduct] = []
    found_count: int = 0
    total_count: int = 0
    match_status: str  # "full_match" | "partial_match" | "client_only" | "not_found"


class RecruitUploadResponse(BaseModel):
    total_clients: int = 0
    total_products: int = 0
    found: int = 0
    client_only: int = 0
    not_found: int = 0
    companies: list[str] = []
    results: list[RecruitFileClient] = []
