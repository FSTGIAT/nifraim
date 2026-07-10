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

    # When True, Railway does NOT execute portal runs itself — it only enqueues
    # them (status="pending"). A LOCAL worker (the agent's Israeli Windows
    # machine, see backend/local_worker.py) polls the DB, claims pending jobs and
    # runs Playwright locally from a real IL IP — sidestepping the foreign-IP
    # geo-block + Bright Data no-KYC POST block entirely. Default False keeps the
    # pre-worker behavior (Railway executes inline). See memory
    # `railway_ip_geoblocked_insurers`.
    WORKER_MODE: bool = False

    # Public (externally reachable) async DB URL the local worker connects to —
    # NOT the Railway-internal DATABASE_URL (postgres.railway.internal is only
    # reachable inside Railway). Format: postgresql+asyncpg://user:pass@host:port/db
    # Used to generate the personalized worker installer. Empty → installer
    # emits a placeholder for the operator to fill.
    WORKER_PUBLIC_DATABASE_URL: str = ""

    # Per-portal proxy override for Harel. Harel's WAF blocks the ISP zone's
    # hosting ASN (WS Telecom) at the network layer (ERR_TUNNEL_CONNECTION_FAILED),
    # but accepts a Bright Data *residential* zone IP. Point this at the
    # residential-zone proxy URL; plugins with proxy_zone_env="IL_HAREL_PROXY"
    # use it instead of IL_RESIDENTIAL_PROXY. Empty → falls back to
    # IL_RESIDENTIAL_PROXY. See memory `railway_ip_geoblocked_insurers`.
    IL_HAREL_PROXY: str = ""

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

    # ── Hachshara production-by-email intake ────────────────────────────────
    # Hachshara doesn't expose production in its agent portal — it emails a
    # `Ild_prod_*.zip`. We fetch it from the agent's mailbox, routed by the MX
    # record of their address (see services/mail_intake/detect.py).
    HACHSHARA_MAIL_ENABLED: bool = False           # gates the scheduler poll
    HACHSHARA_MAIL_POLL_INTERVAL_MINUTES: int = 15
    # Separate Fernet key from PORTAL_CRED_FERNET_KEY — blast-radius isolation.
    # A mailbox credential is far more dangerous than a portal password: it can
    # read password-reset links for every other service the agent uses.
    MAILBOX_ENCRYPTION_KEY: str = ""

    # Path A — Microsoft 365 (Exchange Online basic auth is permanently disabled,
    # so OAuth is the only door). One multi-tenant Azure app registration; free,
    # and with no CASA-style assessment (that is a Google requirement only).
    MS_OAUTH_CLIENT_ID: str = ""
    MS_OAUTH_CLIENT_SECRET: str = ""
    MS_OAUTH_REDIRECT_URI: str = ""

    # Path C — forwarding fallback. Resend already carries our outbound SMTP;
    # its inbound side parses a forwarded mail and POSTs `email.received`.
    RESEND_API_KEY: str = ""
    RESEND_INBOUND_DOMAIN: str = ""
    RESEND_WEBHOOK_SECRET: str = ""                # Svix signing secret ("whsec_…")
    # Overridable only so `scripts/simulate_hachshara_mail.py` can stand a local
    # stub in front of the attachments API and exercise the real inbound path
    # without a Resend account. Never point this anywhere but Resend in prod.
    RESEND_API_BASE: str = "https://api.resend.com"

    model_config = {"env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"), "extra": "ignore"}


settings = Settings()
