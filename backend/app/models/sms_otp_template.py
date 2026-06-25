import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SmsOtpTemplate(Base):
    """A pattern that tells the Android SMS forwarder which incoming SMS are
    insurance-portal OTPs worth forwarding.

    GLOBAL (no user_id): the OTP wording a company sends is the same for every
    agent, so templates are shared. `is_block=True` rows are the privacy lever —
    they DROP a code-bearing SMS even though fail-open would otherwise forward it
    (e.g. personal bank 2FA).
    """

    __tablename__ = "sms_otp_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    portal_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Case-insensitive regex matched against (sender + " " + body).
    pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    # The real SMS this pattern was built from — reference / test fixture.
    example: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_block: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
