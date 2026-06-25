"""Per-product holdings rows returned by the clearinghouse (אחזקות v009).

Field names deliberately mirror `ClientRecord` (`receiving_company`,
`product`, `product_type`, `fund_policy_number`, `track`, `accumulation`,
`total_premium`) so the reconciliation in `services/maslaka/orchestration.py`
can match holdings to existing production rows by id_number + fund_policy_number
without column-name translation.

See `.claude/plans/based-on-our-hashed-twilight.md` for the full design.
"""

import uuid
from datetime import datetime, date

from sqlalchemy import String, DateTime, Date, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PensionHolding(Base):
    __tablename__ = "pension_holdings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pension_inquiries.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Customer scope — duplicated from inquiry for fast filter queries.
    customer_id_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Provider (יצרן) identity. `receiving_company` is the Hebrew label and
    # MUST match values already used in `ClientRecord.receiving_company` so
    # the company breakdown UI joins cleanly. `provider_code` is the
    # clearinghouse's numeric code (from code_tables.py).
    receiving_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Product details — same names/sizes as ClientRecord for reuse.
    product: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fund_policy_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    track: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Financial figures (Numeric for precise reconciliation against production).
    accumulation: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_premium: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    management_fee_deposit: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    management_fee_balance: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    expected_pension: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # Free-form coverage block — JSON-encoded list of {coverage_name, sum_assured,
    # premium, ...} so we don't lose Holdings v009's rich rider structure.
    insurance_coverage: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Valuation / status date from the response.
    status_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Reconciliation against existing production ClientRecord.
    # SET NULL on delete: if a production row is deleted later, we keep the
    # holding visible (just unmatched) so the user can see "this used to match".
    matched_client_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_records.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    # "matched" | "clearinghouse_only" | "production_only"
    match_status: Mapped[str] = mapped_column(String(20), nullable=False, default="clearinghouse_only")

    # Back-pointer to the raw XML so we can prove provenance + replay parsing.
    raw_payload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pension_raw_payloads.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    inquiry = relationship("PensionInquiry", back_populates="holdings")

    __table_args__ = (
        # Most common query: "show me this customer's holdings".
        Index("ix_pension_holdings_user_customer", "user_id", "customer_id_number"),
    )
