import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortalRun(Base):
    __tablename__ = "portal_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    credential_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portal_credentials.id", ondelete="CASCADE"), nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    # pending | running | awaiting_otp | downloading | parsing | success | failed | timeout
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # login | otp | download | parse
    stage: Mapped[str | None] = mapped_column(String(20))

    error_message: Mapped[str | None] = mapped_column(Text)
    screenshot_path: Mapped[str | None] = mapped_column(String(255))
    downloaded_filename: Mapped[str | None] = mapped_column(String(255))
    upload_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"))

    __table_args__ = (
        Index("ix_portal_runs_user_started", "user_id", "started_at"),
        Index("ix_portal_runs_status", "status"),
        Index("ix_portal_runs_credential", "credential_id", "started_at"),
    )
