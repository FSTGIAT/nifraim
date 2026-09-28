import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgreementRequest(Base):
    """One "please send me my commission agreement" email, per (agent, company).

    Sent FROM the agent's own mailbox (services/agreement_requests.py). The
    follow-up poller matches the insurer's reply by In-Reply-To/References to
    `sent_message_id` (or by the contact address after `sent_at`), downloads
    the attached PDF and loads it exactly like a manual agreement-shelf upload.

    status: sent → replied (answered, no PDF) | imported (agreement loaded) | failed
    """

    __tablename__ = "agreement_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_key: Mapped[str] = mapped_column(String(100), nullable=False)   # company_stem
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)  # display
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String(255))
    sent_message_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="sent")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    reply_message_id: Mapped[str | None] = mapped_column(String(255))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_documents.id", ondelete="SET NULL"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "company_key", name="uq_agreement_requests_user_company"),
    )
