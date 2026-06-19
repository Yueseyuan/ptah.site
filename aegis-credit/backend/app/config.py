import warnings
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Aegis Credit Investigator"
    DEV_NO_AUTH: bool = True
    DATABASE_URL: str = "sqlite:///./aegis.db"
    ANTHROPIC_API_KEY: str = ""
    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "generated_reports"
    JWT_SECRET_KEY: str = "change-me-in-production-use-env-var"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    # Comma-separated extra allowed CORS origins (e.g. https://cruelandassociates.site)
    EXTRA_ORIGINS: str = ""

    class Config:
        env_file = ".env"


settings = Settings()


def _validate_settings(s):
    if s.JWT_SECRET_KEY in ("", "change-me", "dev-secret", "secret", "change-me-in-production-use-env-var"):
        warnings.warn("SECRET_KEY is using an insecure default. Set a strong SECRET_KEY in production.")

_validate_settings(settings)
