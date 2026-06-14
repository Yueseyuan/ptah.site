import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import engine, Base
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all DB tables on startup
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

    # Ensure document output directory exists
    Path("generated_docs").mkdir(exist_ok=True)

    # Start automation scheduler (skip if unavailable)
    try:
        from app.services.automation import start_scheduler, stop_scheduler
        start_scheduler()
        scheduler_started = True
    except Exception as e:
        logger.warning("Scheduler not started: %s", e)
        scheduler_started = False

    yield

    if scheduler_started:
        try:
            stop_scheduler()
        except Exception:
            pass
    logger.info("CA Engine shutdown complete")


app = FastAPI(
    title="Cruel & Associates CA Engine",
    description=(
        "Administrative services platform for Cruel & Associates. "
        "Provides client intake, document generation, e-signature, billing, "
        "and appointment management across all 6 service divisions."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://cruelandassociates.site",
        "https://www.cruelandassociates.site",
        "https://ptahconsultants.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from app.routers.auth import router as auth_router
from app.routers.clients import router as clients_router
from app.routers.cases import router as cases_router
from app.routers.documents import router as documents_router
from app.routers.appointments import router as appointments_router
from app.routers.invoices import router as invoices_router
from app.routers.notary import router as notary_router
from app.routers.admin import router as admin_router

app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(cases_router)
app.include_router(documents_router)
app.include_router(appointments_router)
app.include_router(invoices_router)
app.include_router(notary_router)
app.include_router(admin_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "company": settings.COMPANY_NAME,
        "version": "1.0.0",
    }


@app.get("/")
def root():
    return {
        "message": "Cruel & Associates CA Engine API",
        "docs": "/api/docs",
        "health": "/api/health",
    }
