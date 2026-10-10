"""Month-by-month history of every customer's products — kept after the production file that fed it
is replaced or deleted (services/customer_history).

A new production upload replaces that company's previous one and a same-filename re-upload deletes
its records, so "what changed in my book since last month" had no history to read (2026-10-10).
One row per (agent, month, customer, company, policy, product type, track); the latest file for a
month wins. Per-user data — every query filters user_id."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CustomerProductSnapshot(Base):
    __tablename__ = "customer_product_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "period_month", "customer_id_number", "company", "policy_number",
                                       "product_type", "track", name="uq_customer_product_month"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    customer_id_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    product_type: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    product: Mapped[str | None] = mapped_column(String(200))
    policy_number: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    track: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str | None] = mapped_column(String(80))
    accumulation: Mapped[float | None] = mapped_column(Numeric(16, 2))
    premium: Mapped[float | None] = mapped_column(Numeric(14, 2))
    source_upload_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)   # no FK: outlives the file
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CustomerSnapshotUpload(Base):
    """Production uploads already captured — two files for one month overwrite each other's rows, so
    "has rows with this source_upload_id" can't tell what was processed (the sweep re-ran them daily)."""
    __tablename__ = "customer_snapshot_uploads"

    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    rows: Mapped[int] = mapped_column(default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
