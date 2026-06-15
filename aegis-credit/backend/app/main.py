from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.config import settings

import app.models  # ensure all models are registered before create_all

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

Base.metadata.create_all(bind=engine)

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


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}
