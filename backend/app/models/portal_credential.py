import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortalCredential(Base):
    __tablename__ = "portal_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # phoenix | migdal | clal | menora | altshuler | hachshara | excellence | mor | ayalon | clal_health
    portal_kind: Mapped[str] = mapped_column(String(32), nullable=False)

    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)

    twilio_to_number: Mapped[str | None] = mapped_column(String(20))
    # The Twilio number we've successfully written into THIS portal's "contact phone"
    # field. NULL = portal still routes OTPs to the agent's personal phone.
    contact_phone_synced_to: Mapped[str | None] = mapped_column(String(20))
    # 'twilio' (default — Twilio webhook delivers OTP) | 'phone_forward' (user's own
    # phone forwards SMS to /phone-forward/{token}) | 'manual' (user types into modal)
    otp_method: Mapped[str] = mapped_column(String(20), nullable=False, server_default="twilio")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 'manual' (no auto-run), 'daily', 'weekly', 'monthly'
    schedule_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    category_hint: Mapped[str | None] = mapped_column(String(64))

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_run_status: Mapped[str | None] = mapped_column(String(20))
    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "portal_kind", name="uq_portal_credentials_user_kind"),
        Index("ix_portal_credentials_schedule", "schedule_kind", "is_active"),
    )
