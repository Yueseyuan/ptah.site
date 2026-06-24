from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

_url = settings.DATABASE_URL
print(f"[DB] Connecting to: {_url[:30]}...")

if _url.startswith("sqlite"):
    _kwargs = {"check_same_thread": False}
    engine = create_engine(_url, connect_args=_kwargs)
else:
    # PostgreSQL: set connect_timeout so a bad DATABASE_URL fails fast instead of hanging
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
