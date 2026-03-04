import uuid

from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CommissionRate(Base):
    __tablename__ = "commission_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    payment_frequency: Mapped[str | None] = mapped_column(String(20))
    paid_to: Mapped[str | None] = mapped_column(String(50))
    company_email: Mapped[str | None] = mapped_column(String(100))

    user = relationship("User", back_populates="commission_rates")
