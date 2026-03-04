from datetime import datetime
from pydantic import BaseModel


class PayingCompanyCreate(BaseModel):
    company_name: str


class PayingCompanyOut(BaseModel):
    id: str
    company_name: str
    created_at: datetime

    model_config = {"from_attributes": True}
