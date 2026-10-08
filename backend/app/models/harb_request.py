import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# done / failed / not_found are final; the rest mirror the PortalRun that serves the request.
FINAL = ("done", "failed", "not_found")
OPEN = ("pending", "running", "awaiting_otp", "downloading")


class HarbRequest(Base):
    """One customer the agent asked Nifra to fetch from הר הביטוח (harb.cma.gov.il).

    Created only by the agent's click on the proposal card (/office-agent/act kind=harb) — that
    click is the consent the site's checkbox asks for. Served by a `harbituach` PortalRun on the
    agent's local worker; one run drains every pending request of the user in one login
    (כניסה לתיק נוסף), so `portal_run_id` is set when a run picks the request up."""
    __tablename__ = "harb_requests"
    __table_args__ = (Index("ix_harb_requests_user_status", "user_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # zero-stripped
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    id_issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    portal_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portal_runs.id", ondelete="SET NULL"), nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    policies_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # what changed vs the previous fetch of this customer (store.diff_snapshots); None = first fetch
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
