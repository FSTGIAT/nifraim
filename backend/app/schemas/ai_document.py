from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AiDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    size_bytes: int
    doc_type: str | None
    companies_mentioned: list[str] | None
    summary: str | None
    status: str
    error: str | None
    uploaded_at: datetime
    processed_at: datetime | None
    structured_data: dict | None = None


class AiDocumentListItem(BaseModel):
    """Lightweight list entry — omits the full structured_data payload."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    size_bytes: int
    doc_type: str | None
    companies_mentioned: list[str] | None
    summary: str | None
    status: str
    error: str | None
    uploaded_at: datetime
