import uuid
from datetime import datetime

from sqlalchemy import Text, DateTime, ForeignKey, BigInteger, Identity, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DmMessage(Base):
    """A single direct message. Body is PLAIN TEXT — never markdown, never HTML.

    ``seq`` is the cursor for both paging (``before``) and polling (``since``).
    It is a Postgres identity column rather than ``created_at`` because UUIDv4
    carries no time order and two ``created_at`` values can tie at microsecond
    precision under concurrent inserts, which would make ``WHERE created_at >
    :since`` silently skip or double-deliver a message.
    """

    __tablename__ = "dm_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False, unique=True, index=True)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dm_conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Denormalized from the conversation so the poll query ("new messages for me")
    # is a single indexed scan with no join.
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_dm_msg_conv_seq", "conversation_id", "seq"),
        Index("ix_dm_msg_recipient_seq", "recipient_id", "seq"),
        Index("ix_dm_msg_sender_created", "sender_id", "created_at"),  # rate-limit count
    )
