"""Pydantic schemas for the clearinghouse API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Requests ──────────────────────────────────────────────────────────────
class InquiryCreateRequest(BaseModel):
    customer_id_number: str = Field(..., min_length=1, max_length=20)
    customer_name: str | None = Field(default=None, max_length=200)


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
    providers_expected: int | None
    providers_received: int
    created_at: datetime


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
