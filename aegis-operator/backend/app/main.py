"""Aegis Operator Portal — FastAPI application.

Operators are fully isolated from each other via PostgreSQL schema separation.
No tenant_id column exists on any per-operator table.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, PublicBase
import app.models  # ensure models register

from app.routers.auth import router as auth_router
from app.routers.clients import router as clients_router
from app.routers.cases import router as cases_router

app = FastAPI(
    title="Aegis Operator Portal API",
    description="Per-operator schema isolation. Each operator's data is completely separated.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    # Create the public schema tables (operator registry)
    if "postgresql" in settings.DATABASE_URL:
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
            conn.commit()
    PublicBase.metadata.create_all(engine)
    print("[OPERATOR] Public schema ready. Each operator gets op_{slug} schema on registration.")


@app.get("/health")
def health():
    return {"status": "ok", "service": "aegis-operator"}


app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(cases_router)
