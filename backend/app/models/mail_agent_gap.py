"""What the AI mail agent was missing when it drafted a reply.

Append-only: one row per "missing" item per draft (poll or טיוטה חדשה).
`mail_items.draft_warnings` holds only the latest draft and is overwritten on
regeneration; this ledger keeps every gap so we can see which questions agents
get that the system can't answer yet — the backlog for new agent tools.
Not shown in the UI. No mail body is stored here, only the model's own
one-line description of what was missing.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MailAgentGap(Base):
    __tablename__ = "mail_agent_gaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    mail_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mail_items.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    missing: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sender_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)      # insurer / customer / other
    from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linked_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)                  # snapshot of the AI summary
    draft_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
