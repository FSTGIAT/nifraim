import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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
