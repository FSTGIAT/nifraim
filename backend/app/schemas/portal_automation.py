from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PortalKind = Literal[
    "phoenix", "migdal", "clal", "menora", "altshuler",
    "hachshara", "excellence", "mor", "ayalon", "clal_health",
]


class PortalCredentialIn(BaseModel):
    portal_kind: PortalKind
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)
    twilio_to_number: str | None = Field(default=None, max_length=20)
    schedule_enabled: bool = False
    category_hint: str | None = Field(default=None, max_length=64)


class PortalCredentialUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=255)
    twilio_to_number: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    schedule_enabled: bool | None = None
    category_hint: str | None = Field(default=None, max_length=64)


class PortalCredentialOut(BaseModel):
    id: str
    portal_kind: str
    username: str
    twilio_to_number: str | None = None
    is_active: bool
    schedule_enabled: bool
    category_hint: str | None = None
    last_run_at: datetime | None = None
    last_run_status: str | None = None
    last_error: str | None = None
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
