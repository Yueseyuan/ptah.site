import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

import app.models  # ensure all models are registered

from app.routers.clients import router as clients_router
from app.routers.cases import router as cases_router
from app.routers.reports import router as reports_router
from app.routers.tradelines import router as tradelines_router
from app.routers.comparison import router as comparison_router
from app.routers.findings import router as findings_router
from app.routers.evidence import router as evidence_router
from app.routers.court_records import router as court_records_router
from app.routers.timeline import router as timeline_router
from app.routers.strategy import router as strategy_router
from app.routers.report_generator import router as report_generator_router
from app.routers.disputes import router as disputes_router
from app.routers.outcomes import router as outcomes_router
from app.routers.learning import router as learning_router
from app.routers.metro2 import router as metro2_router
from app.routers.auth import router as auth_router
from app.routers.audit import router as audit_router
from app.routers.organizations import router as organizations_router
from app.routers.inquiries import router as inquiries_router


def run_migrations():
    """Run alembic upgrade head on startup."""
    try:
        from alembic.config import Config
        from alembic import command
        # Resolve alembic.ini relative to this file's package root (backend/)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        # Fallback: use SQLAlchemy create_all so the app still starts
        print(f"[WARNING] Alembic migration failed ({e}), falling back to create_all")
        from app.database import engine, Base
        Base.metadata.create_all(bind=engine)


# Skip migrations during test runs (tests call create_all directly)
if not os.environ.get("TESTING"):
    run_migrations()

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients_router)
app.include_router(cases_router)
app.include_router(reports_router)
app.include_router(tradelines_router)
app.include_router(comparison_router)
app.include_router(findings_router)
app.include_router(evidence_router)
app.include_router(court_records_router)
app.include_router(timeline_router)
app.include_router(strategy_router)
app.include_router(report_generator_router)
app.include_router(disputes_router)
app.include_router(outcomes_router)
app.include_router(learning_router)
app.include_router(metro2_router)
app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(organizations_router)
app.include_router(inquiries_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}
