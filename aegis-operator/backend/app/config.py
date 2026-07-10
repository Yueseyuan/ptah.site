import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Aegis Operator Portal"
    DATABASE_URL: str = "sqlite:///./operator.db"
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    ANTHROPIC_API_KEY: str = ""

    # Each operator gets its own PostgreSQL schema: op_{slug}
    # The public schema holds only the operator registry itself.
    OPERATOR_SCHEMA_PREFIX: str = "op"


def _env(k: str, default: str = "") -> str:
    return os.environ.get(k, default)


settings = Settings()

for attr, env in [
    ("DATABASE_URL",     "DATABASE_URL"),
    ("JWT_SECRET_KEY",   "JWT_SECRET_KEY"),
    ("ANTHROPIC_API_KEY","ANTHROPIC_API_KEY"),
]:
    if not getattr(settings, attr).strip() or getattr(settings, attr) == "change-me-in-production":
        v = _env(env)
        if v:
            setattr(settings, attr, v)
