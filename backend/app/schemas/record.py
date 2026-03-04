from datetime import date, datetime
from pydantic import BaseModel


class RecordOut(BaseModel):
    id: str
    upload_id: str
    id_number: str | None
    first_name: str | None
    last_name: str | None
    sign_date: date | None
    product: str | None
    receiving_company: str | None
    expected_amount: float | None
    actual_amount: float | None
    amount_difference: float | None
    balance: float | None
    commission_paid: float | None
    commission_expected: float | None
    reconciliation_status: str | None
    management_fee: float | None
    fund_policy_number: str | None
    employment_status: str | None
    is_active: str | None
    track: str | None
    agent_number: str | None
    general_notes: str | None
    management_fee_amount: float | None = None
    processing_date: str | None = None

    model_config = {"from_attributes": True}


class RecordPage(BaseModel):
    items: list[RecordOut]
    total: int
    page: int
    per_page: int
    pages: int


class StatusSummary(BaseModel):
    paid_match: int = 0
    paid_mismatch: int = 0
    unpaid: int = 0
    cancelled: int = 0
    no_data: int = 0
    matched: int = 0
    missing_from_report: int = 0
    extra_in_report: int = 0
    total: int = 0
    total_expected: float = 0
    total_actual: float = 0
    total_difference: float = 0


class CommissionRateIn(BaseModel):
    company_name: str
    rate: float
    payment_frequency: str | None = None
    paid_to: str | None = None
    company_email: str | None = None


class CommissionRateOut(BaseModel):
    id: str
    company_name: str
    rate: float
    payment_frequency: str | None
    paid_to: str | None
    company_email: str | None = None

    model_config = {"from_attributes": True}


# ── Analytics schemas ──

class StatusDistributionItem(BaseModel):
    status: str
    status_label: str
    count: int
    total_amount: float


class CompanyBreakdownItem(BaseModel):
    company: str
    count: int
    total_expected: float
    total_actual: float
    difference: float


class ProductBreakdownItem(BaseModel):
    product: str
    count: int
    total_amount: float


class TopMismatchItem(BaseModel):
    first_name: str | None
    last_name: str | None
    id_number: str | None
    expected: float | None
    actual: float | None
    difference: float


class AnalyticsResponse(BaseModel):
    status_distribution: list[StatusDistributionItem]
    company_breakdown: list[CompanyBreakdownItem]
    product_breakdown: list[ProductBreakdownItem]
    top_mismatches: list[TopMismatchItem]
