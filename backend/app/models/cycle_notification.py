import uuid
from datetime import datetime, date

from sqlalchemy import String, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CycleNotification(Base):
    """One agent-facing event of the monthly cycle (מחזור).

    Written by the server-side cycle tick (never the worker — the worker has no
    SMTP), emailed once, and shown once in the workspace's CycleNotificationModal.
    UNIQUE (user, kind, period) makes every emit idempotent across hourly ticks.

    kinds: worker_waiting · upload_production · cycle_failed · comparison_ready
    """

    __tablename__ = "cycle_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint("user_id", "kind", "period", name="uq_cycle_notifications_user_kind_period"),
    )
