import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MailboxConfig(Base):
    """One row per agent: how we pull the emailed Hachshara production zip.

    Which columns matter depends on `mail_host`, which is resolved from the MX
    record of `email_address` (services/mail_intake/detect.py) — never asked of
    the user, because with custom domains the mail *client* they name tells you
    nothing about who hosts the mailbox.

        microsoft  Exchange Online. Basic auth is permanently disabled and app
                   passwords blocked with it, so OAuth is the only door. We keep
                   a refresh token; the access token is never persisted.
        google     App password over IMAP (read-only EXAMINE). The OAuth
                   alternative needs Google's annually-revalidated CASA audit.
        other      No credential at all — the agent forwards the mail to
                   `forward_token`'s address and Resend POSTs it to us.

    Credential asymmetry is deliberate and worth preserving: `other` holds
    nothing, `microsoft` holds a revocable token, `google` holds a password that
    grants full mailbox access. Prefer the weaker grant when a user is indifferent.
    """

    __tablename__ = "mailbox_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    # "microsoft" | "google" | "other" — MX-detected, user-overridable.
    mail_host: Mapped[str] = mapped_column(String(16), nullable=False, server_default="other")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── microsoft ──────────────────────────────────────────────────────────
    # Fernet(MAILBOX_ENCRYPTION_KEY). Access tokens are re-minted per poll and
    # never stored.
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text)
    oauth_tenant_id: Mapped[str | None] = mapped_column(String(64))
    # Graph delta cursor — cheaper and more correct than a receivedDateTime
    # high-water mark (which double-delivers on ties and skips on clock skew).
    delta_link: Mapped[str | None] = mapped_column(Text)

    # ── google ─────────────────────────────────────────────────────────────
    encrypted_password: Mapped[str | None] = mapped_column(Text)   # 16-char app password
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False, server_default="imap.gmail.com")
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, server_default="993")
    folder: Mapped[str] = mapped_column(String(128), nullable=False, server_default="INBOX")
    # An IMAP UID is unique only within one (mailbox, UIDVALIDITY). When the
    # server resets UIDVALIDITY the cursor is meaningless and must restart.
    uidvalidity: Mapped[int | None] = mapped_column(Integer)
    last_seen_uid: Mapped[int | None] = mapped_column(Integer)

    # ── other (forwarding) ─────────────────────────────────────────────────
    # Mirrors users.phone_forward_token: the token in the recipient address is
    # what resolves the tenant. Never trust the sender.
    forward_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    # ── status ─────────────────────────────────────────────────────────────
    # `last_received_at` is load-bearing in the UI: every path fails SILENTLY
    # (revoked consent, rotated app password, wrong forwarding rule) and a stale
    # production file looks exactly like a quiet month.
    last_received_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_status: Mapped[str | None] = mapped_column(String(32))
    # A stable ERROR CODE, never a provider message. imaplib error strings can
    # echo the failed LOGIN line — password included — and AADSTS codes mean
    # nothing to an insurance agent. The frontend maps code -> Hebrew copy.
    last_error: Mapped[str | None] = mapped_column(String(64))
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_mailbox_configs_user"),
        Index("ix_mailbox_configs_active", "is_active", "mail_host"),
    )
