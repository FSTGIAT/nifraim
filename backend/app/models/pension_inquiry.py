"""Pension clearinghouse (המסלקה הפנסיונית) inquiry lifecycle.

One row per outbound information request (בקשת מידע, Events v007) sent into
the vault. Tracks the asynchronous round-trip: feedback ack/defect, then
holdings responses (one or many, depending on whether the clearinghouse
returns an aggregate file or per-provider files). Status transitions are
validated against `ALLOWED_TRANSITIONS` in `services/maslaka/orchestration.py`
and every transition writes a `PensionAuditLog` row.

See `.claude/plans/based-on-our-hashed-twilight.md` for the full design.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Status state machine — single source of truth, imported by orchestration.advance_status().
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending":      {"submitted", "failed"},
    "submitted":    {"acknowledged", "failed", "expired"},
    "acknowledged": {"partial", "complete", "failed", "expired"},
    "partial":      {"partial", "complete", "failed", "expired"},
    "complete":     set(),
    "failed":       set(),
    "expired":      set(),
}


class PensionInquiry(Base):
    __tablename__ = "pension_inquiries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Normalized leading-zero-stripped customer ID (e.g. "50417716") so all
    # match queries can rely on `or_()` variants the way portal_service does.
    customer_id_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Lifecycle.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    interface_code: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. "events_v007"

    # Correlation id we put into outbound XML so feedback/holdings responses
    # can be matched back. Unique per row.
    request_reference: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    vault_outbound_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Defect / transport-failure detail (only populated on `failed`).
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Feedback v009 tells us how many providers are expected to respond;
    # we increment `providers_received` per holdings file ingested. When
    # equal → `complete`. Until then → `partial`.
    providers_expected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    providers_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Reverse relationships — cascade so deleting an inquiry purges holdings
    # & raw payloads. Audit logs are intentionally NOT cascaded (compliance:
    # keep the trail even if the inquiry is deleted later).
    holdings = relationship(
        "PensionHolding", back_populates="inquiry",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    raw_payloads = relationship(
        "PensionRawPayload", back_populates="inquiry",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_pension_inquiries_user_status", "user_id", "status"),
        Index("ix_pension_inquiries_user_customer", "user_id", "customer_id_number"),
    )
