from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SmsOtpTemplateCreate(BaseModel):
    company_name: str
    pattern: str
    portal_kind: Optional[str] = None
    example: Optional[str] = None
    is_block: bool = False
    active: bool = True


class SmsOtpTemplateUpdate(BaseModel):
    company_name: Optional[str] = None
    pattern: Optional[str] = None
    portal_kind: Optional[str] = None
    example: Optional[str] = None
    is_block: Optional[bool] = None
    active: Optional[bool] = None


class SmsOtpTemplateOut(BaseModel):
    id: str
    company_name: str
    pattern: str
    portal_kind: Optional[str] = None
    example: Optional[str] = None
    is_block: bool
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
