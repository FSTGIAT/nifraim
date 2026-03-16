from datetime import datetime
from pydantic import BaseModel


class UploadOut(BaseModel):
    id: str
    filename: str
    file_type: str
    company_source: str | None
    record_count: int
    format_type: str | None = None
    file_category: str | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ProductionFileInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    company_source: str | None
    record_count: int
    uploaded_at: datetime
    companies: list[str] = []

    model_config = {"from_attributes": True}


class ProductionAnalytics(BaseModel):
    total_records: int
    unique_clients: int
    total_premium: float
    total_accumulation: float
    companies_count: int
    company_breakdown: list[dict]
    product_type_breakdown: list[dict]
    status_breakdown: list[dict]
    top_clients_premium: list[dict]
    top_clients_accumulation: list[dict]


class ProductionCompareResponse(BaseModel):
    summary: dict
    new_clients: list[dict]
    removed_clients: list[dict]
    changed_clients: list[dict]
    unchanged_clients: list[dict] = []
