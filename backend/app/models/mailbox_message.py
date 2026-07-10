import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MailboxProcessedMessage(Base):
    """Ledger of every mail message we've already handled — the dedup key.

    `external_id` is whatever uniquely identifies the message *for that path*:

        microsoft  the Graph message `id`
        google     f"{uidvalidity}:{uid}" — an IMAP UID is unique only within
                   one UIDVALIDITY epoch, so the bare uid is NOT a safe key
        other      Resend's `email_id`

    A row is written even for `parse_error`, so one permanently-bad attachment
    can't wedge the poller into retrying it forever.

    This is defence in depth, not the only guard: `ingest_file_bytes` replaces on
    (user_id, filename, file_category), so a duplicate ingest self-corrects
    rather than double-counting production.
    """

    __tablename__ = "mailbox_processed_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mailbox_configs.id", ondelete="CASCADE"), nullable=False
    )

    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Secondary dedup that survives a UIDVALIDITY reset, which invalidates every
    # stored IMAP uid but never changes the RFC 5322 Message-ID.
    message_id: Mapped[str | None] = mapped_column(String(255))

    attachment_filename: Mapped[str | None] = mapped_column(String(255))
    # "ingested" | "parse_error" | "rejected"
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    upload_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"))
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("mailbox_id", "external_id", name="uq_mailbox_messages_external"),
        Index("ix_mailbox_messages_message_id", "message_id"),
    )
