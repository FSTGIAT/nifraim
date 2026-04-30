import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UnpaidDismissal(Base):
    """Customer-level "remove from unpaid" marks.

    When the user clicks × on a customer row in the unpaid monitor (or removes
    a whole company row), we record (user, company, customer_id) here. The
    aggregate `current_by_company` query and the drill-in customer list filter
    these out — the underlying snapshot data is left intact so the trend chart
    keeps its history.
    """

    __tablename__ = "unpaid_dismissals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id_number: Mapped[str] = mapped_column(String(40), nullable=False)
    dismissed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="unpaid_dismissals")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "company_name", "customer_id_number",
            name="uq_unpaid_dismissals_user_company_customer",
        ),
        Index("ix_unpaid_dismissals_user_company", "user_id", "company_name"),
    )
