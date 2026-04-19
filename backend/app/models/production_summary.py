import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Numeric, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProductionSummary(Base):
    __tablename__ = "production_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"), nullable=False, unique=True)
    period_label: Mapped[str] = mapped_column(String(20), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Scalar KPIs
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_clients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_premium: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_accumulation: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)

    # JSON breakdowns
    companies_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    product_types_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    top_clients_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Month-over-month changes
    changes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_production_summaries_user_date", "user_id", "upload_date"),
    )
