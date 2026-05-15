import uuid
from datetime import date

from sqlalchemy import String, Numeric, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CommissionRate(Base):
    __tablename__ = "commission_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    product: Mapped[str | None] = mapped_column(String(200))
    rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    payment_frequency: Mapped[str | None] = mapped_column(String(20))
    paid_to: Mapped[str | None] = mapped_column(String(50))
    company_email: Mapped[str | None] = mapped_column(String(100))
    # Agreement validity window. NULL for legacy rows / when the AI didn't
    # detect dates. The reconciliation step picks the rate whose window
    # contains the policy's sign_date — when no row matches by year, falls
    # back to whatever is on file.
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    user = relationship("User", back_populates="commission_rates")
