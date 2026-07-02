from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel, Field


PortalKind = Literal[
    "phoenix", "phoenix_nifraim", "phoenix_nifraim_gemel", "phoenix_sfe", "migdal", "migdal_apm",
    "clal", "clal_nifraim",
    "menora", "menora_nifraim", "altshuler", "hachshara", "excellence", "mor",
    "ayalon", "clal_health", "harel", "harel_commissions", "harel_savings",
    "yelin", "meitav",
    "phoenix_terminal",
]

ScheduleKind = Literal["manual", "daily", "weekly", "monthly"]
OtpMethod = Literal["twilio", "phone_forward", "manual"]


class PortalCredentialScheduleIn(BaseModel):
    schedule_kind: ScheduleKind


class PortalCredentialIn(BaseModel):
    portal_kind: PortalKind
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)
    twilio_to_number: str | None = Field(default=None, max_length=20)
    schedule_kind: ScheduleKind = "manual"
    category_hint: str | None = Field(default=None, max_length=64)
    otp_method: OtpMethod = "twilio"


class PortalCredentialUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=255)
    twilio_to_number: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    schedule_kind: ScheduleKind | None = None
    category_hint: str | None = Field(default=None, max_length=64)
    otp_method: OtpMethod | None = None


class PortalCredentialOut(BaseModel):
    id: str
    portal_kind: str
    username: str
    twilio_to_number: str | None = None
    contact_phone_synced_to: str | None = None
    is_active: bool
    schedule_kind: ScheduleKind
    category_hint: str | None = None
    otp_method: OtpMethod = "twilio"
    last_run_at: datetime | None = None
    last_run_status: str | None = None
    last_error: str | None = None
    recent_run_statuses: list[str] = []
    created_at: datetime


class PortalRunOut(BaseModel):
    id: str
    credential_id: str
    status: str
    stage: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None
    downloaded_filename: str | None = None
    upload_id: str | None = None


class OtpSubmitIn(BaseModel):
    otp: str = Field(pattern=r"^\d{4,8}$")


class RunStartOut(BaseModel):
    run_id: str


class BatchStartOut(BaseModel):
    batch_id: str


class PortalRunBatchOut(BaseModel):
    id: str
    status: str  # pending | running | success | partial | failed
    total: int
    succeeded: int
    failed: int
    current_run_id: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    merged_upload_id: str | None = None
    merged_commission_upload_id: str | None = None
    period_month: date | None = None
    error_message: str | None = None
    # Categories this batch produced a persisted comparison for
    # (e.g. ["gemel_hishtalmut", "insurance"]).
    comparison_categories: list[str] = []
    runs: list[PortalRunOut] = []


class TwilioNumberOut(BaseModel):
    id: str
    phone_number: str
    twilio_sid: str
    provisioned_at: datetime
    released_at: datetime | None = None


class OtpInboxOut(BaseModel):
    id: str
    from_number: str
    to_number: str
    body: str
    otp_code: str | None = None
    received_at: datetime
    consumed_at: datetime | None = None
    portal_run_id: str | None = None
    # Company this OTP was routed to (matched server-side from the body).
    portal_kind: str | None = None
    matched_company: str | None = None
