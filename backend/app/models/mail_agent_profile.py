"""How the agent writes — the AI mail agent drafts in this voice.

One row per user, filled by the first-run "writing style" workshop and
editable later. Server-side (not localStorage): the drafting job runs on a
schedule with no browser around. `examples` are the agent's own past replies
and outlive the mail-body retention window, so they are stored ENCRYPTED
(MAILBOX_ENCRYPTION_KEY) like the bodies they came from.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TONES = ("formal", "warm", "short")
ADDRESS_FORMS = ("plural", "female", "male", "name")
WRITER_FORMS = ("male", "female", "we")     # the agent's own first person


class MailAgentProfile(Base):
    __tablename__ = "mail_agent_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    address_form: Mapped[str | None] = mapped_column(String(16), nullable=True)
    writer_form: Mapped[str | None] = mapped_column(String(16), nullable=True)
    greeting: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closing: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    insurer_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    never_say: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_examples: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON list[str], encrypted
    learn_opt_in: Mapped[bool | None] = mapped_column(Boolean, nullable=True)      # None = never asked
    learned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
