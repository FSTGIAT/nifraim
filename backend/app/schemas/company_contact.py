from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CompanyContactCreate(BaseModel):
    company_name: str
    email: str
    contact_name: Optional[str] = None
    notes: Optional[str] = None


class CompanyContactUpdate(BaseModel):
    company_name: Optional[str] = None
    email: Optional[str] = None
    contact_name: Optional[str] = None
    notes: Optional[str] = None


class CompanyContactOut(BaseModel):
    id: str
    company_name: str
    email: str
    contact_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
