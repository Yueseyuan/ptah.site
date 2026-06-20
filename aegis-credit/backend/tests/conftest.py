"""
Shared pytest fixtures.

Sets TESTING=1 and DATABASE_URL before any app import so that:
  - run_migrations() is skipped (main.py checks TESTING env var)
  - SQLAlchemy engine points at a dedicated test database
"""
import os
import pytest

os.environ["TESTING"] = "1"
os.environ["DEV_NO_AUTH"] = "True"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_aegis.db")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app

_test_engine = create_engine(
    os.environ["DATABASE_URL"],
    connect_args={"check_same_thread": False},
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

# Create all tables once per test session
Base.metadata.create_all(bind=_test_engine)


def _override_db():
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = _override_db


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    path = os.environ.get("DATABASE_URL", "").replace("sqlite:///", "").lstrip("./")
    if path and os.path.exists(path):
        os.remove(path)
