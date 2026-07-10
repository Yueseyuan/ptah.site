"""SQLAlchemy models for the operator portal.

PublicBase models → live in the 'public' schema (operator registry).
OperatorBase models → live in op_{slug} schema (operator-private data).
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func
from app.database import PublicBase, OperatorBase


# ---------------------------------------------------------------------------
# Public schema — operator registry only
# ---------------------------------------------------------------------------
class Operator(PublicBase):
    """One row per registered operator company."""
    __tablename__ = "operators"

    id          = Column(Integer, primary_key=True)
    slug        = Column(String(32), unique=True, nullable=False, index=True)
    schema_name = Column(String(36), unique=True, nullable=False)  # op_{slug}
    name        = Column(String, nullable=False)
    email       = Column(String, nullable=False)
    plan        = Column(String, default="starter")   # starter | pro | enterprise
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Per-operator schema models (no schema in __table_args__)
# SQLAlchemy emits: SELECT * FROM staff   (no schema prefix)
# PostgreSQL resolves via SET search_path TO op_{slug}, public
# ---------------------------------------------------------------------------
class OpStaff(OperatorBase):
    """Operator's own staff members — fully isolated per schema."""
    __tablename__ = "staff"

    id              = Column(Integer, primary_key=True)
    username        = Column(String, unique=True, nullable=False)
    email           = Column(String, unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    full_name       = Column(String, default="")
    role            = Column(String, default="staff")  # owner|admin|staff|readonly
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, server_default=func.now())


class OpClient(OperatorBase):
    """A client managed by an operator. Completely isolated per schema."""
    __tablename__ = "clients"

    id         = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name  = Column(String, nullable=False)
    email      = Column(String)
    phone      = Column(String)
    address    = Column(String)
    city       = Column(String)
    state      = Column(String, default="SC")
    zip_code   = Column(String)
    dob        = Column(String)
    ssn_last4  = Column(String)
    notes      = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class OpCase(OperatorBase):
    __tablename__ = "cases"

    id          = Column(Integer, primary_key=True)
    case_number = Column(String, unique=True, nullable=False)
    client_id   = Column(Integer, nullable=False)
    status      = Column(String, default="intake")
    goal        = Column(Text)
    notes       = Column(Text)
    assigned_to = Column(String)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())


class OpCaseNote(OperatorBase):
    __tablename__ = "case_notes"

    id         = Column(Integer, primary_key=True)
    case_id    = Column(Integer, nullable=False)
    author     = Column(String, nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
