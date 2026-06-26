from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Cardcom payment gateway
    CARDCOM_TERMINAL: str = ""
    CARDCOM_API_NAME: str = ""
    CARDCOM_API_PASSWORD: str = ""
    CARDCOM_SUCCESS_URL: str = "http://localhost:5173/signup?step=success"
    CARDCOM_FAILURE_URL: str = "http://localhost:5173/signup?step=payment"
    CARDCOM_WEBHOOK_URL: str = "http://localhost:8000/api/subscription/webhook"
    CARDCOM_CSS_URL: str = ""

    # 019SMS
    SMS_019_USERNAME: str = ""
    SMS_019_PASSWORD: str = ""
    SMS_019_COMPANY_ID: str = ""

    # Anthropic AI
    ANTHROPIC_API_KEY: str = ""

    # SMTP Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""

    # Twilio (inbound SMS for portal automation OTP)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_PUBLIC_WEBHOOK_BASE: str = "http://localhost:8000"  # ngrok/public URL for prod
    TWILIO_PROVISION_COUNTRY: str = "IL"

    # Android APK download — secret used by CI to push new builds
    ANDROID_APK_SECRET: str = ""

    # Symmetric encryption key for portal credentials (Fernet).
    # Generate once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    PORTAL_CRED_FERNET_KEY: str = ""

    # Israeli residential/ISP proxy for portal automation. Israeli insurer WAFs
    # geo-block Railway's foreign datacenter IP (harel/menora/phoenix time out at
    # the first page.goto), so the runner routes geo-blocked portals' browser
    # contexts through this proxy. Format: a full proxy URL
    # "http://user:pass@host:port" (or "http://host:port"). Empty → direct
    # connection (no proxy), the pre-proxy behavior. See memory
    # `railway_ip_geoblocked_insurers`.
    IL_RESIDENTIAL_PROXY: str = ""

    # Pension clearinghouse (המסלקה הפנסיונית / ממשק אחיד) — asynchronous SFTP vault exchange.
    # See .claude/plans/based-on-our-hashed-twilight.md for the design.
    MASLAKA_TRANSPORT: str = "local"               # "local" (file-system mock) | "sftp" (real vault)
    MASLAKA_ENABLED: bool = False                  # gate scheduler poll + retention jobs
    # Separate Fernet key from PORTAL_CRED_FERNET_KEY — blast-radius isolation.
    MASLAKA_ENCRYPTION_KEY: str = ""
    # Local-filesystem mock vault dirs (used when MASLAKA_TRANSPORT="local").
    MASLAKA_LOCAL_OUTBOX: str = "./maslaka_vault/outbox"
    MASLAKA_LOCAL_INBOX: str = "./maslaka_vault/inbox"
    MASLAKA_LOCAL_ARCHIVE: str = "./maslaka_vault/archive"
    # Real SFTP vault settings (used when MASLAKA_TRANSPORT="sftp").
    MASLAKA_SFTP_HOST: str = ""
    MASLAKA_SFTP_PORT: int = 22
    MASLAKA_SFTP_USERNAME: str = ""
    MASLAKA_SFTP_PASSWORD: str = ""
    MASLAKA_SFTP_KEY_PATH: str = ""
    MASLAKA_SFTP_OUTBOX: str = "/outbox"
    MASLAKA_SFTP_INBOX: str = "/inbox"
    MASLAKA_SFTP_ARCHIVE: str = "/archive"
    # Our identity in outbound XML (filled in once we have a clearinghouse account).
    MASLAKA_AGENT_NUMBER: str = ""
    MASLAKA_AGENT_ID: str = ""
    # Lifecycle + retention knobs.
    MASLAKA_RETENTION_DAYS: int = 90
    MASLAKA_INQUIRY_TIMEOUT_DAYS: int = 7
    MASLAKA_POLL_INTERVAL_MINUTES: int = 15

    model_config = {"env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"), "extra": "ignore"}


settings = Settings()
