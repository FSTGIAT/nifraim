from datetime import datetime
from pydantic import BaseModel


class RecruitCreate(BaseModel):
    id_number: str
    first_name: str
    last_name: str
    company: str | None = None
    product: str | None = None
    amount: float | None = None


class RecruitOut(BaseModel):
    id: str
    id_number: str
    first_name: str
    last_name: str
    company: str | None = None
    product: str | None = None
    amount: float | None = None
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
    found_in_production: bool = False
    production_products: list[dict] = []
    production_premium: float = 0


class RecruitComparisonResponse(BaseModel):
    total: int = 0
    found: int = 0
    not_found: int = 0
    results: list[RecruitMatchResult] = []
