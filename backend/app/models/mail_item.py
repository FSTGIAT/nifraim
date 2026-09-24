"""One incoming email from a watched sender, as the AI mail agent sees it.

The body is stored ENCRYPTED (MAILBOX_ENCRYPTION_KEY) and dropped after the
retention window; metadata and the AI's summary stay. Status flow:
    new → needs_reply → drafted → sent
                    ↘ done / dismissed
Nothing is ever sent without the agent pressing send (`sent_by_user`).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

NEW = "new"
NEEDS_REPLY = "needs_reply"
DRAFTED = "drafted"
SENT = "sent"
DONE = "done"
DISMISSED = "dismissed"
STATUSES = (NEW, NEEDS_REPLY, DRAFTED, SENT, DONE, DISMISSED)
OPEN_STATUSES = (NEW, NEEDS_REPLY, DRAFTED)


class MailItem(Base):
    __tablename__ = "mail_items"
    __table_args__ = (UniqueConstraint("user_id", "internet_message_id", name="uq_mail_item_msgid"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    watch_sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mail_watch_senders.id", ondelete="SET NULL"), nullable=True,
    )

    # ── the message ──
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)      # IMAP uid / Graph id
    internet_message_id: Mapped[str] = mapped_column(String(512), nullable=False)
    in_reply_to: Mapped[str | None] = mapped_column(String(512), nullable=True)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(998), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    encrypted_body: Mapped[str | None] = mapped_column(Text, nullable=True)   # own text + quote, encrypted
    attachments: Mapped[list | None] = mapped_column(JSON, nullable=True)      # [{name, size, content_type}]

    # ── what the AI made of it ──
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    suggested_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ai_skipped_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)   # e.g. "daily_cap"
    linked_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
    linked_customer_id_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── the reply ──
    draft_subject: Mapped[str | None] = mapped_column(String(998), nullable=True)
    draft_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)   # unsupported ₪ amounts etc.
    draft_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    draft_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_message_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    imported_upload_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=NEW, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
