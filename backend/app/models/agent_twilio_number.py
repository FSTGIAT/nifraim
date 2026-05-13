"""Twilio +972 number assigned to a Nifraim agent.

One row per (user, allocation). When an agent's subscription is cancelled
or they're rotated to a new number, the old row stays for audit but
`released_at` is set; the active number for a user is the row with
`released_at IS NULL`.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentTwilioNumber(Base):
    __tablename__ = "agent_twilio_numbers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    twilio_sid: Mapped[str] = mapped_column(String(64), nullable=False)

    provisioned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_agent_twilio_numbers_user_active", "user_id", "released_at"),
        Index("ix_agent_twilio_numbers_phone", "phone_number"),
    )
