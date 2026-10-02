import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Unique public handle — the messenger's search key. Lowercase, ^[a-z0-9_]{3,32}$.
    # Unlike `full_name` (nullable, non-unique) this can identify a person unambiguously
    # without exposing their email. See services/username_service.py.
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    # Seed for the generated avatar. NULL = derive it from `username`.
    avatar_seed: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    phone_forward_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # TEST USERS ONLY: seconds added to the real clock for this user's cycle /
    # מסלקה dates (a simulated "today"). NULL for every real agent. Such users
    # are skipped by the real monthly cycle (cycle_service.run_cycle_tick).
    sim_clock_offset_s: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Made by an admin for testing. Only these can be deleted from the admin.
    is_test_user: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Bumped whenever this agent's data changes (upload ingest, cycle batch end,
    # מסלקה ingest, mail intake, rate edits). Part of every AI cache key, so a
    # cached answer can never outlive the data it was computed from.
    ai_data_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

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
