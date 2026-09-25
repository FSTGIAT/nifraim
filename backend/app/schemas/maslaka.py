"""Pydantic schemas for the clearinghouse API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Requests ──────────────────────────────────────────────────────────────
class InquiryCreateRequest(BaseModel):
    customer_id_number: str = Field(..., min_length=1, max_length=20)
    customer_name: str | None = Field(default=None, max_length=200)


class ProductionReportRequest(BaseModel):
    """One-off production report (event 2000) of the caller's own book, one
    request per institutional body. Each id is that body's ח.פ and must be in
    `code_tables.PROVIDER_CODE_TO_COMPANY` — an unverified ID is refused."""
    yatzran_ids: list[str] = Field(..., min_length=1, max_length=30)
    # "once" → 2000 (one-off, data as of end of this month, due by the 15th of
    # next month); "monthly" → 2100 (ongoing — the מסלקה rules require a
    # minimum commitment of five months).
    frequency: str = Field(default="once", pattern="^(once|monthly)$")
    # Optional TAARICH-NECHONUT-MEIDA (YYYYMMDD), e.g. "20260831".
    information_date: str | None = Field(default=None, pattern=r"^\d{8}$")


# ─── Responses ─────────────────────────────────────────────────────────────
class InquiryOut(BaseModel):
    id: str
    user_id: str
    customer_id_number: str
    customer_name: str | None
    status: str
    interface_code: str | None
    request_reference: str
    vault_outbound_filename: str | None
    submitted_at: datetime | None
    acknowledged_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None
    error_code: str | None
    error_detail: str | None
    # What error_code means, from the מסלקה's feedback spec (feedback_codes.py).
    error_meaning: str | None = None
    providers_expected: int | None
    providers_received: int
    created_at: datetime
    # When the answer is due under Swiftness's own rules (UTC, tz-aware), and
    # which rule set it — see orchestration.expected_answer_by.
    expected_by: datetime | None = None
    expected_basis: str | None = None
    information_date: str | None = None


class AuditEntryOut(BaseModel):
    event_type: str
    from_status: str | None
    to_status: str | None
    actor: str
    detail: str | None
    created_at: datetime


class InquiryDetailOut(InquiryOut):
    audit: list[AuditEntryOut]
    holdings_count: int


class HoldingOut(BaseModel):
    product: str | None
    product_type: str | None
    receiving_company: str | None
    provider_code: str | None
    total_premium: float | None
    accumulation: float | None
    expected_pension: float | None
    management_fee_deposit: float | None
    management_fee_balance: float | None
    fund_policy_number: str | None
    track: str | None
    status_date: str | None
    match_status: str
    insurance_coverage: Any | None


class CompanyBreakdownEntry(BaseModel):
    company: str
    premium: float
    accumulation: float
    count: int


class EnrichedKpi(BaseModel):
    product_count: int
    total_premium: float
    total_accumulation: float
    company_count: int


class LastInquirySummary(BaseModel):
    id: str
    status: str
    completed_at: str | None


class EnrichedPictureOut(BaseModel):
    customer_name: str | None
    as_of: str | None = None
    id_number: str
    products: list[HoldingOut]
    kpi: EnrichedKpi
    company_breakdown: list[CompanyBreakdownEntry]
    last_inquiry: LastInquirySummary | None


class PollStatsOut(BaseModel):
    scanned: int
    feedback_ingested: int
    holdings_ingested: int
    unknown: int
    errors: int
