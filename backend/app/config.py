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

    # Symmetric encryption key for portal credentials (Fernet).
    # Generate once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    PORTAL_CRED_FERNET_KEY: str = ""

    model_config = {"env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"), "extra": "ignore"}


settings = Settings()
