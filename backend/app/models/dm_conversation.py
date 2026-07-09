import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DmConversation(Base):
    """One row per PAIR of users who have exchanged at least one direct message.

    **Ordered-pair invariant:** ``user_a_id`` always holds the numerically smaller
    UUID and ``user_b_id`` the larger, enforced by a unique index on the pair. That
    makes (a,b) and (b,a) resolve to the same row without a separate hash column —
    always build the tuple through ``ordered_pair()`` below, never by hand.

    The ``last_message_*`` and ``*_unread_count`` columns are DENORMALIZED on
    purpose: they let the contacts list render in one flat query instead of a
    COUNT + a "latest message" subquery per contact.
    """

    __tablename__ = "dm_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_message_preview: Mapped[str | None] = mapped_column(String(140), nullable=True)
    last_sender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    a_unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    b_unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    a_last_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    b_last_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # "Delete conversation" is per-side: the row is shared, so dropping it would
    # erase the other person's history. Messages at or before MY cleared_at are
    # hidden from ME only. A newer message revives the thread naturally.
    a_cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    b_cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_dm_conv_pair", "user_a_id", "user_b_id", unique=True),
    )


def ordered_pair(u1: uuid.UUID, u2: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Canonical (user_a_id, user_b_id) for a conversation between two users."""
    return (u1, u2) if str(u1) < str(u2) else (u2, u1)
