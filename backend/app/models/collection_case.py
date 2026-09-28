import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CollectionCase(Base):
    """One insurer the agent has unpaid commission with, for one reporting month
    (services/collection_agent.py — the "סוכן גבייה").

    Built from the latest merged comparison. The mail to the insurer is a DRAFT
    until the agent approves it; replies are followed from the agent's mailbox.

    status: draft → sent → replied → resolved   (resolved = the agent closed it)
    """

    __tablename__ = "collection_cases"
    __table_args__ = (UniqueConstraint("user_id", "company_key", "period", name="uq_collection_cases_user_company_period"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_key: Mapped[str] = mapped_column(String(100), nullable=False)   # company_stem
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)  # display
    period: Mapped[date | None] = mapped_column(Date)                        # the comparison's month
    items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [{id_number,name,product,policy,expected}]
    customers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    to_email: Mapped[str | None] = mapped_column(String(255))
    contact_name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    draft_subject: Mapped[str | None] = mapped_column(String(255))
    draft_body: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    sent_message_id: Mapped[str | None] = mapped_column(String(255))
    reminder_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    reply_message_id: Mapped[str | None] = mapped_column(String(255))
    reply_summary: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
