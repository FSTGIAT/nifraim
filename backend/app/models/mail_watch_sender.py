"""Senders the agent chose for the AI mail agent to handle.

The AI reads ONLY mail from these addresses (or `@domain`s). Nothing is watched
until the agent adds it — suggestions come from their insurer contacts and
their customers' emails, but adding one is always the agent's own click.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

KINDS = ("insurer", "customer", "other")


class MailWatchSender(Base):
    __tablename__ = "mail_watch_senders"
    __table_args__ = (UniqueConstraint("user_id", "address", name="uq_mail_watch_sender"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    # Lower-cased email address, or "@domain.co.il" to match a whole domain.
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="other")
    company_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def matches(self, sender: str) -> bool:
        sender = (sender or "").strip().lower()
        if self.address.startswith("@"):
            return sender.endswith(self.address)
        return sender == self.address
