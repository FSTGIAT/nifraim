from pydantic_settings import BaseSettings
from pydantic import model_validator
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_SYNC: str = ""
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

    # 019SMS
    SMS_019_USERNAME: str = ""
    SMS_019_PASSWORD: str = ""
    SMS_019_COMPANY_ID: str = ""

    model_config = {"env_file": str(Path(__file__).resolve().parent.parent.parent / ".env")}

    @model_validator(mode="after")
    def derive_urls(self):
        # Railway/Heroku may provide postgres:// — normalize to postgresql://
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        # Auto-derive DATABASE_URL_SYNC from DATABASE_URL if not explicitly set
        if not self.DATABASE_URL_SYNC:
            self.DATABASE_URL_SYNC = self.DATABASE_URL.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
        # Auto-convert DATABASE_URL to asyncpg if it's a plain postgresql:// URL
        if self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self


settings = Settings()
