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
