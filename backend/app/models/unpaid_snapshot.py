import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, DateTime, Integer, Numeric, ForeignKey, Index, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UnpaidSnapshot(Base):
    """Per-(user, commission_upload, company) snapshot of unpaid customers.

    Created automatically inside `/api/comparison/compare-with-production` so
    the trend chart and the per-company monitor have stable historical data
    to query without re-running compute_comparison() every time.

    The (user_id, commission_upload_id, company_name) unique constraint
    combined with the existing replace-on-upload semantics for FileUpload
    means re-uploading the same file UPDATEs the row instead of inserting
    a new one — no MoM duplicates.
    """

    __tablename__ = "unpaid_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    commission_upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_uploads.id", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    period_label: Mapped[str] = mapped_column(String(20), nullable=False)
    unpaid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    unpaid_customers_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_sent_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="unpaid_snapshots")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "commission_upload_id", "company_name",
            name="uq_unpaid_snapshots_user_upload_company",
        ),
        Index("ix_unpaid_snapshots_user_period", "user_id", "period_label"),
        Index("ix_unpaid_snapshots_user_company_period", "user_id", "company_name", "period_label"),
    )
