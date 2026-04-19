import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Debt(Base):
    __tablename__ = "debts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)  # gemel_hishtalmut | insurance
    customer_id_number: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product: Mapped[str | None] = mapped_column(String(100))
    policy_number: Mapped[str | None] = mapped_column(String(50))

    # Financial
    expected_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    premium: Mapped[float | None] = mapped_column(Numeric(15, 2))
    accumulation: Mapped[float | None] = mapped_column(Numeric(15, 2))

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Source tracking
    production_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"), nullable=False)
    commission_upload_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"))

    # Email tracking
    last_emailed_at: Mapped[datetime | None] = mapped_column(DateTime)
    email_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_debts_user_status", "user_id", "status"),
        Index("ix_debts_user_company", "user_id", "company_name"),
        Index("ix_debts_user_customer", "user_id", "customer_id_number"),
    )
