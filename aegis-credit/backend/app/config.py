import os
import warnings
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Aegis Credit Investigator"
    DEV_NO_AUTH: bool = False
    DATABASE_URL: str = "sqlite:///./aegis.db"
    ANTHROPIC_API_KEY: str = ""
    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "generated_reports"
    JWT_SECRET_KEY: str = "change-me-in-production-use-env-var"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    EXTRA_ORIGINS: str = ""
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = "pk_live_51Tk9NxFLqRbXTdYOYumLBIhxFsIG3d6i5AVAQBRbEju7xMPQI1JY28szDAlv2QWxz4yTh2u2Iq1Zrwv1hMHuR1kk00XcYyvS7S"
    STRIPE_PRICE_ID: str = "price_1TkA6ZFLqRbXTdYOP1kRMvT5"
    STRIPE_WEBHOOK_SECRET: str = ""
    PORTAL_BASE_URL: str = "https://cruelandassociates.site"
    # Email / SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@cruelandassociates.site"


# Fall back to direct os.environ reads for critical keys if pydantic-settings
# fails to load them (observed with certain Railway + pydantic-settings v2 combos).
def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


settings = Settings()

# Patch: if pydantic-settings returned the default for a critical key but os.environ has it, use os.environ.
if not settings.ANTHROPIC_API_KEY.strip():
    settings.ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY").strip()
if not settings.STRIPE_SECRET_KEY.strip():
    settings.STRIPE_SECRET_KEY = _env("STRIPE_SECRET_KEY").strip()
if settings.DATABASE_URL.strip() == "sqlite:///./aegis.db":
    db_from_env = _env("DATABASE_URL").strip()
    if db_from_env:
        settings.DATABASE_URL = db_from_env
if settings.JWT_SECRET_KEY.strip() in ("", "change-me-in-production-use-env-var"):
    jwt_from_env = _env("JWT_SECRET_KEY").strip()
    if jwt_from_env:
        settings.JWT_SECRET_KEY = jwt_from_env

# Build DATABASE_URL from individual PG* vars when they're available.
# This avoids copy-paste errors with special characters in passwords.
# Set these in Railway backend service as variable references:
#   PGHOST     = ${{Postgres.PGHOST}}
#   PGPORT     = ${{Postgres.PGPORT}}
#   PGUSER     = ${{Postgres.PGUSER}}
#   PGPASSWORD = ${{Postgres.PGPASSWORD}}
#   PGDATABASE = ${{Postgres.PGDATABASE}}
_pghost = _env("PGHOST")
_pgpassword = _env("PGPASSWORD") or _env("POSTGRES_PASSWORD")
if _pghost and _pgpassword:
    from urllib.parse import quote_plus as _qp
    _pguser = _env("PGUSER") or _env("POSTGRES_USER") or "postgres"
    _pgport = _env("PGPORT") or "5432"
    _pgdb = _env("PGDATABASE") or _env("POSTGRES_DB") or "railway"
    settings.DATABASE_URL = f"postgresql://{_pguser}:{_qp(_pgpassword)}@{_pghost}:{_pgport}/{_pgdb}"


def _validate_settings(s):
    if s.JWT_SECRET_KEY in ("", "change-me", "dev-secret", "secret", "change-me-in-production-use-env-var"):
        warnings.warn("SECRET_KEY is using an insecure default. Set a strong SECRET_KEY in production.")

_validate_settings(settings)
