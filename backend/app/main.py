from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.services.scheduler_service import start_scheduler, stop_scheduler
    from app.services.rss_service import start_rss_polling
    from app.services.channel_service import start_email_polling
    await start_scheduler()
    await start_rss_polling()
    await start_email_polling()
    yield
    await stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def root_health():
    return {"status": "ok", "version": settings.app_version}
