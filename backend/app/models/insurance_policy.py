import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InsurancePolicy(Base):
    """One coverage line of a customer's הר הביטוח portfolio (one row of the site's Excel).

    A snapshot: a new fetch for the same customer REPLACES that customer's rows. Never mixed into
    production/נפרעים (client_records) — הר הביטוח lists every insurer's policies, not the agent's book."""
    __tablename__ = "insurance_policies"
    __table_args__ = (Index("ix_insurance_policies_user_customer", "user_id", "customer_id_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id_number: Mapped[str] = mapped_column(String(20), nullable=False)
    harb_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("harb_requests.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="harb")
    domain: Mapped[str | None] = mapped_column(String(80), nullable=True)        # תחום - כללי / בריאות… / חיים…
    main_branch: Mapped[str | None] = mapped_column(String(120), nullable=True)  # ענף ראשי
    sub_branch: Mapped[str | None] = mapped_column(String(160), nullable=True)   # ענף (משני)
    product_type: Mapped[str | None] = mapped_column(String(160), nullable=True)  # סוג מוצר
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # "מתחדש"
    premium: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    premium_type: Mapped[str | None] = mapped_column(String(300), nullable=True)   # שנתית / חודשית / …
    policy_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    plan_class: Mapped[str | None] = mapped_column(String(40), nullable=True)      # אישי / קבוצתי
    produced_at: Mapped[date | None] = mapped_column(Date, nullable=True)          # "הופק… בתאריך"
    # a re-fetch supersedes (False) instead of deleting — the history behind "what changed"
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
