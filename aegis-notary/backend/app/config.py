"""Aegis Notary — fully separate service, separate database.

COMPLIANCE BOUNDARY:
  This service handles signing/loan data regulated under RESPA and state
  notary statutes. It must NEVER share a database, schema, or connection
  pool with aegis-credit (FCRA data) or aegis-operator (FCRA data).

  Any integration between this service and the credit/operator systems must
  go through defined API contracts, never direct DB access.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Aegis Notary"
    # Dedicated DB — never share with credit or operator systems
    DATABASE_URL: str = "sqlite:///./notary.db"
    JWT_SECRET_KEY: str = "notary-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    NOTARY_SCHEMA_PREFIX: str = "notary"


def _env(k: str, d: str = "") -> str:
    return os.environ.get(k, d)


settings = Settings()
for attr, env in [
    ("DATABASE_URL",   "NOTARY_DATABASE_URL"),
    ("JWT_SECRET_KEY", "NOTARY_JWT_SECRET_KEY"),
]:
    if not getattr(settings, attr, "").strip():
        v = _env(env)
        if v:
            setattr(settings, attr, v)
