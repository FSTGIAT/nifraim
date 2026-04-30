import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Role values are stored as plain strings (not a Postgres ENUM) so we can
# evolve roles without writing a migration each time. Allowed values:
#   - "agent"             — regular agent (existing behavior; default)
#   - "agency_admin"      — owner/admin of an agency house (e.g. ד.נ.ר)
#   - "agency_accountant" — חשב עמלות, agency-scoped read-only super user
#   - "site_admin"        — Nifraim platform admin (mirrors is_admin=True)
AGENCY_ROLES = {"agency_admin", "agency_accountant"}


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="agent", server_default="agent")
    agency_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=True, index=True
    )
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    uploads = relationship("FileUpload", back_populates="user", cascade="all, delete-orphan")
    records = relationship("ClientRecord", back_populates="user", cascade="all, delete-orphan")
    commission_rates = relationship("CommissionRate", back_populates="user", cascade="all, delete-orphan")
    recruits = relationship("Recruit", back_populates="user", cascade="all, delete-orphan")
    paying_companies = relationship("PayingCompany", back_populates="user", cascade="all, delete-orphan")
    company_contacts = relationship("CompanyContact", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    portal_links = relationship("CustomerPortalLink", back_populates="user", cascade="all, delete-orphan")
    volume_commission_rates = relationship("VolumeCommissionRate", back_populates="user", cascade="all, delete-orphan")
    volume_bonus_payments = relationship("VolumeBonusPayment", back_populates="user", cascade="all, delete-orphan")
    unpaid_snapshots = relationship("UnpaidSnapshot", back_populates="user", cascade="all, delete-orphan")
    unpaid_dismissals = relationship("UnpaidDismissal", back_populates="user", cascade="all, delete-orphan")
    agency = relationship("Agency", back_populates="members", foreign_keys=[agency_id])
