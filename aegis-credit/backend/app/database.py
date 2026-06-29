import os
import re
from urllib.parse import quote_plus, urlparse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings


def _resolve_db_url() -> str:
    """
    Resolve the correct DB URL from every possible source, in priority order.
    This makes the app robust against wrong/placeholder DATABASE_URL values.
    """
    pghost = os.environ.get("PGHOST", "").strip()
    pgpw   = (os.environ.get("PGPASSWORD", "") or os.environ.get("POSTGRES_PASSWORD", "")).strip()

    # Priority 1: Build from individual PG* vars (most explicit, set when user adds PGHOST reference)
    if pghost and pgpw:
        user   = (os.environ.get("PGUSER") or os.environ.get("POSTGRES_USER") or "postgres").strip()
        port   = (os.environ.get("PGPORT") or "5432").strip()
        dbname = (os.environ.get("PGDATABASE") or os.environ.get("POSTGRES_DB") or "railway").strip()
        url    = f"postgresql://{user}:{quote_plus(pgpw)}@{pghost}:{port}/{dbname}"
        print(f"[DB] URL built from PG* vars — host={pghost} user={user} db={dbname}")
        return url

    # Priority 2: settings.DATABASE_URL (may already be patched by config.py if PGPASSWORD was set)
    base_url = settings.DATABASE_URL

    # Priority 3: If we have PGPASSWORD but no PGHOST, substitute password into existing URL
    if pgpw and base_url.startswith("postgresql"):
        try:
            p      = urlparse(base_url)
            host   = p.hostname or "postgres.railway.internal"
            port   = p.port or 5432
            user   = p.username or "postgres"
            dbname = (p.path or "/railway").lstrip("/") or "railway"
            url    = f"postgresql://{user}:{quote_plus(pgpw)}@{host}:{port}/{dbname}"
            print(f"[DB] URL patched with PGPASSWORD — host={host}")
            return url
        except Exception as exc:
            print(f"[DB] PGPASSWORD patch failed: {exc}")

    return base_url


_url = _resolve_db_url()
_safe = re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", _url)
print(f"[DB] Final URL: {_safe[:80]}")

if _url.startswith("sqlite"):
    engine = create_engine(_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        _url,
        connect_args={"connect_timeout": 10},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
