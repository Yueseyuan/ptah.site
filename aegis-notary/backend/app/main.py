"""Aegis Notary — FastAPI application.

COMPLIANCE BOUNDARY:
  This service handles signing/loan data regulated under RESPA and state
  notary statutes. It must NEVER share a database, schema, or connection
  pool with aegis-credit (FCRA data) or aegis-operator (FCRA data).

  Any integration with credit/operator systems must go through API contracts.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
import app.models  # ensure models register

from app.routers.auth import router as auth_router
from app.routers.orders import router as orders_router
from app.routers.profile import router as profile_router

app = FastAPI(
    title="Aegis Notary API",
    description="Signing order management. RESPA/notary statute data only.",
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
    Base.metadata.create_all(engine)
    print("[NOTARY] Database tables ready.")


@app.get("/health")
def health():
    return {"status": "ok", "service": "aegis-notary"}


app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(profile_router)
