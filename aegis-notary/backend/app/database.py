"""Aegis Notary — database setup.

COMPLIANCE BOUNDARY: This database must never be shared with aegis-credit
(FCRA data) or aegis-operator (FCRA data). Signing/loan data is regulated
under RESPA and state notary statutes.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
