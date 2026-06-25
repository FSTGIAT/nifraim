import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OtpInbox(Base):
    __tablename__ = "otp_inbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NULL = broadcast (no matching twilio_to_number was found at insert time)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    otp_code: Mapped[str | None] = mapped_column(String(8))

    # Company routing: which insurer this OTP belongs to, derived server-side by
    # matching the body against SmsOtpTemplate patterns at insert time. NULL when
    # no company template matched (generic/unknown) — the runner then falls back
    # to time-based matching so a missing template never blocks a run.
    # `portal_kind` is the BASE company token (e.g. "phoenix", "migdal") shared by
    # all that company's portals; `matched_company` is the Hebrew display name.
    portal_kind: Mapped[str | None] = mapped_column(String(32))
    matched_company: Mapped[str | None] = mapped_column(String(100))

    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime)
    portal_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("portal_runs.id"))

    __table_args__ = (
        Index("ix_otp_inbox_user_consumed", "user_id", "consumed_at"),
        Index("ix_otp_inbox_received", "received_at"),
    )
