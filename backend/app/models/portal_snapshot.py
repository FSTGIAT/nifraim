import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortalSnapshot(Base):
    __tablename__ = "portal_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_link_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_portal_links.id"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    customer_id_number: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    period_label: Mapped[str] = mapped_column(String(100), default="")
    kpi_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    products_json: Mapped[list] = mapped_column(JSON, nullable=False)
    company_breakdown_json: Mapped[list] = mapped_column(JSON, nullable=False)
    has_changes: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    changes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_portal_snapshots_link_date", "portal_link_id", "snapshot_date"),
    )
