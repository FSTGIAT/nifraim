import uuid

from sqlalchemy import String, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VolumeCommissionRate(Base):
    __tablename__ = "volume_commission_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    nifraim_rate: Mapped[float | None] = mapped_column(Numeric(10, 6))
    volume_rate_per_million: Mapped[float | None] = mapped_column(Numeric(15, 2))
    pension_accumulation: Mapped[float | None] = mapped_column(Numeric(15, 2))
    changed_percent: Mapped[float | None] = mapped_column(Numeric(10, 6))
    conversion_to_annuity: Mapped[float | None] = mapped_column(Numeric(15, 2))
    payment_frequency: Mapped[str | None] = mapped_column(String(20))
    paid_to: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", back_populates="volume_commission_rates")
