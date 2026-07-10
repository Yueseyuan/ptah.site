"""Notary data models — RESPA/state notary statute scope only.

No FCRA data lives here. Integration with credit/operator systems
goes through API contracts, not these tables.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class NotaryProfile(Base):
    __tablename__ = "notary_profiles"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    license_number = Column(String(100), nullable=True)
    license_state = Column(String(2), nullable=True)
    license_expires = Column(String(20), nullable=True)   # ISO date string
    phone = Column(String(30), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())


class SigningOrder(Base):
    __tablename__ = "signing_orders"

    id = Column(Integer, primary_key=True, index=True)
    # Loan/signing metadata (RESPA scope — no FCRA credit data)
    loan_number = Column(String(100), nullable=True, index=True)
    borrower_name = Column(String(200), nullable=False)
    borrower_phone = Column(String(30), nullable=True)
    borrower_email = Column(String(255), nullable=True)
    property_address = Column(String(500), nullable=False)
    closing_date = Column(String(30), nullable=True)       # ISO datetime string
    signing_type = Column(String(50), default="purchase")  # purchase|refinance|heloc|reverse
    status = Column(String(30), default="pending")         # pending|assigned|completed|cancelled
    notes = Column(Text, nullable=True)
    # Assigned notary (NULL = not yet assigned)
    notary_id = Column(Integer, ForeignKey("notary_profiles.id"), nullable=True)
    fee = Column(Float, nullable=True)
    # Reference back to originating system via opaque external_id — no direct DB link
    external_ref = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SigningDocument(Base):
    __tablename__ = "signing_documents"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("signing_orders.id"), nullable=False, index=True)
    document_type = Column(String(100), nullable=False)    # deed_of_trust|note|disclosure|etc
    filename = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=True)       # S3/object storage key
    status = Column(String(30), default="pending")         # pending|signed|rejected
    created_at = Column(DateTime, server_default=func.now())
