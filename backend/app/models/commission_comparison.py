import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CommissionComparison(Base):
    """Persisted snapshot of a commission-vs-production comparison.

    One row per `compute_comparison` call. We always serve `latest` per
    (user_id, category) to the Comparison tab so a page reload — or a user
    opening the tab AFTER an automated portal run completed — shows the
    last known result without re-uploading.
    """
    __tablename__ = "commission_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    production_upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_uploads.id", ondelete="SET NULL"), nullable=True
    )
    # Compact summary for cheap reads / list views
    summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Full comparison payload — what the dashboard component needs to render
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Companies that contributed to this comparison
    commission_company_sources: Mapped[list | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_commission_comparisons_latest", "user_id", "category", "computed_at"),
    )
