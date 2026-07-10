"""Aegis Admin Console — internal support tool.

Auth: completely separate JWT secret. No token from the consumer portal,
operator portal, or notary app is valid here. Admin credentials are set via
ADMIN_USERNAME + ADMIN_PASSWORD_HASH environment variables — never via
an 'admin mode' toggle on any customer-facing app.

This service is NOT deployed publicly. It should run on an internal port
(not exposed to the internet) or behind VPN/IP allowlist.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings

app = FastAPI(
    title="Aegis Admin Console",
    description="Internal support tool. Not publicly deployed.",
    version="1.0.0",
    docs_url="/docs",   # restrict at the infra level, not here
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3100", "http://127.0.0.1:3100"],  # admin UI only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/admin/login")


# ---------------------------------------------------------------------------
# Admin auth — its own secret, its own token
# ---------------------------------------------------------------------------
def _issue_token(username: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "role": "admin_console", "exp": exp},
        settings.ADMIN_JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def _require_admin(token: str = Depends(oauth2)) -> str:
    try:
        payload = jwt.decode(token, settings.ADMIN_JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("role") != "admin_console":
            raise HTTPException(403, "Not an admin console token")
        return payload["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired admin token")


@app.post("/admin/login")
def admin_login(form: OAuth2PasswordRequestForm = Depends()):
    """Login to the admin console. Credentials are separate from all other services."""
    if form.username != settings.ADMIN_USERNAME:
        raise HTTPException(401, "Invalid credentials")
    if not settings.ADMIN_PASSWORD_HASH:
        raise HTTPException(503, "ADMIN_PASSWORD_HASH not set. Run: python -c \"from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('your-password'))\"")
    if not _pwd.verify(form.password, settings.ADMIN_PASSWORD_HASH):
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": _issue_token(form.username), "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Cross-system read endpoints — each creates its own DB connection
# ---------------------------------------------------------------------------
def _consumer_db():
    if not settings.CONSUMER_DB_URL:
        raise HTTPException(503, "CONSUMER_DB_URL not configured")
    engine = create_engine(settings.CONSUMER_DB_URL, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def _operator_db(schema: Optional[str] = None):
    if not settings.OPERATOR_DB_URL:
        raise HTTPException(503, "OPERATOR_DB_URL not configured")
    engine = create_engine(settings.OPERATOR_DB_URL, pool_pre_ping=True)
    session = sessionmaker(bind=engine)()
    if schema:
        session.execute(text(f"SET LOCAL search_path TO {schema}, public"))
    return session


def _notary_db():
    if not settings.NOTARY_DB_URL:
        raise HTTPException(503, "NOTARY_DB_URL not configured")
    engine = create_engine(settings.NOTARY_DB_URL, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


# Consumer portal — support views
@app.get("/admin/consumer/clients")
def consumer_clients(q: Optional[str] = None, _: str = Depends(_require_admin)):
    db = _consumer_db()
    try:
        sql = "SELECT id, first_name, last_name, email, phone, state, created_at FROM aegis_clients"
        if q:
            sql += f" WHERE lower(first_name || ' ' || last_name) LIKE lower('%{q}%')"
        sql += " ORDER BY id DESC LIMIT 100"
        rows = db.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


@app.get("/admin/consumer/cases")
def consumer_cases(client_id: Optional[int] = None, _: str = Depends(_require_admin)):
    db = _consumer_db()
    try:
        sql = "SELECT * FROM aegis_cases"
        if client_id:
            sql += f" WHERE client_id = {client_id}"
        sql += " ORDER BY id DESC LIMIT 100"
        rows = db.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


# Operator system — list operators + drill into any schema
@app.get("/admin/operators")
def list_operators(_: str = Depends(_require_admin)):
    db = _operator_db()
    try:
        rows = db.execute(text(
            "SELECT id, slug, schema_name, name, email, plan, is_active, created_at FROM operators ORDER BY id"
        )).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


@app.get("/admin/operators/{slug}/clients")
def operator_clients(slug: str, _: str = Depends(_require_admin)):
    schema = f"op_{slug.replace('-', '_')}"
    db = _operator_db(schema)
    try:
        rows = db.execute(text(
            "SELECT id, first_name, last_name, email, phone, state, created_at FROM clients ORDER BY id DESC LIMIT 100"
        )).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


# Notary system — support view
@app.get("/admin/notary/jobs")
def notary_jobs(status: Optional[str] = None, _: str = Depends(_require_admin)):
    db = _notary_db()
    try:
        sql = "SELECT * FROM signing_orders"
        if status:
            sql += f" WHERE status = '{status}'"
        sql += " ORDER BY id DESC LIMIT 100"
        rows = db.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "aegis-admin",
        "consumer_db": bool(settings.CONSUMER_DB_URL),
        "operator_db": bool(settings.OPERATOR_DB_URL),
        "notary_db":   bool(settings.NOTARY_DB_URL),
    }
