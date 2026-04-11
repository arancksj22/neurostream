from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.redis_client import get_job_tracker
from app.services.pipeline import build_processing_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.job_tracker = get_job_tracker()
    app.state.processing_service = build_processing_service(settings)
    yield


app = FastAPI(title="NeuroStream MS2", version="0.1.0", lifespan=lifespan)
app.include_router(router)

