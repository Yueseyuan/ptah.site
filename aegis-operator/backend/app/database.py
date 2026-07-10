"""Schema-per-operator database isolation.

Every operator is provisioned their own PostgreSQL schema: op_{slug}.
No tenant_id column exists on any per-operator table. A query bug that
forgets a WHERE clause can only read one operator's rows — there are no
other operators' rows in that schema.

Session routing:
  get_public_db()           → search_path = public (operator registry)
  get_operator_db(slug)     → search_path = op_{slug}, public
"""
import re
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.config import settings

# ---------------------------------------------------------------------------
# Slug validation (prevents SQL injection via schema name)
# ---------------------------------------------------------------------------
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


def _safe_schema(slug: str) -> str:
    clean = slug.lower().replace("-", "_")
    if not _SLUG_RE.match(clean):
        raise ValueError(f"Invalid operator slug: {slug!r}")
    return f"{settings.OPERATOR_SCHEMA_PREFIX}_{clean}"


# ---------------------------------------------------------------------------
# Engine + session factory
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# Declarative bases — keep public and per-operator models strictly separate
# ---------------------------------------------------------------------------
class PublicBase(DeclarativeBase):
    """Models that live in the public schema (operator registry, audit log)."""


class OperatorBase(DeclarativeBase):
    """Models that live in the operator's private schema.

    Never access these through a public-schema session. Always use
    get_operator_db() so search_path is set first.
    """


# ---------------------------------------------------------------------------
# FastAPI dependency: public schema
# ---------------------------------------------------------------------------
def get_public_db():
    db = SessionLocal()
    try:
        if "postgresql" in settings.DATABASE_URL:
            db.execute(text("SET search_path TO public"))
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# FastAPI dependency: operator-scoped schema
# Call via Depends(operator_db_for("acme")) or inject via middleware.
# ---------------------------------------------------------------------------
def get_operator_db(slug: str):
    """Return a FastAPI dependency that routes to op_{slug} schema."""
    schema = _safe_schema(slug)

    def _dep():
        db = SessionLocal()
        try:
            if "postgresql" in settings.DATABASE_URL:
                db.execute(text(f"SET LOCAL search_path TO {schema}, public"))
            yield db
        finally:
            db.close()

    return _dep


# ---------------------------------------------------------------------------
# Schema provisioning — called once when a new operator registers
# ---------------------------------------------------------------------------
OPERATOR_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS staff (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'staff',   -- owner | admin | staff | readonly
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT DEFAULT 'SC',
    zip_code TEXT,
    dob TEXT,
    ssn_last4 TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cases (
    id SERIAL PRIMARY KEY,
    case_number TEXT NOT NULL UNIQUE,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'intake',
    goal TEXT,
    notes TEXT,
    assigned_to TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_notes (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def provision_operator_schema(slug: str, db: Session) -> str:
    """Create the schema and all tables for a new operator. Idempotent."""
    schema = _safe_schema(slug)
    db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    db.execute(text(f"SET LOCAL search_path TO {schema}, public"))
    for stmt in OPERATOR_TABLE_DDL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            db.execute(text(stmt))
    db.commit()
    return schema
