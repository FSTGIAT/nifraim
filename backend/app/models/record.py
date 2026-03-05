import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, Numeric, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClientRecord(Base):
    __tablename__ = "client_records"
    __table_args__ = (
        Index("ix_client_records_user_id", "user_id"),
        Index("ix_client_records_upload_id", "upload_id"),
        Index("ix_client_records_id_number", "id_number"),
        Index("ix_client_records_receiving_company", "receiving_company"),
        Index("ix_client_records_reconciliation_status", "reconciliation_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id", ondelete="CASCADE"), nullable=False)

    # Client info
    id_number: Mapped[str | None] = mapped_column(String(20))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    sign_date: Mapped[date | None] = mapped_column(Date)
    recruitment_type: Mapped[str | None] = mapped_column(String(50))
    product: Mapped[str | None] = mapped_column(String(100))
    fund_policy_number: Mapped[str | None] = mapped_column(String(50))
    employment_status: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[str | None] = mapped_column(String(20))
    receiving_company: Mapped[str | None] = mapped_column(String(100))
    track: Mapped[str | None] = mapped_column(String(100))
    transferring_fund: Mapped[str | None] = mapped_column(String(100))
    transferring_body: Mapped[str | None] = mapped_column(String(100))

    # Production file fields
    product_type: Mapped[str | None] = mapped_column(String(100))
    total_premium: Mapped[float | None] = mapped_column(Numeric(15, 2))
    accumulation: Mapped[float | None] = mapped_column(Numeric(15, 2))
    product_status: Mapped[str | None] = mapped_column(String(20))

    # Nifraim (commission report) fields
    fund_type: Mapped[str | None] = mapped_column(String(100))
    fund_number: Mapped[str | None] = mapped_column(String(50))
    month_end_balance: Mapped[float | None] = mapped_column(Numeric(15, 2))
    annual_commission_pct: Mapped[float | None] = mapped_column(Numeric(10, 6))
    monthly_commission_pct: Mapped[float | None] = mapped_column(Numeric(10, 6))
    commission_before_fee: Mapped[float | None] = mapped_column(Numeric(15, 2))

    # Amounts — agent tracking
    expected_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    actual_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    expected_raw: Mapped[str | None] = mapped_column(Text)
    actual_raw: Mapped[str | None] = mapped_column(Text)
    amount_difference: Mapped[float | None] = mapped_column(Numeric(15, 2))

    # Dates & misc
    transfer_date: Mapped[date | None] = mapped_column(Date)
    management_fee: Mapped[float | None] = mapped_column(Numeric(10, 6))
    lead_source: Mapped[str | None] = mapped_column(String(100))
    agent_number: Mapped[str | None] = mapped_column(String(20))
    rights_assignment_date: Mapped[date | None] = mapped_column(Date)
    general_notes: Mapped[str | None] = mapped_column(Text)

    # Hachshara / shared commission fields
    management_fee_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    processing_date: Mapped[str | None] = mapped_column(String(20))

    # Commission — company reports
    balance: Mapped[float | None] = mapped_column(Numeric(15, 2))
    commission_paid: Mapped[float | None] = mapped_column(Numeric(15, 2))
    commission_expected: Mapped[float | None] = mapped_column(Numeric(15, 2))

    # Client contact & employer (from production file)
    client_phone: Mapped[str | None] = mapped_column(String(30))
    client_email: Mapped[str | None] = mapped_column(String(100))
    employer_name: Mapped[str | None] = mapped_column(String(100))
    employer_id: Mapped[str | None] = mapped_column(String(20))

    # Reconciliation
    reconciliation_status: Mapped[str | None] = mapped_column(String(20))

    user = relationship("User", back_populates="records")
    upload = relationship("FileUpload", back_populates="records")
