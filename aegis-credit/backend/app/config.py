import warnings
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Aegis Credit Investigator"
    DEV_NO_AUTH: bool = False
    DATABASE_URL: str = "sqlite:///./aegis.db"
    ANTHROPIC_API_KEY: str = ""
    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "generated_reports"
    JWT_SECRET_KEY: str = "change-me-in-production-use-env-var"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    # Comma-separated extra allowed CORS origins (e.g. https://cruelandassociates.site)
    EXTRA_ORIGINS: str = ""
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = "pk_live_51Tk9NxFLqRbXTdYOYumLBIhxFsIG3d6i5AVAQBRbEju7xMPQI1JY28szDAlv2QWxz4yTh2u2Iq1Zrwv1hMHuR1kk00XcYyvS7S"
    STRIPE_PRICE_ID: str = "price_1TkA6ZFLqRbXTdYOP1kRMvT5"
    STRIPE_WEBHOOK_SECRET: str = ""
    PORTAL_BASE_URL: str = "https://cruelandassociates.site"

    class Config:
        env_file = ".env"


settings = Settings()


def _validate_settings(s):
    if s.JWT_SECRET_KEY in ("", "change-me", "dev-secret", "secret", "change-me-in-production-use-env-var"):
        warnings.warn("SECRET_KEY is using an insecure default. Set a strong SECRET_KEY in production.")

_validate_settings(settings)
