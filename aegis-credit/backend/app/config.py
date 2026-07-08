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
    DATA_DIR: str = ""           # set to /app/data in Railway for persistent volume
    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "generated_reports"
    EVIDENCE_DIR: str = "evidence_files"
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
    ADMIN_NOTIFICATION_EMAIL: str = "yueseyuan.cruel@cruelandassociates.site"
    ADMIN_RESET_SECRET: str = ""   # set in Railway to enable /api/auth/reset-admin
    # ── External AI Services ──────────────────────────────────────────────────
    # Dify (langgenius/dify) — workflow + chatflow orchestration
    DIFY_API_KEY: str = ""
    DIFY_BASE_URL: str = "https://api.dify.ai/v1"
    DIFY_RECEPTIONIST_TOKEN: str = ""   # public embed token for the chatbot widget
    # OpenHands (All-Hands-AI) — autonomous coding/document agent
    OPENHANDS_API_KEY: str = ""
    OPENHANDS_BASE_URL: str = "https://app.all-hands.dev/api/v1"
    # LibreChat — multi-model staff chat UI
    LIBRECHAT_URL: str = ""
    LIBRECHAT_API_KEY: str = ""
    # OpenJarvis — voice-first AI sidecar (run: jarvis serve --port 8765)
    OPENJARVIS_URL: str = "http://localhost:8765"


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
if not settings.ADMIN_RESET_SECRET.strip():
    settings.ADMIN_RESET_SECRET = _env("ADMIN_RESET_SECRET").strip()
if settings.ADMIN_RESET_SECRET:
    print("[CONFIG] ADMIN_RESET_SECRET: SET")

# Secondary fallback: if the primary variable names are being truncated/blocked by Railway
# (observed when variable value arrives as <50 chars despite full key being set),
# read from alternate variable names ANTHROPIC_KEY and STRIPE_SK instead.
if len(settings.ANTHROPIC_API_KEY.strip()) < 100:
    _alt_ant = _env("ANTHROPIC_KEY").strip()
    if len(_alt_ant) >= 100:
        settings.ANTHROPIC_API_KEY = _alt_ant
        print("[CONFIG] ANTHROPIC_API_KEY loaded from ANTHROPIC_KEY (alternate name)")

if len(settings.STRIPE_SECRET_KEY.strip()) < 50:
    _alt_stripe = _env("STRIPE_SK").strip()
    if len(_alt_stripe) >= 50:
        settings.STRIPE_SECRET_KEY = _alt_stripe
        print("[CONFIG] STRIPE_SECRET_KEY loaded from STRIPE_SK (alternate name)")
if settings.DATABASE_URL.strip() == "sqlite:///./aegis.db":
    db_from_env = _env("DATABASE_URL").strip()
    if db_from_env:
        settings.DATABASE_URL = db_from_env
if settings.JWT_SECRET_KEY.strip() in ("", "change-me-in-production-use-env-var"):
    jwt_from_env = _env("JWT_SECRET_KEY").strip()
    if jwt_from_env:
        settings.JWT_SECRET_KEY = jwt_from_env

# If PGPASSWORD (or POSTGRES_PASSWORD) is available, rebuild the DATABASE_URL
# with the correct password + proper URL encoding. This avoids manual copy-paste errors.
# Add ONE variable reference in the Railway backend service:
#   PGPASSWORD = ${{Postgres.PGPASSWORD}}
_pg_pw = _env("PGPASSWORD") or _env("POSTGRES_PASSWORD")
if _pg_pw and settings.DATABASE_URL.startswith("postgresql"):
    try:
        from urllib.parse import urlparse, urlunparse, quote_plus as _qp
        _p = urlparse(settings.DATABASE_URL)
        _host = _p.hostname or "postgres.railway.internal"
        _port = _p.port or 5432
        _user = _p.username or "postgres"
        _db   = (_p.path or "/railway").lstrip("/") or "railway"
        settings.DATABASE_URL = f"postgresql://{_user}:{_qp(_pg_pw)}@{_host}:{_port}/{_db}"
    except Exception:
        pass

# Build DATABASE_URL entirely from PG* vars if PGHOST is also provided.
_pghost = _env("PGHOST")
if _pghost and _pg_pw:
    from urllib.parse import quote_plus as _qp2
    _pguser = _env("PGUSER") or _env("POSTGRES_USER") or "postgres"
    _pgport = _env("PGPORT") or "5432"
    _pgdb   = _env("PGDATABASE") or _env("POSTGRES_DB") or "railway"
    settings.DATABASE_URL = f"postgresql://{_pguser}:{_qp2(_pg_pw)}@{_pghost}:{_pgport}/{_pgdb}"


# If a persistent volume is mounted, root all file storage under it.
# Railway: create a volume at /app/data and set DATA_DIR=/app/data in Variables.
# Local dev: leave DATA_DIR empty and files go to relative paths (uploads/, etc.).
if settings.DATA_DIR.strip():
    _d = settings.DATA_DIR.strip().rstrip("/")
    settings.UPLOAD_DIR   = f"{_d}/uploads"
    settings.REPORTS_DIR  = f"{_d}/reports"
    settings.EVIDENCE_DIR = f"{_d}/evidence"
    print(f"[CONFIG] DATA_DIR={_d} — all file storage routed to persistent volume")


def _validate_settings(s):
    if s.JWT_SECRET_KEY in ("", "change-me", "dev-secret", "secret", "change-me-in-production-use-env-var"):
        warnings.warn("SECRET_KEY is using an insecure default. Set a strong SECRET_KEY in production.")

_validate_settings(settings)
