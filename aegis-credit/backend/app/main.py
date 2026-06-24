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
from app.routers.personal_info import router as personal_info_router
from app.routers.legal import router as legal_router
from app.routers.legal_updates import router as legal_updates_router
from app.routers.collection_review import router as collection_review_router
from app.routers.analytics import router as analytics_router
from app.routers.search import router as search_router
from app.routers.ai_consult import router as ai_consult_router
from app.routers.portal import router as portal_router
from app.routers.billing import router as billing_router


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


def run_seeds():
    """Seed reference data (legal knowledge engine)."""
    try:
        from app.database import SessionLocal
        from app.services.legal_seed import seed_federal_laws, seed_agency_guidance, seed_case_law, seed_state_laws
        db = SessionLocal()
        try:
            seed_federal_laws(db)
            seed_agency_guidance(db)
            seed_case_law(db)
            seed_state_laws(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[WARNING] Seed functions failed ({e})")


# Skip migrations during test runs (tests call create_all directly)
if not os.environ.get("TESTING"):
    import threading
    def _startup_tasks():
        run_migrations()
        run_seeds()
    threading.Thread(target=_startup_tasks, daemon=True).start()

# Startup diagnostics — visible in Railway deploy logs
print(f"[ENV-RAW] ANTHROPIC_API_KEY in os.environ: {'YES' if os.environ.get('ANTHROPIC_API_KEY') else 'NO'}")
print(f"[ENV-RAW] STRIPE_SECRET_KEY in os.environ: {'YES' if os.environ.get('STRIPE_SECRET_KEY') else 'NO'}")
print(f"[ENV-RAW] DATABASE_URL in os.environ: {os.environ.get('DATABASE_URL', 'NOT SET')[:40]}")
print(f"[CONFIG] DATABASE_URL: {settings.DATABASE_URL[:35]}...")
print(f"[CONFIG] ANTHROPIC_API_KEY: {'SET (' + str(len(settings.ANTHROPIC_API_KEY)) + ' chars)' if settings.ANTHROPIC_API_KEY else 'MISSING — reports will fail'}")
print(f"[CONFIG] STRIPE_SECRET_KEY: {'SET' if settings.STRIPE_SECRET_KEY else 'MISSING — billing will fail'}")
print(f"[CONFIG] JWT_SECRET_KEY: {'SET (custom)' if settings.JWT_SECRET_KEY not in ('change-me-in-production-use-env-var', '') else 'MISSING — using insecure default'}")

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

_extra_origins = [o.strip() for o in settings.EXTRA_ORIGINS.split(",") if o.strip()]
_allowed_origins = _extra_origins if _extra_origins else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"http://localhost(:\d+)?|https://(www\.)?cruelandassociates\.site",
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
app.include_router(personal_info_router)
app.include_router(legal_router)
app.include_router(legal_updates_router)
app.include_router(collection_review_router)
app.include_router(analytics_router)
app.include_router(search_router)
app.include_router(ai_consult_router)
app.include_router(portal_router)
app.include_router(billing_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "anthropic_key": "SET" if settings.ANTHROPIC_API_KEY else "MISSING",
        "stripe_key": "SET" if settings.STRIPE_SECRET_KEY else "MISSING",
        "database": settings.DATABASE_URL[:30] + "...",
    }


@app.get("/api/env-check")
def env_check():
    """Temporary diagnostic — shows which Railway env vars reached the container."""
    import os
    keys_to_check = [
        "ANTHROPIC_API_KEY", "STRIPE_SECRET_KEY", "DATABASE_URL",
        "JWT_SECRET_KEY", "RAILWAY_ENVIRONMENT", "RAILWAY_SERVICE_NAME",
        "RAILWAY_PROJECT_ID", "PORT",
    ]
    result = {}
    for k in keys_to_check:
        val = os.environ.get(k)
        if val:
            # Show first 6 chars only for secrets
            if k in ("ANTHROPIC_API_KEY", "STRIPE_SECRET_KEY", "JWT_SECRET_KEY"):
                result[k] = f"SET — starts with: {val[:6]}..."
            else:
                result[k] = val[:60]
        else:
            result[k] = "NOT SET"
    return result
