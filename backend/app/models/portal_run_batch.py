import uuid
from datetime import datetime, date

from sqlalchemy import String, DateTime, Date, Text, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortalRunBatch(Base):
    """A single "run all portals" operation.

    Groups the per-credential ``PortalRun`` children (via ``PortalRun.batch_id``)
    so the orchestrator can, after every site has downloaded, aggregate all
    production files into ONE merged production upload and all נפרעים files into
    ONE merged commission upload. Durable (survives a uvicorn --reload) and
    pollable by the frontend.
    """

    __tablename__ = "portal_run_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # pending | running | success | partial | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    total: Mapped[int] = mapped_column(Integer, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)

    # The child run currently logging in / awaiting OTP — lets the UI point the
    # existing PortalOtpModal at the right run during a sequential batch.
    current_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    # The two merged outputs produced at batch end.
    merged_upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_uploads.id", ondelete="SET NULL"), nullable=True
    )
    merged_commission_upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_uploads.id", ondelete="SET NULL"), nullable=True
    )

    # Reporting month the merged files describe (first-of-month).
    period_month: Mapped[date | None] = mapped_column(Date, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_portal_run_batches_user_started", "user_id", "started_at"),
        Index("ix_portal_run_batches_status", "status"),
    )
