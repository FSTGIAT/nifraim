import uuid
from datetime import datetime, date

from sqlalchemy import String, DateTime, Date, Text, Integer, ForeignKey, Index, text
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

    # 'cycle' = queued by the monthly cycle job (the ONLY trigger for agents);
    # 'admin' = support override. A pending cycle batch waits for the worker
    # indefinitely — it is never orphan-reaped (see cycle_service).
    trigger: Mapped[str] = mapped_column(String(10), nullable=False, default="admin", server_default="admin")
    # The reporting month (first-of-month, M-1) this cycle batch downloads.
    cycle_period: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        Index("ix_portal_run_batches_user_started", "user_id", "started_at"),
        Index("ix_portal_run_batches_status", "status"),
        Index(
            "uq_portal_run_batches_user_cycle",
            "user_id", "cycle_period",
            unique=True,
            postgresql_where=text("trigger = 'cycle'"),
        ),
    )
