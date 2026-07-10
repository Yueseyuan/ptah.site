import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Aegis Admin Console"

    # Admin console has its OWN secret — completely separate from
    # consumer portal and operator portal JWT secrets.
    ADMIN_JWT_SECRET: str = "admin-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 240  # shorter session for the internal tool

    # Credentials for the admin console itself (not shared with any other service)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""  # bcrypt hash; set ADMIN_PASSWORD to auto-generate on startup

    # Connection strings for the three systems this console can reach
    CONSUMER_DB_URL:  str = ""  # aegis-credit PostgreSQL URL
    OPERATOR_DB_URL:  str = ""  # aegis-operator PostgreSQL URL (public schema for registry)
    NOTARY_DB_URL:    str = ""  # aegis-notary PostgreSQL URL


def _env(k: str, default: str = "") -> str:
    return os.environ.get(k, default)


settings = Settings()

for attr, env in [
    ("ADMIN_JWT_SECRET",    "ADMIN_JWT_SECRET"),
    ("ADMIN_USERNAME",      "ADMIN_USERNAME"),
    ("ADMIN_PASSWORD_HASH", "ADMIN_PASSWORD_HASH"),
    ("CONSUMER_DB_URL",     "CONSUMER_DB_URL"),
    ("OPERATOR_DB_URL",     "OPERATOR_DB_URL"),
    ("NOTARY_DB_URL",       "NOTARY_DB_URL"),
]:
    if not getattr(settings, attr, "").strip():
        v = _env(env)
        if v:
            setattr(settings, attr, v)
