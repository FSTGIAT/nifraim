"""Two tables that back compliance + retention for the clearinghouse flow:

- `pension_audit_logs` (append-only): every status change, every poll cycle,
  every parse failure. Never deleted by retention.
- `pension_raw_payloads` (encrypted XML at rest): the literal outbound /
  inbound XML, ciphertext-only via Fernet. Retention job nulls `ciphertext`
  after `MASLAKA_RETENTION_DAYS` and sets `purged=True`; the row itself
  (size + lifecycle pointer) stays for audit.

See `.claude/plans/based-on-our-hashed-twilight.md` for the full design.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index, Integer, LargeBinary, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PensionAuditLog(Base):
    """Append-only audit trail. Never deleted by retention — compliance."""

    __tablename__ = "pension_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # No FK cascade — if an inquiry is deleted we keep the audit row pointing
    # to a dead id (the event still happened). FK is nullable for system-wide
    # events (poll cycle stats) that aren't tied to one inquiry.
    inquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pension_inquiries.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    customer_id_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # Event types are application-defined (string, not enum) so new ones can
    # be added without migrations. Examples: inquiry_created, submitted,
    # ack_received, holdings_ingested, status_changed, transport_error, expired.
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "agent" (user-initiated) | "system" (scheduler / background)
    actor: Mapped[str] = mapped_column(String(20), nullable=False, default="agent")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_pension_audit_user_created", "user_id", "created_at"),
    )


class PensionRawPayload(Base):
    """Encrypted XML payloads (Fernet, MASLAKA_ENCRYPTION_KEY). LargeBinary
    so we don't pay base64's 33% overhead on every round-trip."""

    __tablename__ = "pension_raw_payloads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pension_inquiries.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # "outbound" (we sent it) | "inbound" (clearinghouse sent it)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    interface_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Fernet ciphertext. Nulled when retention purges; original `byte_size`
    # of the plaintext is kept for audit math.
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    purged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    inquiry = relationship("PensionInquiry", back_populates="raw_payloads")
